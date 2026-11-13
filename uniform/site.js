(()=>{'use strict';
const header=document.querySelector('header');
if(header){const sync=()=>document.documentElement.style.setProperty('--header-height',header.getBoundingClientRect().height+'px');sync();new ResizeObserver(sync).observe(header)}
document.querySelectorAll('.cabinet').forEach(c=>{const s=c.querySelector('.shelf'),buttons=c.querySelectorAll('.shelf-controls button');if(!s||buttons.length!==2)return;const sign=document.documentElement.dir==='rtl'?-1:1;const update=()=>{const offset=Math.abs(s.scrollLeft);buttons[0].disabled=offset<2;buttons[1].disabled=offset+s.clientWidth>=s.scrollWidth-2};buttons[0].onclick=()=>s.scrollBy({left:-sign*(s.clientWidth+15),behavior:'smooth'});buttons[1].onclick=()=>s.scrollBy({left:sign*(s.clientWidth+15),behavior:'smooth'});s.addEventListener('scroll',update);window.addEventListener('resize',update);requestAnimationFrame(update)});
document.querySelectorAll('.research-enter').forEach(a=>a.addEventListener('click',()=>{const ref=a.getAttribute('href');if(ref&&ref.startsWith('#')){const d=document.querySelector(ref);if(d)d.open=true}}));
document.querySelectorAll('.print-page').forEach(b=>b.onclick=()=>window.print());
const form=document.getElementById('contact-form');
if(form)form.addEventListener('submit',e=>{e.preventDefault();const d=new FormData(form);const body='Name: '+String(d.get('name')||'').trim()+'\nReply email: '+String(d.get('email')||'').trim()+'\nInquiry type: '+String(d.get('topic')||'')+'\n\n'+String(d.get('message')||'').trim();const status=document.getElementById('contact-status');if(status)status.hidden=false;location.href='mailto:cjean-pierre@captechu.edu?subject='+encodeURIComponent(String(d.get('topic')||'CRSIS-47 inquiry'))+'&body='+encodeURIComponent(body)});
document.addEventListener('keydown',e=>{if(e.key==='Escape')document.querySelectorAll('.language-menu[open]').forEach(d=>d.open=false)});
document.addEventListener('click',e=>document.querySelectorAll('.language-menu[open]').forEach(d=>{if(!d.contains(e.target))d.open=false}));
})();
