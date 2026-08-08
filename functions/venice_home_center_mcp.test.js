const assert = require('node:assert/strict');
const test = require('node:test');

const {
  VENICE_ALLOWED_RUNTIME_SERVICE_ACCOUNT,
  VENICE_MAX_TOOL_ROUNDS,
  callVeniceHomeCenterTool,
  fortressControlIntentFromPrompt,
  homeCenterToolsToOpenAI,
  listVeniceHomeCenterTools,
  promptAuthorizesMutation,
  runVeniceFortressControlTurn,
  runVeniceHomeCenterToolLoop,
} = require('./venice_home_center_mcp');

function fakeAdmin() {
  const audits = [];
  const firestore = function firestore() {
    return {
      collection(name) {
        return {
          add: async (doc) => {
            audits.push({name, doc});
            return {id: String(audits.length)};
          },
          doc() {
            return {
              async get() { return {exists: false, data: () => ({})}; },
              async set() {},
            };
          },
        };
      },
    };
  };
  firestore.FieldValue = {
    serverTimestamp() {
      return {__serverTimestamp: true};
    },
  };
  return {
    audits,
    firestore,
  };
}

function fakeGoogle() {
  return {
    auth: {
      OAuth2: class {
        setCredentials() {}
        on() {}
      },
    },
  };
}

function baseContext(overrides = {}) {
  const admin = fakeAdmin();
  return {
    admin,
    google: fakeGoogle(),
    googleClientId: () => '',
    googleClientSecret: () => '',
    githubToken: () => '',
    githubAdmin: {},
    cartesiaApiKey: () => '',
    geminiApiKey: () => '',
    runtimeServiceAccount: VENICE_ALLOWED_RUNTIME_SERVICE_ACCOUNT,
    delegatingUser: 'dclarke1005@gmail.com',
    discordUserId: 'discord-user-1',
    discordInteractionId: 'discord-interaction-1',
    originalPrompt: 'Use Home Center to inspect the repository. Do not change anything.',
    allowMutations: false,
    allowSessionControl: false,
    homeCenterAuth: {user: {email: 'dclarke1005@gmail.com', authKind: 'test'}, auth: {}},
    ensureTaskCurrent: async () => {},
    ...overrides,
  };
}

function fakeToolServer(tools) {
  return {
    _registeredTools: Object.fromEntries(tools.map((tool) => [tool.name, {
      title: tool.title || tool.name,
      description: tool.description || tool.name,
      inputSchema: tool.inputSchema || {type: 'object', properties: {}, additionalProperties: false},
      annotations: tool.annotations || {},
      enabled: tool.enabled !== false,
      handler: tool.handler,
    }])),
  };
}

function functionCall(callId, name, args) {
  return {
    output: [{type: 'function_call', call_id: callId, name, arguments: JSON.stringify(args)}],
    output_text: '',
  };
}

function finalText(text) {
  return {
    output: [{type: 'message', content: [{type: 'output_text', text}]}],
    output_text: text,
  };
}

test('canonical Home Center tools are discoverable through Venice', async () => {
  const tools = await listVeniceHomeCenterTools(baseContext());
  const names = new Set(tools.map((tool) => tool.name));
  assert.ok(names.has('health'));
  assert.ok(names.has('drive_search'));
  assert.ok(names.has('docs_create'));
  assert.ok(names.has('fortress_online'));
  assert.ok(names.has('home_center_session_status'));
  assert.ok(names.has('home_center_session_update'));
  assert.ok(names.has('home_center_work_request'));
  assert.ok(names.has('home_center_work_status'));
  assert.ok(names.has('command_center_operation'));
});

