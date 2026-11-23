/* "Start counting" forms on guide pages: opens the counter with the dhikr and your own target. */
document.querySelectorAll('form[data-start-form]').forEach(f=>{f.addEventListener('submit',e=>{e.preventDefault();
 const d=f.dataset.dhikr,from=f.dataset.from||'',inp=f.querySelector('input'),v=parseInt(inp.value,10);
 const msg=f.querySelector('.start-msg');
 if(inp.value.trim()!==''&&(!Number.isInteger(v)||v<1||v>100000)){if(msg)msg.textContent='Enter a whole number from 1 to 100000, or leave it empty for no limit.';inp.focus();return}
 location.href='/?dhikr='+encodeURIComponent(d)+'&goal='+(inp.value.trim()===''?0:v)+(/^\/[a-z0-9-]{2,60}$/.test(from)?'&from='+from:'')})});
