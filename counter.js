/* Tasbih Digital Counter - shared counter logic (English + language pages).
   Strings and dhikr presets come from /i18n.js (window.TDC_I18N). */
(()=>{
const $=s=>document.querySelector(s),C=565.5;
const I=window.TDC_I18N||{ui:{en:{}},presets:[],groups:[],m:{}};
const LANG=((document.documentElement.lang||'en').split('-')[0]);
const UI=Object.assign({},I.ui.en,I.ui[LANG]||{});
const T=(k,...a)=>String(UI[k]!==undefined?UI[k]:k).replace(/\{(\d+)\}/g,(m,i)=>a[i]!==undefined?a[i]:'');
const MEAN=(id,fallback)=>{if(LANG==='en')return fallback;const m=(I.m||{})[LANG];return m&&m[id]?m[id]:''};
const D=I.presets;
const SEQ=['sub','alh','akb'],SG=[33,33,34];
const SLEEP_ORDERS=[{seq:['akb','sub','alh'],goals:[34,33,33],label:'34-33-33'},{seq:['sub','alh','akb'],goals:[33,33,34],label:'33-33-34'}];
const sleepOrder=()=>SLEEP_ORDERS[S.sleepVariant?1:0];
let S={cur:'sub',goal:33,c:{},life:0,day:'',today:0,last:'',streak:0,sun:0,sleep:0,custom:[],vib:1,snd:0,wake:0,theme:'auto',dailyGoal:100,bestDay:0,bestCount:0,history:{},focus:0,sleepVariant:0,step:1,lastStep:1};
function clean(o){
 if(!o||typeof o!=='object'||Array.isArray(o))throw new Error('bad backup');
 const R={},n=(v,max)=>Number.isFinite(v)&&v>=0?Math.min(Math.floor(v),max):null,dre=/^\d{4}-\d{1,2}-\d{1,2}$/;
 for(const k of['life','today','streak']){const v=n(o[k],1e9);if(v!==null)R[k]=v}
 {const v=n(o.goal,1e5);if(v!==null)R.goal=v}
 {const v=n(o.step,1000);if(v!==null&&v>0)R.step=v}
 {const v=n(o.lastStep,1000);if(v!==null&&v>0)R.lastStep=v}
 for(const k of['sun','sleep','vib','snd','wake','focus','sleepVariant'])if(k in o)R[k]=o[k]?1:0;
 {const v=n(o.dailyGoal,1e5);if(v!==null&&v>0)R.dailyGoal=v}
 {const v=n(o.bestDay,1e9);if(v!==null)R.bestDay=v}
 {const v=n(o.bestCount,1e9);if(v!==null)R.bestCount=v}
 if(o.history&&typeof o.history==='object'&&!Array.isArray(o.history)){R.history={};for(const k of Object.keys(o.history).slice(-90)){const v=n(o.history[k],1e9);if(/^\d{4}-\d{1,2}-\d{1,2}$/.test(k)&&v!==null)R.history[k]=v}}
 if(o.sun&&o.sleep){R.sun=1;R.sleep=0}
 if(['auto','light','dark'].includes(o.theme))R.theme=o.theme;
 for(const k of['day','last'])if(typeof o[k]==='string'&&(o[k]===''||dre.test(o[k])))R[k]=o[k];
 if(o.c&&typeof o.c==='object'&&!Array.isArray(o.c)){R.c={};for(const k of Object.keys(o.c)){const v=n(o.c[k],1e9);if(/^(?:[a-z]{3}|c\d{1,16})$/.test(k)&&v!==null)R.c[k]=v}}
 if(Array.isArray(o.custom))R.custom=o.custom.filter(x=>Array.isArray(x)&&typeof x[0]==='string'&&/^c\d{1,16}$/.test(x[0])&&typeof x[2]==='string'&&x[2].trim()).slice(0,200).map(x=>[x[0],'',x[2].trim().slice(0,60),'',0]);
 if(typeof o.cur==='string')R.cur=o.cur;
 return R}
try{Object.assign(S,clean(JSON.parse(localStorage.getItem('tdc')||'{}')))}catch(e){}
if(!D.some(x=>x[0]===S.cur)&&!S.custom.some(x=>x[0]===S.cur))S.cur='sub';
const dstr=(o=0)=>{const d=new Date(Date.now()+o*864e5);return d.getFullYear()+'-'+(d.getMonth()+1)+'-'+d.getDate()};
const dh=id=>D.find(x=>x[0]==id)||S.custom.find(x=>x[0]==id)||D[0];
const params=new URLSearchParams(location.search);
if(params.get('routine')||params.get('study')||params.get('dhikr'))S.step=1;
if(params.get('routine')==='after-salah'){S.sun=1;S.sleep=0;S.cur='sub';S.goal=33}
else if(params.get('routine')==='bedtime'){S.sun=0;S.sleep=1;S.sleepVariant=params.get('variant')==='33-33-34'?1:0;const o=sleepOrder();S.cur=o.seq[0];S.goal=o.goals[0]}
else if(params.get('study')==='names'){S.sun=0;S.sleep=0;const id='c9999999999999999';if(!S.custom.some(x=>x[0]===id))S.custom.push([id,'',T('study'),'',0]);S.cur=id;S.goal=0}
else if(params.get('dhikr')&&D.some(x=>x[0]===params.get('dhikr'))){S.sun=0;S.sleep=0;S.cur=params.get('dhikr');const qgoal=parseInt(params.get('goal')||'',10);S.goal=params.get('goal')==='0'?0:(qgoal>0&&qgoal<=100000?qgoal:dh(S.cur)[4])}
let ac,lock,storageOk=true;
function tone(f,at,len,vol){try{ac=ac||new AudioContext();const o=ac.createOscillator(),g=ac.createGain(),t=ac.currentTime+at;o.frequency.value=f;g.gain.setValueAtTime(vol||.08,t);g.gain.exponentialRampToValueAtTime(.0001,t+len);o.connect(g);g.connect(ac.destination);o.start(t);o.stop(t+len+.02)}catch(e){}}
function beep(){tone(880,0,.04)}
function chime(){tone(660,0,.16,.1);tone(880,.18,.16,.1);tone(1175,.36,.32,.1)}
const vibrationSupported=typeof navigator!=='undefined'&&typeof navigator.vibrate==='function';
function vib(p){if(S.vib&&vibrationSupported){try{navigator.vibrate(p)}catch(e){}}}
function showDeviceNote(message){const note=$('#deviceNote'),btn=$('#vib');if(!note||!btn)return;if(!vibrationSupported){S.vib=0;btn.disabled=true;btn.textContent=T('vibUnavailable');btn.setAttribute('aria-pressed','false');note.textContent=message||T('noteUnsup');return}btn.disabled=false;btn.textContent=T('vib',S.vib?T('on'):T('off'));btn.setAttribute('aria-pressed',String(!!S.vib));note.textContent=message||(S.vib?T('noteOn'):T('noteOff'))}
function fill(){
 const sel=$('#dsel');sel.textContent='';
 const mk=x=>{const o=document.createElement('option');o.value=x[0];o.textContent=x[2];return o};
 (I.groups||[]).forEach(g=>{const items=D.filter(x=>x[5]===g);if(!items.length)return;const og=document.createElement('optgroup');og.label=T('g_'+g);items.forEach(x=>og.appendChild(mk(x)));sel.appendChild(og)});
 if(S.custom.length){const og=document.createElement('optgroup');og.label=T('g_mine');S.custom.forEach(x=>og.appendChild(mk(x)));sel.appendChild(og)}
 sel.value=S.cur}
function applyStatic(){
 document.querySelectorAll('[data-i]').forEach(e=>{e.textContent=T(e.dataset.i)});
 document.querySelectorAll('[data-ia]').forEach(e=>{e.setAttribute('aria-label',T(e.dataset.ia))});
}
const stepNow=()=>(S.sun||S.sleep)?1:Math.max(1,S.step||1);
function render(){
 const d=dh(S.cur),n=S.c[S.cur]||0,g=S.goal,st=stepNow();
 $('#ar').textContent=d[1];$('#tr').textContent=d[2];$('#mn').textContent=MEAN(d[0],d[3]);
 $('#n').textContent=n;$('#n').classList.remove('count-pop');void $('#n').offsetWidth;$('#n').classList.add('count-pop');$('#g').textContent=g?T('of',g):T('noLimit');
 $('#ring').style.strokeDashoffset=g?C*(1-Math.min(1,n/g)):C;
 if(S.day!==dstr()){S.day=dstr();S.today=S.history&&S.history[dstr()]?S.history[dstr()]:0}
 $('#st').textContent=S.today;$('#sl').textContent=S.life;$('#ss').textContent=(S.last===dstr()||S.last===dstr(-1))?S.streak:0;
 $('#best').textContent=S.bestCount||S.bestDay||0;
 $('#dailyProgress').textContent=Math.min(100,Math.round((S.today/Math.max(1,S.dailyGoal))*100))+'%';
 $('#dailyGoalBtn').textContent=T('dailyGoal',S.dailyGoal);
 $('#dailyGoalText').textContent=S.today>=S.dailyGoal?T('dayDone'):T('goalLeft',S.dailyGoal-S.today);
 $('#sleepOrder').textContent=T('sleepOrder',sleepOrder().label);
 $('#focus').setAttribute('aria-pressed',String(!!S.focus));
 document.body.classList.toggle('focus-mode',!!S.focus);
 $('#exitFocus').hidden=!S.focus;
 const ss=$('#stepSel');if(ss){if(![...ss.options].some(o=>+o.value===S.step)){const o=document.createElement('option');o.value=S.step;o.textContent=S.step;ss.appendChild(o)}ss.value=String(S.step||1);ss.disabled=!!(S.sun||S.sleep)}
 $('#tap').setAttribute('aria-label',st>1?T('tapAria2',n,g?T('of',g):T('noLimit'),st):T('tapAria',n,g?T('of',g):T('noLimit')));
 document.querySelectorAll('#goals [data-g]').forEach(b=>b.classList.toggle('on',+b.dataset.g===g));
 [['sun',S.sun],['sleep',S.sleep],['vib',S.vib],['snd',S.snd],['wake',S.wake]].forEach(([k,v])=>$('#'+k).setAttribute('aria-pressed',!!v));showDeviceNote();
 $('#dsel').value=S.cur;
 const t=S.theme;if(t=='auto')document.documentElement.removeAttribute('data-theme');else document.documentElement.dataset.theme=t;
 try{localStorage.setItem('tdc',JSON.stringify(S));storageOk=true}catch(e){if(storageOk){storageOk=false;$('#deviceNote').textContent=T('noStorage')}}
}
function tap(){
 const st=stepNow(),prev=S.c[S.cur]||0,n=S.c[S.cur]=prev+st;S.life+=st;S.today+=st;S.lastStep=st;
 S.history=S.history||{};S.history[dstr()]=(S.history[dstr()]||0)+st;
 const todayRecord=S.history[dstr()]||0;
 if(todayRecord>S.bestCount){S.bestCount=todayRecord;S.bestDay=dstr()}
 if(S.last!==dstr()){S.streak=S.last===dstr(-1)?S.streak+1:1;S.last=dstr()}
 const hit=S.goal&&n>=S.goal&&prev<S.goal;
 if(S.snd&&!hit)beep();
 if(hit){
  vib([120,60,120]);if(S.snd)chime();
  const bedtime=sleepOrder(),activeSeq=S.sleep?bedtime.seq:(S.sun?SEQ:null),activeGoals=S.sleep?bedtime.goals:(S.sun?SG:null);
  const i=activeSeq?activeSeq.indexOf(S.cur):-1;
  if(activeSeq&&i>-1&&i<2){S.cur=activeSeq[i+1];S.goal=activeGoals[i+1];$('#msg').textContent=T('next',dh(S.cur)[2])}
  else if(S.sleep||S.sun){$('#msg').textContent=S.sleep?T('bedDone'):T('salahDone');S.sun=0;S.sleep=0}
  else $('#msg').textContent=T('goalDone');
 }else{vib(12);$('#msg').textContent=''}
 render();
}
$('#tap').onclick=tap;
document.addEventListener('keydown',e=>{if(e.repeat||e.ctrlKey||e.metaKey||e.altKey)return;if((e.key==' '||e.key=='Enter')&&!/^(SELECT|INPUT|TEXTAREA|BUTTON|A|SUMMARY)$/.test(e.target.tagName)&&!e.target.isContentEditable){e.preventDefault();tap()}});
$('#dsel').onchange=e=>{S.cur=e.target.value;S.goal=dh(S.cur)[4];S.sun=0;S.sleep=0;$('#msg').textContent='';render()};
$('#goals').onclick=e=>{if(e.target.dataset.g!==undefined){S.goal=+e.target.dataset.g;render()}};
$('#cg').onclick=()=>{const v=parseInt(prompt(T('pGoal')),10);if(v>0&&v<=1e5){S.goal=v;render()}};
if($('#stepSel'))$('#stepSel').onchange=e=>{const v=parseInt(e.target.value,10);S.step=v>0&&v<=1000?v:1;render()};
$('#minus').onclick=()=>{const cur=S.c[S.cur]||0;if(cur>0){const u=Math.min(S.lastStep||1,cur);S.c[S.cur]=cur-u;S.life=Math.max(0,S.life-u);S.today=Math.max(0,S.today-u);S.history=S.history||{};S.history[dstr()]=Math.max(0,(S.history[dstr()]||0)-u);const entries=Object.entries(S.history);entries.sort((a,b)=>b[1]-a[1]);S.bestDay=entries.length?entries[0][0]:0;S.bestCount=entries.length?entries[0][1]:0;render()}};
$('#reset').onclick=()=>{if(confirm(T('confirmReset'))){S.c[S.cur]=0;$('#msg').textContent='';render()}};
$('#sun').onclick=()=>{S.sun=S.sun?0:1;S.sleep=0;if(S.sun){SEQ.forEach(k=>S.c[k]=0);S.cur='sub';S.goal=33}render()};
$('#sleep').onclick=()=>{S.sleep=S.sleep?0:1;S.sun=0;if(S.sleep){const o=sleepOrder();o.seq.forEach(k=>S.c[k]=0);S.cur=o.seq[0];S.goal=o.goals[0]}render()};
$('#sleepOrder').onclick=()=>{S.sleepVariant=S.sleepVariant?0:1;if(S.sleep){const o=sleepOrder();o.seq.forEach(k=>S.c[k]=0);S.cur=o.seq[0];S.goal=o.goals[0]}render()};
$('#dailyGoalBtn').onclick=()=>{const v=parseInt(prompt(T('pDaily'),String(S.dailyGoal)),10);if(Number.isInteger(v)&&v>0&&v<=100000){S.dailyGoal=v;render()}};
$('#focus').onclick=()=>{S.focus=S.focus?0:1;render()};
$('#exitFocus').onclick=()=>{S.focus=0;render()};
$('#shareCard').onclick=async()=>{
 const text=T('shareBody',S.today,S.dailyGoal,S.life);
 if(navigator.share){try{await navigator.share({title:T('shareTitle'),text})}catch(e){}}
 else if(navigator.clipboard&&navigator.clipboard.writeText){try{await navigator.clipboard.writeText(text);$('#msg').textContent=T('copied')}catch(e){alert(text)}}
 else alert(text);
};
$('#add').onclick=()=>{const t=(prompt(T('pName'))||'').trim().slice(0,60);if(t){const raw=prompt(T('pTarget'),'33');if(raw===null)return;const target=parseInt(raw,10);if(!Number.isInteger(target)||target<0||target>100000){alert(T('badTarget'));return}const id='c'+Date.now();S.custom.push([id,'',t,'',target]);S.cur=id;S.goal=target;S.sun=0;S.sleep=0;fill();render()}};
$('#vib').onclick=()=>{if(!vibrationSupported){showDeviceNote();return}S.vib=S.vib?0:1;let testMessage=S.vib?T('noteOn'):T('noteOff');if(S.vib){try{const ok=navigator.vibrate(60);testMessage=ok===false?T('testFail'):T('testOk')}catch(e){testMessage=T('testFail')}}else{try{navigator.vibrate(0)}catch(e){}}render();showDeviceNote(testMessage)};
$('#snd').onclick=()=>{S.snd=S.snd?0:1;if(S.snd)beep();render()};
async function lk(){try{if(S.wake&&'wakeLock' in navigator)lock=await navigator.wakeLock.request('screen');else if(lock){lock.release();lock=null}}catch(e){}}
$('#wake').onclick=()=>{S.wake=S.wake?0:1;lk();render()};
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&S.wake)lk()});
$('#theme').onclick=()=>{S.theme={auto:'light',light:'dark',dark:'auto'}[S.theme]||'auto';render()};
$('#exp').onclick=()=>{const a=document.createElement('a'),u=URL.createObjectURL(new Blob([JSON.stringify(S)],{type:'application/json'}));a.href=u;a.download='tasbih-backup.json';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),1500)};
$('#impbtn').onclick=()=>$('#imp').click();
$('#imp').onchange=e=>{const f=e.target.files[0];if(!f)return;if(f.size>1e6){alert(T('bigBackup'));e.target.value='';return}f.text().then(t=>{try{const c=clean(JSON.parse(t));if(!confirm(T('confirmImport'))){e.target.value='';return}Object.assign(S,c);if(!D.some(x=>x[0]===S.cur)&&!S.custom.some(x=>x[0]===S.cur))S.cur='sub';fill();render();$('#msg').textContent=T('imported')}catch(x){alert(T('badBackup'))}e.target.value=''})};
window.TDC={record(id,n){n=Math.max(1,n|0);if(id&&dh(id)&&dh(id)[0]===id)S.c[id]=(S.c[id]||0)+n;S.life+=n;S.today+=n;S.history=S.history||{};S.history[dstr()]=(S.history[dstr()]||0)+n;const r=S.history[dstr()];if(r>S.bestCount){S.bestCount=r;S.bestDay=dstr()}if(S.last!==dstr()){S.streak=S.last===dstr(-1)?S.streak+1:1;S.last=dstr()}render()}};
{const f=params.get('from'),bb=$('#backBar'),bl=$('#backGuide');if(bb&&bl&&f&&/^\/[a-z0-9-]{2,60}$/.test(f)){bl.href=f;bb.hidden=false}}
applyStatic();fill();render();
if('serviceWorker' in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{});
})();