test('tool schemas convert to OpenAI function tools without losing required fields', () => {
  const openAiTools = homeCenterToolsToOpenAI([{
    name: 'github_admin_create_branch',
    description: 'Create a branch.',
    inputSchema: {
      type: 'object',
      properties: {
        repo: {type: 'string'},
        branch: {type: 'string'},
        requestId: {type: 'string'},
      },
      required: ['repo', 'branch', 'requestId'],
      additionalProperties: false,
    },
  }]);
  assert.equal(openAiTools.length, 1);
  assert.deepEqual(openAiTools[0].parameters.required, ['repo', 'branch', 'requestId']);
  assert.equal(openAiTools[0].parameters.additionalProperties, false);
  assert.equal(openAiTools[0].parameters.properties.branch.type, 'string');
});

test('one Venice tool call round returns the final reply after MCP execution', async () => {
  const calls = [];
  const context = baseContext({
    homeCenterServer: fakeToolServer([{
      name: 'github_get_repo',
      annotations: {readOnlyHint: true},
      handler: async (args) => {
        calls.push(args);
        return {defaultBranch: 'main'};
      },
    }]),
  });
  const requests = [];
  let turn = 0;
  const reply = await runVeniceHomeCenterToolLoop({
    context,
    prompt: 'Inspect the repo.',
    requestBody: {model: 'gpt-5.5', instructions: 'test'},
    fetchOpenAIResponses: async (body) => {
      requests.push(body);
      turn += 1;
      return turn === 1
        ? {response: {ok: true, status: 200}, json: functionCall('call-1', 'github_get_repo', {repo: 'Valar05/home-center'})}
        : {response: {ok: true, status: 200}, json: finalText('The default branch is main.')};
    },
    extractOutputText: (json) => json.output_text || '',
    veniceReplyNeedsRepair: () => false,
  });
  assert.equal(reply, 'The default branch is main.');
  assert.equal(calls.length, 1);
  assert.equal(requests[1].input[1].type, 'function_call_output');
  assert.match(requests[1].input[1].output, /main/);
});

test('sequential Venice tool calls continue across rounds', async () => {
  const seen = [];
  const context = baseContext({
    homeCenterServer: fakeToolServer([
      {
        name: 'github_get_repo',
        annotations: {readOnlyHint: true},
        handler: async () => {
          seen.push('repo');
          return {defaultBranch: 'main'};
        },
      },
      {
        name: 'github_read_file',
        annotations: {readOnlyHint: true},
        handler: async () => {
          seen.push('read');
          return {text: '# GitHub Admin MCP'};
        },
      },
    ]),
  });
  let turn = 0;
  const reply = await runVeniceHomeCenterToolLoop({
    context,
    prompt: 'Inspect the repo and read the doc.',
    requestBody: {model: 'gpt-5.5', instructions: 'test'},
    fetchOpenAIResponses: async () => {
      turn += 1;
      if (turn === 1) return {response: {ok: true, status: 200}, json: functionCall('call-1', 'github_get_repo', {repo: 'Valar05/home-center'})};
      if (turn === 2) return {response: {ok: true, status: 200}, json: functionCall('call-2', 'github_read_file', {repo: 'Valar05/home-center', path: 'docs/GITHUB_ADMIN_MCP.md'})};
      return {response: {ok: true, status: 200}, json: finalText('The default branch is main and the doc starts with GitHub Admin MCP.')};
    },
    extractOutputText: (json) => json.output_text || '',
    veniceReplyNeedsRepair: () => false,
  });
  assert.equal(reply, 'The default branch is main and the doc starts with GitHub Admin MCP.');
  assert.deepEqual(seen, ['repo', 'read']);
});

test('quota exhaustion before any tool call uses the configured fallback lane', async () => {
  let fallbackCalls = 0;
  const context = baseContext({homeCenterServer: fakeToolServer([])});
  const reply = await runVeniceHomeCenterToolLoop({
    context,
    prompt: 'Reply normally.',
    requestBody: {model: 'gpt-5.5', instructions: 'test'},
    fetchOpenAIResponses: async () => ({
      response: {ok: false, status: 429},
      json: {},
    }),
    extractOutputText: () => '',
    veniceReplyNeedsRepair: () => false,
    geminiFallback: async () => {
      fallbackCalls += 1;
      return 'fallback reply';
    },
  });
  assert.equal(reply, 'fallback reply');
  assert.equal(fallbackCalls, 1);
});

