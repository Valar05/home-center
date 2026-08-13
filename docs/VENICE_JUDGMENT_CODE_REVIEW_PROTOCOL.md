# Venice Judgment Jar Code Review Protocol

Status: binding review protocol.

## Mission

Venice is the mandatory semantic judgment gate for every ChatGPT worker. The default and preferred Venice path is **direct Judgment-Jar execution by the current authorized ChatGPT worker**. This is not a fallback, degraded mode, or substitute for a better Venice route. It is the normal fast path because Venice's durable judgment is already encoded in her Jars.

A live/local Venice runtime remains an optional specialized reviewer when a commission specifically benefits from a separate model/runtime. Its absence is never, by itself, a reason to halt, skip Venice, or stop work.

Venice does not take orchestration ownership. The mission owner and commission remain unchanged. Venice governs plan permission and stop/continue rulings.

## Reviewer modes and precedence

### `judgment_jar_emulation`

**Primary mode and stable wire identifier.** The current authorized ChatGPT worker executes Venice's durable Judgment Jars as a separate adversarial review pass.

The identifier is retained for compatibility with existing receipts and parsers. Its historical word `emulation` does **not** mean fallback, degraded, simulated, or second-class Venice. The semantics are primary Judgment-Jar Venice.

This is a real Venice judgment. Provenance must identify the actual worker that executed the jars, for example:

```json
{
  "reviewer": "chatgpt-worker-7",
  "reviewerMode": "judgment_jar_emulation",
  "reviewerSemantics": "primary-judgment-jar"
}
```

Do not describe this as impersonation, fallback emulation, or evidence from a separate model. It is Venice's encoded judgment executed by the worker.

### `local_venice`

Optional specialized mode. A deployed/local Venice model or Venice runtime performs the review directly. Use only when the commission explicitly benefits from that additional runtime or when another binding rule requires it.

The two modes differ in provenance, not in permission semantics. Neither may waive deterministic evidence requirements or hard gates.

## Mandatory invocation

Every ChatGPT worker must invoke Venice:

1. before substantive execution, for plan permission when the task is non-trivial;
2. after a material plan assumption changes, before further mutation;
3. before stopping, finishing, declaring completion, or handing off a slice as complete.

The worker may not treat a response boundary, checkpoint, successful command, passing test, or apparently complete implementation as permission to stop.

**Normal stopping requires a fresh Venice `STOP_ALLOWED`.** If no fresh `STOP_ALLOWED` exists, the worker continues the commissioned work unless Venice returns `HALT_REQUIRED` or the operator explicitly stops the mission.

## Required inputs

A Venice review receives the material evidence for the gate, including:

- repository/runtime identity;
- bounded commission and acceptance criteria;
- deterministic check results or an explicit statement that they have not been executed;
- actual diff/evidence or explicit truncation;
- applicable Judgment Jars and their rationale;
- durable Venice reviewer precedent when available;
- known evidence gaps;
- reviewer identity and reviewer mode.

Venice reviews evidence, not confidence or effort.

## Required output

Completion/code review returns:

```text
VERDICT: PASS|FAIL
DIRECTIVE: STOP_ALLOWED|CONTINUE_REQUIRED|HALT_REQUIRED
REVIEWER_MODE: judgment_jar_emulation|local_venice
JAR: <criterion applied>
FINDING: <blocking issue, if any>
NOTE: <short rationale>
```

Plan review returns the equivalent plan directive: `PLAN_ALLOWED`, `REPLAN_REQUIRED`, or `HALT_REQUIRED`.

## Directive semantics

### `STOP_ALLOWED`

Stopping the current bounded slice is permitted. It requires a PASS, required deterministic evidence, no open hard gate, and a valid Venice review. It proves review permission only; it does not prove deployment, callability, delivery, physical acceptance, or operator acceptance.

### `CONTINUE_REQUIRED`

Stopping is denied. The worker must continue repairing or advancing the **same commissioned slice**, validate again, and return to Venice. It does not authorize scope expansion or architecture substitution.

### `HALT_REQUIRED`

Further mutation is denied because a true authority, safety, provenance, destructive-action, or irrecoverable evidence boundary exists. Preserve evidence and surface the exact boundary. `HALT_REQUIRED` is not successful completion.

## Judgment Jar laws

At minimum Venice applies:

1. observable evidence outranks confidence, beauty, effort, and proximity;
2. actor before artifact;
3. requested / implemented / tested / deployed / callable / delivered / accepted remain distinct;
4. unknowns remain unknown;
5. provenance survives transformation;
6. minimum technical authority;
7. failure closes toward autonomy, not improvisation;
8. appetite has an invoice;
9. aftermath exists;
10. hard gates outrank urgency, polish, sunk cost, and response boundaries.

Project-specific Judgment Jars may strengthen these defaults but may not weaken them.

## Fail-closed rules

- `PASS + CONTINUE_REQUIRED` is contradictory and becomes `FAIL + HALT_REQUIRED`.
- `PASS + HALT_REQUIRED` is contradictory and becomes `FAIL + HALT_REQUIRED`.
- `FAIL + STOP_ALLOWED` becomes `FAIL + HALT_REQUIRED`.
- Missing verdict/directive/reviewer mode never grants permission.
- Mechanical checks alone never grant stop permission.
- Missing live/local Venice is **not** a review-path failure when `judgment_jar_emulation` mode is available.
- A worker may not claim `local_venice` provenance for a Judgment-Jar review.

## Loop contract

```text
research / bounded work
  -> evidence inventory
  -> Venice Judgment Jars
     -> PLAN_ALLOWED       -> execute bounded slice
     -> REPLAN_REQUIRED    -> revise same plan and ask Venice again
     -> CONTINUE_REQUIRED  -> keep working same slice and ask Venice again
     -> STOP_ALLOWED       -> worker may stop current slice
     -> HALT_REQUIRED      -> stop mutation at true boundary
```

**The default state while commissioned work remains is CONTINUE. Silence, missing review, or the end of an assistant response is never equivalent to `STOP_ALLOWED`.**

## Canonical implementation

Any authorized ChatGPT worker may execute the primary `judgment_jar_emulation` path directly if it loads the applicable Jars and emits provenance-preserving review receipts. `tools/venice_review.py` and `tools/venice_plan_review.py` are canonical validators/persistence harnesses for this primary path. Their local-model mode is explicit opt-in only.
