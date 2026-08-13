#!/usr/bin/env node
import fs from 'node:fs';

const wrapper = fs.readFileSync('tools/build_operator_overlay_signed_windows.ps1', 'utf8');
const canonical = fs.readFileSync('tools/build_operator_overlay_signed.ps1', 'utf8');

for (const anchor of [
  "Join-Path $PSScriptRoot 'build_operator_overlay_signed.ps1'",
  "IndexOf('function Invoke-Checked {'",
  "IndexOf('function Get-Sha256 {'",
  "$savedErrorActionPreference = $ErrorActionPreference",
  "$ErrorActionPreference = 'Continue'",
  '$exitCode = $LASTEXITCODE',
  '$ErrorActionPreference = $savedErrorActionPreference',
  'if ($exitCode -ne 0)',
  'GeneratedSigningRef = $GeneratedSigningRef',
  'ExpectedSourceSha = $ExpectedSourceSha',
  'Remove-Item -LiteralPath $tempRoot -Recurse -Force',
]) {
  if (!wrapper.includes(anchor)) throw new Error(`Windows signer wrapper missing ${anchor}`);
}

if (!canonical.includes('durableSigningKey = $true')) {
  throw new Error('Canonical builder lost durable-signing evidence');
}
if (!canonical.includes('if ($apkCertificateSha -ne $signingCertificateSha)')) {
  throw new Error('Canonical builder lost signer equality verification');
}
if (!wrapper.includes('if ($ExportKeystore) { $parameters.ExportKeystore = $true }')) {
  throw new Error('Keystore export must remain explicit-only');
}
if (!wrapper.includes("$canonicalSource -notmatch [regex]::Escape('durableSigningKey = $true')")) {
  throw new Error('Wrapper must verify canonical durable-signing evidence before execution');
}

console.log('Windows-safe durable overlay signer wrapper contract: PASS');