test('non-quota OpenAI failures do not use the fallback lane', async () => {
  const context = baseContext({homeCenterServer: fakeToolServer([])});
  await assert.rejects(
    runVeniceHomeCenterToolLoop({
      context,
      prompt: 'Reply normally.',
      requestBody: {model: 'gpt-5.5', instructions: 'test'},
      fetchOpenAIResponses: async () => ({
        response: {ok: false, status: 500},
        json: {},
      }),
      extractOutputText: () => '',
      veniceReplyNeedsRepair: () => false,
      geminiFallback: async () => 'fallback reply',
    }),
    /venice_openai_http_500/,
  );
});

test('quota exhaustion after tool execution has started does not switch lanes', async () => {
  let executions = 0;
  let fallbackCalls = 0;
  const context = baseContext({
    homeCenterServer: fakeToolServer([{
      name: 'health',
      annotations: {readOnlyHint: true},
      handler: async () => {
        executions += 1;
        return {ok: true};
      },
    }]),
  });
  let turn = 0;
  await assert.rejects(
    runVeniceHomeCenterToolLoop({
      context,
      prompt: 'Check health, then continue.',
      requestBody: {model: 'gpt-5.5', instructions: 'test'},
      fetchOpenAIResponses: async () => {
        turn += 1;
        if (turn === 1) {
          return {
            response: {ok: true, status: 200},
            json: functionCall('call-1', 'health', {}),
          };
        }
        return {
          response: {ok: false, status: 429},
          json: {},
        };
      },
      extractOutputText: () => '',
      veniceReplyNeedsRepair: () => false,
      geminiFallback: async () => {
        fallbackCalls += 1;
        return 'fallback reply';
      },
    }),
    /venice_openai_http_429/,
  );
  assert.equal(executions, 1);
  assert.equal(fallbackCalls, 0);
});

test('unknown tool names fail closed', async () => {
  const context = baseContext({homeCenterServer: fakeToolServer([])});
  await assert.rejects(
    callVeniceHomeCenterTool(context, 'missing_tool', {}),
    (err) => err && err.code === 'venice_tool_not_found',
  );
});

test('malformed tool arguments fail closed', async () => {
  const context = baseContext({
    homeCenterServer: fakeToolServer([{
      name: 'health',
      annotations: {readOnlyHint: true},
      handler: async () => ({ok: true}),
    }]),
  });
  await assert.rejects(
    runVeniceHomeCenterToolLoop({
      context,
      prompt: 'Check health.',
      requestBody: {model: 'gpt-5.5', instructions: 'test'},
      fetchOpenAIResponses: async () => ({
        response: {ok: true, status: 200},
        json: {output: [{type: 'function_call', call_id: 'call-1', name: 'health', arguments: '[]'}]},
      }),
      extractOutputText: () => '',
      veniceReplyNeedsRepair: () => false,
    }),
    (err) => err && err.code === 'venice_tool_arguments_invalid_shape',
  );
});

test('MCP handler errors propagate out of Venice tool execution', async () => {
  const context = baseContext({
    homeCenterServer: fakeToolServer([{
      name: 'github_read_file',
      annotations: {readOnlyHint: true},
      handler: async () => {
        const err = new Error('mcp boom');
        err.status = 502;
        throw err;
      },
    }]),
  });
  await assert.rejects(
    runVeniceHomeCenterToolLoop({
      context,
      prompt: 'Read the file.',
      requestBody: {model: 'gpt-5.5', instructions: 'test'},
      fetchOpenAIResponses: async () => ({
        response: {ok: true, status: 200},
        json: functionCall('call-1', 'github_read_file', {repo: 'Valar05/home-center', path: 'README.md'}),
      }),
      extractOutputText: () => '',
      veniceReplyNeedsRepair: () => false,
    }),
    /mcp boom/,
  );
});

