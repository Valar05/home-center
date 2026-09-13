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
- deterministic headless scripting over the exact same combat state machine used by interactive play.

## Motion corpus ingestion is now subordinate to play

The game does not wait for a universal motion ontology. Existing ASCII Kinesis work is mined for specific useful laws and then forced to earn its keep inside play.

Current transfers include:

- `experiments/ascii-kinesis/v2-strikes-026-yielding-contact-chase-step-debt/` — contact does not magically erase momentum; yielding contact creates chase/braking debt. The game therefore preserves range consequence instead of snapping targets back into an attack slot.
- `experiments/ascii-kinesis/v2-defense-014-tool-kickstand-catch-recovery/` — the tool can temporarily buy support before the body finishes recovery. This became the shovel-brace / parry mechanic.
- the airborne and locomotion families — support break, airborne travel, landing, and recovery remain separate states rather than one jump flag. `UPROOT`, juggle, `BURIAL`, and landing debt use that distinction.
- timing work — ONES/TWOS/FOURS and STREET_FIGHTER/CAPCOM remain direction vocabulary, not claims about source-authentic timing. The terminal game's tick counts are authored gameplay opinions.

Future ingestion should answer questions raised by the playable program: better launch timing, chase-step cancels, crowd control, tool custody, enemy reactions, aerial drift, recoil, camera response, and style-system readability. Corpus work that cannot change play remains evidence on the shelf.

## Regression contract

```sh
python3 -B tools/test_terminal_dmc.py
```

The deterministic contract checks that:

1. `UPROOT` creates a real airborne state;
2. ground string -> launch -> air re-hit -> spike executes as one combo;
3. move variety earns more style than repetition;
4. dodge can beat a telegraphed strike;
5. shovel brace can parry into enemy recovery debt;
6. the rendered frame exposes the target, style meter, and first-person shovel;
7. scripted state is deterministic.

This is intentionally narrower than human acceptance. A test can prove that the combat rules executed. It cannot prove that the terminal game feels good.

## Capability ledger

- **Requested:** actual terminal DMC-shaped game.
- **Implemented on branch:** deterministic combat core, ANSI renderer, raw input loop, fallback input mode, regression contract, proof runner.
- **Runtime-proven on authorized Home Center body:** pending.
- **Interactive feel accepted by Drew:** pending.
- **Merged/deployed:** no.

The next useful work is not a larger architecture document. It is to run this exact branch on the authorized terminal, play it, and mutate whichever part feels dead first.
