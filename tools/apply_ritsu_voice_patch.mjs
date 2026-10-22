import fs from 'node:fs';
function once(s, anchor, replacement) {
 const count=s.split(anchor).length-1;
 if(count!==1)throw Error('Expected one wiring anchor, got '+count+': '+anchor.slice(0,95));
 return s.replace(anchor,replacement);
}
function update(file, fn){
 const old=fs.readFileSync(file,'utf8'),next=fn(old);
 if(old!==next){fs.writeFileSync(file,next);console.log('PATCHED',file);}
 else console.log('UNCHANGED',file);
}
update('functions/home_center_mcp.js',s=>{
 const anchor="const {computerHandsOperationEntries, computerHandsOperationRunOperation} = require('./computer_hands_api');";
 const newImport="const {entryList: ritsuVoiceOperationEntries, runOperation: ritsuVoiceOperationRunOperation} = require('./ritsu_voice_api');";
 if(!s.includes(newImport))s=once(s,anchor,anchor+'\n'+newImport);
 if(!s.includes('...ritsuVoiceOperationEntries(),'))s=once(s,'...computerHandsOperationEntries(),','...computerHandsOperationEntries(),\n    ...ritsuVoiceOperationEntries(),');
 const block=`  if (ritsuVoiceOperationEntries()[operation]) {
    requireCreditGatedEmail(user && user.email, operation);
    const result = await ritsuVoiceOperationRunOperation({admin, user, operation, args: operationArgs});
    return {operation, registryVersion: registry.version, completed: true, result};
  }
`;
 if(!s.includes('if (ritsuVoiceOperationEntries()[operation])'))s=once(s,'  if (computerHandsOperationEntries()[operation]) {',block+'  if (computerHandsOperationEntries()[operation]) {');
 // Kokoro's old generic local_voice ticket operation was for a discarded model.
 // Remove its MCP exposure without deleting its HTTP endpoint or historic data.
 s=s.replace(/^\s*\.\.\.localVoiceOperationEntries\(\),\s*\n/m,'\n');
 const legacy=/  if \(localVoiceOperationEntries\(\)\[operation\]\) \{\n    requireCreditGatedEmail\(user && user\.email, operation\);\n    const result = await localVoiceOperationRunOperation\(\{admin, user, operation, args: operationArgs\}\);\n    return \{operation, registryVersion: registry.version, completed: true, result\};\n  \}\n/;
 s=s.replace(legacy,'');
 return s;
});
update('functions/index.js',s=>{
 const anchor="const {createComputerHandsHandler} = require('./computer_hands_api');";
 const line="const {handler: createRitsuVoiceHandler} = require('./ritsu_voice_api');";
 if(!s.includes(line))s=once(s,anchor,anchor+'\n'+line);
 const exp="exports.computerHands = onRequest({timeoutSeconds: 300}, createComputerHandsHandler({admin}));";
 if(!s.includes('exports.ritsuVoice ='))s=once(s,exp,exp+'\nexports.ritsuVoice = onRequest({timeoutSeconds: 60}, createRitsuVoiceHandler({admin}));');
 return s;
});
const mcp=fs.readFileSync('functions/home_center_mcp.js','utf8'),index=fs.readFileSync('functions/index.js','utf8');
if(!mcp.includes('...ritsuVoiceOperationEntries()')||!mcp.includes('ritsuVoiceOperationRunOperation({'))throw Error('Typed Ritsu MCP wiring absent');
if(mcp.includes('...localVoiceOperationEntries()'))throw Error('Legacy Kokoro MCP entry still advertised');
if(!index.includes('exports.ritsuVoice ='))throw Error('Voice worker HTTPS export absent');
console.log('RITSU_TYPED_VOICE_WIRING_PASS');
