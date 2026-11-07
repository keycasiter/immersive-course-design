"""Synthetic HTML and real local subprocess tests, not course acceptance evidence."""
import json, subprocess, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experience_contract import file_digest,validate_plan
from test_experience import plan_fixture
from validate_page_structure import validate_html
ROOT=Path(__file__).resolve().parents[1]

class PageTests(unittest.TestCase):
 def test_free_layout_no_modal_or_fixed_regions(self):self.assertEqual(validate_html('<main><canvas aria-label="World"></canvas><section><p>Context and same-content support</p><button>Inspect object</button></section></main>'),[])
 def test_missing_canvas(self):self.assertTrue(validate_html('<main><p>Text only</p></main>'))
 def test_empty_control(self):self.assertTrue(validate_html('<main><canvas aria-label="World"></canvas><p>Context</p><button></button></main>'))
 def test_labelledby(self):self.assertEqual(validate_html('<main><h1 id="title">World</h1><canvas aria-labelledby="title"></canvas><p>Context</p><button aria-label="Inspect"></button></main>'),[])
 def test_duplicate_id(self):self.assertTrue(validate_html('<main><canvas aria-label="World"></canvas><p id="a">A</p><p id="a">B</p></main>'))

class RecorderTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name);self.file=self.base/'source.mjs';self.file.write_text('owned synthetic source');self.record=self.base/'check.json'
 def run_check(self,code):return subprocess.run([sys.executable,str(ROOT/'run_check.py'),'--record',str(self.record),'--bind',str(self.file),'--',sys.executable,'-c',code],capture_output=True,text=True)
 def test_actual_success_hashes_sources_and_logs(self):
  r=self.run_check('print("observed output")');self.assertEqual(r.returncode,0);d=json.loads(self.record.read_text());self.assertEqual(d['kind'],'command_run');self.assertTrue(d['inputs_unchanged']);self.assertEqual(d['input_snapshots'][0]['content_sha256'],file_digest(self.file));self.assertEqual(d['stdout_sha256'],file_digest(self.base/d['stdout_reference']));self.assertIn('observed output',(self.base/d['stdout_reference']).read_text())
 def test_original_failure_code_retained(self):
  r=self.run_check('import sys;sys.exit(7)');self.assertEqual(r.returncode,7);self.assertEqual(json.loads(self.record.read_text())['exit_code'],7)
 def test_input_mutation_cannot_pass(self):
  code='from pathlib import Path;Path('+repr(str(self.file))+').write_text("changed")';r=self.run_check(code);self.assertEqual(r.returncode,1);d=json.loads(self.record.read_text());self.assertFalse(d['inputs_unchanged']);self.assertEqual(d['exit_code'],0)
 def test_receipt_immutable(self):self.assertEqual(self.run_check('pass').returncode,0);before=self.record.read_bytes();self.assertNotEqual(self.run_check('print("overwrite")').returncode,0);self.assertEqual(self.record.read_bytes(),before)

class MalformedTests(unittest.TestCase):
 def test_nested_invalid_types_report_not_crash(self):
  for field,value in [('kind',[]),('emits_event_identifier',{}),('target_identifier',None)]:
   p=plan_fixture();p['learning']['scenes'][0]['interactions'][0][field]=value;self.assertTrue(validate_plan(p))
 def test_invalid_graph_and_nonfinite_data(self):
  p=plan_fixture();p['learning']['scenes'][0]['progression']['next_scene_identifiers']=None;self.assertTrue(validate_plan(p));p=plan_fixture();p['presentation']['bad']=float('nan');self.assertTrue(validate_plan(p))
