/* 99 Names study tools: search, favourites, learned tracking, random name, learning cards. Progress stays on this device. */
(()=>{
const table=document.querySelector('.tw table');if(!table)return;
const rows=[...table.querySelectorAll('tr')].slice(1);if(rows.length<90)return;
const SK='tdc_names';let st={fav:[],learned:[]};
try{const v=JSON.parse(localStorage.getItem(SK)||'null');if(v&&Array.isArray(v.fav)&&Array.isArray(v.learned))st={fav:v.fav.filter(n=>n>=1&&n<=99),learned:v.learned.filter(n=>n>=1&&n<=99)}}catch(e){}
const save=()=>{try{localStorage.setItem(SK,JSON.stringify(st))}catch(e){}};
const mk=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e};
const btn=(t,f)=>{const b=mk('button','',t);b.type='button';b.onclick=f;return b};
const norm=s=>s.normalize('NFKD').replace(/[\u064B-\u065F\u0670\u06D6-\u06ED\u0300-\u036f]/g,'').replace(/ٱ/g,'ا').toLowerCase().replace(/['’`-]/g,'');
const data=rows.map(r=>{const c=r.children;return{n:+c[0].textContent.trim(),ar:c[1].childNodes[0]?c[1].childNodes[0].textContent:'',tr:c[2].querySelector('b')?c[2].querySelector('b').textContent:'',mean:c[2].lastChild?c[2].lastChild.textContent:'',row:r}});
// extra columns
const hr=table.querySelector('tr');['Favourite','Learned'].forEach(t=>hr.appendChild(Object.assign(mk('th','names-col'),{textContent:t})));
data.forEach(d=>{
 const f=btn('☆',()=>{const i=st.fav.indexOf(d.n);if(i<0)st.fav.push(d.n);else st.fav.splice(i,1);save();paint(d);filter()});f.setAttribute('aria-label','Favourite '+d.tr);
 const l=mk('input');l.type='checkbox';l.setAttribute('aria-label','Mark '+d.tr+' as learned');l.onchange=()=>{const i=st.learned.indexOf(d.n);if(l.checked&&i<0)st.learned.push(d.n);if(!l.checked&&i>-1)st.learned.splice(i,1);save();stats()};
 const c1=mk('td','names-col');c1.appendChild(f);const c2=mk('td','names-col');c2.appendChild(l);d.row.appendChild(c1);d.row.appendChild(c2);d.f=f;d.l=l;d.key=norm(d.n+' '+d.ar+' '+d.tr+' '+d.mean);paint(d)});
function paint(d){const on=st.fav.includes(d.n);d.f.textContent=on?'★':'☆';d.f.setAttribute('aria-pressed',String(on));d.l.checked=st.learned.includes(d.n)}
// tools panel
const tools=mk('div','names-tools card');
const lab=mk('label','','Search the Names (number, Arabic, transliteration or meaning)');lab.htmlFor='nmSearch';const q=mk('input');q.type='search';q.id='nmSearch';q.autocomplete='off';
const row=mk('div','row');let favOnly=false;
const favB=btn('Show favourites only',()=>{favOnly=!favOnly;favB.setAttribute('aria-pressed',String(favOnly));favB.textContent=favOnly?'Showing favourites':'Show favourites only';filter()});favB.setAttribute('aria-pressed','false');
const rndB=btn('Random name',()=>{const d=data[Math.floor(Math.random()*data.length)];show(d,true)});
const lrnB=btn('Learning mode',()=>openLearn());
const cnt=mk('a','btn','Count while studying');cnt.href='/?study=names&from=/99-names-of-allah';
const rst=btn('Reset my progress',()=>{if(confirm('Clear your favourites and learned Names on this device?')){st={fav:[],learned:[]};save();data.forEach(paint);filter();stats();say('Progress cleared.')}});
[favB,rndB,lrnB,cnt,rst].forEach(x=>row.appendChild(x));
const prog=mk('p','small');prog.id='nmProg';const live=mk('p','small');live.setAttribute('role','status');live.setAttribute('aria-live','polite');
const card=mk('div','names-card');card.hidden=true;
tools.append(lab,q,row,prog,live,card);
table.closest('.tw').insertAdjacentElement('beforebegin',tools);
function say(t){live.textContent=t}
function stats(){prog.textContent='Learned: '+st.learned.length+' of 99 · Favourites: '+st.fav.length+'. Saved on this device only.'}
function filter(){const k=norm(q.value.trim());let shown=0;data.forEach(d=>{const ok=(!k||d.key.includes(k))&&(!favOnly||st.fav.includes(d.n));d.row.hidden=!ok;if(ok)shown++});say(k||favOnly?shown+' of 99 Names shown.':'')}
q.oninput=filter;
function show(d,scroll){card.hidden=false;card.textContent='';card.appendChild(mk('p','small','Name '+d.n+' of 99'));const a=mk('div','ar',d.ar);a.lang='ar';card.appendChild(a);card.appendChild(mk('p','',d.tr+' — '+d.mean));
 const r=mk('div','row');const l=btn('Listen',()=>window.TDC_AUDIO&&window.TDC_AUDIO.play('name-'+d.n,d.ar,l));l.dataset.voicePlay='';r.appendChild(l);r.appendChild(btn('Close',()=>{card.hidden=true;card.textContent=''}));card.appendChild(r);
 if(scroll)card.scrollIntoView({block:'center',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'})}
function openLearn(){
 const pool=()=>{const left=data.filter(d=>!st.learned.includes(d.n));return left.length?left:null};
 const next=()=>{const p=pool();card.hidden=false;card.textContent='';
  if(!p){card.appendChild(mk('p','','You have marked all 99 Names as learned. Reset your progress to practise again.'));card.appendChild(btn('Close',()=>{card.hidden=true}));return}
  const d=p[Math.floor(Math.random()*p.length)];
  card.appendChild(mk('p','small','Learning mode · '+(99-p.length)+' learned, '+p.length+' to go'));const a=mk('div','ar',d.ar);a.lang='ar';card.appendChild(a);
  const ans=mk('p','',d.tr+' — '+d.mean);ans.hidden=true;card.appendChild(ans);
  const r1=mk('div','row'),r2=mk('div','row');r2.hidden=true;
  const reveal=btn('Show meaning',()=>{ans.hidden=false;r2.hidden=false;reveal.hidden=true;say('Meaning shown.')});r1.appendChild(reveal);
  const l=btn('Listen',()=>window.TDC_AUDIO&&window.TDC_AUDIO.play('name-'+d.n,d.ar,l));l.dataset.voicePlay='';r1.appendChild(l);
  r2.appendChild(btn('I knew it',()=>{if(!st.learned.includes(d.n))st.learned.push(d.n);save();paint(d);stats();next()}));
  r2.appendChild(btn('Still learning',()=>next()));r1.appendChild(btn('Exit',()=>{card.hidden=true;card.textContent=''}));
  card.appendChild(r1);card.appendChild(r2)};
 next();card.scrollIntoView({block:'center',behavior:'auto'})}
stats();
})();
