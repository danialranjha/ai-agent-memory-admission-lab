"""Compile actual source slices; compare one early-exit change on fixed recall lists."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
METHODS = ('stop', 'continue')

def fixtures():
    large='L'*48
    def case(name, records, budget=8, **opts):
        return dict(name=name,records=[dict(id=i,content=c) for i,c in records],budget=budget,
                    header=opts.get('header'),footer=opts.get('footer'),template=opts.get('template','{content}'))
    a=('a','KEEP-A');b=('b','KEEP-B');big=('large',large)
    return [
        case('oversized_first',[big,a,b]),
        case('oversized_middle',[a,big,b]),
        case('oversized_last',[a,b,big]),
        case('ordinary_twin',[a,b]),
        case('exact_fill',[a,b],4),
        case('no_remaining_room',[a,b],2),
        case('all_oversized',[big,('large2','Z'*52)]),
        case('empty',[]),
        case('header_consumes_room',[big,a,b],8,header='H'*16),
        case('footer_is_preserved',[big,a,b],8,footer='END'),
        case('oversized_header',[a],2,header='H'*16),
        case('newline_estimate_limit',[('a','ABCD'),('b','EFGH')],2),
        case('empty_record_limit',[('a',''),('b',''),('c',''),('d',''),('e','')],1),
        case('unicode_cost',[('large','界'*16),('a','猫'),('b','🙂')],4),
        case('default_template',[big,a,b],24,header='### Relevant Agent Memories:',template='- [{kind}] {content} (score: {score:.2})'),
    ]

def verify_source():
    source=json.loads((ROOT/'vendor/source.json').read_text())
    for name, digest in source['files'].items():
        assert hashlib.sha256((ROOT/'vendor'/name).read_bytes()).hexdigest()==digest, name
    return source

def build(directory, mutation=None):
    verify_source()
    body=(ROOT/'vendor/formatter_body.rs').read_text()
    needle='if current_token_estimate + line_tokens > options.max_tokens {\n                break;'
    assert body.count(needle)==1
    altered=body.replace(needle,needle.replace('break;','continue;'))
    if mutation=='restore_stop': altered=body
    elif mutation=='accept_overflow': altered=altered.replace('current_token_estimate + line_tokens > options.max_tokens','false')
    elif mutation is not None: raise ValueError(mutation)
    code=(ROOT/'harness.rs').read_text()+'\n'+(ROOT/'vendor/estimate.rs').read_text()
    for name, b in [('stop',body),('continue_scan',altered)]:
        code+='\nfn '+name+'(response: Response, options: Options) -> Result<String,String> {\n'+b+'}\n'
    src=Path(directory)/'main.rs';src.write_text(code)
    binary=Path(directory)/'formatter'
    subprocess.run(['rustc','--edition=2021',str(src),'-o',str(binary)],check=True,capture_output=True,text=True)
    return binary

def execute(binary,cases):
    lines=[]
    enc=lambda s:s.encode().hex()
    for c in cases:
        if c['budget']<=0: raise ValueError('positive budget required by upstream option validation')
        for method in METHODS:
            lines.append('\t'.join([method,str(c['budget']),enc(c['header']) if c['header'] is not None else '-',enc(c['footer']) if c['footer'] is not None else '-',enc(c['template']),','.join(enc(r['content']) for r in c['records']) if c['records'] else '-']))
    p=subprocess.run([str(binary)],input='\n'.join(lines)+'\n',capture_output=True,text=True,check=True)
    outputs=p.stdout.splitlines();assert len(outputs)==len(lines)
    rows=[]
    for i,c in enumerate(cases):
        for k,method in enumerate(METHODS):
            data=bytes.fromhex(outputs[2*i+k]);out=data.decode()
            # Unique non-empty literal fixture markers only. Empty records require exact-byte oracle.
            ids=[r['id'] for r in c['records'] if r['content'] and r['content'] in out]
            rows.append(dict(case=c['name'],method=method,output=out,output_hex=data.hex(),visible_fixture_ids=ids,
                             output_bytes=len(data),whole_output_byte_estimate=(len(data)+3)//4,
                             exceeds_whole_output_estimate=c['budget']<(len(data)+3)//4))
    return rows

def run(mutation=None):
    cases=fixtures()
    with tempfile.TemporaryDirectory(prefix='memory-admission-') as t:
        rows=execute(build(t,mutation),cases)
    pairs={c['name']:{r['method']:r for r in rows if r['case']==c['name']} for c in cases}
    return dict(scope='Pinned formatter slice with supplied recall records. No storage, retrieval, model, network or real secrets.',
                source_commit=verify_source()['commit'],budget_unit='ceil(UTF-8 bytes/4), unchanged upstream estimate; not actual model tokens',
                fixture_count=len(cases),row_count=len(rows),changed_pairs=sum(p['stop']['output']!=p['continue']['output'] for p in pairs.values()),
                fixtures=cases,rows=rows)

def write_artifacts():
    result=run();a=ROOT/'artifacts';a.mkdir(exist_ok=True)
    (a/'run.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    rows=result['rows'];pairs={c['name']:{r['method']:r for r in rows if r['case']==c['name']} for c in result['fixtures']}
    text='# Exact formatter evidence\n\n15 fixed fixtures, two methods each. These are source-slice observations, not attack rates or live-agent behavior.\n\n'
    text+='The ordered input for oversized_first is 48 L characters, KEEP-A, KEEP-B, budget8, template {content}, no header/footer. The upstream estimate assigns12,2,2 units.\n\n'
    for method in METHODS:text+=f'**{method} output, exact JSON string:** `{json.dumps(pairs["oversized_first"][method]["output"])}`\n\n'
    text+='The large record is omitted by both. Continue scans the remaining list. The ordinary twin returns the same two lines in both.\n\n| Fixture | Budget | Input IDs | Stop IDs | Continue IDs | Whole-output estimate exceeds budget (stop / continue) |\n|---|---:|---|---|---|---|\n'
    for c in result['fixtures']:
        p=pairs[c['name']]
        text+='|'+ '|'.join(map(str,[c['name'],c['budget'],[x['id'] for x in c['records']],p['stop']['visible_fixture_ids'],p['continue']['visible_fixture_ids'],str(p['stop']['exceeds_whole_output_estimate'])+' / '+str(p['continue']['exceeds_whole_output_estimate'])]))+'|\n'
    text+='\nIDs here are an exact substring witness for unique non-empty fixture strings, not a general parser. Empty-record behavior is established by the exact output bytes in run.json. Whole-output estimate is an independent ceil(bytes/4) check, not an actual tokenizer. Header and newline cases expose remaining limits, not fixes supplied by this patch. Greedy continuation does not optimize relevance or prevent a full context of many small records.\n'
    (ROOT/'evidence.md').write_text(text)
    print(json.dumps({k:result[k] for k in ['fixture_count','row_count','changed_pairs']}))
if __name__=='__main__': write_artifacts()
