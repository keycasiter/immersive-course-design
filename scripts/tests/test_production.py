"""Synthetic contract receipts; these never count as real human, browser or learner evidence."""
import copy, json, re, struct, sys, tempfile, unittest, zlib, subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experience_contract import design_digest, file_digest, representative_digest, runtime_digest
from validate_production import validate_manifest
from test_experience import plan_fixture

def png(w,h):
 def chunk(k,d):return struct.pack('>I',len(d))+k+d+struct.pack('>I',zlib.crc32(k+d)&0xffffffff)
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+b'\0'*w*3)*h))+chunk(b'IEND',b'')
class ProductionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name);self.p=plan_fixture();self.p['learning']['sources'][0]['verification_status']='verified';self.p['presentation']['target_devices'][0]['viewport']={'width':64,'height':36}
  self.m={'schema_version':'2.0','experience_identifier':self.p['experience_identifier'],'experience_version':self.p['experience_version'],'current_status':'design_draft','active_design_approval':None,'active_representative_approval':None,'approvals':[],'representative':{'scene_identifiers':['scene_entry'],'candidate_files':[],'check_identifiers':[]},'files':[],'evidence':[],'checks':[],'learner_trial':None}
 def write(self,name,data):
  path=self.base/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data if isinstance(data,bytes) else json.dumps(data).encode());return file_digest(path)
 def ev(self,identifier,kind,data):
  path=identifier+'.json';sha=self.write(path,data);row={'evidence_identifier':identifier,'kind':kind,'path':path,'content_sha256':sha};self.m['evidence'].append(row);return identifier
 def approve(self,kind,subject):
  identifier=kind+'_approval';ev=self.ev(identifier,'human_confirmation',{'kind':'human_confirmation','confirmed_by':'Synthetic human','confirmed_at':'2026-11-08T00:00:00Z','subject_sha256':subject,'confirmation_text':'Synthetic fixture only, never actual consent'})
  self.m['approvals'].append({'approval_identifier':identifier,'kind':kind,'confirmed_by':'Synthetic human','confirmed_at':'2026-11-08T00:00:00Z','subject_sha256':subject,'evidence_identifier':ev});self.m['active_'+kind+'_approval']=identifier
 def design(self):self.approve('design',design_digest(self.p));self.m['current_status']='design_confirmed'
 def runtime(self):
  for identifier,path,role in [('entry','index.html','entry'),('source','src/main.mjs','source')]:
   sha=self.write(path,b'Synthetic owned source');self.m['files'].append({'file_identifier':identifier,'path':path,'role':role,'content_sha256':sha})
  self.m['representative']['candidate_files']=copy.deepcopy(self.m['files']);rd=runtime_digest(self.m['files']);screen='viewport.png';sha=self.write(screen,png(64,36));artifact={'kind':'screenshot','path':screen,'content_sha256':sha}
  for domain,kind in [('content','content_review'),('visual','visual_review'),('motion','motion_review'),('interaction','cua_operation'),('accessibility','cua_operation'),('recovery','cua_operation'),('performance','performance_review')]:
   data={'kind':kind,'runtime_digest':rd,'scene_identifiers':['scene_entry'],'result':'passed','observed_result':'Synthetic structural observation','reviewed_by':'Synthetic reviewer','artifacts':[artifact]}
   if kind=='cua_operation':data.update(tool='cua',target_url='http://127.0.0.1:1/owned-fixture',captured_at='2026-11-08T00:00:00Z',device_identifier='desktop',viewport={'width':64,'height':36},actions=[{'kind':'inspect','target_identifier':'object_core','interaction_identifier':'inspect_core','observed_result':'Synthetic response'},{'kind':'return','target_identifier':'object_core','observed_result':'Synthetic return'}])
   ref=self.ev('ev_'+domain,kind,data);cid='check_'+domain;self.m['checks'].append({'check_identifier':cid,'domain':domain,'scene_identifiers':['scene_entry'],'status':'passed','evidence_identifiers':[ref],'scope':'Synthetic scope'});self.m['representative']['check_identifiers'].append(cid)
 def representative(self):
  self.design();self.runtime();self.approve('representative',representative_digest(self.p,self.m['representative'],self.m['checks'],self.m['evidence']));self.m['current_status']='representative_confirmed'
 def errors(self,previous=None):return validate_manifest(self.m,self.p,self.base,previous)
 def test_draft_no_fake_media_or_approval(self):self.assertEqual(self.errors(),[])
 def test_design_confirmation_with_no_full_course_demo(self):self.design();self.assertEqual(self.errors(),[])
 def test_semantic_rule_change_invalidates_confirmation(self):self.design();self.p['learning']['scenes'][0]['perception']['relationship']='Changed meaning';self.assertTrue(any('design' in e and 'fingerprint' in e for e in self.errors()))
 def test_presentation_tweak_does_not_reopen_design(self):self.design();self.p['presentation']['lighting_and_materials']='Adjusted light';self.assertEqual(self.errors(),[])
 def test_actual_representative_scope_accepted(self):self.representative();self.assertEqual(self.errors(),[])
 def test_final_with_all_required_scene_evidence(self):self.representative();self.m['current_status']='functional_accepted';self.assertEqual(self.errors(),[])
 def test_self_signed_agent_rejected(self):self.design();self.m['approvals'][0]['confirmed_by']='Codex agent';self.assertTrue(any('human' in e for e in self.errors()))
 def test_missing_actual_confirmation_record_rejected(self):self.design();self.m['evidence']=[];self.assertTrue(self.errors())
 def test_representative_style_change_invalidates_sample(self):self.representative();self.p['presentation']['style_goal']='Changed world look';self.assertTrue(any('representative' in e and 'fingerprint' in e for e in self.errors()))
 def test_source_change_rejects_stale_runtime(self):self.representative();self.write('src/main.mjs',b'Changed source');self.assertTrue(any('hash' in e for e in self.errors()))
 def test_current_file_change_preserves_frozen_sample_but_needs_new_final_checks(self):
  self.representative()
  for f in self.m['representative']['candidate_files']:
   original=self.base/f['path'];new='frozen/'+f['path'];f['path']=new;f['content_sha256']=self.write(new,original.read_bytes())
  rd=runtime_digest(self.m['representative']['candidate_files'])
  for e in self.m['evidence']:
   if e['kind']=='human_confirmation':continue
   p=self.base/e['path'];d=json.loads(p.read_text());d['runtime_digest']=rd;e['content_sha256']=self.write(e['path'],d)
  self.m['approvals']=self.m['approvals'][:1];self.m['evidence']=[e for e in self.m['evidence'] if e['evidence_identifier']!='representative_approval'];self.approve('representative',representative_digest(self.p,self.m['representative'],self.m['checks'],self.m['evidence']))
  f=self.m['files'][1];f['content_sha256']=self.write(f['path'],b'Current build updated')
  self.assertEqual(self.errors(),[])
  self.m['current_status']='functional_accepted';self.assertTrue(any('current' in e or 'coverage' in e for e in self.errors()))
 def test_history_cannot_be_deleted(self):self.design();old=copy.deepcopy(self.m);self.m['approvals']=[];self.assertTrue(any('history' in e for e in self.errors(old)))
 def test_bad_receipt_tool_rejected(self):
  self.representative();row=next(e for e in self.m['evidence'] if e['kind']=='cua_operation');data=json.loads((self.base/row['path']).read_text());data['tool']='static_screenshot';row['content_sha256']=self.write(row['path'],data);self.assertTrue(any('CUA' in e for e in self.errors()))
 def test_malformed_manifest_returns_diagnostics(self):self.m['checks']=[None];self.assertTrue(self.errors())
 def test_pending_check_needs_no_fabricated_evidence(self):self.m['checks']=[{'check_identifier':'pending','domain':'visual','scene_identifiers':['scene_entry'],'status':'pending','evidence_identifiers':[],'scope':'Awaiting actual viewing'}];self.assertEqual(self.errors(),[])
 def test_all_declared_actions_need_actual_qa_not_student_completion(self):
  self.representative();row=next(e for e in self.m['evidence'] if e['evidence_identifier']=='ev_interaction');d=json.loads((self.base/row['path']).read_text());del d['actions'][0]['interaction_identifier'];row['content_sha256']=self.write(row['path'],d);self.assertTrue(any('interaction coverage' in e for e in self.errors()))
 def test_promised_second_device_needs_actual_coverage(self):
  self.representative();self.p['presentation']['target_devices'].append({'device_identifier':'phone','viewport':{'width':36,'height':64},'acceptance_goal':'Synthetic touch support'});self.assertTrue(any('device coverage' in e for e in self.errors()))
 def test_missing_required_scene_evidence_cannot_claim_final(self):
  self.representative();scene=copy.deepcopy(self.p['learning']['scenes'][0]);scene['scene_identifier']='scene_end';scene['events']=[];scene['interactions']=[];scene['progression']['required_event_identifiers']=[];self.p['learning']['scenes'][0]['progression']['next_scene_identifiers']=['scene_end'];self.p['learning']['scenes'].append(scene);view=copy.deepcopy(self.p['presentation']['scene_views'][0]);view['scene_identifier']='scene_end';self.p['presentation']['scene_views'].append(view);self.m['current_status']='functional_accepted';self.assertTrue(any('current final coverage' in e for e in self.errors()))
 def test_actual_rule_command_inputs_and_logs_verified(self):
  self.p['learning']['rules']=[{'rule_identifier':'rule_core','statement':'Synthetic source rule','source_identifiers':['source_core'],'verification':'executable','test_check_identifier':'check_rule'}];self.p['learning']['objects'][0]['rule_identifiers']=['rule_core'];self.p['implementation']['rule_bindings']=[{'rule_identifier':'rule_core','source_file':'src/main.mjs','export_name':'evaluate'}];self.representative();self.m['current_status']='functional_accepted'
  record=self.base/'command.json';runner=Path(__file__).resolve().parents[1]/'run_check.py'
  run=subprocess.run([sys.executable,str(runner),'--record',str(record),'--bind',str(self.base/'src/main.mjs'),'--',sys.executable,'-c','print("Synthetic command execution")'],capture_output=True);self.assertEqual(run.returncode,0)
  self.m['evidence'].append({'evidence_identifier':'ev_rule','kind':'command_run','path':'command.json','content_sha256':file_digest(record)});self.m['checks'].append({'check_identifier':'check_rule','domain':'rule','scene_identifiers':['scene_entry'],'status':'passed','evidence_identifiers':['ev_rule'],'scope':'Synthetic command structure, no learning claim'})
  self.assertEqual(self.errors(),[])
  (self.base/'command.json.stdout.log').write_text('tampered');self.assertTrue(any('log hash' in e for e in self.errors()))
 def test_audio_cannot_be_accepted_using_only_visual_receipts(self):
  self.p['learning']['audio_enabled']=True;self.representative();self.assertTrue(any('coverage missing for audio' in e for e in self.errors()))
