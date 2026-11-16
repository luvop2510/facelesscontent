import {companies,shows,formats,placementCopy,storyboards} from './data.js';
const $=s=>document.querySelector(s);
const state={company:'specflow',format:'story',show:'build'};
const assetUrl=name=>new URL(`assets/${name}`,import.meta.url).href;
const query=new URLSearchParams(location.search);
if(Object.hasOwn(companies,query.get('company'))) state.company=query.get('company');
if(Object.hasOwn(shows,query.get('show'))) state.show=query.get('show');
const dialog=$('#concept-dialog');
const placementScenes={
  story:['workshop.webp','The crew works through an idea together at a workbench.'],
  shoutout:['cafe.webp','Two members of the cast pause for a shout-out in the cafe.'],
  board:['cinema.webp','The cast looks toward a feature board at the outdoor cinema.']
};
const shelfMount=$('#shelf-mount');
function showShelf(){
  const existing=shelfMount.firstElementChild;
  if(!shelfMount.parentElement.open||existing?.getAttribute('company')===state.company)return;
  const shelf=document.createElement('company-story-shelf');
  shelf.setAttribute('company',state.company);
  shelfMount.replaceChildren(shelf);
}
shelfMount.parentElement.addEventListener('toggle',showShelf);
let timer=null,scene=0,currentShow='build',paused=false,returnFocus=null;
function selectShow(show){
  state.show=show;
  const data=shows[show];
  document.querySelectorAll('[data-show]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.show===show)));
  $('#show-image').src=assetUrl(data.image);$('#show-image').alt=data.alt;$('#show-caption').textContent=data.caption;
  $('#show-description').replaceChildren();
  const heading=document.createElement('h3');
  heading.textContent=data.episode;
  const description=document.createElement('p');description.textContent=data.description;
  const note=document.createElement('p');note.className='concept-line';note.textContent=`Featured product: ${companies[data.company].name}`;
  $('#show-description').append(heading,description,note);$('#show-play').dataset.play=show;
  updateSelection();
}
function embedCode(){
  const episode=new URL(`specflow/?company=${state.company}&show=${state.company==='launchplan'?'town':'build'}#shows`,import.meta.url);
  return `<company-story-shelf company="${state.company}"><a href="${episode.href.replaceAll('&','&amp;')}">Watch ${companies[state.company].name} on SpecFlow</a></company-story-shelf>\n<script src="${new URL('embed.js',import.meta.url).href}" defer><\/script>`;
}
function updateSelection(){
  const c=companies[state.company],f=formats[state.format],copy=placementCopy(state.company,state.format);
  const [image,alt]=placementScenes[state.format],placementImage=$('#placement-image');
  placementImage.src=assetUrl(image);placementImage.alt=alt;$('.preview-art').dataset.format=state.format;
  $('#board-company').textContent=c.name;$('#board-domain').textContent=c.domain;
  $('#placement-scene').textContent=copy.title;$('#placement-dialogue').textContent=copy.dialogue;
  $('#placement-detail').textContent=`${f.name} · ${f.duration}`;
  $('#brief-selection').textContent=`${c.name} · ${f.name} · ${shows[state.show].name}`;
  $('#embed-code').textContent=embedCode();showShelf();$('#brief-feedback').textContent='';$('#copy-feedback').textContent='';
}
document.querySelectorAll('[data-show]').forEach(b=>b.addEventListener('click',()=>selectShow(b.dataset.show)));
$('[data-select-build]').addEventListener('click',()=>{selectShow('build');$('#shows').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});});
$('#placement-form').addEventListener('change',e=>{
  if(e.target.name==='company'&&Object.hasOwn(companies,e.target.value))state.company=e.target.value;
  if(e.target.name==='format'&&Object.hasOwn(formats,e.target.value))state.format=e.target.value;
  updateSelection();const art=$('.preview-art');art.classList.remove('changed');requestAnimationFrame(()=>art.classList.add('changed'));
});
$(`input[name="company"][value="${state.company}"]`).checked=true;
selectShow(state.show);
function showScene(){
  const frames=storyboards[currentShow],frame=frames[scene];
  $('#concept-image').src=assetUrl(frame.image);$('#concept-image').alt=frame.alt;

  $('#concept-caption').textContent=`${frame.speaker}: “${frame.line}”`;
  $('#scene-count').textContent=`Scene ${scene+1} of ${frames.length}`;
}
function stopTimer(){clearInterval(timer);timer=null;}
function startTimer(){stopTimer();timer=setInterval(()=>{if(scene<storyboards[currentShow].length-1){scene++;showScene();}else{paused=true;stopTimer();$('#pause-concept').textContent='Replay';}},4800);}
function play(show,trigger){
  currentShow=show;scene=0;paused=matchMedia('(prefers-reduced-motion: reduce)').matches;returnFocus=trigger;
  $('#concept-title').textContent=shows[show].episode;$('#pause-concept').textContent=paused?'Play scenes':'Pause';
  const transcript=$('#transcript-content');transcript.replaceChildren();
  storyboards[show].forEach(frame=>{const p=document.createElement('p');p.textContent=`${frame.speaker}: “${frame.line}”`;transcript.append(p);});
  showScene();dialog.showModal();document.body.style.overflow='hidden';$('#close-concept').focus();if(!paused)startTimer();
}
document.querySelectorAll('[data-play]').forEach(b=>b.addEventListener('click',()=>play(b.dataset.play,b)));
$('#close-concept').addEventListener('click',()=>dialog.close());
dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();}});
dialog.addEventListener('close',()=>{stopTimer();document.body.style.overflow='';returnFocus?.focus();});
$('#pause-concept').addEventListener('click',()=>{
  if(paused){if(scene===storyboards[currentShow].length-1)scene=0;paused=false;showScene();startTimer();$('#pause-concept').textContent='Pause';}
  else{paused=true;stopTimer();$('#pause-concept').textContent='Resume';}
});
$('#next-scene').addEventListener('click',()=>{scene=(scene+1)%storyboards[currentShow].length;showScene();if(!paused)startTimer();});
document.addEventListener('visibilitychange',()=>{if(document.hidden&&dialog.open){paused=true;stopTimer();$('#pause-concept').textContent='Resume';}});
$('#copy-embed').addEventListener('click',async()=>{
  try{if(!navigator.clipboard)throw new Error('Clipboard unavailable');await navigator.clipboard.writeText(embedCode());$('#copy-feedback').textContent='Embed copied. Paste it into your website’s HTML.';}
  catch{$('#copy-feedback').textContent='Select the code above and copy it with your keyboard.';const range=document.createRange();range.selectNodeContents($('#embed-code'));const selection=getSelection();selection.removeAllRanges();selection.addRange(range);}
});
$('#download-brief').addEventListener('click',()=>{
  const brief={status:'concept-for-review',createdAt:new Date().toISOString(),company:companies[state.company],show:shows[state.show].name,placement:{...formats[state.format],...placementCopy(state.company,state.format)},disclosure:'Featured: our own company. Paid external placements require Sponsored disclosure.',proposedChannels:['Instagram Reels','TikTok','YouTube Shorts','LinkedIn','X','Company website'],production:['Approve story and product claims','Produce voice, animation, captions and sound','Review company placement and disclosure','Connect authorized platform publishing adapters','Publish and measure actual results'],publishingConnected:false};
  const blob=new Blob([JSON.stringify(brief,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`${state.company}-${state.format}-concept-brief.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);$('#brief-feedback').textContent='Brief downloaded. Ready for production review.';
});
if('IntersectionObserver' in window&&!matchMedia('(prefers-reduced-motion: reduce)').matches){
  const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){entry.target.classList.add(entry.target.tagName==='IMG'?'motion-picture':'motion-enter');observer.unobserve(entry.target);}}),{threshold:.12});
  document.querySelectorAll('main .chapter:not(.hero) h2,main .chapter:not(.hero) h3,main .chapter:not(.hero) .section-intro>p,main .chapter:not(.hero) img,.show-selector,.show-actions,.company-options,.format-options,.embed-code,.faq-list,.brief-main>p').forEach(el=>observer.observe(el));
}
if(query.get('play')==='1')play(state.show,$('#show-play'));