test('tool loop stops at the eight-round limit', async () => {
  let executions = 0;
  const context = baseContext({
    homeCenterServer: fakeToolServer([{
      name: 'health',
      annotations: {readOnlyHint: true},
      handler: async () => {
        executions += 1;
        return {ok: true};
      },
    }]),
  });
  await assert.rejects(
    runVeniceHomeCenterToolLoop({
      context,
      prompt: 'Keep checking.',
      requestBody: {model: 'gpt-5.5', instructions: 'test'},
      fetchOpenAIResponses: async () => ({
        response: {ok: true, status: 200},
        json: functionCall('call-loop', 'health', {}),
      }),
      extractOutputText: () => '',
      veniceReplyNeedsRepair: () => false,
      maxToolRounds: VENICE_MAX_TOOL_ROUNDS,
    }),
    /venice_tool_round_limit/,
  );
  assert.equal(executions, VENICE_MAX_TOOL_ROUNDS);
});

test('CUT before a tool call prevents execution', async () => {
  let executed = false;
  const context = baseContext({
    ensureTaskCurrent: async () => {
      const err = new Error('venice_generation_stale');
      err.code = 'venice_generation_stale';
      throw err;
    },
    homeCenterServer: fakeToolServer([{
      name: 'health',
      annotations: {readOnlyHint: true},
      handler: async () => {
        executed = true;
        return {ok: true};
      },
    }]),
  });
  await assert.rejects(
    runVeniceHomeCenterToolLoop({
      context,
      prompt: 'Check health.',
      requestBody: {model: 'gpt-5.5', instructions: 'test'},
      fetchOpenAIResponses: async () => ({
        response: {ok: true, status: 200},
        json: functionCall('call-1', 'health', {}),
      }),
      extractOutputText: () => '',
      veniceReplyNeedsRepair: () => false,
    }),
    /venice_generation_stale/,
  );
  assert.equal(executed, false);
});

test('stale epoch between rounds prevents the next MCP call', async () => {
  let guardCalls = 0;
  let executions = 0;
  const context = baseContext({
    ensureTaskCurrent: async () => {
      guardCalls += 1;
      if (guardCalls >= 3) {
        const err = new Error('venice_generation_stale');
        err.code = 'venice_generation_stale';
        throw err;
      }
    },
    homeCenterServer: fakeToolServer([{
      name: 'health',
      annotations: {readOnlyHint: true},
      handler: async () => {
        executions += 1;
        return {ok: true};
      },
    }]),
  });
  let turn = 0;
  await assert.rejects(
    runVeniceHomeCenterToolLoop({
      context,
      prompt: 'Check health twice.',
      requestBody: {model: 'gpt-5.5', instructions: 'test'},
      fetchOpenAIResponses: async () => {
        turn += 1;
        return {
          response: {ok: true, status: 200},
          json: functionCall(`call-${turn}`, 'health', {}),
        };
      },
      extractOutputText: () => '',
      veniceReplyNeedsRepair: () => false,
    }),
    /venice_generation_stale/,
  );
  assert.equal(executions, 1);
});

test('read-only requests never authorize mutation tools', async () => {
  let executed = false;
  const context = baseContext({
    allowMutations: false,
    homeCenterServer: fakeToolServer([{
      name: 'github_admin_upsert_file',
      annotations: {readOnlyHint: false},
      inputSchema: {
        type: 'object',
        properties: {
          repo: {type: 'string'},
          path: {type: 'string'},
          requestId: {type: 'string'},
          callerNote: {type: 'string'},
        },
        required: ['repo', 'path', 'requestId'],
        additionalProperties: false,
      },
      handler: async () => {
        executed = true;
        return {ok: true};
      },
    }]),
  });
  await assert.rejects(
    callVeniceHomeCenterTool(context, 'github_admin_upsert_file', {repo: 'Valar05/home-center', path: 'docs/test.md'}),
    (err) => err && err.code === 'venice_mutation_not_authorized',
  );
  assert.equal(executed, false);
});

