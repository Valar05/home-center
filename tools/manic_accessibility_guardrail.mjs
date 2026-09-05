#!/usr/bin/env node
'use strict';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {runCli} from '../skills/manic-accessibility-guardrail/scripts/audit.mjs';
const invokedAsScript = process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1]);
if (invokedAsScript) process.exitCode = runCli();
export * from '../skills/manic-accessibility-guardrail/scripts/audit.mjs';
