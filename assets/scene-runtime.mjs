// Scene-state orchestration only. The authored adapter provides real Three.js/DOM/audio behavior.
const clone=value=>structuredClone(value);
const plain=value=>value!==null&&typeof value==='object'&&!Array.isArray(value)&&Object.getPrototypeOf(value)===Object.prototype;
function serializable(value){
 if(value===null||typeof value==='string'||typeof value==='boolean')return;
 if(typeof value==='number'&&Number.isFinite(value))return;
 if(Array.isArray(value)){value.forEach(serializable);return;}
 if(plain(value)){for(const [key,v] of Object.entries(value)){if(['__proto__','constructor','prototype'].includes(key))throw Error('Unsafe state key');serializable(v);}return;}
 throw Error('State must contain finite serializable values');
}
function canonical(value){
 if(Array.isArray(value))return '['+value.map(canonical).join(',')+']';
 if(plain(value))return '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+canonical(value[k])).join(',')+'}';
 return JSON.stringify(value);
}
export function createExperienceController(inputPlan,adapter={}){
 serializable(inputPlan);const plan=clone(inputPlan);
 if(plan.schema_version!=='2.0')throw Error('Expected experience plan 2.0');
 const scenes=new Map(plan.learning.scenes.map(s=>[s.scene_identifier,s]));
 if(!scenes.has(plan.learning.entry_scene_identifier))throw Error('Unknown entry scene');
 const targetIds=new Set([...(plan.learning.objects||[]).map(o=>o.object_identifier),...(plan.learning.characters||[]).map(c=>c.character_identifier)]);
 // This structural signature prevents accidental stale restores; production file identity uses SHA256 separately.
 const signature=canonical({id:plan.experience_identifier,learning:plan.learning});
 let state={state_version:'2.0',experience_identifier:plan.experience_identifier,experience_version:plan.experience_version,design_signature:signature,scene:plan.learning.entry_scene_identifier,time:0,paused:true,events:{},objects:{},dialogue:{},view:{},notes:[]};
 function scene(){return scenes.get(state.scene);}
 function evaluate(){adapter.evaluate?.(clone(state));}
 function validate(candidate){
  serializable(candidate);
  if(candidate.state_version!=='2.0'||candidate.experience_identifier!==plan.experience_identifier||candidate.experience_version!==plan.experience_version||candidate.design_signature!==signature)throw Error('Checkpoint version/design differs');
  if(!scenes.has(candidate.scene)||!Number.isFinite(candidate.time)||candidate.time<0||typeof candidate.paused!=='boolean')throw Error('Invalid checkpoint scene/time');
  if(!plain(candidate.events)||!plain(candidate.objects)||!plain(candidate.dialogue)||!plain(candidate.view)||!Array.isArray(candidate.notes))throw Error('Invalid checkpoint state');
  if(Object.keys(candidate.objects).some(k=>!targetIds.has(k)))throw Error('Unknown object state');
  for(const [sid,ids] of Object.entries(candidate.events)){
   const s=scenes.get(sid);if(!s||!Array.isArray(ids)||new Set(ids).size!==ids.length||ids.some(id=>!s.events.some(e=>e.event_identifier===id)))throw Error('Unknown or duplicate checkpoint event');
  }
 }
 const controller={
  getState:()=>clone(state),
  act(identifier,payload=null){
   serializable(payload);const action=scene().interactions.find(a=>a.interaction_identifier===identifier);
   if(!action)throw Error('Unknown action in current scene');
   if(typeof adapter.act!=='function')throw Error('Action needs an authored implementation');
   const patch=adapter.act(clone(action),clone(payload),clone(state));
   if(!plain(patch)||Object.keys(patch).some(k=>!['objects','dialogue','view','notes'].includes(k)))throw Error('Adapter may only return object/dialogue/view/note state');
   const next={...state,...clone(patch)};validate(next);state=next;evaluate();
   // The host marks an event only after its actual visual/audio effect has been presented.
   return clone(state);
  },
  markEvent(identifier){
   if(!scene().events.some(e=>e.event_identifier===identifier))throw Error('Unknown event');
   const local=state.events[state.scene]||[];
   if(!local.includes(identifier))state.events={...state.events,[state.scene]:[...local,identifier]};
   evaluate();
  },
  continueTo(identifier){
   if(!scene().progression.next_scene_identifiers.includes(identifier)||!scenes.has(identifier))throw Error('Next scene not allowed');
   const events=state.events[state.scene]||[];
   if(scene().progression.required_event_identifiers.some(id=>!events.includes(id)))throw Error('Required event not presented');
   state={...state,scene:identifier,time:0};adapter.onSceneEnter?.(identifier,clone(state));evaluate();
  },
  tick(seconds){
   if(!Number.isFinite(seconds)||seconds<0)throw Error('Invalid time delta');
   if(!state.paused){state.time+=seconds;evaluate();}
  },
  seek(seconds){if(!Number.isFinite(seconds)||seconds<0)throw Error('Invalid scene time');state.time=seconds;evaluate();},
  pause(value=true){if(typeof value!=='boolean')throw Error('pause expects boolean');state.paused=value;evaluate();},
  snapshot(){
   const view=adapter.captureView?.();
   const next=view===undefined?clone(state):{...clone(state),view:clone(view)};
   validate(next);return next;
  },
  restore(snapshot){
   const next=clone(snapshot);validate(next);next.paused=true;state=next;
   adapter.onSceneEnter?.(state.scene,clone(state));adapter.restoreView?.(clone(state.view));evaluate();
  }
 };
 adapter.onSceneEnter?.(state.scene,clone(state));evaluate();return controller;
}
