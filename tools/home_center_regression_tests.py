#!/data/data/com.termux/files/usr/bin/python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
failures = []

def read(relative):
    return (ROOT / relative).read_text()

def fail(message):
    failures.append(message)

def require_contains(source, needle, label):
    if needle not in source:
        fail(f"{label}: missing {needle}")

def require_absent(source, needle, label):
    if needle in source:
        fail(f"{label}: still contains {needle}")

def method_body(source, signature, next_signature):
    start = source.find(signature)
    if start < 0:
        fail(f"missing method signature: {signature}")
        return ""
    end = source.find(next_signature, start + len(signature))
    if end < 0:
        fail(f"missing following method signature: {next_signature}")
        return source[start:]
    return source[start:end]

main_activity = read('app/src/main/java/com/dclar/homecenter/MainActivity.java')
openai_client = read('app/src/main/java/com/dclar/homecenter/OpenAiAgentClient.java')
drive_client = read('app/src/main/java/com/dclar/homecenter/GoogleDriveClient.java')
functions_index = read('functions/index.js')
proxy_script = read('tools/cartesia_proxy.py')
build_gradle = read('app/build.gradle')
manifest = read('app/src/main/AndroidManifest.xml')

submit = method_body(main_activity, 'private void submitMessage', 'private void sendAgentTurn')
require_contains(submit, 'sendAgentTurn(clean);', 'typed chat always enters GPT-5.5 first')
require_absent(submit, 'tryHandleLocalStatusQuestion', 'typed chat must not run local status parser before GPT')
require_absent(submit, 'tryHandleLocalCommand', 'typed chat must not run local command parser before GPT')
require_absent(main_activity, 'private boolean tryHandleLocalStatusQuestion', 'local natural-language status parser removed')
require_absent(main_activity, 'private boolean tryHandleLocalCommand', 'local natural-language command parser removed from MainActivity')
require_absent(main_activity, 'private boolean isDriveDiagnosticIntent', 'Drive keyword router removed')
require_absent(main_activity, 'CommandParser.parse(text)', 'typed chat no longer parses English commands locally')
require_absent(main_activity, 'googleDriveClient.answerRequest', 'MainActivity no longer uses local Drive planner')
require_contains(main_activity, 'runAgentToolLoop', 'Android runs GPT-directed tool loop')
require_contains(main_activity, 'executeRegisteredTool', 'Android dispatches registered tool calls only')
require_contains(main_activity, '"drive.search".equals(toolName)', 'Drive search is registered as a named tool')
require_contains(main_activity, '"drive.read".equals(toolName)', 'Drive read is registered as a named tool')
require_contains(main_activity, 'LocalLog.info("agent", "tool_call " + toolName)', 'tool calls are logged as tool calls, not chat plumbing')
require_contains(main_activity, 'tool_loop_limit', 'tool loop has a bounded failure mode')

require_contains(openai_client, 'ToolTurn sendToolTurn', 'Android client can request GPT tool decisions')
require_contains(openai_client, 'postJson("agentToolTurn"', 'Android client calls tool-turn gateway endpoint')
require_contains(openai_client, '"drive.search"', 'Android advertises drive.search tool')
require_contains(openai_client, '"drive.read"', 'Android advertises drive.read tool')
require_absent(openai_client, 'if (message.contains', 'OpenAI client must not inspect English text')

require_contains(functions_index, 'exports.agentToolTurn', 'gateway exposes GPT tool-turn endpoint')
require_contains(functions_index, 'The Android app is only your hands', 'gateway prompt encodes tool-host architecture')
require_contains(functions_index, 'A successful tool call is not a final answer unless it satisfies the request', 'gateway prompt forbids stopping after first successful tool')
require_contains(functions_index, 'do not answer Drive document questions without tool results', 'gateway prompt prevents canned Drive refusals')
require_contains(functions_index, 'Hide plumbing', 'gateway prompt hides connector diagnostics from normal chat')
require_contains(functions_index, 'drive.search({query, folderName, mimeType, pageSize})', 'gateway exposes structured Drive search contract')
require_contains(functions_index, 'drive.read({fileId, mimeType, name})', 'gateway exposes structured Drive read contract')

require_contains(drive_client, 'JSONObject runTool(String toolName, JSONObject arguments, GoogleSignInAccount account)', 'Drive client exposes registered tool executor')
require_contains(drive_client, '"drive.search".equals(toolName)', 'Drive search tool is dispatchable')
require_contains(drive_client, '"drive.read".equals(toolName)', 'Drive read tool is dispatchable')
require_contains(drive_client, 'readDocumentText', 'Drive read tool can export document text')
require_absent(drive_client, 'DriveAnswer answerRequest', 'Drive client no longer owns user-request planning')
require_absent(drive_client, 'value.contains("first sentence")', 'Drive client no longer parses first-sentence intent')
require_absent(drive_client, 'value.contains("summarize")', 'Drive client no longer parses summarize intent')
require_absent(drive_client, 'value.startsWith("read ")', 'Drive client no longer parses read intent')
require_absent(drive_client, 'folderNameFrom(requestText)', 'Drive client no longer derives folder names from English requests')

require_contains(main_activity, 'GoogleDriveClient.DRIVE_METADATA_SCOPE', 'Google sign-in requests Drive scope')
require_contains(drive_client, 'https://www.googleapis.com/auth/drive.readonly', 'Drive tool uses readonly scope')
require_contains(drive_client, 'GoogleAuthUtil.getToken', 'Drive tool fetches real Google access token')
require_contains(drive_client, 'https://www.googleapis.com/drive/v3/files', 'Drive tool calls Drive files REST endpoint')
require_contains(functions_index, "model: 'gpt-5.5'", 'gateway uses GPT-5.5')
require_contains(functions_index, "type: 'web_search'", 'gateway enables hosted web search')
require_contains(proxy_script, 'Connection", "close', 'Cartesia proxy closes streams')
require_contains(proxy_script, 'traceback.print_exc()', 'Cartesia proxy prints tracebacks')
require_contains(main_activity, 'cartesia_pcm_write receivedBytes=', 'Cartesia playback logs byte counts')
require_contains(main_activity, 'AudioTrack.WRITE_BLOCKING', 'Cartesia playback uses blocking writes')
require_contains(build_gradle, 'gemini-2.0-flash', 'Gradle default Gemini model matches orientation')
require_contains(main_activity, 'BuildConfig.GEMINI_MODEL', 'Android runtime uses configured Gemini model')
require_contains(manifest, 'networkSecurityConfig="@xml/network_security_config"', 'manifest keeps local network config')

if re.search(r'contains\("drive"\)|contains\("first sentence"\)|contains\("summarize"\)', submit):
    fail('submitMessage still contains English intent checks')

if failures:
    print('Home Center regression tests failed:', file=sys.stderr)
    for item in failures:
        print(f'- {item}', file=sys.stderr)
    sys.exit(1)

print('Home Center tool-host regression tests: OK')
