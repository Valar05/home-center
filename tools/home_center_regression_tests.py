#!/data/data/com.termux/files/usr/bin/python3
from pathlib import Path
import json
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

def registry_tools(source):
    return set(re.findall(r'new ToolDefinition\("([^"]+)"', source))

def dispatched_tools(source):
    return set(re.findall(r'"([a-z]+\.[a-z_]+)"\.equals\(toolName\)', source))

main_activity = read('app/src/main/java/com/dclar/homecenter/MainActivity.java')
openai_client = read('app/src/main/java/com/dclar/homecenter/OpenAiAgentClient.java')
drive_client = read('app/src/main/java/com/dclar/homecenter/GoogleDriveClient.java')
sheets_client = read('app/src/main/java/com/dclar/homecenter/GoogleSheetsClient.java')
gmail_client = read('app/src/main/java/com/dclar/homecenter/GoogleGmailClient.java')
calendar_client = read('app/src/main/java/com/dclar/homecenter/GoogleCalendarClient.java')
tool_registry = read('app/src/main/java/com/dclar/homecenter/ToolRegistry.java')
functions_index = read('functions/index.js')
build_gradle = read('app/build.gradle')
contract = json.loads(read('tools/home_center_tool_contract.json'))
contract_tools = {tool['name']: tool for tool in contract['tools']}
contract_names = set(contract_tools)

submit = method_body(main_activity, 'private void submitMessage', 'private boolean ensureGoogleToolScopesForTurn')
require_contains(submit, 'sendAgentTurn(clean);', 'typed chat enters GPT-5.5 first')
require_absent(submit, 'tryHandleLocalStatusQuestion', 'typed chat must not run local status parser before GPT')
require_absent(submit, 'tryHandleLocalCommand', 'typed chat must not run local command parser before GPT')
require_absent(main_activity, 'private boolean isDriveDiagnosticIntent', 'Drive keyword router removed')
require_absent(main_activity, 'CommandParser.parse(text)', 'typed chat no longer parses English commands locally')

registered = registry_tools(tool_registry)
if registered != contract_names:
    fail(f'tool registry mismatch contract: missing={sorted(contract_names - registered)} extra={sorted(registered - contract_names)}')

for group in contract['requiredGroups']:
    ops = {tool['operation'] for tool in contract_tools.values() if tool['group'] == group}
    for required_op in {'read', 'create', 'update'}:
        if required_op not in ops:
            fail(f'{group} contract lacks {required_op} operation')

source_by_dispatcher = {
    'GoogleDriveClient': drive_client,
    'GoogleSheetsClient': sheets_client,
    'GoogleGmailClient': gmail_client,
    'GoogleCalendarClient': calendar_client,
    'MainActivity': main_activity,
}
for name, tool in sorted(contract_tools.items()):
    source = source_by_dispatcher.get(tool['dispatcher'])
    if source is None:
        fail(f'{name} names unknown dispatcher {tool["dispatcher"]}')
        continue
    require_contains(source, f'"{name}".equals(toolName)', f'{name} has dispatcher')
    if tool['write'] and not tool['confirmationRequired'] and name.startswith(('drive.', 'docs.', 'sheets.', 'calendar.')):
        fail(f'{name} is an external Google write without confirmation')
    for scope in tool['scopes']:
        require_contains(tool_registry, scope, f'{name} scope appears in registry')

for source_name, source in source_by_dispatcher.items():
    for tool in dispatched_tools(source):
        if tool not in contract_names:
            fail(f'{source_name} dispatches uncontracted tool {tool}')

for source_name, source in {'ToolRegistry': tool_registry, 'GoogleDriveClient': drive_client, 'GoogleSheetsClient': sheets_client}.items():
    require_absent(source, 'drive.readonly', f'{source_name} must not use readonly Drive scope for the write-capable host')

