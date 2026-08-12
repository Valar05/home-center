# Fortress Online V2 Installation

## Promotion authority
Drew's explicit instruction to install the new Fortress Online authorizes promotion from the isolated V2 candidate to the live Fortress boot path, provided the acceptance gates remain green on the exact promoted head.

## Install invariant
The live installation must not alter unrelated working trees. Installation is source-controlled and should consume the merged `main` copy of Fortress V2 boot assets.

## Live entrypoint
`node tools/fortress_online_v2_boot.mjs`

The resulting `fortress.online.v2.boot-capsule.v3` JSON is the canonical boot payload. Consumers invoking Fortress Online must load its `bootPrompt` before mission execution. The boot fails closed if canonical `fortress-core` or `phone-runtime` skill documents are absent.

## Acceptance before promotion
- full deterministic V2 suite green on the exact candidate head;
- canonical skill body boot test green;
- Phone Hands execution proof green on `primary-phone`;
- three current non-destructive real-work shadow missions green;
- persistent GitHub readback/receipt exists;
- explicit operator acceptance to promote.

## Post-merge installation proof
After merge, run the same boot and deterministic suite from an isolated LFS-disabled clone of `main` through Phone Hands. The installed version is accepted only when the emitted commit equals merged main and the boot capsule reports both canonical skill documents plus a successful three-shadow receipt.
