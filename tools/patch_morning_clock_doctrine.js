'use strict';

const fs = require('node:fs');

function insertSection(path, marker, heading, section) {
  let text = fs.readFileSync(path, 'utf8');
  if (text.includes(heading)) return false;
  const index = text.indexOf(marker);
  if (index < 0) throw new Error(`Missing marker ${marker} in ${path}`);
  text = text.slice(0, index) + section.trimEnd() + '\n\n' + text.slice(index);
  fs.writeFileSync(path, text);
  return true;
}

const common = `## Deterministic morning clock wrapper

The always-on clock also owns one daily stateful question: **is the morning wrapper relevant now?** This is not model taste. Evaluate the pure policy in \`functions/morning_brief_policy.js\` as \`dru.morning-clock.v1\` using the same freshly observed local-clock turn.

Deterministic relevance:

- timezone: \`America/Chicago\`;
- normal window: 04:00 through 11:59 local;
- exact phrase \`good morning\` extends relevance through 14:59 local;
- relevant only when today's local date has not already received the wrapper;
- after today's wrapper is emitted, repeated messages and repeated \`good morning\` are a no-op for this wrapper.

When relevant, the wrapper is additive: it MUST NOT replace, delay, or reinterpret Drew's actual request. After the clock is exposed, include before/alongside the requested work:

1. a reminder to take Drew's **prescribed inhaler and morning pills**; never infer or alter dosing;
2. live local weather/current-day forecast;
3. deterministic need-to-know only: today's time-bound calendar items, material/severe weather, and explicit Home Center obligations due today when available;
4. then continue the user's requested work in the same turn.

End the wrapper with a concise request to confirm inhaler + pills. While that confirmation is pending, the short replies \`done\`, \`taken\`, \`yes\`, \`yep\`, \`yeah\`, \`got them\`, \`did it\`, \`both done\`, and \`both taken\` count as confirmation. Longer replies count only when they explicitly mention inhaler/pills/meds as taken/used/done. Unrelated replies are not confirmation.

Morning state is durable and idempotent. On wrapper emission, persist a Home Center state record for the local date with at least \`briefedLocalDate\`, \`briefedAtUtc\`, \`confirmedLocalDate\`, \`followUpDueUtc = briefedAtUtc + 30 minutes\`, and \`followUpSentLocalDate\`. Use a stable date-scoped identity/tag so automation can retrieve it without conversational memory.

The automated follow-up is one-shot. It may notify only when \`morningFollowUpDecision(...)\` returns \`shouldFollowUp=true\`: today's wrapper exists, confirmation is absent, 30 minutes have elapsed, and no follow-up was already sent. After sending, persist \`followUpSentLocalDate=today\`. Confirmation makes the follow-up a no-op.

Failure labels: \`MORNING_CLOCK_BYPASS\` (relevant morning turn escaped without wrapper), \`MORNING_DUPLICATE\` (same local date received duplicate wrapper), \`MORNING_FALSE_CONFIRMATION\` (unrelated reply treated as medication confirmation), \`MORNING_FOLLOWUP_DUPLICATE\` (more than one follow-up for the same local date), and \`MORNING_REQUEST_DISPLACED\` (wrapper replaced or delayed the user's actual commission).

Acceptance is deterministic regression evidence from \`node --test functions/morning_brief_policy.test.js\`, including ordinary first-morning relevance, once-per-date idempotence, explicit-good-morning override, outside-window no-op, confirmation classification, one-shot due follow-up, and DST-aware local-clock conversion.
`;

insertSection(
  '.continue/rules/05-judgement-jar-simulation-trap.md',
  '## Full-machine invocation',
  '## Deterministic morning clock wrapper',
  common,
);

insertSection(
  'skills/dru-simulation-trap/SKILL.md',
  '## Composed machine',
  '## Deterministic morning clock wrapper',
  common,
);