for forbidden in ['drive.delete', 'docs.delete', 'sheets.delete', 'gmail.delete', 'calendar.delete', 'lists.delete']:
    require_absent(tool_registry, forbidden, f'{forbidden} must not be registered')
    require_absent(functions_index, forbidden, f'{forbidden} must not be described by gateway')

require_contains(tool_registry, 'SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"', 'Sheets scope exists')
require_contains(tool_registry, 'new Scope(SHEETS_SCOPE)', 'Google sign-in scope list includes Sheets')
require_contains(main_activity, 'for (Scope scope : ToolRegistry.signInScopes())', 'Google sign-in requests registry scopes')
require_contains(main_activity, 'ToolRegistry.availableTools(account, hasSignedInHomeUser())', 'MainActivity advertises runtime registry tools')
require_contains(main_activity, 'ToolRegistry.unavailableToolGroups(account, hasSignedInHomeUser())', 'MainActivity reports missing scope groups')
require_contains(main_activity, '"drive".equals(definition.group) || "docs".equals(definition.group)', 'Docs dispatches through Drive/Docs REST client')
require_contains(main_activity, '"sheets".equals(definition.group)', 'Sheets dispatcher exists')
require_contains(main_activity, 'GoogleSheetsClient googleSheetsClient', 'MainActivity owns Sheets client')
require_contains(main_activity, 'tool.startsWith("docs.")', 'Docs auth failures trigger reconnect')
require_contains(main_activity, 'tool.startsWith("sheets.")', 'Sheets auth failures trigger reconnect')
require_contains(main_activity, 'Drive, Docs, Sheets, Gmail, and Calendar tools', 'reconnect copy names full Google contract')
require_contains(main_activity, 'definition.confirmationRequired', 'Android refuses unconfirmed dangerous tools')
require_contains(main_activity, 'arguments.optBoolean("_confirmedByGateway", false)', 'Android requires gateway confirmation marker')

require_contains(openai_client, 'body.put("tools", tools == null ? new JSONArray() : tools)', 'OpenAI client sends registry-provided tools')
require_contains(openai_client, 'body.put("unavailableToolGroups"', 'OpenAI client sends unavailable capability groups')
require_contains(openai_client, 'google:drive_docs_sheets_gmail_calendar', 'legacy capability text includes full Google contract')
require_absent(openai_client, 'google:drive_docs_gmail_calendar', 'legacy capability text must not omit Sheets')
require_absent(openai_client, '.put("name", "drive.search")', 'OpenAI client must not hardcode advertised tools')

require_contains(functions_index, 'Available tools JSON', 'agentToolTurn prompt is registry-driven')
require_contains(functions_index, 'Unavailable tool groups JSON', 'agentToolTurn sees missing scopes')
require_contains(functions_index, 'toolByName(tools, toolName)', 'gateway rejects unadvertised tool calls')
require_contains(functions_index, 'tool.confirmationRequired && !messageConfirms(message)', 'gateway enforces confirmation outside prompt prose')
require_contains(functions_index, 'args._confirmedByGateway = true', 'gateway marks confirmed dangerous tool calls')
require_contains(functions_index, 'Say "confirm ${action}" or press Confirm.', 'confirmation copy uses short confirm phrase')
require_contains(functions_index, 'pendingConfirmation: pendingConfirmation(toolName, args)', 'gateway returns hidden pending confirmation payload')
require_contains(functions_index, 'pendingConfirmationFromBody(body, tools)', 'gateway resumes pending confirmation from Android payload')
require_contains(functions_index, "toolContractVersion: 'google-cru-v1'", 'gateway health exposes contract version')
for group in contract['requiredGroups']:
    require_contains(functions_index, f"'{group}'", f'gateway health exposes {group} group')
agent_turn = method_body(functions_index, 'exports.agentTurn', 'async function synthesizeCartesia')
require_absent(agent_turn, 'wantsConfirmedCreateDoc', 'legacy agentTurn create-doc route is bypassed')

