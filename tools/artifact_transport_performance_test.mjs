import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);const {boundedMap}=require('../functions/artifact_transport.js');
const delays=[80,80,80,80];const task=(ms)=>new Promise(r=>setTimeout(r,ms));
let start=performance.now();for(const delay of delays)await task(delay);const sequentialMs=Math.round(performance.now()-start);
start=performance.now();await boundedMap(delays,4,task);const parallelMs=Math.round(performance.now()-start);
assert(parallelMs<sequentialMs*0.6,`bounded parallel staging must materially improve wall time: ${sequentialMs} vs ${parallelMs}`);
console.log(JSON.stringify({ok:true,fixtureFiles:4,perFileDelayMs:80,sequentialMs,boundedParallelMs:parallelMs,concurrency:4,speedup:Number((sequentialMs/parallelMs).toFixed(2))},null,2));
