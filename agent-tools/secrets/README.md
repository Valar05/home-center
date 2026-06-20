# Shell Secret Conversion Tools

These tools move API keys and tokens out of shell startup files and into a sourced secrets file.

Default conversion:

```sh
python3 agent-tools/secrets/convert_bashrc_secrets.py
python3 agent-tools/secrets/convert_bashrc_secrets.py --apply
```

Defaults:

- source rc: `~/.bashrc`
- secret env: `~/.secrets/shell.env`
- candidates: variable names containing `API_KEY`, `TOKEN`, `SECRET`, `PASSWORD`, `PRIVATE_KEY`, `ACCESS_KEY`, `AUTH`, or `CREDENTIAL`

The script prints variable names and counts only. It does not print values. With `--apply`, it creates a timestamped `.bashrc` backup, writes the secrets file with mode `600`, replaces moved lines with comments, and adds a small source block to `.bashrc`.

Use explicit names if you want a narrower move:

```sh
python3 agent-tools/secrets/convert_bashrc_secrets.py --include OPENAI_API_KEY,ANTHROPIC_API_KEY --apply
```

## Refresh Shell And Test APIs

Run this from your normal Termux shell when you want to move matching keys out of `~/.bashrc`, source `~/.secrets/shell.env`, and smoke-test configured APIs:

```sh
cd /storage/emulated/0/Documents/GodotProjects/home-center
sh agent-tools/secrets/refresh_and_test_apis.sh
```

The API tester sends tiny prompts to OpenAI, Anthropic, and Gemini when their keys are present. Cartesia and itch.io are checked with lightweight authenticated account/list endpoints because they are not text-prompt APIs. Results print provider names and short status only, never key values.

Optional model overrides:

```sh
OPENAI_TEST_MODEL=gpt-5-mini ANTHROPIC_TEST_MODEL=claude-3-5-haiku-latest GEMINI_TEST_MODEL=gemini-2.0-flash sh agent-tools/secrets/refresh_and_test_apis.sh
```
