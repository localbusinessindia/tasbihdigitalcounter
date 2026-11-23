/* Consent gate for advertising scripts.
   DORMANT BY DEFAULT: while ADS_CLIENT is empty this file does nothing (no banner, no requests).
   To enable ads see README-DEPLOY.md "Enabling ads": set ADS_CLIENT, swap in _headers.ads-enabled,
   and review privacy-policy.html. Google requires a Google-certified consent tool (CMP) for ads served
   in the EEA, UK and Switzerland - use AdSense "Privacy & messaging" for those regions. */
(()=>{
const ADS_CLIENT='';            // e.g. 'ca-pub-0000000000000000' once AdSense has approved the site
const KEY='tdc_consent';
if(!/^ca-pub-\d{10,20}$/.test(ADS_CLIENT))return;
let choice=null;try{choice=localStorage.getItem(KEY)}catch(e){}
const load=()=>{if(document.querySelector('script[data-tdc-ads]'))return;const s=document.createElement('script');s.async=true;s.crossOrigin='anonymous';s.dataset.tdcAds='1';s.src='https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client='+ADS_CLIENT;document.head.appendChild(s)};
const set=v=>{try{localStorage.setItem(KEY,v)}catch(e){}};
if(choice==='granted'){load();return}
if(choice==='denied')return;
const bar=document.createElement('div');bar.className='consent-bar';bar.setAttribute('role','dialog');bar.setAttribute('aria-label','Advertising choice');
bar.innerHTML='<p>This site may show ads. Allow advertising cookies? The counter works the same either way. <a href="/privacy-policy">Privacy policy</a></p>';
const mk=(t,v)=>{const b=document.createElement('button');b.type='button';b.textContent=t;b.onclick=()=>{set(v);bar.remove();if(v==='granted')load()};return b};
bar.appendChild(mk('Allow','granted'));bar.appendChild(mk('Decline','denied'));
document.body.appendChild(bar);
})();
