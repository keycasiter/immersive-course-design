#!/usr/bin/env python3
"""Validate evidence structure and file provenance; never certify aesthetics or learning."""
import argparse
import json
import re
import struct
from pathlib import Path
from experience_contract import STAGES, design_digest, file_digest, representative_digest, runtime_digest, validate_plan

DOMAINS = {'content':'content_review','visual':'visual_review','motion':'motion_review','interaction':'cua_operation','accessibility':'cua_operation','recovery':'cua_operation','performance':'performance_review','audio':'audio_review','rule':'command_run'}
CUA_ACTIONS = {'enter','inspect','approach','viewpoint','follow','manipulate','dialogue','choose','read','return','replay','restore','keyboard','touch','mute','reduced_motion','resize','context_restore'}

def validate_manifest(manifest, plan, base, previous=None):
    errors = validate_plan(plan)
    if errors: return errors
    base = Path(base).resolve()
    def need(ok, message):
        if not ok: errors.append(message)
    def txt(value): return isinstance(value,str) and bool(value.strip())
    def rows(value, field):
        if not isinstance(value,list): errors.append(field+' must be array'); return []
        need(all(isinstance(x,dict) for x in value),field+' requires objects')
        return [x for x in value if isinstance(x,dict)]
    def index(value, field, label):
        result={}
        for row in rows(value,label):
            key=row.get(field)
            if not txt(key): errors.append(label+' missing '+field); continue
            need(key not in result,label+' duplicate '+key); result[key]=row
        return result
    def identifiers(value, allowed, label, nonempty=False):
        if not isinstance(value,list): errors.append(label+' must be array'); return set()
        valid=[x for x in value if isinstance(x,str)]
        need(len(valid)==len(value) and len(valid)==len(set(valid)),label+' invalid or duplicate identifiers')
        need(set(valid)<=set(allowed),label+' unknown reference')
        need(not nonempty or bool(valid),label+' is empty')
        return set(valid)
    def checked_file(row,label):
        path=row.get('path'); sha=row.get('content_sha256')
        if not txt(path) or not isinstance(sha,str) or not re.fullmatch('[0-9a-f]{64}',sha):
            errors.append(label+' needs path and SHA256'); return None
        target=(base/path).resolve()
        try:
            need(target.is_file() and target.stat().st_size>0,label+' missing or empty file')
            if target.is_file(): need(file_digest(target)==sha,label+' hash mismatch')
            return target if target.is_file() else None
        except OSError as e: errors.append(label+' file unavailable: '+str(e)); return None
    if not isinstance(manifest,dict): return ['manifest must be object']
    m=manifest
    need(m.get('schema_version')=='2.0','manifest schema_version must be 2.0')
    for key in ('experience_identifier','experience_version'): need(m.get(key)==plan.get(key),'manifest '+key+' differs from plan')
    stage=m.get('current_status'); need(stage in STAGES,'invalid current_status')
    level=STAGES.index(stage) if stage in STAGES else 0
    scenes={s['scene_identifier']:s for s in plan['learning']['scenes']}
    required={sid for sid,s in scenes.items() if s['required']}
    devices={d['device_identifier']:d for d in plan['presentation']['target_devices']}
    files=index(m.get('files'),'file_identifier','files')
    rep=m.get('representative')
    if not isinstance(rep,dict): errors.append('representative must be object'); rep={}
    selected=identifiers(rep.get('scene_identifiers'),scenes,'representative.scene_identifiers',True)
    candidates=index(rep.get('candidate_files'),'file_identifier','candidate_files')
    for label, group in [('files',files),('candidate_files',candidates)]:
        for key,f in group.items():
            checked_file(f,label+'.'+key)
            need(f.get('role') in ('entry','source','resource','reference'),label+' invalid role')
    if level>=2:
        need(bool(candidates),'representative needs frozen candidate files')
        need(any(f.get('role')=='entry' for f in candidates.values()),'candidate needs entry')
        paths={f.get('path') for f in files.values() if txt(f.get('path'))}
        expected={plan['implementation']['entry_file'],*plan['implementation']['source_files'],*[r['file'] for r in plan['resources']]}
        need(expected<=paths,'current files coverage must include entry, all source and resources')
    evidence=index(m.get('evidence'),'evidence_identifier','evidence')
    receipts={}
    for eid,e in evidence.items():
        path=checked_file(e,'evidence.'+eid)
        if path:
            try:
                value=json.loads(path.read_text())
                if not isinstance(value,dict): raise ValueError('receipt must be object')
                receipts[eid]=value
                need(value.get('kind')==e.get('kind'),'evidence kind mismatch: '+eid)
            except (OSError,ValueError) as ex: errors.append('invalid receipt '+eid+': '+str(ex))
    approvals=rows(m.get('approvals'),'approvals')
    approval_index=index(approvals,'approval_identifier','approvals')
    if previous is not None:
        old=previous.get('approvals',[]) if isinstance(previous,dict) else None
        need(isinstance(old,list) and approvals[:len(old)]==old,'approval history must preserve previous prefix')
    for a in approvals:
        signer=a.get('confirmed_by')
        need(txt(signer) and not re.search(r'\b(agent|codex|script|assistant|automation)\b|智能体|脚本|自动签',signer,re.I),'approval requires actual human confirmation')
        need(a.get('kind') in ('design','representative'),'approval invalid kind')
        need(txt(a.get('confirmed_at')),'approval missing time')
        receipt=receipts.get(a.get('evidence_identifier')) if isinstance(a.get('evidence_identifier'),str) else None
        need(isinstance(receipt,dict) and receipt.get('kind')=='human_confirmation','approval missing human confirmation evidence')
        if receipt:
            for key in ('confirmed_by','confirmed_at','subject_sha256'): need(receipt.get(key)==a.get(key),'approval evidence differs: '+key)
            need(txt(receipt.get('confirmation_text')),'confirmation needs actual text/reference')
    checks=index(m.get('checks'),'check_identifier','checks')
    sample_checks=identifiers(rep.get('check_identifiers'),checks,'representative.check_identifiers',level>=2)
    def active(kind,subject,minimum):
        ref=m.get('active_'+kind+'_approval')
        if ref is None and level<minimum: return
        a=approval_index.get(ref) if isinstance(ref,str) else None
        need(a is not None and a.get('kind')==kind,kind+' approval missing')
        if a: need(a.get('subject_sha256')==subject,kind+' fingerprint differs from confirmed subject')
    active('design',design_digest(plan),1)
    try: sample_digest=representative_digest(plan,rep,list(checks.values()),list(evidence.values()))
    except (TypeError,ValueError,KeyError): sample_digest=None; errors.append('representative fingerprint input invalid')
    active('representative',sample_digest,2)
    current_digest=runtime_digest(list(files.values())) if files and all(all(k in f for k in ('path','content_sha256')) for f in files.values()) else None
    candidate_digest=runtime_digest(list(candidates.values())) if candidates and all(all(k in f for k in ('path','content_sha256')) for f in candidates.values()) else None
    coverage={}
    for cid,c in checks.items():
        domain=c.get('domain'); need(isinstance(domain,str) and domain in DOMAINS,cid+' invalid domain')
        scope=identifiers(c.get('scene_identifiers'),scenes,cid+'.scenes',True)
        refs=identifiers(c.get('evidence_identifiers'),evidence,cid+'.evidence',c.get('status')=='passed')
        need(c.get('status') in ('pending','passed','failed','blocked','superseded'),cid+' invalid status')
        need(txt(c.get('scope')),cid+' scope required')
        bound=set(); device_coverage=set(); tested_actions=set()
        if c.get('status')!='passed': continue
        need(bool(refs),cid+' passed needs real evidence')
        for ref in refs:
            r=receipts.get(ref)
            if not r: continue
            kind=DOMAINS.get(domain) if isinstance(domain,str) else None
            need(r.get('kind')==kind,cid+' incorrect evidence kind')
            if r.get('kind')!=kind: continue
            if kind=='command_run':
                need(r.get('execution_status')=='completed' and type(r.get('exit_code')) is int and r['exit_code']==0,cid+' command did not pass')
                need(r.get('inputs_unchanged') is True,cid+' command changed bound inputs')
                need(isinstance(r.get('command'),list) and bool(r['command']),cid+' needs real command')
                for time in ('cwd','started_at','finished_at'): need(txt(r.get(time)),cid+' command missing '+time)
                record_path=(base/evidence[ref]['path']).resolve()
                for stream in ('stdout','stderr'):
                    name=r.get(stream+'_reference'); sha=r.get(stream+'_sha256')
                    log=record_path.parent/name if isinstance(name,str) else None
                    need(log is not None and log.is_file() and file_digest(log)==sha,cid+' command log hash mismatch')
                inputs=rows(r.get('input_snapshots'),cid+'.input_snapshots')
                need(bool(inputs),cid+' command inputs missing')
                input_paths=set()
                for inp in inputs:
                    target=checked_file(inp,cid+'.input')
                    if target: input_paths.add(target)
                bindings={b['rule_identifier']:b['source_file'] for b in plan['implementation']['rule_bindings']}
                rules=[x for x in plan['learning']['rules'] if x.get('test_check_identifier')==cid and x['verification']=='executable']
                need(bool(rules),cid+' executable rule binding missing')
                need(all((base/bindings[x['rule_identifier']]).resolve() in input_paths for x in rules),cid+' rule source not bound to actual command')
                continue
            need(r.get('result')=='passed' and txt(r.get('observed_result')) and txt(r.get('reviewed_by')),cid+' needs actual observations and reviewer')
            receipt_scope=identifiers(r.get('scene_identifiers'),scenes,cid+'.receipt.scenes',True)
            need(scope<=receipt_scope,cid+' receipt scene coverage incomplete')
            artifacts=rows(r.get('artifacts'),cid+'.artifacts'); need(bool(artifacts),cid+' artifacts missing')
            for art in artifacts: checked_file(art,cid+'.artifact')
            if kind=='audio_review': need(any(a.get('kind')=='audio' for a in artifacts),cid+' audio listening needs audio artifact')
            rd=r.get('runtime_digest')
            need(isinstance(rd,str) and bool(re.fullmatch('[0-9a-f]{64}',rd)),cid+' runtime digest missing/invalid')
            if isinstance(rd,str): bound.add(rd)
            if kind=='cua_operation':
                need(r.get('tool') in ('cua','mcp'),cid+' requires actual CUA/MCP operation')
                for key in ('target_url','captured_at'): need(txt(r.get(key)),cid+' CUA missing '+key)
                did=r.get('device_identifier'); device=devices.get(did) if isinstance(did,str) else None
                need(device is not None and r.get('viewport')==device['viewport'],cid+' CUA viewport/device mismatch')
                if device: device_coverage.add(did)
                actions=rows(r.get('actions'),cid+'.actions'); need(bool(actions),cid+' CUA actions missing')
                targets={x for sid in scope for x in scenes[sid]['object_identifiers']+scenes[sid]['character_identifiers']}|set(scenes)
                for a in actions:
                    need(a.get('kind') in CUA_ACTIONS if isinstance(a.get('kind'),str) else False,cid+' CUA action invalid')
                    need(a.get('target_identifier') in targets if isinstance(a.get('target_identifier'),str) else False,cid+' CUA target unknown')
                    need(txt(a.get('observed_result')),cid+' CUA response missing')
                    aid=a.get('interaction_identifier')
                    if aid is not None:
                        declared={x['interaction_identifier']:x for sid in scope for x in scenes[sid]['interactions']}
                        interaction=declared.get(aid) if isinstance(aid,str) else None
                        need(interaction is not None and interaction['target_identifier']==a.get('target_identifier') and interaction['kind']==a.get('kind'),cid+' CUA interaction binding mismatch')
                        if interaction: tested_actions.add(aid)
                screenshots=[a for a in artifacts if a.get('kind')=='screenshot']
                need(bool(screenshots),cid+' CUA needs target viewport screenshot')
                for art in screenshots:
                    path=checked_file(art,cid+'.screenshot')
                    if path and path.suffix.lower()=='.png':
                        raw=path.read_bytes()
                        dims=struct.unpack('>II',raw[16:24]) if len(raw)>=24 and raw[:8]==b'\x89PNG\r\n\x1a\n' else None
                        vp=r.get('viewport',{})
                        need(isinstance(vp,dict) and dims==(vp.get('width'),vp.get('height')),cid+' CUA screenshot viewport size differs')
        coverage[cid]=(domain,scope,bound,device_coverage,tested_actions)
    common={'content','visual','motion','interaction','accessibility','recovery','performance'}
    if plan['learning']['audio_enabled']: common.add('audio')
    def cover(ids,needed,rd,label):
        for domain in common:
            covered=set()
            for cid,(d,s,b,devs,actions) in coverage.items():
                if cid in ids and d==domain and rd is not None and rd in b: covered|=s
            need(needed<=covered,label+' coverage missing for '+domain)
        for did in devices:
            covered=set()
            for cid,(d,s,b,devs,actions) in coverage.items():
                if cid in ids and d=='interaction' and rd in b and did in devs: covered|=s
            need(needed<=covered,label+' CUA device coverage missing: '+did)
        actions=set()
        for cid,(d,s,b,devs,a) in coverage.items():
            if cid in ids and d=='interaction' and rd is not None and rd in b: actions|=a
        expected={a['interaction_identifier'] for sid in needed for a in scenes[sid]['interactions']}
        need(expected<=actions,label+' CUA declared interaction coverage missing')
    if level>=2: cover(sample_checks,selected,candidate_digest,'representative')
    if level>=4:
        cover(set(checks),required,current_digest,'current final')
        for rule in plan['learning']['rules']:
            if rule['verification']=='executable':
                c=checks.get(rule.get('test_check_identifier'),{})
                need(c.get('domain')=='rule' and c.get('status')=='passed','current executable rule needs passed command check')
        need(all(s['verification_status']!='unverified' for s in plan['learning']['sources']),'final content has unverified sources')
    trial=m.get('learner_trial')
    if level>=5:
        need(isinstance(trial,dict) and trial.get('authorized') is True,'learner trial needs actual authorized participation')
        if isinstance(trial,dict):
            ref=trial.get('evidence_identifier'); r=receipts.get(ref) if isinstance(ref,str) else None
            need(r is not None and r.get('kind')=='experience_trial' and r.get('runtime_digest')==current_digest,'learner trial evidence missing/current version differs')
            if r:
                for k in ('observed_result','reviewed_by','participation_context','privacy_basis'): need(txt(r.get(k)),'learner trial missing '+k)
    return errors

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('manifest',type=Path); p.add_argument('--plan',required=True,type=Path); p.add_argument('--previous-manifest',type=Path); p.add_argument('--fingerprints',action='store_true'); a=p.parse_args()
    try:
        m=json.loads(a.manifest.read_text()); plan=json.loads(a.plan.read_text()); old=json.loads(a.previous_manifest.read_text()) if a.previous_manifest else None
        errors=validate_manifest(m,plan,a.manifest.parent,old)
        if a.fingerprints and not validate_plan(plan):
            print(json.dumps({'design_sha256':design_digest(plan),'representative_sha256':representative_digest(plan,m.get('representative',{}),m.get('checks',[]),m.get('evidence',[]))},ensure_ascii=False))
        for e in errors: print('ERROR: '+e)
        if not errors: print('VALID: structure and referenced evidence; actual quality requires review')
        return bool(errors)
    except (OSError,ValueError,KeyError,TypeError) as ex: print('ERROR: '+str(ex)); return 1

if __name__=='__main__': raise SystemExit(main())
