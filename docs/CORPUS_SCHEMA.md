# She-Raw Corpus Schema

Canonical cases are Markdown files with YAML front matter and readable bodies. The runtime database imports/indexes them into `sheRawCorpusCases`.

Required fields:

- `id`
- `status`
- `type`
- `domains`
- `patterns`
- `source_refs`
- `source_date`
- `confidence`
- `confirmed_by_user`
- `situation`
- `accepted_assumption`
- `observation`
- `intervention`
- `outcome`
- `treasure`
- `collateral_damage`
- `lesson`

The corpus is evidence, not identity. Seed cases must be grounded in repository docs, issues, PRs, commits, review comments, or user corrections. Inferred cases must say they are inferred and carry lower confidence.
