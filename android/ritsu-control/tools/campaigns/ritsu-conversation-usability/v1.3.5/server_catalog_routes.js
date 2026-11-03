      // RITSU_V135_CATALOG_ROUTES: placed before any old catalog routes.
      if(req.method==='GET'&&url.pathname==='/v1/ritsu/catalog'){
        if(url.searchParams.get('probe')==='1')return send(200,{ok:true,route:'catalog',verified:false,probe:true});
        try{
          const record=await ritsuBrowserCatalogCommand(['--discover']);
          if(record.kind!=='ritsu_catalog'||!record.verified||!Array.isArray(record.chats))throw Error('CATALOG_RECEIPT_INVALID');
          return send(200,record);
        }catch(e){return send(503,{verified:false,error:String(e.message||e).replace(/[^A-Za-z0-9_:.-]/g,'_').slice(0,120)});}
      }
      if(req.method==='POST'&&url.pathname==='/v1/ritsu/bind'){
        let source='',bytes=0;
        for await(const piece of req){bytes+=piece.length;if(bytes>2200)return send(413,{error:'binding_too_large'});source+=piece.toString('utf8')}
        let body;try{body=JSON.parse(source)}catch{return send(400,{error:'invalid_json'})}
        if(!tabPattern.test(body.tabId||'')||
           !/^https:\/\/chatgpt\.com\/c\/(?:[A-Za-z0-9-]{8,120}|local-chatgpt%3[Aa][a-fA-F0-9-]{36})$/.test(body.url||''))
          return send(400,{error:'invalid_exact_binding'});
        try{
          const record=await ritsuBrowserCatalogCommand(['--bind',body.tabId,body.url]);
          if(record.kind!=='ritsu_catalog_bound'||!record.verified||record.tabId!==body.tabId||record.url!==body.url)
            throw Error('VERIFIED_BIND_RECEIPT_MISMATCH');
          return send(200,record);
        }catch(e){return send(409,{verified:false,error:String(e.message||e).replace(/[^A-Za-z0-9_:.-]/g,'_').slice(0,120)});}
      }
