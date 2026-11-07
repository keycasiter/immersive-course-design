"""Synthetic structural regressions; no course, human confirmation or effect evidence."""
import copy
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest
from validate_spatial_learning import validate
from validate_course import validate as validate_blueprint
ROOT=Path(__file__).resolve().parents[1]
def fill(v):
    if isinstance(v,str): return re.sub(r'\{\{.*?\}\}','Synthetic fixture',v)
    if isinstance(v,list): return [fill(x) for x in v]
    if isinstance(v,dict): return {k:fill(x) for k,x in v.items()}
    return v
class SpatialContractTests(unittest.TestCase):
    def setUp(self):
        self.plan=fill(json.loads((ROOT/'assets/spatial-learning-plan.template.json').read_text()))
        self.blueprint=fill(json.loads((ROOT/'assets/course-blueprint.template.json').read_text()))
    def errors(self,delivery=False,base=ROOT): return validate(self.plan,self.blueprint,base,delivery)
    def reject(self,needle): self.assertTrue(any(needle in x for x in self.errors()),self.errors())
    def test_valid_design(self): self.assertEqual(self.errors(),[])
    def test_version_mismatch(self): self.plan['course_version']='old';self.reject('course_version')
    def test_bad_scene(self): self.plan['scenes'][0]['scene_identifier']='missing';self.reject('unknown scene')
    def test_wrong_resource(self): self.plan['scenes'][0]['media_resource_identifier']='video_introduction';self.reject('scene resource')
    def test_unknown_source(self): self.plan['scenes'][0]['representation']['invariants'][0]['source_identifiers']=['missing'];self.reject('source')
    def test_invalid_parameter(self): self.plan['scenes'][0]['representation']['parameters'][0]['default']=99;self.reject('parameter domain')
    def test_boolean_parameter(self): self.plan['scenes'][0]['representation']['parameters'][0]['min']=True;self.reject('parameter domain')
    def test_nan_parameter(self): self.plan['scenes'][0]['representation']['parameters'][0]['max']=float('nan');self.reject('parameter domain')
    def test_missing_consequence(self): self.plan['scenes'][0]['learning_actions'][0]['visible_consequence']='';self.reject('visible_consequence')
    def test_wrong_action_task(self): self.plan['scenes'][0]['learning_actions'][0]['task_identifier']='task_transfer';self.reject('action task')
    def test_all_passive(self): self.plan['scenes'][0]['learning_actions']=[];self.reject('at least one learning action')
    def test_missing_recovery(self): self.plan['runtime']['context_loss_policy']='';self.reject('context_loss_policy')
    def test_malformed(self): self.plan['scenes']=[None];self.assertTrue(self.errors())
    def test_wrong_beat(self): self.plan['scenes'][0]['beat_identifiers']=['beat_unknown'];self.reject('scene Beats')
    def test_valid_dcc(self): self.plan['scenes'][0]['representation']['route']='dcc_asset';self.assertEqual(self.errors(),[])
    def test_delivery_evidence_and_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);p=base/'owned.txt';p.write_text('Synthetic owned evidence, no real acceptance')
            digest=hashlib.sha256(p.read_bytes()).hexdigest();self.plan['delivery']['files']=[{'path':p.name,'content_sha256':digest}]
            self.plan['delivery']['checks']=[{'domain':x,'status':'passed','reviewer':'Synthetic reviewer','scope':'Synthetic checks only','evidence_file':p.name,'content_sha256':digest} for x in ['subject_rules','visual','motion','runtime','equivalent_path','audio']]
            self.assertEqual(self.errors(True,base),[])
            self.plan['delivery']['checks'].pop();self.assertTrue(any('audio' in x for x in self.errors(True,base)))
            p.write_text('Changed');self.assertTrue(any('hash' in x for x in self.errors(True,base)))
    def test_placeholder_rejected(self): self.plan['runtime']['engine_version']='{{version}}';self.reject('unfilled')
    def test_progression_accepts_spatial_and_diagram(self):
        for kind in ['video','three_dimensional','diagram']:
            self.blueprint['media_resources'][0]['media_type']=kind
            self.assertEqual(validate_blueprint(self.blueprint,ROOT),[])
    def test_document_cannot_fake_progression(self):
        self.blueprint['media_resources'][0]['media_type']='document'
        self.assertTrue(any('progression requires' in x for x in validate_blueprint(self.blueprint,ROOT)))

