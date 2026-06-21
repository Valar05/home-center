# Netrunner Architecture

Netrunner is a Home Center child capability with two halves:

1. Local browser shell: visible, interruptible, accessible, and safe.
2. Cloud brain: shared playbooks, discoveries, schemas, and trust promotion.

## Local components

### Browser shell

A borrowed browser surface, preferably Android WebView first, with a path to Chromium Custom Tabs or Playwright-backed desktop experimentation later.

Responsibilities:

- Load pages.
- Provide visible browser area beside or above chat.
- Expose page state to the observer.
- Accept safe commands from the action executor.

### Accessibility overlay

Responsibilities:

- Focus spotlight.
- Magnifier region.
- High contrast transforms.
- Large target mode.
- Element Command Mode on long press.
- Read focused element.
- Freeze-and-confirm mode for risky actions.

### DOM observer

Responsibilities:

- Extract visible text.
- Extract landmarks, headings, buttons, inputs, links, labels, forms, and focused element.
- Associate clicked/touched coordinates with DOM candidates.
- Capture modal/overlay candidates.
- Redact sensitive values before writing episode logs.

### Episode recorder

Records human-driven sessions as training data.

An episode is not automatically trusted. It is raw evidence.

### Action executor

Executes constrained local actions:

- Scroll.
- Focus.
- Click only after policy allows.
- Type only into selected fields.
- Apply temporary CSS/DOM user overrides.
- Undo temporary overrides.

### Voice engine

Cartesia-backed read aloud.

API keys must be entered by the user through Home Center settings and stored in Android Keystore or cloud Secret Manager. Keys must never enter repository files, logs, prompt memory, or shared discovery data.

## Cloud components

### Discovery store

Stores observed facts from episodes.

Discovery states:

1. observed
2. candidate
3. tested
4. trusted
5. deprecated

### Site playbooks

Site-specific knowledge:

- navigation paths
- recurring modal patterns
- checkout quirks
- hidden totals
- accessibility repairs
- common failure modes

### Task playbooks

Task-specific knowledge independent of site:

- compare products
- fill a form
- download invoice
- cancel subscription
- find return policy
- manage appointment

### Safety policies

Shared rules for risky tasks.

Never allow global behavior to self-modify directly from one session. Use promote-through-evidence, not mutation-by-vibes.

## Recommended first implementation path

1. Build WebView page loader.
2. Add split chat/browser layout.
3. Add DOM snapshot endpoint.
4. Add read-focused-element using Cartesia.
5. Add long-press Element Command Mode.
6. Add redacted episode recorder.
7. Add local JSON export for episodes.
8. Add cloud ingestion later.
