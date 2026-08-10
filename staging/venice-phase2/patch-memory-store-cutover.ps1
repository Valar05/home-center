param(
  [string]$RuntimeRoot = 'G:\My Drive\Venice Runtime',
  [string]$ExpectedMd5 = 'baedc5ec46bc47d625bedf9136c2c56a'
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$p = Join-Path $RuntimeRoot 'src\workstation-store.mjs'
$current = (Get-FileHash -LiteralPath $p -Algorithm MD5).Hash.ToLowerInvariant()
if ($current -ne $ExpectedMd5) { throw "SOURCE_DRIFT workstation-store.mjs md5=$current expected=$ExpectedMd5" }
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backup = "$p.pre-memory-cutover-$stamp"
Copy-Item -LiteralPath $p -Destination $backup -Force
try {
  $t = Get-Content -LiteralPath $p -Raw
  $import = 'import { DatabaseSync } from "node:sqlite";'
  $newImport = $import + "`n" + 'import { memoryRecordView, promoteMemoryInput } from "./durable-core/memory-policy.mjs";'
  if (-not $t.Contains($import)) { throw 'memory policy import anchor missing' }
  if (-not $t.Contains('promoteMemoryInput')) { $t = $t.Replace($import, $newImport) }

  $pattern = '(?s)  upsertMemory\(\{ scope = "global", scopeId = null, key, value, source = "user" \}\) \{.*?\n  deleteMemory\(id\) \{ return this\.db\.prepare\("DELETE FROM memories WHERE id=\?"\)\.run\(id\)\.changes > 0; \}'
  if (-not [regex]::IsMatch($t, $pattern)) { throw 'legacy memory method block missing' }
  $replacement = @'
  upsertMemory({ scope = "global", scopeId = null, key, value, source = "user", type = null, sourceRefs = [], threadId = null, jobId = null }) {
    const scopeKind = scope === "project" ? "project" : "global";
    const existing = this.listDurableMemories({ scopeKind, scopeId }).find((memory) => memory.key === String(key || "").trim());
    if (existing) this.retireDurableMemory(existing.memoryId, "superseded");
    const record = promoteMemoryInput({ scope: scopeKind, scopeId, key, value, source, type }, { projectId: scopeId, threadId, jobId, sourceRefs });
    return memoryRecordView(this.putDurableMemory(record));
  }
  listMemories(scope = null, scopeId = null) {
    const rows = scope
      ? this.listDurableMemories({ scopeKind: scope === "project" ? "project" : "global", scopeId })
      : this.listDurableMemories();
    return rows.map(memoryRecordView).filter(Boolean);
  }
  deleteMemory(id) { return this.retireDurableMemory(id, "superseded"); }
'@
  $t = [regex]::Replace($t, $pattern, $replacement, 1)
  [IO.File]::WriteAllText($p, $t, [Text.UTF8Encoding]::new($false))
  & node --check $p
  if ($LASTEXITCODE -ne 0) { throw 'workstation-store syntax check failed' }
  $testOutput = (& node --test (Join-Path $RuntimeRoot 'test\workstation-store.test.mjs') (Join-Path $RuntimeRoot 'test\typed-memory.test.mjs') 2>&1 | Out-String)
  if ($LASTEXITCODE -ne 0) { throw "typed memory/store tests failed`n$testOutput" }
  [pscustomobject]@{
    ok = $true
    backup = $backup
    beforeMd5 = $current
    afterMd5 = (Get-FileHash -LiteralPath $p -Algorithm MD5).Hash.ToLowerInvariant()
    tests = ($testOutput -split "`r?`n" | Where-Object { $_ -match '^# (tests|pass|fail) ' })
  } | ConvertTo-Json -Depth 4
} catch {
  Copy-Item -LiteralPath $backup -Destination $p -Force
  throw
}
