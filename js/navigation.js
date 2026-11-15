/* Enlaces entre las dos vistas: conserva misión y configuración local explícita. */
(function(root){
  'use strict';
  function modeURL(href,mode,mission={}){
    const current=new URL(href),url=new URL(mode==='advanced'?'classic.html':'./',current);
    ['planetary','earth'].forEach(key=>{if(current.searchParams.has(key))url.searchParams.set(key,current.searchParams.get(key));});
    if(mode==='advanced'){
      url.searchParams.set('mode','advanced');
      for(const key of ['target','preset','region','site'])if(mission[key])url.searchParams.set(key,mission[key]);
      if(typeof mission.mask==='boolean')url.searchParams.set('mask',String(mission.mask));
    }
    return url.href;
  }
  const api={modeURL};root.HexastraNavigation=api;
  if(typeof module!=='undefined' && module.exports)module.exports=api;
})(typeof window!=='undefined'?window:this);
