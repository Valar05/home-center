#!/usr/bin/env node
import fs from 'node:fs';

function patch(path, edits) {
  let text=fs.readFileSync(path,'utf8');
  for (const {needle,replacement} of edits) {
    if (text.includes(replacement)) continue;
    if (!text.includes(needle)) throw new Error(`anchor missing in ${path}: ${needle.slice(0,120)}`);
    text=text.replace(needle,replacement);
  }
  fs.writeFileSync(path,text);
}

patch('functions/command_center_mcp.js',[
  {
    needle:"const {APP_CONTROL_COLLECTIONS, APP_CONTROL_DEFAULT_SEEDS, appControlProfileObjectId, appControlProfilePath} = require('./app_control_cloud');",
    replacement:"const {APP_CONTROL_COLLECTIONS, APP_CONTROL_DEFAULT_SEEDS, appControlProfileObjectId, appControlProfilePath} = require('./app_control_cloud');\nconst {registerCommandCenterPhoneTools} = require('./phone_hands_relay');"
  },
  {
    needle:"  server.registerTool('command_center.browser_sessions.create', {",
    replacement:"  registerCommandCenterPhoneTools(server, {admin, z, textResult, callerFromExtra});\n\n  server.registerTool('command_center.browser_sessions.create', {"
  }
]);

patch('functions/index.js',[
  {
    needle:"const {createCommandCenterMcpApp} = require('./command_center_mcp');",
    replacement:"const {createCommandCenterMcpApp} = require('./command_center_mcp');\nconst {createPhoneHandsRelayHandler} = require('./phone_hands_relay');"
  },
  {
    needle:"exports.commandCenterMcp = onRequest({timeoutSeconds: 300}, createCommandCenterMcpApp({admin}));",
    replacement:"exports.commandCenterMcp = onRequest({timeoutSeconds: 300}, createCommandCenterMcpApp({admin}));\nexports.phoneHandsRelay = onRequest({timeoutSeconds: 120}, createPhoneHandsRelayHandler(admin));"
  }
]);

console.log('phone hands relay wiring applied');
