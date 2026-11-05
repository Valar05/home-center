// Network-only ChatGPT SSE text reconstruction for a bounded user-authorized canary.
// Never emit hidden reasoning, tool events, input messages, token headers or raw SSE logs.
const MAX_TEXT=4096,MAX_WIRE=2*1024*1024;
const safe=v=>typeof v==='string'&&/^[A-Za-z0-9_.-]{1,80}$/.test(v)?v:null;
const textParts=m=>Array.isArray(m?.content?.parts)&&
  m.content.parts.every(p=>typeof p==='string')&&
  ['text','markdown'].includes(m.content?.content_type)
  ?m.content.parts.join(''):null;

export class RitsuNetworkSse {
  #decoder=new TextDecoder('utf-8',{fatal:true});
  #buffer=''; #wire=0; #events=0; #unknown=0; #done=false;
  #messageId=null; #rawText=''; #candidate=null; #visible=false;
  #finished=false; #conflict=false; #seeded=false;
  #lastPath=null; #lastOp=null; #shapes=[];
  #visibleMarkerIds=new Set();

  push(bytes){
    if(this.#done)throw Error('sse_data_after_done');
    if(!(bytes instanceof Uint8Array))throw Error('sse_bytes_required');
    this.#wire+=bytes.length;
    if(this.#wire>MAX_WIRE)throw Error('sse_canary_wire_size_exceeded');
    this.#buffer+=this.#decoder.decode(bytes,{stream:true});
    this.#drain();
  }
  #setText(text){
    if(text.length>MAX_TEXT)throw Error('sse_canary_text_size_exceeded');
    this.#rawText=text;
    this.#refresh();
  }
  #refresh(){
    if(this.#visible&&this.#seeded&&this.#rawText.trim())this.#candidate=this.#rawText;
  }
  #seed(message){
    if(!message||message.author?.role!=='assistant')return;
    if(message.recipient&&message.recipient!=='all')return;
    if(message.metadata?.is_visually_hidden_from_conversation===true)return;
    if(message.metadata?.channel&&!['final'].includes(message.metadata.channel))return;
    const text=textParts(message);
    if(text==null||typeof message.id!=='string'||!message.id)return;
    if(this.#messageId&&this.#messageId!==message.id){
      if(this.#visible||message.metadata?.channel==='final'||
        this.#visibleMarkerIds.has(message.id))this.#conflict=true;
      return;
    }
    this.#messageId=message.id;
    this.#seeded=true;
    this.#visible=this.#visible||message.metadata?.channel==='final'||
      this.#visibleMarkerIds.has(message.id);
    this.#finished=this.#finished||message.status==='finished_successfully'||
      message.end_turn===true;
    this.#setText(text);
  }
  #patch(path,operation,value){
    if(operation==='patch'&&Array.isArray(value)){
      for(const nested of value)this.#patch(nested?.p,nested?.o,nested?.v);
      return;
    }
    if((path===''||path==null)&&['add','replace'].includes(operation)&&
      value&&typeof value==='object'){
      this.#seed(value.message||value);
      return;
    }
    if(!this.#seeded)return;
    if(path==='/message/content/parts/0'){
      if(typeof value!=='string')return;
      if(operation==='append')this.#setText(this.#rawText+value);
      else if(operation==='replace'||operation==='add')this.#setText(value);
      return;
    }
    if(path==='/message/status'&&operation==='replace'&&
      value==='finished_successfully')this.#finished=true;
    if(path==='/message/end_turn'&&operation==='replace'&&value===true)
      this.#finished=true;
  }
  #drain(){
    this.#buffer=this.#buffer.replace(/\r\n/g,'\n');
    for(;;){
      const at=this.#buffer.indexOf('\n\n');if(at<0)break;
      const frame=this.#buffer.slice(0,at);this.#buffer=this.#buffer.slice(at+2);
      const data=frame.split('\n').filter(l=>l.startsWith('data:'))
        .map(l=>l.slice(5).replace(/^ /,'')).join('\n');
      if(!data)continue;
      this.#events++;
      if(data==='[DONE]'){this.#done=true;continue;}
      let payload;try{payload=JSON.parse(data)}catch{this.#unknown++;continue}
      if(payload&&typeof payload==='object'&&!Array.isArray(payload)&&
         this.#shapes.length<8){
        this.#shapes.push({
          keys:Object.keys(payload).slice(0,12).filter(k=>/^[A-Za-z0-9_.-]{1,64}$/.test(k)),
          type:safe(payload.type),role:safe(payload.message?.author?.role),
          channel:safe(payload.message?.metadata?.channel),
          contentType:safe(payload.message?.content?.content_type)
        });
      }
      if(payload?.type==='message_marker'&&
         payload.marker==='user_visible_token'&&
         typeof payload.message_id==='string'){
        this.#visibleMarkerIds.add(payload.message_id);
        if(payload.message_id===this.#messageId){
          this.#visible=true;this.#refresh();
        }
        continue;
      }
      if(payload?.message){this.#seed(payload.message);continue}
      if(!payload||typeof payload!=='object'||Array.isArray(payload))continue;
      if(payload.p!==undefined&&typeof payload.o==='string'){
        this.#lastPath=payload.p;this.#lastOp=payload.o;
        this.#patch(payload.p,payload.o,payload.v);
      }else if(payload.v!==undefined){
        if(typeof payload.v==='object'&&payload.v!==null){
          this.#seed(payload.v.message||payload.v);
        }else if(typeof payload.v==='string'&&
                 this.#lastPath==='/message/content/parts/0'&&
                 this.#lastOp==='append'){
          this.#patch(this.#lastPath,'append',payload.v);
        }
      }
    }
  }
  diagnostic(){
    return Object.freeze({
      wireBytes:this.#wire,eventCount:this.#events,
      unparseableEvents:this.#unknown,terminalDone:this.#done,
      textCandidate:Boolean(this.#candidate),seeded:this.#seeded,
      visible:this.#visible,finished:this.#finished,
      bufferedChars:this.#buffer.length,
      shapes:this.#shapes.map(s=>({...s})),
    });
  }
  result({marker,requestFinished=false}={}){
    if(!requestFinished||!this.#done)throw Error('sse_stream_not_terminal');
    if(this.#conflict)throw Error('sse_multiple_final_messages');
    if(!this.#candidate||!this.#visible||!this.#candidate.includes(marker))
      throw Error('sse_no_matching_final_canary_text');
    return Object.freeze({
      text:this.#candidate,messageId:this.#messageId,
      eventCount:this.#events,unknownEventCount:this.#unknown,
      wireBytes:this.#wire,terminal:true});
  }
}
