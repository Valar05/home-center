# DMC Terminal — concrete vertical slice

This is the concrete endpoint for the ASCII Kinesis / Motion Dungeon research: a real-time terminal action game, not another animation framework diagram.

The target is **Devil-May-Cry-like combat grammar in an original first-person ASCII game**. The current weapon is the commissioned giant shovel. No Devil May Cry character art, audio, dialogue, stage art, or other source assets are copied into the program.

## Run

From the Home Center repository root on Termux/Linux:

```sh
python3 -B tools/terminal_dmc.py
```

If raw-key terminal mode is unavailable:

```sh
python3 -B tools/terminal_dmc.py --turn
```

Deterministic scripted combat uses the same simulation core:

```sh
python3 -B tools/terminal_dmc.py \
  --script 'wwwwwwwwwwwwj......j.......k....j.....l' \
  --render-final
```

The commit-bound proof entrypoint is:

```sh
python3 -B tools/terminal_dmc_prove.py
```

That proof is mechanical only. It does not replace playing the raw-key build on Drew's actual terminal.

## Anticipation Theorem mode

`tools/terminal_dmc_anticipation.py` turns the current enemy attack loop into a playable experiment for the working theorem:

```text
I(X;A) > I(X;R) > I(X;I)=0
```

under the theorem's stated assumptions.

The game does **not** treat this inequality as already proven by code. The normal condition deliberately instantiates the proposed information structure:

- **A — anticipation:** three attacks have distinct early cues (`^`, `>`, `_`).
- **COMMIT:** the attack becomes committed and the counterfactual window begins closing.
- **R — reaction/committed action:** identity is compressed to a coarser cue (`ARC` or `LINE`).
- **I — impact:** every attack exposes the same `X` marker, so impact itself carries no pre-action attack-identity information.

Run the normal condition:

```sh
python3 -B tools/terminal_dmc_anticipation.py
```

Every resolved enemy attack records attack identity, A/R/I observations, first response, response phase, correctness, response latency, physical outcome, and experimental condition under the Home Center state directory.

Two counterfactual conditions are built in specifically so the theorem can lose:

```sh
# Destroy anticipation identity information.
python3 -B tools/terminal_dmc_anticipation.py --collapse-anticipation

# Give reaction the same identity information as anticipation.
python3 -B tools/terminal_dmc_anticipation.py --perfect-reaction
```

The channel contract can be inspected without playing:

```sh
python3 -B tools/terminal_dmc_anticipation.py --theorem-channel-report --no-theorem-log
python3 -B tools/terminal_dmc_anticipation.py --collapse-anticipation --theorem-channel-report --no-theorem-log
python3 -B tools/terminal_dmc_anticipation.py --perfect-reaction --theorem-channel-report --no-theorem-log
```

The normal channel should satisfy the strict ordering. `--collapse-anticipation` must break it by driving `I(X;A)` to zero. `--perfect-reaction` must break strict `A > R` by making the channels equally informative.

Human behavior is a separate layer. After play, inspect the condition-specific response evidence:

```sh
python3 -B tools/terminal_dmc_anticipation.py --theorem-behavior-report
python3 -B tools/terminal_dmc_anticipation.py --collapse-anticipation --theorem-behavior-report
python3 -B tools/terminal_dmc_anticipation.py --perfect-reaction --theorem-behavior-report
```

Those reports compare response timing/correctness by the phase in which the player first acted. They intentionally do **not** print `THEOREM PROVEN`. The useful falsification question is whether degrading anticipation information degrades actual decisions, and whether upgrading reaction information closes that gap.

Offensive action also enters the experiment concretely: staggering an enemy during anticipation/commit/reaction terminates that trial as `INTERRUPTED_BY_OFFENSE`. The attack does not get credited with an impact that never happened. This makes initiative measurable as a mechanism that closes the opponent's remaining counterfactual window.

The design sentence is preserved because the game now gives it something to lose against:

> Anticipation is information with a head start.

## Controls

- `A / D` — strafe between left, center, and right lanes.
- `W / S` — earn or surrender range.
- `J` — shovel ground string; against an airborne target it becomes an air re-hit.
- `K` — `UPROOT`, the launcher.
- `L` — grounded heavy; against an airborne target it becomes `BURIAL`, a downward spike.
- `F` — shovel brace. A correctly timed incoming strike is caught as a tool-supported parry and converts enemy momentum into recovery debt.
- `SPACE` — dodge / lane break.
- `R` — reset room.
- `Q` — quit.

In Anticipation Theorem mode the three deliberately readable counter classes are:

- `FALLING_EDGE` → `DODGE`
- `LINE_THRUST` → `STRAFE`
- `LOW_SWEEP` → `BRACE`

