"""Current experience contract. Structural checks do not assert learning or visual quality."""
import hashlib
import json
import re
import math

ACTION_KINDS = {'inspect', 'approach', 'viewpoint', 'follow', 'manipulate', 'dialogue', 'choose', 'read'}
ASSESSMENT_FIELDS = {'correct_answer', 'expected_answer', 'grading', 'score', 'pass_score', 'quiz', 'exam', 'exercise', 'retry_until_correct', 'mastery_level'}
STAGES = ['design_draft', 'design_confirmed', 'representative_confirmed', 'production_complete', 'functional_accepted', 'learner_trial_complete']

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def file_digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def design_digest(plan):
    return digest({'schema_version': plan['schema_version'], 'experience_identifier': plan['experience_identifier'], 'learning': plan['learning']})

def runtime_digest(files):
    return digest(sorted([{'file_identifier': x['file_identifier'], 'path': x['path'], 'content_sha256': x['content_sha256']} for x in files], key=lambda x: x['file_identifier']))

def representative_digest(plan, rep, checks, evidence=()):
    selected = set(rep.get('scene_identifiers', []))
    presentation = {k: v for k, v in plan['presentation'].items() if k != 'scene_views'}
    presentation['scene_views'] = [v for v in plan['presentation']['scene_views'] if v.get('scene_identifier') in selected]
    chosen = [c for c in checks if c.get('check_identifier') in rep.get('check_identifiers', [])]
    refs = {r for c in chosen for r in c.get('evidence_identifiers', [])}
    return digest({'design_sha256': design_digest(plan), 'presentation': presentation, 'scenes': sorted(selected), 'candidate_files': rep.get('candidate_files', []), 'checks': chosen, 'evidence': [e for e in evidence if e.get('evidence_identifier') in refs]})

