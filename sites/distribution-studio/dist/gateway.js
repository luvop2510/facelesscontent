if('IntersectionObserver' in window&&!matchMedia('(prefers-reduced-motion: reduce)').matches){
  const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{
    if(!entry.isIntersecting)return;
    entry.target.classList.add(entry.target.tagName==='IMG'?'motion-picture':'motion-enter');
    observer.unobserve(entry.target);
  }),{threshold:.12});
  document.querySelectorAll('main h1,main h2,main .lead,.entrance,.handoff .section-intro p,.handoff-actions,.handoff-images img').forEach(el=>observer.observe(el));
}