class NativeRuntimeTests(unittest.TestCase):
    def setUp(self):
        from check_workflow_and_demo import fixture
        from demo_contract import runtime_fingerprints
        from validate_production import file_digest
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.data=fixture(self.base)
        self.data['experience_profile']['profile_identifier']='spatial_native_web'
        self.runtime=self.data['demo_runtime'];self.runtime['runtime_mode']='scene_state'
        self.runtime['visual_gate_reference']=None
        self.evidence={x['reference_identifier']:x for x in self.data['evidence_files']}
        self.digest=file_digest;self.fingerprints=runtime_fingerprints
        # These are byte-bound synthetic receipts, never claims of real browser or human acceptance.
        self.plan=fill(json.loads((ROOT/'assets/spatial-learning-plan.template.json').read_text()))
        self.plan['event_graph_version']=self.runtime['event_graph_version']
        p=self.base/'owned-source.txt';p.write_text('Synthetic source snapshot')
        sha=file_digest(p)
        self.plan['delivery'].update(files=[{'path':p.name,'content_sha256':sha}],checks=[
            {'domain':domain,'status':'passed','reviewer':'Synthetic reviewer','scope':'Fixture coverage',
             'evidence_file':p.name,'content_sha256':sha}
            for domain in ['subject_rules','visual','motion','runtime','equivalent_path','audio']])
        self.write_plan()
    def write_plan(self):
        from demo_contract import runtime_fingerprints
        r=self.runtime;entry=self.evidence[r['event_map_reference']]
        entry['kind']='spatial_learning_plan'
        path=self.base/entry['path'];path.write_text(json.dumps(self.plan));entry['content_sha256']=self.digest(path)
        html_entry=self.evidence[r['entry_reference']];html=self.base/html_entry['path']
        html.write_text('<main id="course-stage" data-runtime-mode="scene_state"><canvas id="scene-media"></canvas></main><script type="application/json" id="spatial-learning-plan">'+json.dumps(self.plan)+'</script>')
        html_entry['content_sha256']=self.digest(html)
        browser_entry=self.evidence[r['browser_evidence_reference']];browser_path=self.base/browser_entry['path']
        browser=json.loads(browser_path.read_text());browser['runtime_mode']='scene_state'
        browser['runtime_fingerprints']=runtime_fingerprints(self.data,self.base,r)
        browser_path.write_text(json.dumps(browser));browser_entry['content_sha256']=self.digest(browser_path)
    def errors(self,formal=False):
        from demo_contract import validate_runtime_delivery
        if formal:self.data['runtime_delivery']=self.runtime
        return validate_runtime_delivery(self.data,self.base,formal=formal)
    def test_native_demo_reuses_existing_matrix_and_browser_contract(self):self.assertEqual(self.errors(),[])
    def test_native_rejects_wrong_profile(self):
        self.data['experience_profile']['profile_identifier']='video_led_web'
        self.assertTrue(any('scene_state requires' in x for x in self.errors()))
    def test_native_rejects_missing_visual_evidence(self):
        self.plan['delivery']['checks']=[x for x in self.plan['delivery']['checks'] if x['domain']!='visual'];self.write_plan()
        self.assertTrue(any('visual' in x for x in self.errors()))
    def test_native_rejects_stale_embedded_plan(self):
        entry=self.evidence[self.runtime['entry_reference']];p=self.base/entry['path'];p.write_text('<main data-runtime-mode="scene_state"></main>');entry['content_sha256']=self.digest(p)
        self.assertTrue(any('identical spatial-learning plan' in x for x in self.errors()))
    def test_video_formal_still_requires_real_clock(self):
        self.data['experience_profile']['profile_identifier']='video_led_web';self.runtime['runtime_mode']='storyboard_events'
        self.assertTrue(any('formal video runtime requires video_clock' in x for x in self.errors(True)))
    def test_native_formal_requires_scene_integration_paths(self):
        self.assertTrue(any('scene_state' in x and 'integration evidence' in x for x in self.errors(True)))

    def test_native_formal_accepts_complete_scene_paths(self):
        # No deferred formal video may be hidden in the native formal asset list.
        for asset in self.data['assets']:
            if asset['kind']=='linear_video': asset['required']=False
        entry=self.evidence[self.runtime['browser_evidence_reference']];p=self.base/entry['path']
        browser=json.loads(p.read_text())
        for viewport in ('desktop','narrow'):
            base=next(x for x in browser['tests'] if x['viewport_class']==viewport)
            for category in ('scene_state','parameter_boundaries','context_restore','deterministic_seek','caption_sync','return_state','responsive_layout','accessibility'):
                row=copy.deepcopy(base);row.update(test_identifier=category+'_'+viewport,path_category=category);browser['tests'].append(row)
        p.write_text(json.dumps(browser));entry['content_sha256']=self.digest(p)
        self.assertEqual(self.errors(True),[])
    def test_joint_requires_plan(self):
        from validate_production import validate as validate_manifest
        old=self.evidence[self.runtime['event_map_reference']]['kind']
        self.evidence[self.runtime['event_map_reference']]['kind']='runtime_event_map'
        self.assertTrue(any('one spatial_learning_plan' in x for x in validate_manifest(self.data,self.base)))
        self.evidence[self.runtime['event_map_reference']]['kind']=old
    def test_joint_plan_profile_mismatch(self):
        from validate_production import validate as validate_manifest
        self.plan['experience_profile']='hybrid_web';self.write_plan()
        self.assertTrue(any('spatial design/profile differs' in x for x in validate_manifest(self.data,self.base)))
    def test_joint_malformed_plan_is_diagnostic(self):
        from validate_production import validate as validate_manifest
        row=self.evidence[self.runtime['event_map_reference']];p=self.base/row['path'];p.write_text('[]');row['content_sha256']=self.digest(p)
        self.assertTrue(any('spatial plan must be' in x for x in validate_manifest(self.data,self.base)))

if __name__=='__main__': unittest.main()