def validate_plan(plan):
    errors = []
    def need(condition, message):
        if not condition: errors.append(message)
    def obj(value, label):
        need(isinstance(value, dict), label + ' must be object')
        return value if isinstance(value, dict) else {}
    def rows(value, label, empty=True):
        need(isinstance(value, list), label + ' must be array')
        value = value if isinstance(value, list) else []
        need(empty or bool(value), label + ' must not be empty')
        need(all(isinstance(x, dict) for x in value), label + ' requires objects')
        return [x for x in value if isinstance(x, dict)]
    def text(value, label): need(isinstance(value, str) and bool(value.strip()), label + ' must be text')
    def strings(value, label, empty=True):
        need(isinstance(value, list), label + ' must be array')
        value = value if isinstance(value, list) else []
        need(empty or bool(value), label + ' must not be empty')
        need(all(isinstance(x, str) and x for x in value), label + ' requires identifiers/text')
        valid = [x for x in value if isinstance(x, str)]
        need(len(valid) == len(set(valid)), label + ' duplicates')
        return valid
    def index(value, field, label, empty=True):
        result = {}
        for row in rows(value, label, empty):
            key = row.get(field); text(key, label + '.' + field)
            if isinstance(key, str):
                need(bool(re.fullmatch(r'[a-z][a-z0-9_-]*', key)), label + ' invalid identifier')
                need(key not in result, label + ' duplicate identifier'); result[key] = row
        return result
    def refs(value, allowed, label, empty=True):
        values = strings(value, label, empty)
        need(set(values).issubset(allowed), label + ' unknown reference')
        return values
    def walk(value, path='plan'):
        if isinstance(value, dict):
            for key, val in value.items():
                need(key not in ASSESSMENT_FIELDS, path + '.' + key + ': assessment field is outside this experience contract')
                walk(val, path + '.' + key)
        elif isinstance(value, list):
            for i, val in enumerate(value): walk(val, path + '[' + str(i) + ']')
        elif isinstance(value, str): need(not re.search(r'\{\{.*?\}\}', value), path + ': unfilled placeholder')
        elif isinstance(value, float): need(math.isfinite(value), path + ': number must be finite')
    plan = obj(plan, 'plan'); walk(plan)
    need(plan.get('schema_version') == '2.0', 'schema_version must be 2.0; historical packages are not automatically migrated')
    need(plan.get('profile') == 'threejs_experience', 'profile must be threejs_experience')
    for key in ('experience_identifier', 'experience_version'): text(plan.get(key), key)
    learning = obj(plan.get('learning'), 'learning')
    for key in ('title', 'learner_context', 'experience_promise', 'audio_rationale'): text(learning.get(key), 'learning.' + key)
    strings(learning.get('understanding_focus'), 'understanding_focus', False)
    need(type(learning.get('audio_enabled')) is bool, 'audio_enabled must be boolean')
    sources = index(learning.get('sources'), 'source_identifier', 'sources', False)
    for sid, source in sources.items():
        for key in ('title', 'reference', 'supports'): text(source.get(key), sid + '.' + key)
        need(source.get('verification_status') in ('verified', 'provided', 'unverified'), sid + ' invalid verification status')
    content = index(learning.get('required_content'), 'content_identifier', 'required_content', False)
    for cid, item in content.items(): text(item.get('description'), cid + '.description'); refs(item.get('source_identifiers'), sources, cid + '.source', False)
    rules = index(learning.get('rules'), 'rule_identifier', 'rules')
    for rid, rule in rules.items():
        text(rule.get('statement'), rid + '.statement'); refs(rule.get('source_identifiers'), sources, rid + '.source', False)
        need(rule.get('verification') in ('source_review', 'executable'), rid + ' invalid verification')
        if rule.get('verification') == 'executable': text(rule.get('test_check_identifier'), rid + '.test_check_identifier')
    objects = index(learning.get('objects'), 'object_identifier', 'objects')
    for oid, item in objects.items():
        text(item.get('meaning'), oid + '.meaning'); refs(item.get('source_identifiers'), sources, oid + '.source')
        refs(item.get('rule_identifiers'), rules, oid + '.rules')
    characters = index(learning.get('characters'), 'character_identifier', 'characters')
    for cid, item in characters.items():
        for key in ('identity_basis', 'participation'): text(item.get(key), cid + '.' + key)
        need(type(item.get('fictional')) is bool, cid + '.fictional must be boolean')
        refs(item.get('source_identifiers'), sources, cid + '.source', item.get('fictional') is True)
        intro = obj(item.get('introduction'), cid + '.introduction')
        for key in ('text', 'trigger', 'anchor'): text(intro.get(key), cid + '.introduction.' + key)
    need(not set(objects).intersection(characters), 'object and character identifiers must be distinct')
    scenes = index(learning.get('scenes'), 'scene_identifier', 'scenes', False)
    entry = learning.get('entry_scene_identifier'); need(isinstance(entry, str) and entry in scenes, 'entry scene is unknown')
    all_actions = {}; all_events = set(); covered = set()
    for sid, scene in scenes.items():
        for key in ('title', 'orientation'): text(scene.get(key), sid + '.' + key)
        need(type(scene.get('required')) is bool, sid + '.required must be boolean')
        local_content = refs(scene.get('content_identifiers'), content, sid + '.content')
        if scene.get('required'): covered.update(local_content)
        object_refs = refs(scene.get('object_identifiers'), objects, sid + '.objects')
        char_refs = refs(scene.get('character_identifiers'), characters, sid + '.characters')
        perception = obj(scene.get('perception'), sid + '.perception')
        for key in ('see', 'hear', 'relationship'): text(perception.get(key), sid + '.perception.' + key)
        events = index(scene.get('events'), 'event_identifier', sid + '.events')
        for eid, event in events.items():
            need(eid not in all_events, 'event identifier must be globally unique'); all_events.add(eid)
            for key in ('trigger', 'visible_change'): text(event.get(key), eid + '.' + key)
        actions = index(scene.get('interactions'), 'interaction_identifier', sid + '.interactions')
        for aid, action in actions.items():
            need(aid not in all_actions, 'interaction identifier must be globally unique'); all_actions[aid] = action
            need(isinstance(action.get('kind'), str) and action['kind'] in ACTION_KINDS, aid + ' invalid interaction kind')
            need(action.get('target_identifier') in object_refs + char_refs, aid + ' target must be present in scene')
            for key in ('invitation', 'response', 'visible_consequence', 'accessibility_equivalent'): text(action.get(key), aid + '.' + key)
            emitted = action.get('emits_event_identifier'); need(emitted is None or (isinstance(emitted,str) and emitted in events), aid + ' unknown emitted event')
        progression = obj(scene.get('progression'), sid + '.progression')
        refs(progression.get('next_scene_identifiers'), scenes, sid + '.next')
        refs(progression.get('required_event_identifiers'), events, sid + '.required_events')
        text(progression.get('rationale'), sid + '.progression.rationale')
    need(bool(all_actions), 'experience must provide genuine participation, not only passive playback')
    need(set(content) <= covered, 'required content coverage is incomplete')
    seen = set(); pending = [entry] if isinstance(entry, str) else []
    while pending:
        sid = pending.pop()
        if sid in seen or sid not in scenes: continue
        seen.add(sid)
        value = scenes[sid].get('progression', {})
        if isinstance(value, dict) and isinstance(value.get('next_scene_identifiers'),list): pending.extend(x for x in value['next_scene_identifiers'] if isinstance(x, str))
    for sid, scene in scenes.items(): need(not scene.get('required') or sid in seen, 'required scene unreachable: ' + sid)
    need(not scenes or any(not s.get('progression', {}).get('next_scene_identifiers') for s in scenes.values() if isinstance(s.get('progression'), dict)), 'experience needs a declared exit scene')
    access = obj(learning.get('accessibility'), 'accessibility')
    for key in ('keyboard', 'reduced_motion', 'silent', 'graphics_failure'): text(access.get(key), 'accessibility.' + key)
    pres = obj(plan.get('presentation'), 'presentation')
    for key in ('style_goal', 'structure_goal', 'lighting_and_materials', 'viewpoint_policy', 'typography_and_safety'): text(pres.get(key), 'presentation.' + key)
    devices = index(pres.get('target_devices'), 'device_identifier', 'target_devices', False)
    for did, device in devices.items():
        viewport = obj(device.get('viewport'), did + '.viewport')
        need(all(type(viewport.get(k)) is int and viewport[k] > 0 for k in ('width', 'height')), did + ' invalid viewport')
        text(device.get('acceptance_goal'), did + '.acceptance_goal')
    views = index(pres.get('scene_views'), 'scene_identifier', 'scene_views', False)
    need(set(views) == set(scenes), 'scene_views must cover declared scenes exactly')
    for sid, view in views.items():
        for key in ('camera_and_projection', 'attention_target', 'detail_and_motion'): text(view.get(key), sid + '.view.' + key)
    profiles = index(pres.get('character_profiles'), 'character_identifier', 'character_profiles')
    need(set(profiles) == set(characters), 'character profiles must match actual characters')
    for cid, profile in profiles.items():
        for key in ('form_and_identity', 'speech_and_motion'): text(profile.get(key), cid + '.' + key)
    resources = index(plan.get('resources'), 'resource_identifier', 'resources')
    for rid, resource in resources.items():
        need(resource.get('kind') in ('audio', 'image', 'texture', 'font', 'document'), rid + ' unsupported resource kind')
        for key in ('file', 'purpose'): text(resource.get(key), rid + '.' + key)
        gov = obj(resource.get('governance'), rid + '.governance')
        for key in ('source', 'rights', 'privacy', 'disclosure', 'retention', 'equivalent_path'): text(gov.get(key), rid + '.governance.' + key)
    for profile in profiles.values():
        ref=profile.get('voice_reference')
        need(ref is None or (isinstance(ref,str) and ref in resources and resources[ref].get('kind')=='audio'), 'unknown character voice resource')
    for scene in scenes.values():
        for event in rows(scene.get('events'), 'events'):
            ref = event.get('sound_resource_identifier')
            need(ref is None or (isinstance(ref,str) and ref in resources and resources[ref].get('kind') == 'audio'), 'unknown sound resource')
    impl = obj(plan.get('implementation'), 'implementation')
    need(impl.get('engine') == 'threejs', 'engine must be threejs')
    for key in ('engine_version', 'entry_file', 'clock_policy', 'lifecycle_policy'): text(impl.get(key), 'implementation.' + key)
    source_files = strings(impl.get('source_files'), 'source_files', False)
    bindings = index(impl.get('bindings'), 'interaction_identifier', 'bindings')
    need(set(bindings) == set(all_actions), 'runtime binding coverage differs from declared interactions')
    for aid, binding in bindings.items():
        for key in ('locator', 'handler'): text(binding.get(key), aid + '.binding.' + key)
    rule_bindings = index(impl.get('rule_bindings'), 'rule_identifier', 'rule_bindings')
    need(set(rule_bindings) == set(rules), 'rule binding coverage differs')
    for rid, binding in rule_bindings.items():
        need(binding.get('source_file') in source_files, rid + ' rule source must be declared')
        text(binding.get('export_name'), rid + '.export_name')
    api = obj(impl.get('state_api'), 'state_api')
    for key in ('evaluate', 'act', 'snapshot', 'restore'): text(api.get(key), 'state_api.' + key)
    return errors

