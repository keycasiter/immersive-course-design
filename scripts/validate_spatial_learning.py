#!/usr/bin/env python3
"""Check a spatial-learning plan; never claims semantic, visual or learner acceptance."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from contract_checks import placeholder_paths

DOMAINS={'subject_rules','visual','motion','runtime','equivalent_path'}
def validate(data,blueprint,base,delivery=False):
    errors=[];base=Path(base)
    def need(ok,label):
        if not ok: errors.append(label)
    def obj(value,label):
        need(isinstance(value,dict),label+' must be object');return value if isinstance(value,dict) else {}
    def rows(value,label,empty=False):
        need(isinstance(value,list),label+' must be array')
        result=value if isinstance(value,list) else []
        need(all(isinstance(x,dict) for x in result),label+' requires objects')
        need(empty or bool(result),label+' must not be empty')
        return [x for x in result if isinstance(x,dict)]
    def text(value,label): need(isinstance(value,str) and bool(value.strip()),label+' must be text')
    def strings(value,label,empty=False):
        need(isinstance(value,list),label+' must be array');result=value if isinstance(value,list) else []
        need(empty or bool(result),label+' must not be empty')
        need(all(isinstance(x,str) and x.strip() for x in result),label+' requires text')
        valid=[x for x in result if isinstance(x,str)]
        need(len(set(valid))==len(valid),label+' has duplicates');return valid
    def index(value,key): return {x[key]:x for x in value if isinstance(x,dict) and isinstance(x.get(key),str)}
    def file_check(path,expected,label):
        try:
            if not isinstance(path,str) or not path: raise ValueError('missing file')
            p=Path(path);p=p if p.is_absolute() else base/p
            actual=hashlib.sha256(p.read_bytes()).hexdigest()
            need(actual==expected,label+' hash differs')
        except (OSError,ValueError) as exc: errors.append(label+': '+str(exc))
    data=obj(data,'plan');blueprint=obj(blueprint,'blueprint')
    errors.extend('unfilled template: '+str(p) for p in placeholder_paths(data))
    need(data.get('schema_version')=='1.0','spatial plan schema_version must be 1.0')
    need(data.get('experience_profile') in ('spatial_native_web','hybrid_web'),'invalid spatial experience_profile')
    need(data.get('runtime_mode')=='scene_state','spatial runtime_mode must be scene_state')
    for key in ('course_identifier','course_version'):
        text(data.get(key),key);need(data.get(key)==blueprint.get(key),key+' differs from blueprint')
    text(data.get('event_graph_version'),'event_graph_version')
    runtime=obj(data.get('runtime'),'runtime')
    for key in ('engine','engine_version','state_evaluation','clock_policy','rebuild_policy','context_loss_policy'):
        text(runtime.get(key),'runtime.'+key)
    fields=strings(runtime.get('checkpoint_fields'),'checkpoint_fields')
    need({'course_version','scene_identifier','task_identifier','object_state','parameters','camera','first_response','assistance','revision','focus'}.issubset(fields),'checkpoint_fields missing recovery state')
    scene_map=index(rows(blueprint.get('scenes'),'blueprint.scenes'),'scene_identifier')
    resources=index(rows(blueprint.get('media_resources'),'blueprint.media_resources'),'resource_identifier')
    objectives=index(rows(blueprint.get('learning_objectives'),'blueprint.learning_objectives'),'objective_identifier')
    sources=index(rows(blueprint.get('sources'),'blueprint.sources'),'source_identifier')
    scenes=rows(data.get('scenes'),'scenes');seen=set();actions_seen=set();action_count=0
    for row in scenes:
        sid=row.get('scene_identifier');text(sid,'scene_identifier')
        if not isinstance(sid,str):continue
        need(sid not in seen,'duplicate scene '+sid);seen.add(sid)
        original=scene_map.get(sid,{})
        need(bool(original),'unknown scene '+sid)
        target_ids=strings(row.get('objective_identifiers'),sid+'.objectives')
        need(set(target_ids).issubset(objectives) and set(target_ids).issubset(original.get('objective_identifiers',[])),sid+' objective references differ')
        beats=strings(row.get('beat_identifiers'),sid+'.beats')
        need(set(beats).issubset(original.get('beat_identifiers',[])),sid+' scene Beats differ')
        resource=row.get('media_resource_identifier')
        need(isinstance(resource,str) and resource in original.get('media_resource_identifiers',[]) and resource in resources,sid+' scene resource differs')
        if isinstance(resource,str) and resource in resources:
            need(resources[resource].get('media_type') in ('three_dimensional','diagram'),sid+' spatial resource must be three_dimensional or diagram')
        task_ids=strings(row.get('task_identifiers'),sid+'.tasks',True)
        original_task=original.get('task') or {};original_task=original_task if isinstance(original_task,dict) else {}
        allowed_tasks={original_task.get('task_identifier')}- {None}
        need(set(task_ids).issubset(allowed_tasks),sid+' task references differ')
        text(row.get('teaching_job'),sid+'.teaching_job')
        text(row.get('learning_action_decision'),sid+'.learning_action_decision')
        rep=obj(row.get('representation'),sid+'.representation')
        need(rep.get('route') in ('procedural','dcc_asset','hybrid'),sid+' invalid authoring route')
        for key in ('source_of_truth','units','coordinate_system'):text(rep.get(key),sid+'.'+key)
        names=set()
        for param in rows(rep.get('parameters'),sid+'.parameters',True):
            name=param.get('name');text(name,'parameter.name');text(param.get('unit'),'parameter.unit')
            if isinstance(name,str):need(name not in names,'duplicate parameter');names.add(name)
            values=[param.get(k) for k in ('min','max','default')]
            valid=all(type(v) in (int,float) and math.isfinite(v) for v in values)
            need(valid and values[0]<=values[2]<=values[1] and values[0]<values[1],sid+' invalid parameter domain')
        invariant_ids=set()
        for inv in rows(rep.get('invariants'),sid+'.invariants'):
            for key in ('invariant_identifier','statement','test_reference'):text(inv.get(key),sid+'.invariant.'+key)
            iid=inv.get('invariant_identifier')
            if isinstance(iid,str):need(iid not in invariant_ids,'duplicate invariant');invariant_ids.add(iid)
            refs=strings(inv.get('source_identifiers'),sid+'.invariant.sources')
            need(set(refs).issubset(sources),sid+' unknown invariant source')
        pres=obj(row.get('presentation'),sid+'.presentation')
        for key in ('attention_target','camera_and_projection','structure_and_look','labels_and_units','approximation_boundary'):text(pres.get(key),sid+'.'+key)
        actions=rows(row.get('learning_actions'),sid+'.learning_actions',True);action_count+=len(actions)
        for action in actions:
            for key in ('action_identifier','task_identifier','target','input','guard','transition_rule','visible_consequence','learning_evidence','feedback_and_retry'):text(action.get(key),sid+'.action.'+key)
            aid=action.get('action_identifier')
            if isinstance(aid,str):need(aid not in actions_seen,'duplicate action');actions_seen.add(aid)
            need(action.get('task_identifier') in task_ids,sid+' action task differs')
        for section,keys in [('continuity',('entry_condition','completion_rule','return_checkpoint')),('equivalent_path',('equivalent_task','keyboard_actions','reduced_motion','media_failure'))]:
            value=obj(row.get(section),sid+'.'+section)
            for key in keys:text(value.get(key),sid+'.'+section+'.'+key)
    need(action_count>0,'spatial learning requires at least one learning action')
    for sid,scene in scene_map.items():
        if scene.get('required') and any(resources.get(ref,{}).get('media_type')=='three_dimensional' for ref in scene.get('media_resource_identifiers',[])):
            need(sid in seen,'required spatial scene not covered: '+sid)
    output=obj(data.get('delivery'),'delivery')
    need(type(output.get('audio_included')) is bool,'audio_included must be boolean')
    if output.get('audio_included') is False:text(output.get('no_audio_rationale'),'no_audio_rationale')
    files=rows(output.get('files'),'delivery.files',not delivery)
    checks=rows(output.get('checks'),'delivery.checks',not delivery)
    if delivery:
        for f in files:file_check(f.get('path'),f.get('content_sha256'),'delivery file')
        domains=set()
        for check in checks:
            domain=check.get('domain');text(domain,'check.domain')
            if isinstance(domain,str):need(domain not in domains,'duplicate check domain');domains.add(domain)
            need(check.get('status')=='passed',str(domain)+' not passed')
            for key in ('reviewer','scope'):text(check.get(key),'check.'+key)
            file_check(check.get('evidence_file'),check.get('content_sha256'),str(domain)+' evidence')
        needed=DOMAINS|({'audio'} if output.get('audio_included') else set())
        need(needed.issubset(domains),'missing delivery evidence domains: '+', '.join(sorted(needed-domains)))
    return errors

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan',type=Path);parser.add_argument('--blueprint',required=True,type=Path)
    parser.add_argument('--delivery',action='store_true');args=parser.parse_args()
    try:
        errors=validate(json.loads(args.plan.read_text()),json.loads(args.blueprint.read_text()),args.plan.parent,args.delivery)
    except (OSError,ValueError) as exc: errors=[str(exc)]
    if errors:print('INVALID:\n'+'\n'.join('- '+x for x in errors));return 1
    print('VALID: spatial plan structure/references'+(' and current file fingerprints' if args.delivery else '')+'; semantics/visual/browser/learning acceptance NOT established');return 0
if __name__=='__main__':sys.exit(main())
