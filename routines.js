/* Guided routine player: built-in routines + custom routine creator. Progress is saved locally. */
(()=>{
const host=document.getElementById('routine-player');if(!host)return;
const I=window.TDC_I18N||{presets:[],groups:[]},P=I.presets,pid=id=>P.find(x=>x[0]===id);
const SK='tdc_routine',CK='tdc_custom_routines';
const mk=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e};
const btn=(t,f,c)=>{const b=mk('button',c||'',t);b.type='button';b.onclick=f;return b};
const MORNING=[
 {title:'Ayat al-Kursi',ar:'آية الكرسي',count:1,key:'ayat-al-kursi',note:'Qur’an 2:255. Read the full verse from your mushaf.'},
 {title:'Surah al-Ikhlas',ar:'سورة الإخلاص',count:3,key:'surah-ikhlas',note:'Qur’an 112, three times. Read it from your mushaf.'},
 {title:'Surah al-Falaq',ar:'سورة الفلق',count:3,key:'surah-falaq',note:'Qur’an 113, three times. Read it from your mushaf.'},
 {title:'Surah an-Nas',ar:'سورة الناس',count:3,key:'surah-nas',note:'Qur’an 114, three times. Read it from your mushaf.'},
 {id:'sbh',count:100,note:'Sahih Muslim 2692.'},
 {title:'Sayyid al-Istighfar',ar:'سيد الاستغفار',count:1,key:'sayyid-istighfar',note:'Sahih al-Bukhari 6306. Read the complete supplication from a reliable text.'}];
const BUILT={
 'after-salah':{name:'After salah: 33-33-34',guide:'/dhikr-after-salah',guideName:'After-salah guide',steps:[{id:'sub',count:33},{id:'alh',count:33},{id:'akb',count:34}]},
 'bedtime-34':{name:'Bedtime: 34-33-33',guide:'/tasbih-before-sleep',guideName:'Bedtime guide',steps:[{id:'akb',count:34},{id:'sub',count:33},{id:'alh',count:33}]},
 'bedtime-33':{name:'Bedtime, alternate order: 33-33-34',guide:'/tasbih-before-sleep',guideName:'Bedtime guide',steps:[{id:'sub',count:33},{id:'alh',count:33},{id:'akb',count:34}]},
 'morning':{name:'Morning adhkar (starter list)',guide:'/morning-evening-adhkar',guideName:'Morning and evening guide',steps:MORNING},
 'evening':{name:'Evening adhkar (starter list)',guide:'/morning-evening-adhkar',guideName:'Morning and evening guide',steps:MORNING}};
const load=k=>{try{return JSON.parse(localStorage.getItem(k)||'null')}catch(e){return null}};
const save=(k,v)=>{try{if(v===null)localStorage.removeItem(k);else localStorage.setItem(k,JSON.stringify(v))}catch(e){}};
const okSteps=a=>Array.isArray(a)&&a.length>0&&a.length<=20&&a.every(s=>s&&typeof s.id==='string'&&pid(s.id)&&Number.isInteger(s.count)&&s.count>=1&&s.count<=100000);
const customs=()=>{const c=load(CK);return Array.isArray(c)?c.filter(r=>r&&typeof r.name==='string'&&r.name&&r.name.length<=40&&okSteps(r.steps)).slice(0,10):[]};
let R=null,creating=false,draft=[];
const get=id=>{if(BUILT[id])return Object.assign({id},BUILT[id]);const m=/^custom:(\d+)$/.exec(id||'');const c=m&&customs()[+m[1]];return c?{id,name:c.name,guide:null,steps:c.steps}:null};
const persist=()=>save(SK,R&&!R.done?{id:R.id,i:R.i,counts:R.counts,paused:R.paused}:null);
function start(id,resume){const r=get(id);if(!r)return;R=Object.assign({},r,{i:0,counts:r.steps.map(()=>0),paused:false,done:false});
 if(resume&&Array.isArray(resume.counts)&&resume.counts.length===r.steps.length){R.counts=resume.counts.map((n,k)=>Math.max(0,Math.min(r.steps[k].count,n|0)));R.i=Math.max(0,Math.min(r.steps.length-1,resume.i|0));R.paused=!!resume.paused}
 persist();draw();host.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'})}
function draw(){host.textContent='';host.appendChild(mk('h2','','Guided routine player'));
 if(R)drawPlayer();else if(creating)drawCreator();else drawPicker();
 const live=mk('p','small');live.id='rpLive';live.setAttribute('role','status');live.setAttribute('aria-live','polite');host.appendChild(live)}
function say(t){const l=document.getElementById('rpLive');if(l)l.textContent=t}
function drawPicker(){
 host.appendChild(mk('p','small','Step-by-step routines with a counter for each step. Your place is saved on this device, so you can come back to an unfinished routine.'));
 const sv=load(SK);const sr=sv&&get(sv.id);
 if(sr&&Array.isArray(sv.counts)&&sv.counts.length===sr.steps.length){const b=mk('div','rp-resume');b.appendChild(mk('p','','Unfinished routine: '+sr.name+' (step '+(Math.min(sv.i|0,sr.steps.length-1)+1)+' of '+sr.steps.length+').'));
  b.appendChild(btn('Resume',()=>start(sv.id,sv)));b.appendChild(btn('Discard',()=>{if(confirm('Discard this unfinished routine?')){save(SK,null);draw()}}));host.appendChild(b)}
 const lab=mk('label','sr','Choose a routine');lab.htmlFor='rpSel';const sel=mk('select');sel.id='rpSel';
 const g1=mk('optgroup');g1.label='Built-in routines';Object.keys(BUILT).forEach(k=>{const o=mk('option','',BUILT[k].name);o.value=k;g1.appendChild(o)});sel.appendChild(g1);
 const cs=customs();if(cs.length){const g2=mk('optgroup');g2.label='My routines';cs.forEach((c,n)=>{const o=mk('option','',c.name);o.value='custom:'+n;g2.appendChild(o)});sel.appendChild(g2)}
 const q=new URLSearchParams(location.search).get('play');if(q&&get(q))sel.value=q;
 host.appendChild(lab);host.appendChild(sel);
 const row=mk('div','row');row.appendChild(btn('Start routine',()=>start(sel.value)));row.appendChild(btn('Create my own routine',()=>{creating=true;draft=[];draw()}));
 const del=btn('Delete this routine',()=>{const m=/^custom:(\d+)$/.exec(sel.value);if(m&&confirm('Delete this custom routine?')){const c=customs();c.splice(+m[1],1);save(CK,c);draw()}});del.hidden=true;row.appendChild(del);host.appendChild(row);
 sel.onchange=()=>{del.hidden=!/^custom:/.test(sel.value)};sel.onchange();
 const note=mk('p','small');note.appendChild(document.createTextNode('Counts and wording for the morning and evening list follow the '));const a=mk('a','','morning and evening guide');a.href='/morning-evening-adhkar';note.appendChild(a);note.appendChild(document.createTextNode('. Longer texts are not reproduced here: read them from a reliable mushaf or adhkar book.'));host.appendChild(note)}
function stepView(s){const p=s.id?pid(s.id):null;return{ar:p?p[1]:s.ar,tr:p?p[2]:s.title,mean:p?p[3]:'',note:s.note||'',key:s.id||s.key,speak:p?p[1]:''}}
function drawPlayer(){
 if(R.done){host.appendChild(mk('h3','','Routine complete. Masha’Allah!'));host.appendChild(mk('p','',R.name));
  const ul=mk('ul');R.steps.forEach((s,k)=>{const v=stepView(s);ul.appendChild(mk('li','',v.tr+': '+R.counts[k]+' of '+s.count))});host.appendChild(ul);
  const row=mk('div','row');row.appendChild(btn('Do it again',()=>start(R.id)));row.appendChild(btn('Back to counter',()=>{R=null;draw();window.scrollTo({top:0})}));
  if(R.guide){const a=mk('a','btn',R.guideName||'Read the guide');a.href=R.guide;row.appendChild(a)}host.appendChild(row);return}
 const s=R.steps[R.i],v=stepView(s),n=R.counts[R.i],rem=s.count-n,full=rem<=0;
 host.appendChild(mk('p','small',R.name+' · Step '+(R.i+1)+' of '+R.steps.length));
 const pr=mk('progress');pr.max=R.steps.length;pr.value=R.counts.filter((c,k)=>c>=R.steps[k].count).length;pr.setAttribute('aria-label','Routine progress');host.appendChild(pr);
 const ar=mk('div','ar',v.ar);ar.lang='ar';host.appendChild(ar);host.appendChild(mk('p','rp-tr',v.tr));if(v.mean)host.appendChild(mk('p','small',v.mean));if(v.note)host.appendChild(mk('p','small',v.note));
 const t=btn('',()=>tap(),'rp-tap');t.id='rpTap';t.disabled=R.paused||full;t.setAttribute('aria-label',full?'Step complete':R.paused?'Paused':'Count '+n+' of '+s.count+'. Tap to add one');
 t.appendChild(mk('span','',String(n)));t.appendChild(mk('span','small',R.paused?'paused':full?'done':'of '+s.count));host.appendChild(t);
 host.appendChild(mk('p','rp-rem',full?'Step complete.':rem+' remaining'));
 const row=mk('div','row');
 const prev=btn('Previous',()=>go(-1));prev.disabled=R.i===0;row.appendChild(prev);
 row.appendChild(btn(R.paused?'Resume':'Pause',()=>{R.paused=!R.paused;persist();draw();say(R.paused?'Paused':'Resumed')}));
 row.appendChild(btn(R.i===R.steps.length-1?'Finish':'Next',()=>go(1)));host.appendChild(row);
 const row2=mk('div','row');
 if(window.TDC_AUDIO){const l=btn(v.speak?'Listen':'Listen (recording only)',()=>window.TDC_AUDIO.play(v.key,v.speak,l));l.dataset.voicePlay='';row2.appendChild(l)}
 row2.appendChild(btn('Restart step',()=>{if(confirm('Restart this step from 0?')){R.counts[R.i]=0;persist();draw()}}));
 row2.appendChild(btn('Exit routine',()=>{if(confirm('Leave this routine? Your place is saved so you can resume later.')){R=null;draw()}}));host.appendChild(row2)}
function go(d){const j=R.i+d;if(j<0)return;if(j>=R.steps.length){finish();return}R.i=j;persist();draw();say('Step '+(j+1)+' of '+R.steps.length)}
function finish(){R.done=true;save(SK,null);draw();say('Routine complete')}
function tap(){if(!R||R.paused)return;const s=R.steps[R.i];if(R.counts[R.i]>=s.count)return;R.counts[R.i]++;
 if(s.id&&window.TDC)window.TDC.record(s.id,1);
 if(R.counts[R.i]>=s.count){if(navigator.vibrate)try{navigator.vibrate([80,40,80])}catch(e){}
  if(R.i===R.steps.length-1){finish();return}R.i++;persist();draw();say('Step complete. Next: step '+(R.i+1)+' of '+R.steps.length);return}
 persist();const b=document.getElementById('rpTap');if(b){b.firstChild.textContent=String(R.counts[R.i]);b.lastChild.textContent='of '+s.count;b.setAttribute('aria-label','Count '+R.counts[R.i]+' of '+s.count+'. Tap to add one')}
 const r=host.querySelector('.rp-rem');if(r)r.textContent=(s.count-R.counts[R.i])+' remaining';const pr=host.querySelector('progress');if(pr)pr.value=R.counts.filter((c,k)=>c>=R.steps[k].count).length}
function drawCreator(){
 host.appendChild(mk('h3','','Create your own routine'));
 const l1=mk('label','','Routine name (up to 40 characters)');const nm=mk('input');nm.type='text';nm.maxLength=40;nm.id='rpName';l1.htmlFor='rpName';host.appendChild(l1);host.appendChild(nm);
 const l2=mk('label','','Add a step');l2.htmlFor='rpDh';const sel=mk('select');sel.id='rpDh';(I.groups||[]).forEach(g=>{const og=mk('optgroup');og.label=({core:'Core dhikr',istighfar:'Istighfar',salawat:'Salawat',dua:'Duas and remembrance'})[g]||g;P.filter(x=>x[5]===g).forEach(x=>{const o=mk('option','',x[2]);o.value=x[0];og.appendChild(o)});sel.appendChild(og)});
 const l3=mk('label','','Target count (1-100000)');l3.htmlFor='rpCnt';const ct=mk('input');ct.type='number';ct.min=1;ct.max=100000;ct.value=33;ct.id='rpCnt';
 host.appendChild(l2);host.appendChild(sel);host.appendChild(l3);host.appendChild(ct);
 const list=mk('ol');list.id='rpList';
 const redraw=()=>{list.textContent='';draft.forEach((d,k)=>{const li=mk('li','',pid(d.id)[2]+' × '+d.count+' ');li.appendChild(btn('Remove',()=>{draft.splice(k,1);redraw()}));list.appendChild(li)})};
 const row=mk('div','row');row.appendChild(btn('Add step',()=>{const c=parseInt(ct.value,10);if(!Number.isInteger(c)||c<1||c>100000){say('Enter a whole number from 1 to 100000.');return}if(draft.length>=20){say('A routine can have up to 20 steps.');return}draft.push({id:sel.value,count:c});redraw();say('Step added.')}));host.appendChild(row);host.appendChild(list);
 const row2=mk('div','row');row2.appendChild(btn('Save routine',()=>{const name=nm.value.trim().slice(0,40);const c=customs();if(!name){say('Please enter a routine name.');return}if(!draft.length){say('Add at least one step.');return}if(c.length>=10){say('You can save up to 10 routines. Delete one first.');return}c.push({name,steps:draft.slice()});save(CK,c);creating=false;draft=[];draw();say('Routine saved.')}));
 row2.appendChild(btn('Cancel',()=>{creating=false;draw()}));host.appendChild(row2)}
draw();
if(new URLSearchParams(location.search).get('play')&&get(new URLSearchParams(location.search).get('play')))setTimeout(()=>host.scrollIntoView({block:'start'}),50);
})();