def compile_design(plan):
    l = plan['learning']
    out = ['# ' + l['title'], '', l['experience_promise'], '', '## 理解关注', '']
    out += ['- ' + value for value in l['understanding_focus']]
    out += ['', '## 学习者与支持', '', l['learner_context'], '', '## 内容与来源', '']
    out += ['- ' + x['content_identifier'] + '：' + x['description'] for x in l['required_content']]
    out += ['- ' + s['source_identifier'] + ' · ' + s['title'] + '：' + s['reference'] + '；' + s['supports'] + '（' + s['verification_status'] + '）' for s in l['sources']]
    out += ['', '声音方案：' + l['audio_rationale'], '', '## 对象与含义', '']
    out += ['- ' + o['object_identifier'] + '：' + o['meaning'] + '；规则：' + ', '.join(o['rule_identifiers']) for o in l['objects']]
    for scene in l['scenes']:
        out += ['', '## ' + scene['title'] + ' · ' + scene['scene_identifier'], '', '范围：' + ('必需' if scene['required'] else '可选') + '；内容：' + ', '.join(scene['content_identifiers']), '', scene['orientation'], '', '画面：' + scene['perception']['see'], '', '声音：' + scene['perception']['hear'], '', '关系：' + scene['perception']['relationship']]
        for event in scene['events']: out += ['', '事件 ' + event['event_identifier'] + '：' + event['trigger'] + ' → ' + event['visible_change']]
        for action in scene['interactions']: out += ['', '### ' + action['invitation'], '', '参与：' + action['interaction_identifier'] + ' · ' + action['kind'] + ' → ' + action['target_identifier'], '', action['response'], '', '现场回应：' + action['visible_consequence'], '', '等价参与：' + action['accessibility_equivalent']]
        out += ['', '接续：' + scene['progression']['rationale'], '', '后继：' + ', '.join(scene['progression']['next_scene_identifiers']) + '；必要事件：' + ', '.join(scene['progression']['required_event_identifiers'])]
    out += ['', '## 规则与人物', '']
    out += ['- ' + r['rule_identifier'] + '：' + r['statement'] for r in l['rules']]
    out += ['- ' + c['character_identifier'] + '：' + c['identity_basis'] + '；' + c['participation'] + '；' + ('虚构' if c['fictional'] else '有据身份') + '；首次介绍：' + c['introduction']['text'] + '；触发：' + c['introduction']['trigger'] + '；位置：' + c['introduction']['anchor'] for c in l['characters']]
    out += ['', '## 等价体验', ''] + [k + '：' + v for k, v in l['accessibility'].items()]
    return '\n'.join(out) + '\n'

def compile_index(plan):
    return {'schema_version': '2.0', 'experience_identifier': plan['experience_identifier'], 'experience_version': plan['experience_version'], 'design_sha256': design_digest(plan), 'scenes': [{'scene_identifier': s['scene_identifier'], 'required': s['required'], 'interaction_identifiers': [a['interaction_identifier'] for a in s['interactions']], 'event_identifiers': [e['event_identifier'] for e in s['events']], 'next_scene_identifiers': s['progression']['next_scene_identifiers']} for s in plan['learning']['scenes']]}
