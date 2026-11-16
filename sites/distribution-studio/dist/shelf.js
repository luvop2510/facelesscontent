import {companies} from './data.js';
const q=new URLSearchParams(location.search),id=q.get('company')==='specflow'?'specflow':'launchplan';
document.querySelector('#shelf-description').textContent=`See ${companies[id].name} in the SpecFlow build show. Watch the concept episode featuring this company.`;
document.querySelector('#shelf-watch').href=`./specflow/?company=${id}&show=${id==='launchplan'?'town':'build'}#shows`;
const art=document.querySelector('.shelf img');
if(id==='launchplan'){art.src='assets/cafe.webp';art.alt='Two robot neighbors talking through a launch.';}
function resize(){if(window.parent!==window)window.parent.postMessage({type:'company-story-height',height:Math.ceil(document.documentElement.getBoundingClientRect().height)},'*');}
new ResizeObserver(resize).observe(document.body);window.addEventListener('load',resize);document.fonts.ready.then(resize);
