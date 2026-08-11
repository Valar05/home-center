import readline from 'node:readline/promises';
import {stdin, stdout} from 'node:process';
import {createRuntime} from './daemon.mjs';

const runtime = createRuntime({port: Number(process.env.PORCHLIGHT_PORT || 9235), dataDir: process.env.PORCHLIGHT_DATA_DIR});
await runtime.listen();
stdout.write('Porchlight is local. No model is running. Type help.\n');
const io = readline.createInterface({input: stdin, output: stdout});
for (;;) {
  const line = await io.question('porchlight> ');
  if (/^(quit|exit)$/i.test(line.trim())) break;
  try { stdout.write(JSON.stringify(runtime.prompt(line), null, 2) + '\n'); }
  catch (error) { stdout.write(JSON.stringify({status: 'error', error: error.message}) + '\n'); }
}
io.close();
runtime.revoke('cli_exit');
await runtime.close();
