import itertools
import os
import tempfile
import unittest
import experiment as e

class FormatterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='formatter-tests-')
        cls.binary=e.build(cls.temp.name,os.environ.get('EXPERIMENT_MUTATION'))
        cls.rows=e.execute(cls.binary,e.fixtures())
        cls.p={(r['case'],r['method']):r for r in cls.rows}
    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()
    def output(self,case,method):return self.p[case,method]['output']
    def test_first_big_record_and_later_small_records(self):
        self.assertEqual(self.output('oversized_first','stop'),'')
        self.assertEqual(self.output('oversized_first','continue'),'KEEP-A\nKEEP-B\n')
    def test_middle_and_last_order_counterfactuals(self):
        self.assertEqual(self.output('oversized_middle','stop'),'KEEP-A\n')
        self.assertEqual(self.output('oversized_middle','continue'),'KEEP-A\nKEEP-B\n')
        for m in e.METHODS:self.assertEqual(self.output('oversized_last',m),'KEEP-A\nKEEP-B\n')
    def test_ordinary_and_exact_fill_twins(self):
        for c in ['ordinary_twin','exact_fill']:
            for m in e.METHODS:self.assertEqual(self.output(c,m),'KEEP-A\nKEEP-B\n')
    def test_still_no_room_means_no_admission(self):
        for m in e.METHODS:
            self.assertEqual(self.output('no_remaining_room',m),'KEEP-A\n')
            self.assertEqual(self.output('all_oversized',m),'')
            self.assertEqual(self.output('empty',m),'')
    def test_header_and_footer_retained(self):
        self.assertEqual(self.output('header_consumes_room','stop'),'H'*16+'\n')
        self.assertEqual(self.output('header_consumes_room','continue'),'H'*16+'\nKEEP-A\n')
        self.assertEqual(self.output('footer_is_preserved','stop'),'END')
        self.assertEqual(self.output('footer_is_preserved','continue'),'KEEP-A\nKEEP-B\nEND')
    def test_known_header_and_newline_estimator_limits(self):
        for m in e.METHODS:
            self.assertEqual(self.output('oversized_header',m),'H'*16+'\n')
            self.assertEqual(self.output('newline_estimate_limit',m),'ABCD\nEFGH\n')
            self.assertEqual(self.output('empty_record_limit',m),'\n'*5)
            for c in ['oversized_header','newline_estimate_limit','empty_record_limit']:
                self.assertTrue(self.p[c,m]['exceeds_whole_output_estimate'])
    def test_unicode_uses_utf8_bytes(self):
        self.assertEqual(self.output('unicode_cost','stop'),'')
        self.assertEqual(self.output('unicode_cost','continue'),'猫\n🙂\n')
    def test_upstream_default_template(self):
        header='### Relevant Agent Memories:\n'
        self.assertEqual(self.output('default_template','stop'),header)
        self.assertEqual(self.output('default_template','continue'),header+'- [fact] KEEP-A (score: 0.50)\n- [fact] KEEP-B (score: 0.50)\n')
    def test_independent_finite_admission_oracle(self):
        cases=[];expected=[]
        for lengths in itertools.product([0,1,4,5,8,12],repeat=3):
            for capacity in range(1,9):
                texts=[chr(65+i)*n for i,n in enumerate(lengths)]
                cases.append(dict(name=str(len(cases)),budget=capacity,records=[dict(id=str(i),content=s) for i,s in enumerate(texts)],header=None,footer=None,template='{content}'))
                for mode in e.METHODS:
                    available=capacity;chosen=[]
                    for s in texts:
                        cost=sum(1 for _ in range(0,len(s.encode()),4))
                        if cost>available:
                            if mode=='stop':break
                            continue
                        chosen.append(s+'\n');available-=cost
                    expected.append(''.join(chosen))
        actual=e.execute(self.binary,cases)
        self.assertEqual(len(actual),3456)
        self.assertEqual([r['output'] for r in actual],expected)
    def test_repeatability_and_exact_byte_oracle(self):
        self.assertEqual(e.execute(self.binary,e.fixtures()),self.rows)
        for r in self.rows:self.assertEqual(bytes.fromhex(r['output_hex']),r['output'].encode())
    def test_invalid_zero_budget_is_rejected(self):
        c=e.fixtures()[0];c['budget']=0
        with self.assertRaises(ValueError):e.execute(self.binary,[c])
    def test_source_hash_and_single_budget_branch(self):
        source=e.verify_source()
        self.assertEqual(source['commit'],'b5679309d4e072d34d7ac1456426c51361970002')
        self.assertEqual((e.ROOT/'vendor/formatter_body.rs').read_text().count('                break;'),1)
if __name__=='__main__':unittest.main()
