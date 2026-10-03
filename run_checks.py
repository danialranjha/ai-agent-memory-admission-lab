"""Record normal suite and require both deliberate regressions to be detected."""
import json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def suite(mutation=None):
    env=dict(os.environ);env.pop('EXPERIMENT_MUTATION',None)
    if mutation:env['EXPERIMENT_MUTATION']=mutation
    p=subprocess.run([sys.executable,'-m','unittest','-v','test_experiment'],cwd=ROOT,env=env,capture_output=True,text=True)
    output=p.stdout+p.stderr
    tests=int(re.search(r'Ran (\d+) tests?',output).group(1))
    failing=re.search(r'FAILED \(failures=(\d+)\)',output)
    return dict(mutation=mutation,tests=tests,exit_code=p.returncode,failures=int(failing.group(1)) if failing else 0),output
if __name__=='__main__':
    normal,log=suite();print(log)
    assert normal['exit_code']==0 and normal['tests']==12
    mutants=[]
    for mutation in ['restore_stop','accept_overflow']:
        result,_=suite(mutation)
        assert result['exit_code']!=0 and result['failures']>0,result
        mutants.append(result)
    (ROOT/'artifacts').mkdir(exist_ok=True)
    (ROOT/'artifacts/tests.json').write_text(json.dumps(normal,indent=2)+'\n')
    (ROOT/'artifacts/mutations.json').write_text(json.dumps(mutants,indent=2)+'\n')
    print(json.dumps(mutants))
