# Judgement Jar: Repository Truth and Evidence

Status: active
Scope: claims, edits, validation, and completion

## Judgement

Repository evidence outranks model confidence. Runtime evidence outranks repository intention when the claim is about deployed or physical behavior.

## Operating rule

Before modifying code:

1. inspect relevant files and nearby doctrine;
2. inspect git status/diff when available;
3. identify the project-native validation command rather than inventing one.

After modifying code:

1. show the diff or summarize exact changed paths;
2. run the narrowest relevant deterministic validation;
3. run broader validation when the change warrants it;
4. record failures exactly rather than translating them into optimistic prose.

Never claim a build, deployment, device action, service state, or physical acceptance test passed unless fresh evidence for that specific claim exists.

A green local test means only that the declared local test passed. It does not imply deployment.

## Truth labels

When evidence is incomplete, distinguish:

- DOCUMENTED: directly supported by repository or durable artifact;
- OBSERVED: directly supported by fresh command/runtime output;
- INFERENCE: likely but not directly verified;
- OPEN: unresolved.

## Evidence that can change this judgement

A newer explicit engineering doctrine artifact that supersedes this evidence contract.
