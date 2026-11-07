import copy, json, re, sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experience_contract import validate_plan, design_digest, representative_digest, compile_design, compile_index
ROOT=Path(__file__).resolve().parents[2]
def fill(v):
 if isinstance(v,str):return re.sub(r"\{\{.*?\}\}","Synthetic authored content",v)
 if isinstance(v,list):return [fill(x) for x in v]
 if isinstance(v,dict):return {k:fill(x) for k,x in v.items()}
 return v
def plan_fixture():return fill(json.loads((ROOT/'assets/scene-plan.template.json').read_text()))
class PlanTests(unittest.TestCase):
 def setUp(self):self.p=plan_fixture()
 def check_bad(self,part):self.assertTrue(any(part in x for x in validate_plan(self.p)),validate_plan(self.p))
 def test_valid_exploration_without_quiz_or_grading(self):self.assertEqual(validate_plan(self.p),[])
 def test_old_version_explicitly_rejected(self):self.p['schema_version']='1.2';self.check_bad('2.0')
 def test_unresolved_template(self):self.p['learning']['title']='{{title}}';self.check_bad('placeholder')
 def test_unknown_object(self):self.p['learning']['scenes'][0]['interactions'][0]['target_identifier']='none';self.check_bad('target')
 def test_missing_content_coverage(self):self.p['learning']['required_content'].append({'content_identifier':'other','description':'Other content','source_identifiers':['source_core']});self.check_bad('coverage')
 def test_unreachable_required_scene(self):
  s=copy.deepcopy(self.p['learning']['scenes'][0]);s.update(scene_identifier='scene_other',events=[],interactions=[]);s['progression']['required_event_identifiers']=[];self.p['learning']['scenes'].append(s);self.check_bad('unreachable')
 def test_optional_exploration_does_not_require_completion(self):self.p['learning']['scenes'][0]['progression']['required_event_identifiers']=[];self.assertEqual(validate_plan(self.p),[])
 def test_missing_binding(self):self.p['implementation']['bindings']=[];self.check_bad('binding')
 def test_no_modal_or_model_dependencies(self):
  self.assertNotIn('glb',json.dumps(self.p));self.assertNotIn('blender',json.dumps(self.p));self.assertEqual(validate_plan(self.p),[])
 def test_forbidden_exam_action(self):self.p['learning']['scenes'][0]['interactions'][0]['kind']='quiz';self.check_bad('interaction kind')
 def test_hidden_scoring_field_rejected(self):self.p['learning']['scenes'][0]['interactions'][0]['correct_answer']='A';self.check_bad('assessment')
 def test_source_must_exist(self):self.p['learning']['required_content'][0]['source_identifiers']=['missing'];self.check_bad('source')
 def test_malformed_returns_errors(self):self.p['learning']['scenes']=[None];self.assertTrue(validate_plan(self.p))
 def test_no_participation_anywhere_rejected(self):self.p['learning']['scenes'][0]['interactions']=[];self.p['implementation']['bindings']=[];self.check_bad('participation')
 def test_presentation_change_preserves_design(self):
  old=design_digest(self.p);self.p['presentation']['lighting_and_materials']='Different lighting';self.assertEqual(design_digest(self.p),old)
 def test_implementation_fix_preserves_design(self):
  old=design_digest(self.p);self.p['implementation']['source_files'].append('src/fix.mjs');self.assertEqual(design_digest(self.p),old)
 def test_rule_change_invalidates_design(self):
  old=design_digest(self.p);self.p['learning']['rules']=[{'rule_identifier':'area','statement':'Area is invariant','source_identifiers':['source_core'],'verification':'source_review','test_check_identifier':None}];self.assertNotEqual(design_digest(self.p),old)
 def test_dialogue_change_invalidates_design(self):
  old=design_digest(self.p);self.p['learning']['scenes'][0]['interactions'][0]['response']='A different scene response';self.assertNotEqual(design_digest(self.p),old)
 def test_package_bump_preserves_design(self):
  old=design_digest(self.p);self.p['experience_version']='0.2';self.assertEqual(design_digest(self.p),old)
 def test_derived_output_has_exact_content(self):
  text=compile_design(self.p);self.assertIn(self.p['learning']['experience_promise'],text);index=compile_index(self.p);self.assertEqual(index['design_sha256'],design_digest(self.p));self.assertEqual(index['scenes'][0]['interaction_identifiers'],['inspect_core'])
 def test_representative_changes_with_style(self):
  rep={'scene_identifiers':['scene_entry'],'candidate_files':[],'check_identifiers':[]};before=representative_digest(self.p,rep,[]);self.p['presentation']['style_goal']='New style';self.assertNotEqual(before,representative_digest(self.p,rep,[]))
