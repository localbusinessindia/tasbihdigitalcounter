/* Audio module: plays VERIFIED recordings listed in /audio/manifest.json when available,
   otherwise falls back to the browser's text-to-speech and labels it clearly as NOT a recording.
   No recordings are bundled in v2.6 (see audio/README.md). */
(()=>{
const synth=('speechSynthesis' in window&&'SpeechSynthesisUtterance' in window)?window.speechSynthesis:null;
const RATES={slow:{mp3:.75,tts:.7},normal:{mp3:1,tts:.85},fast:{mp3:1.25,tts:1}};
let manifest=null,mp=null,el=null,mode=null,activeBtn=null,paused=false,token=0;
const loadManifest=()=>mp||(mp=fetch('/audio/manifest.json').then(r=>r.ok?r.json():{items:{}}).catch(()=>({items:{}})).then(m=>(manifest=m)));
const usable=e=>!!(e&&e.file&&e.verified===true&&e.reciter&&e.source&&e.license&&/^\/audio\/[A-Za-z0-9._-]+\.(mp3|ogg|m4a)$/.test(e.file));
const $=s=>document.querySelector(s);
const speed=()=>RATES[($('#voiceRate')||{}).value||'normal']||RATES.normal;
const label=b=>b&&(b.dataset.compact?'▶':b.dataset.label||'Listen');
function status(t){const s=$('#voiceStatus');if(s)s.textContent=t||''}
function ui(){const pb=$('#voicePause');if(pb){pb.disabled=!mode;pb.textContent=paused?'Resume':'Pause'}const sb=$('#voiceStop');if(sb)sb.disabled=!mode;
 document.querySelectorAll('[data-voice-play]').forEach(b=>{const on=b===activeBtn&&!!mode;b.setAttribute('aria-pressed',String(on));b.textContent=on?(paused?'Paused':(b.dataset.compact?'■':'Playing…')):label(b)})}
function stop(silent){token++;if(el){el.onended=el.onerror=el.oncanplay=null;try{el.pause()}catch(e){}el=null}if(synth)synth.cancel();mode=null;paused=false;activeBtn=null;ui();if(!silent)status('')}
function pause(){if(!mode||paused)return;paused=true;if(mode==='mp3'&&el)el.pause();else if(synth)synth.pause();ui();status('Paused')}
function resume(){if(!mode||!paused)return;paused=false;if(mode==='mp3'&&el)el.play();else if(synth)synth.resume();ui();status(mode==='mp3'?status._rec||'':'Device voice (text-to-speech), not a recording')}
function tts(text,t,note){
 const v=(text||'').replace(/\s+/g,' ').trim();
 if(!v){status('No verified recording is available for this item yet.');stop(true);return}
 if(!synth){status('Audio is not available in this browser.');stop(true);return}
 const u=new SpeechSynthesisUtterance(v);u.lang='ar-SA';u.rate=speed().tts;
 const voice=synth.getVoices().find(x=>/^ar([_-]|$)/i.test(x.lang));if(voice)u.voice=voice;
 mode='tts';paused=false;ui();status((note?note+' ':'')+'Device voice (text-to-speech), not a recording.');
 u.onend=u.onerror=()=>{if(t===token)stop(true)};synth.speak(u)}
async function play(key,text,btn,opts){
 stop(true);const t=token;activeBtn=btn||null;mode='loading';ui();status('Loading…');
 const m=await loadManifest();if(t!==token)return;
 const e=m&&m.items&&key?m.items[key]:null;
 if(usable(e)){
  const a=new Audio(e.file);a.preload='auto';a.playbackRate=speed().mp3;el=a;
  const rec='Recording: '+e.reciter+' · '+e.source+' · '+e.license;status._rec=rec;
  a.oncanplay=()=>{if(t!==token)return;mode='mp3';ui();status(rec)};
  a.onended=()=>{if(t===token)stop(true)};
  a.onerror=()=>{if(t!==token)return;el=null;tts(text,t,'Recording could not be loaded.')};
  a.play().catch(()=>{if(t===token&&!el)return;});
 }else tts(text,t,'');
 if(opts&&opts.onStart)opts.onStart()}
const cleanText=n=>{const c=n.cloneNode(true);c.querySelectorAll('button').forEach(b=>b.remove());return c.textContent};
window.TDC_AUDIO={play,stop,pause,resume,usable};
const host=document.querySelector('.main-content')||document.body;
const panel=document.createElement('div');panel.className='voice-guide-panel';
panel.innerHTML='<strong>Audio guide</strong> <label>Speed <select id="voiceRate" aria-label="Playback speed"><option value="slow">Slow</option><option value="normal" selected>Normal</option><option value="fast">Fast</option></select></label> <button type="button" id="voicePause" disabled>Pause</button> <button type="button" id="voiceStop" disabled>Stop</button><p id="voiceStatus" role="status" aria-live="polite" class="small"></p><p class="small">Verified recordings are played when available and credited here. Otherwise your device’s text-to-speech reads the Arabic; that is not a recitation and may pronounce words incorrectly.</p>';
const h1=host.querySelector('h1');if(h1)h1.insertAdjacentElement('afterend',panel);else host.prepend(panel);
$('#voicePause').onclick=()=>paused?resume():pause();$('#voiceStop').onclick=()=>stop();
$('#voiceRate').onchange=()=>{if(el)el.playbackRate=speed().mp3};
const add=(node,key,compact)=>{if(node.dataset.voiceReady)return;node.dataset.voiceReady='1';
 const b=document.createElement('button');b.type='button';b.className=compact?'voice-inline':'voice-play';b.dataset.voicePlay='1';b.dataset.compact=compact?'1':'';b.dataset.label='Listen';
 b.setAttribute('aria-label',compact?'Listen to this Arabic name':'Listen to this Arabic text');b.textContent=label(b);
 b.addEventListener('click',()=>{if(activeBtn===b&&mode){stop();return}play(key(),cleanText(node),b)});
 if(compact)node.appendChild(b);else node.insertAdjacentElement('afterend',b)};
const cur=document.querySelector('#ar[lang="ar"]');
if(cur){const b=document.createElement('button');b.type='button';b.className='voice-play';b.dataset.voicePlay='1';b.dataset.label='Listen to selected dhikr';b.textContent=b.dataset.label;
 b.addEventListener('click',()=>{if(activeBtn===b&&mode){stop();return}const sel=$('#dsel');play(sel?sel.value:null,cur.textContent,b)});cur.insertAdjacentElement('afterend',b)}
document.querySelectorAll('.ar[lang="ar"], [lang="ar"].ar, td.a').forEach(n=>{
 if(n.id==='ar')return;
 if(n.matches('td.a')){const r=n.parentElement.firstElementChild;add(n,()=>'name-'+(r?r.textContent.trim():''),true)}
 else add(n,()=>n.dataset.audioKey||null,false)});
})();