test('Fortress session-control prompts are classified separately from general mutations', () => {
  assert.equal(fortressControlIntentFromPrompt('Fortress online.'), 'fortress_online');
  assert.equal(fortressControlIntentFromPrompt('Where were we?'), 'session_status');
  assert.equal(fortressControlIntentFromPrompt('We\'re fixing Vanguard SwordAttack3 drift.'), 'objective_update');
  assert.equal(fortressControlIntentFromPrompt('Fortress online, the task is fleshpunk secret garden.'), 'objective_update');
  assert.equal(fortressControlIntentFromPrompt('Tell me how you would fix it.'), '');
});

test('Fortress session-control tools are allowed without broad mutation authority', async () => {
  let executed = false;
  const context = baseContext({
    allowMutations: false,
    allowSessionControl: true,
    homeCenterServer: fakeToolServer([{
      name: 'fortress_online',
      annotations: {readOnlyHint: false},
      inputSchema: {
        type: 'object',
        properties: {
          requestId: {type: 'string'},
        },
        additionalProperties: false,
      },
      handler: async () => {
        executed = true;
        return {ok: true};
      },
    }]),
  });
  const result = await callVeniceHomeCenterTool(context, 'fortress_online', {});
  assert.equal(result.ok, true);
  assert.equal(executed, true);
});

test('Fortress control turn invokes Home Center orientation exactly once without ordinary model generation', async () => {
  const calls = [];
  const context = baseContext({
    allowMutations: false,
    allowSessionControl: true,
    homeCenterServer: fakeToolServer([{
      name: 'fortress_online',
      annotations: {readOnlyHint: false},
      inputSchema: {
        type: 'object',
        properties: {
          requestId: {type: 'string'},
          callerNote: {type: 'string'},
        },
        additionalProperties: false,
      },
      handler: async (args) => {
        calls.push(args);
        return {
          ok: true,
          orientation: {
            project: {projectId: 'home-center', name: 'Home Center'},
            workspace: {workspaceId: 'home-center-workspace', label: 'Home Center workspace'},
            current_objective: 'We are fixing Vanguard SwordAttack3 drift.',
            pending_work: [],
            recent_completed_work: [],
            blockers: [],
          },
        };
      },
    }]),
  });
  const reply = await runVeniceFortressControlTurn({
    context,
    controlTurn: {kind: 'fortress_online', normalizedPrompt: 'fortress online'},
  });
  assert.equal(calls.length, 1);
  assert.match(reply, /^Fortress online\./);
  assert.match(reply, /Current objective: We are fixing Vanguard SwordAttack3 drift\./);
});

test('Fortress control turn reports unresolved Home Center state without fabrication', async () => {
  const context = baseContext({
    allowSessionControl: true,
    homeCenterServer: fakeToolServer([{
      name: 'fortress_online',
      annotations: {readOnlyHint: false},
      inputSchema: {type: 'object', properties: {}, additionalProperties: false},
      handler: async () => ({
        ok: true,
        orientation: {
          project: {},
          workspace: {},
          current_objective: '',
          last_checkpoint: '',
          pending_work: [],
          recent_completed_work: [],
          blockers: [],
        },
      }),
    }]),
  });
  const reply = await runVeniceFortressControlTurn({
    context,
    controlTurn: {kind: 'fortress_online', normalizedPrompt: 'fortress online'},
  });
  assert.equal(reply, 'Fortress online. Home Center does not have an active project or checkpoint yet.');
});

test('prompt mutation authority is fail-closed for explanation-only prompts and allows explicit repair prompts', () => {
  assert.equal(promptAuthorizesMutation('Tell me how you would fix yourself.'), false);
  assert.equal(promptAuthorizesMutation('Use Home Center to inspect Valar05/home-center. Do not change anything.'), false);
  assert.equal(promptAuthorizesMutation('Fix yourself, create a branch, update the file, and open a pull request.'), true);
});
