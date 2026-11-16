(()=>{
  const base=new URL('./',document.currentScript.src);
  if(customElements.get('company-story-shelf'))return;
  customElements.define('company-story-shelf',class extends HTMLElement{
    connectedCallback(){
      if(!this.shadowRoot){
        const company=this.getAttribute('company')==='specflow'?'specflow':'launchplan';
        const root=this.attachShadow({mode:'open'}), frame=document.createElement('iframe');
        frame.src=new URL(`shelf.html?company=${company}`,base).href;
        frame.title=`SpecFlow episode featuring ${company==='specflow'?'SpecFlow':'LaunchPlan'}`;
        frame.loading='lazy';
        frame.style.cssText='display:block;width:100%;height:600px;border:0;background:#d1ddd3';
        this.style.display='block';
        this._message=e=>{
          if(e.origin===base.origin&&e.source===frame.contentWindow&&e.data?.type==='company-story-height'&&Number.isFinite(e.data.height)){
            frame.style.height=`${Math.min(1200,Math.max(280,e.data.height))}px`;
          }
        };
        root.append(frame);
      }
      window.addEventListener('message',this._message);
    }
    disconnectedCallback(){window.removeEventListener('message',this._message);}
  });
})();