A player can survive with a response that is classified as the wrong read. That is intentional. Inference correctness and physical survival are stored separately so the experiment cannot quietly redefine every lucky escape as understanding.

## What is concrete already

The program currently has:

- a real-time nonblocking raw-terminal loop at 20 simulation ticks per second;
- a first-person pseudo-3D ASCII arena with three lateral lanes and distance-scaled enemies;
- an always-visible first-person shovel whose pose changes with attacks, launcher, spike, dodge, hurt, and brace;
- three enemies with approach, windup, strike, stagger, landing, death, and recovery states;
- a three-hit ground string;
- launcher -> airborne state -> air re-hit -> spike;
- hit-stop on authored impact classes;
- cancel windows after successful hits;
- enemy telegraphs and timed dodge resolution;
- shovel-brace parry;
- combo timer and style rank;
- style reward for move variety with repetition decay;
- deterministic headless scripting over the exact same combat state machine used by interactive play;
- a theorem experiment that separates anticipation, commitment/reaction, and impact information;
- explicit counterfactual channel conditions and append-only behavioral trial evidence.

## Motion corpus ingestion is now subordinate to play

The game does not wait for a universal motion ontology. Existing ASCII Kinesis work is mined for specific useful laws and then forced to earn its keep inside play.

Current transfers include:

- `experiments/ascii-kinesis/v2-strikes-026-yielding-contact-chase-step-debt/` — contact does not magically erase momentum; yielding contact creates chase/braking debt. The game therefore preserves range consequence instead of snapping targets back into an attack slot.
- `experiments/ascii-kinesis/v2-defense-014-tool-kickstand-catch-recovery/` — the tool can temporarily buy support before the body finishes recovery. This became the shovel-brace / parry mechanic.
- the airborne and locomotion families — support break, airborne travel, landing, and recovery remain separate states rather than one jump flag. `UPROOT`, juggle, `BURIAL`, and landing debt use that distinction.
- timing work — ONES/TWOS/FOURS and STREET_FIGHTER/CAPCOM remain direction vocabulary, not claims about source-authentic timing. The terminal game's tick counts are authored gameplay opinions.
- **The Anticipation Theorem** — enemy offense now has an explicit information-bearing anticipation window, commitment, compressed reaction cue, impact, counterfactual manipulations, and interruption-by-offense evidence.

Future ingestion should answer questions raised by the playable program: better launch timing, chase-step cancels, crowd control, tool custody, enemy reactions, aerial drift, recoil, camera response, anticipation distinctiveness, counterfactual-window closure, and style-system readability. Corpus work that cannot change play remains evidence on the shelf.

## Regression contract

```sh
python3 -B tools/test_terminal_dmc.py
python3 -B tools/test_terminal_dmc_anticipation.py
```

The deterministic contracts check that:

1. `UPROOT` creates a real airborne state;
2. ground string -> launch -> air re-hit -> spike executes as one combo;
3. move variety earns more style than repetition;
4. dodge can beat a telegraphed strike;
5. shovel brace can parry into enemy recovery debt;
6. the rendered frame exposes the target, style meter, and first-person shovel;
7. scripted state is deterministic;
8. normal theorem-channel design satisfies `I(X;A) > I(X;R) > I(X;I)=0`;
9. collapse-A and perfect-R counterfactuals break the strict ordering in the intended ways;
10. first-response phase/correctness is retained separately from physical survival;
11. offensive interruption closes an attack trial instead of fabricating impact;
12. theorem phase/cue is visible on the playable render.

`tools/terminal_dmc_prove.py` runs both regression families plus the theorem channel counterfactuals and remains commit-bound.

This is intentionally narrower than human acceptance. A test can prove that the combat rules and experiment wiring executed. It cannot prove that the terminal game feels good or that the theorem predicts Drew's behavior.

## Capability ledger

- **Requested:** actual terminal DMC-shaped game.
- **Implemented on branch:** deterministic combat core, ANSI renderer, raw input loop, fallback input mode, regression contract, proof runner, Anticipation Theorem mode, counterfactual conditions, behavioral logging/reporting.
- **Theorem channel design mechanically checked:** pending authorized-runtime proof execution.
- **Theorem behaviorally supported/falsified by Drew:** pending actual comparative play.
- **Runtime-proven on authorized Home Center body:** pending.
- **Interactive feel accepted by Drew:** pending.
- **Merged/deployed:** no.

The useful next step is not a larger architecture document. It is to run the exact branch on the authorized terminal, play normal and counterfactual theorem conditions, and mutate whichever part feels dead or predicts badly first.
