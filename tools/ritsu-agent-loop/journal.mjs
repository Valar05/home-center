import fs from 'node:fs/promises';
import path from 'node:path';

/**
 * Durable campaign checkpoint and append-only receipts. The worker owns the
 * state directory; stop/status readers never change journal records directly.
 * This is a storage primitive, not permission for unattended host execution.
 */
export class CampaignJournal {
  constructor(root){this.root=root;this.receipts=new Map();
    this.pendingReceipt=null;this.state={phase:'uninitialized'};
  }
  static async open(root) {
    const j=new CampaignJournal(path.resolve(root));
    await fs.mkdir(j.root,{recursive:true,mode:0o700});
    const statePath=path.join(j.root,'latest.json');
    try{j.state=JSON.parse(await fs.readFile(statePath,'utf8'));}
    catch(error){if(error?.code!=='ENOENT')throw error;}
    const historyPath=path.join(j.root,'history.jsonl');
    let data='';
    try{data=await fs.readFile(historyPath,'utf8');}
    catch(error){if(error?.code!=='ENOENT')throw error;}
    for(const line of data.trim().split('\n')){
      if(!line)continue;
      const event=JSON.parse(line);
      if(event.event==='script_receipt'&&event.receipt){
        const existing=j.receipts.get(event.scriptId);
        if(existing&&existing.sha256!==event.receipt.sha256)
          throw Error('journal_conflicting_script_hash');
        j.receipts.set(event.scriptId,event.receipt);
        j.pendingReceipt=event.receipt;
      }
    }
    return j;
  }
  async append(entry){
    if(!entry||typeof entry!=='object')throw Error('invalid_campaign_event');
    const row={...entry};
    await fs.appendFile(path.join(this.root,'history.jsonl'),
      JSON.stringify(row)+'\n',{encoding:'utf8',mode:0o600});
    if(row.event==='script_receipt'&&row.receipt){
      this.receipts.set(row.scriptId,row.receipt);
      this.pendingReceipt=row.receipt;
    }
  }
  async checkpoint(next){
    if(!next||typeof next!=='object'||typeof next.phase!=='string')
      throw Error('invalid_campaign_checkpoint');
    // Each checkpoint is durable before the next agent step.
    const current={...next,updatedAt:new Date().toISOString()};
    const dest=path.join(this.root,'latest.json');
    const temporary=path.join(this.root,'.latest-'+process.pid+'.tmp');
    try{
      await fs.writeFile(temporary,JSON.stringify(current,null,2)+'\n',
        {encoding:'utf8',mode:0o600});
      await fs.rename(temporary,dest);
    }finally{await fs.rm(temporary,{force:true});}
    this.state=current;
  }
  async ownerStop(){
    await fs.writeFile(path.join(this.root,'owner-stop.json'),
      JSON.stringify({stop:true,at:new Date().toISOString()})+'\n',
      {encoding:'utf8',mode:0o600});
  }
  async clearOwnerStop(){
    await fs.rm(path.join(this.root,'owner-stop.json'),{force:true});
  }
  async isOwnerStopped(){
    try{await fs.access(path.join(this.root,'owner-stop.json'));return true;}
    catch(error){if(error?.code==='ENOENT')return false;throw error;}
  }
  receiptSummary(){
    return {phase:this.state.phase,updatedAt:this.state.updatedAt||null,
      scripts:this.receipts.size,lastScriptId:this.pendingReceipt?.scriptId||null,
      lastStatus:this.pendingReceipt?.status||null,
      done:this.state.phase==='completed'};
  }
}