require_contains(drive_client, '"google_doc_created"', 'Docs create returns google_doc_created status')
require_contains(drive_client, '"drive_folder_created"', 'Drive create folder returns drive_folder_created status')
require_contains(drive_client, '"drive_metadata_updated"', 'Drive metadata update returns drive_metadata_updated status')
require_contains(sheets_client, 'SHEETS_URL = "https://sheets.googleapis.com/v4/spreadsheets"', 'Sheets client calls Sheets REST')
require_contains(sheets_client, '"google_sheet_created"', 'Sheets create returns google_sheet_created status')
require_contains(sheets_client, '"google_sheet_updated"', 'Sheets update returns google_sheet_updated status')
require_contains(gmail_client, 'BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me"', 'Gmail client calls Gmail REST')
require_contains(calendar_client, 'BASE_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"', 'Calendar client calls Calendar REST')
require_contains(calendar_client, '"calendar.read".equals(toolName)', 'Calendar read dispatcher exists')
require_contains(main_activity, 'homeTaskClient.updateTaskByIdOrName', 'List tools can update status/text by id or item text')
require_contains(build_gradle, 'versionCode', 'Android build declares versionCode')

build_ui = method_body(main_activity, 'private void buildUi', '    private void initializePortableCommandFields')
require_absent(build_ui, 'title.setText("Home Center")', 'default chat view must not duplicate app title')
require_absent(build_ui, 'talkButton.setText("Mic")', 'default chat view must not show dedicated Mic button')
require_absent(build_ui, 'bottomPanel.addView(talkButton)', 'default chat composer must not stack a Mic panel')
require_contains(build_ui, 'messageEdit.setHint("Ask Home Center...")', 'composer prompt is primary input')
require_contains(build_ui, 'root.addView(chatScroll)', 'chat view contains message list')
require_contains(build_ui, 'root.addView(bottomPanel, matchWrap())', 'composer is pinned after weighted chat list')
require_contains(build_ui, 'stopSpeechButton.setVisibility(View.GONE)', 'Stop button is hidden until speech plays')
require_contains(main_activity, 'private void setSpeechPlaying(boolean playing)', 'speech playback controls Stop visibility')
require_contains(main_activity, 'setSpeechPlaying(true);', 'Cartesia playback reveals Stop button')
require_contains(main_activity, 'setSpeechPlaying(false);', 'speech completion hides Stop button')
require_absent(main_activity, 'appendDashboardCard();', 'startup must not insert dashboard card into chat')
for color in ['#121212', '#1E1E1E', '#2A2A2A', '#6AA9FF', '#8BC34A', '#FFFFFF', '#B8B8B8', '#C75B5B']:
    require_contains(main_activity, color, f'dark chat palette includes {color}')
require_absent(main_activity, 'Home Center sync: signed in as', 'default status must not expose account prose')
require_absent(main_activity, 'Type or use Talk', 'default status must not reference removed Talk workflow')
require_contains(main_activity, 'statusView.setText(gptState + " | " + speechState + " | " + model)', 'provider status is compact')
require_contains(main_activity, 'wireMessageBubbleInteractions(bubble, text)', 'chat bubbles wire copy and replay interactions')
require_contains(main_activity, 'bubble.setOnLongClickListener', 'message long press copies text')
require_contains(main_activity, 'ClipData.newPlainText("Home Center message", clean)', 'message copy uses clipboard plain text')
require_contains(main_activity, 'clipboard.setPrimaryClip', 'message copy writes clipboard')
require_contains(main_activity, 'ViewConfiguration.getDoubleTapTimeout()', 'message replay uses double-tap timing')
require_contains(main_activity, 'replayMessageText(text)', 'double tap replays message text')
require_contains(main_activity, 'speak(clean)', 'message replay uses narration path')
require_contains(main_activity, 'Long press to copy. Double tap to replay.', 'message interaction is exposed to accessibility')

if failures:
    print('Home Center regression tests failed:', file=sys.stderr)
    for item in failures:
        print(f'- {item}', file=sys.stderr)
    sys.exit(1)

print('Home Center tool contract regression tests: OK')
