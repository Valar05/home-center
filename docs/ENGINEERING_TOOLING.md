# Home Center Engineering Tooling

Type: Doctrine / engineering memory / local-first tooling / workflow substrate
Status: Repo-local source of truth
Date: 2026-07-10

Home Center's engineering tooling mission is to make engineering state durable.

Home Center is not an IDE, not a chat interface, and not an agent framework. It is the persistent operating layer between repositories, cloud services, local machines, AI models, and human engineers. Every engineering action should either discover, preserve, verify, or promote knowledge.

## Primary Goal

Home Center should become the canonical workspace for engineering state. It should answer, from durable records rather than chat history:

- what changed
- why it changed
- who or what changed it
- what evidence supports it
- what remains unknown
- what should happen next

If every chat history disappeared tomorrow, Home Center should preserve enough context for a new engineer or AI model to continue work from repository truth and engineering memory.

## Principles

### Repository Truth

Repositories are primary sources. Read before writing. Never assume project structure when it can be discovered.

### Evidence Before Opinion

Measure before summarizing. Summarize before recommending. Claims about build state, provider access, artifacts, or behavior need evidence records.

### Durable Memory

Chat is transient. Repositories, generated artifacts, review records, workflow runs, and indexed evidence persist. Important engineering knowledge must become a repo-local or provider-backed artifact with provenance.

### Local First

Expensive or hardware-bound work belongs on local execution surfaces such as Termux, desktop workstations, CI runners, Godot, Blender, FFmpeg, compilers, Docker, Android, Shizuku, ADB, or project-native tools. Cloud agents orchestrate; execution backends execute.

### Stateless Agents

Agents are replaceable capabilities. Knowledge is not. Important engineering state must not live only inside an agent conversation.

## V1 Responsibilities

### Repository Orientation

One command should produce a repository orientation report covering git state, docs, build systems, validation commands, artifact folders, recent commits, branch/remotes, risks, and open unknowns.

### Artifact Catalog

Development outputs such as screenshots, benchmark reports, test results, exported meshes, rendered videos, profiler traces, review notes, measurements, diagrams, and generated reports must be catalogable with source repo, branch, commit, generator, workflow, timestamp, dependencies when known, hash, and dirty-worktree state.

### Prompt Library

Prompts are versioned assets. Each prompt should declare purpose, inputs, outputs, required tools, expected artifacts, and acceptance criteria. Prompts should reference reusable workflows rather than duplicating large instruction blocks.

### Tool And Agent Registries

Executable capabilities are tools with machine-readable metadata. Agents are capabilities, not personalities; each advertises purpose, tools, permissions, inputs, outputs, and limitations.

### Workflow Engine

Workflow definitions should become data, not one-off chat instructions. V1 records workflow runs and their artifacts before attempting a full event automation engine.

Command Center is the retained project, knowledge-bucket, app-control, and browser-learning compatibility plane for this workflow layer. Its repo-local contract is `docs/COMMAND_CENTER_MCP.md`. Command Center Codex execution is retired; owned asynchronous capabilities such as Foundry use their own isolated workers behind Home Center registries.

Command Center's managed knowledge bucket is the durable organization surface for execution memory and cross-repository engineering learning. It separates `memory/past-logs`, `memory/current-condensed`, `skills/scratch`, `skills/promoted`, and `notes/cross-repo` so worker evidence, resumable state, candidate procedures, promoted skills, and repo-spanning notes do not collapse into one catch-all document.

### State Graph

Engineering memory is a graph. Nodes include repositories, documents, issues, experiments, artifacts, prompts, agents, tools, commits, reviews, workflows, and verification runs. Edges include `created`, `depends_on`, `supersedes`, `references`, `generated`, `reviewed`, `blocks`, `duplicates`, `derived_from`, `verified_by`, and `belongs_to`.

### Search

V1 search is structured file and text search over durable manifests and reports. Semantic search is not claimed until the records are useful and stable enough to index.

### Independent Verification

Builders do not verify themselves. Verification records must name the command, environment, target, result, evidence path, and residual risk.

## Non-Goals

Home Center engineering tooling is not another IDE, task manager, note app, Git client, CI platform, vector database, or chat-only agent shell. It coordinates those systems and preserves durable engineering memory across them.

## First Implementation Contract

The first useful substrate is local and file-backed:

- `tools/home_center_engineering_orient.mjs` produces orientation artifacts.
- `tools/home_center_artifact_register.mjs` catalogs generated artifacts.
- `generated/engineering_memory/` stores JSONL records and markdown reports.
- `prompts/engineering/` stores versioned prompt assets.

Cloud publication, Drive archival, MCP search tools, semantic search, and automation triggers should build on this substrate only after local records prove useful.
