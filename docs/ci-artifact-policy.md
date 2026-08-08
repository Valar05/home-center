# CI Artifact Policy

Home Center CI should keep durable records where they help operators debug failures and prove what ran, while avoiding accidental retention of secrets or bulky generated data.

## Defaults

- Upload logs, coverage reports, and test result summaries for failing or diagnostic workflows.
- Prefer short retention windows for routine CI artifacts.
- Do not upload `.env` files, credentials, OAuth tokens, private keys, or provider payloads that may contain secrets.
- Do not upload generated dependency folders such as `node_modules/`.
- Name artifacts clearly with the workflow purpose, job, and platform when relevant.

## Recommended retention

| Artifact type | Recommended retention |
| --- | ---: |
| Test summaries and coverage | 7-14 days |
| Failure debug logs | 7 days |
| Release bundles | Match release policy |
| Security-sensitive diagnostics | Avoid upload unless scrubbed |

## Checklist for new workflows

Before adding an `upload-artifact` step:

1. Confirm the artifact is useful after the job completes.
2. Confirm the path excludes secrets and local configuration.
3. Set an explicit `retention-days` value.
4. Use a deterministic artifact name.
5. Keep artifact size bounded.

## Example

```yaml
- name: Upload test report
  uses: actions/upload-artifact@v4
  if: always()
  with:
    name: test-report-${{ runner.os }}
    path: reports/test-results.xml
    retention-days: 7
```
