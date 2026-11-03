  // RITSU_V135_CATALOG_FUNCTIONS: authenticated, rendered browser only.
  async function ritsuBrowserCatalogCommand(args){
    const helper=path.join(path.dirname(BRIDGE),'ritsu_browser_catalog_v135.mjs');
    return await new Promise((resolve,reject)=>{
      const p=spawn(process.execPath,[helper,...args],{cwd:path.dirname(BRIDGE),windowsHide:true,stdio:['ignore','pipe','pipe']});
      let out='',err='',done=false;
      const finish=(e,value)=>{if(done)return;done=true;clearTimeout(timer);e?reject(e):resolve(value);};
      const timer=setTimeout(()=>{p.kill('SIGTERM');finish(Error('BROWSER_CATALOG_TIMEOUT'));},35000);
      p.stdout.on('data',b=>{out=(out+b.toString()).slice(-60000)});
      p.stderr.on('data',b=>{err=(err+b.toString()).slice(-500)});
      p.on('error',()=>finish(Error('BROWSER_CATALOG_SPAWN_FAILED')));
      p.on('close',code=>{
        if(done)return;
        const rows=out.split(/\r?\n/).filter(s=>s.startsWith('RITSU_BROWSER_CATALOG='));
        if(rows.length!==1)return finish(Error('BROWSER_CATALOG_NO_UNIQUE_RECEIPT'));
        let record;try{record=JSON.parse(rows[0].slice('RITSU_BROWSER_CATALOG='.length))}catch{return finish(Error('BROWSER_CATALOG_BAD_JSON'))}
        if(code!==0||!record.verified)return finish(Error('BROWSER_'+String(record.code||'FAILED').slice(0,100)));
        finish(null,record);
      });
    });
  }
