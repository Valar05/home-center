# Wizware DNS Debug Jar — MVP

Status: SOURCE JAR / durable Home Center
Owner: Drew
Scope: Diagnose DNS failures quickly without turning DNS debugging into architecture.

## Trigger

Use when a Wizware hostname/domain is failing, inconsistent, newly changed, or suspected of resolving incorrectly.

## Input

Minimum: hostname/domain.
Optional: expected target/IP/CNAME, failing client/network, observed error, recent DNS change.

## Deterministic pass

1. **NAME** — record exact hostname; never silently normalize to a neighboring domain.
2. **AUTHORITATIVE** — identify NS/SOA and query authoritative answers for relevant A/AAAA/CNAME/TXT/MX records.
3. **PUBLIC** — compare at least two independent public recursive resolvers when available.
4. **LOCAL** — compare the failing client's resolver/cache result when that lane is available.
5. **PATH** — follow the CNAME chain and flag loops, missing targets, unexpected flattening, split-horizon answers, stale values, SERVFAIL, NXDOMAIN, or timeout.
6. **TTL** — record TTLs and distinguish propagation/cache lag from an actually wrong authoritative record.
7. **DNSSEC** — if SERVFAIL or validation is implicated, inspect DS/DNSKEY/validation state rather than guessing.
8. **VERDICT** — output the smallest evidenced failure class and next mutation. Do not change DNS unless explicitly authorized.

## Output contract

Always return:
- hostname checked;
- timestamp;
- authoritative answer;
- public resolver comparison;
- local result if available, otherwise `LOCAL: NOT OBSERVED`;
- TTL/propagation note;
- failure class;
- smallest next action;
- evidence/receipt references.

## Failure classes

`AUTHORITATIVE_WRONG`
`PROPAGATION_OR_CACHE`
`CNAME_CHAIN`
`NXDOMAIN`
`SERVFAIL_DNSSEC`
`RESOLVER_SPECIFIC`
`LOCAL_NETWORK`
`APPLICATION_NOT_DNS`
`INSUFFICIENT_EVIDENCE`

## Guardrails

- Read/diagnose by default. DNS mutation requires explicit authorization.
- Never claim propagation when authoritative data itself is wrong.
- Never claim DNS failure solely from an HTTP/TLS/application error.
- Do not flush caches, change resolvers, edit zones, or restart infrastructure merely to make a test pass without recording why.
- Preserve before/after evidence for any later authorized mutation.

## Drew Durable gate

The Jar does not pass because it produced troubleshooting prose. It passes when the evidence narrows the failure to a testable class and names the smallest next action.

Compact question: **Which resolver is lying, and compared to what authority?**
