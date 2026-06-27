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
contacts_client = read('app/src/main/java/com/dclar/homecenter/GoogleContactsClient.java')
tool_registry = read('app/src/main/java/com/dclar/homecenter/ToolRegistry.java')
functions_index = read('functions/index.js')
build_gradle = read('app/build.gradle')
provider_smoke = read('tools/home_center_provider_smoke.py')
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
    required_ops = {'read'} if group == 'contacts' else {'read', 'create', 'update'}
    for required_op in required_ops:
        if required_op not in ops:
            fail(f'{group} contract lacks {required_op} operation')

source_by_dispatcher = {
    'GoogleDriveClient': drive_client,
    'GoogleSheetsClient': sheets_client,
    'GoogleGmailClient': gmail_client,
    'GoogleCalendarClient': calendar_client,
    'GoogleContactsClient': contacts_client,
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

for forbidden in ['drive.delete', 'docs.delete', 'sheets.delete', 'gmail.delete', 'calendar.delete', 'contacts.delete', 'lists.delete']:
    require_absent(tool_registry, forbidden, f'{forbidden} must not be registered')
    require_absent(functions_index, forbidden, f'{forbidden} must not be described by gateway')

require_contains(tool_registry, 'SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"', 'Sheets scope exists')
require_contains(tool_registry, 'new Scope(SHEETS_SCOPE)', 'Google sign-in scope list includes Sheets')
require_contains(main_activity, 'for (Scope scope : ToolRegistry.signInScopes())', 'Google sign-in requests registry scopes')
require_contains(main_activity, 'ToolRegistry.availableTools(account, hasSignedInHomeUser())', 'MainActivity advertises runtime registry tools')
require_contains(main_activity, 'LocalLog.info("agent_trace", "android_received_tool=" + turn.toolName)', 'Android logs received tool name')
require_contains(main_activity, 'android_dispatch_result tool=', 'Android logs dispatcher result')
require_contains(main_activity, 'documentId=', 'Android trace includes documentId')
require_contains(openai_client, 'body.put("debugTrace", true)', 'Android requests gateway trace details')
require_contains(openai_client, 'body.put("workingMemory", workingMemory == null ? new JSONObject() : workingMemory)', 'Android sends working memory to gateway')
require_contains(openai_client, 'body.put("timeContext", timeContext == null ? new JSONObject() : timeContext)', 'Android sends device time context to gateway')
require_contains(main_activity, 'currentTimeContext()', 'Android builds current time context for agent turns')
require_contains(main_activity, 'json.put("nowEpochMillis", nowMillis)', 'time context includes epoch millis')
require_contains(main_activity, 'json.put("nowIso", iso.format(new Date(nowMillis)))', 'time context includes local ISO timestamp')
require_contains(main_activity, 'json.put("timeZoneId", zone.getID())', 'time context includes timezone id')
require_contains(main_activity, 'json.put("timeZoneOffsetMillis", zone.getOffset(nowMillis))', 'time context includes timezone offset')
require_contains(main_activity, 'private final JSONObject workingMemory = new JSONObject()', 'Android has session working memory')
require_contains(main_activity, 'workingMemorySnapshot()', 'Android snapshots working memory for agent turns')
require_contains(main_activity, 'updateWorkingMemoryFromToolResult(turn.toolName, turn.arguments, result)', 'Android updates working memory after tool results')
require_contains(main_activity, 'rememberEntity("lastDocument", toolName', 'Android stores lastDocument')
require_contains(main_activity, 'rememberEntity("lastFolder", toolName', 'Android stores lastFolder')
require_contains(main_activity, 'rememberEntity("lastSheet", toolName', 'Android stores lastSheet')
require_contains(main_activity, 'workingMemory.put("lastEmailDraft", draft)', 'Android stores lastEmailDraft')
require_contains(main_activity, 'workingMemory.put("lastCalendarEvent", memory)', 'Android stores lastCalendarEvent')
require_contains(main_activity, 'workingMemory.put("lastContact", memory)', 'Android stores lastContact')
require_contains(main_activity, 'if ("contacts.search".equals(toolName))', 'Android updates working memory from contacts.search')
require_contains(main_activity, 'rememberContact(toolName, result.optJSONObject("contact"))', 'Android updates working memory from contacts.read')
require_contains(drive_client, '"google_doc_created"', 'working memory test path includes docs.create success status')
require_contains(main_activity, 'ToolRegistry.unavailableToolGroups(account, hasSignedInHomeUser())', 'MainActivity reports missing scope groups')
require_contains(main_activity, '"drive".equals(definition.group) || "docs".equals(definition.group)', 'Docs dispatches through Drive/Docs REST client')
require_contains(main_activity, '"sheets".equals(definition.group)', 'Sheets dispatcher exists')
require_contains(main_activity, 'GoogleSheetsClient googleSheetsClient', 'MainActivity owns Sheets client')
require_contains(main_activity, 'tool.startsWith("docs.")', 'Docs auth failures trigger reconnect')
require_contains(main_activity, 'tool.startsWith("sheets.")', 'Sheets auth failures trigger reconnect')
require_contains(main_activity, 'tool.startsWith("contacts.")', 'Contacts auth failures trigger reconnect')
require_contains(main_activity, 'Drive, Docs, Sheets, Gmail, Calendar, and Contacts tools', 'reconnect copy names full Google contract')
require_contains(main_activity, 'definition.confirmationRequired', 'Android refuses unconfirmed dangerous tools')
require_contains(main_activity, 'arguments.optBoolean("_confirmedByGateway", false)', 'Android requires gateway confirmation marker')

require_contains(openai_client, 'body.put("tools", tools == null ? new JSONArray() : tools)', 'OpenAI client sends registry-provided tools')
require_contains(openai_client, 'body.put("unavailableToolGroups"', 'OpenAI client sends unavailable capability groups')
require_contains(openai_client, 'google:drive_docs_sheets_gmail_calendar_contacts', 'legacy capability text includes full Google contract')
require_absent(openai_client, 'google:drive_docs_gmail_calendar', 'legacy capability text must not omit Sheets')
require_absent(openai_client, 'google:drive_docs_sheets_gmail_calendar"', 'legacy capability text must not omit Contacts')
require_absent(openai_client, '.put("name", "drive.search")', 'OpenAI client must not hardcode advertised tools')

require_contains(functions_index, 'Available tools JSON', 'agentToolTurn prompt is registry-driven')
require_contains(functions_index, 'OpenAI web_search for public web pages, including public GitHub repositories', 'planner prompt routes public GitHub through web search')
require_contains(functions_index, 'Do not claim a GitHub tool is required for public GitHub repositories', 'planner prompt forbids false missing-GitHub-tool refusal')
require_contains(functions_index, 'private repo access, authenticated GitHub writes, issues, pull requests, or repository mutations', 'planner prompt limits GitHub-tool requirement to authenticated operations')
require_contains(functions_index, 'Google Docs rule: for a request to create a Google Doc, call docs.create', 'planner prompt forces Google Doc creation to docs.create')
require_contains(functions_index, 'Contacts rule: if the user names a person from contacts, call contacts.search', 'planner prompt searches contacts by name')
require_contains(functions_index, 'Do not ask for an email address while contacts.search is available', 'planner prompt forbids false missing-contacts refusal')
require_contains(functions_index, 'Contacts plus Calendar rule: to add a named contact to an event', 'planner prompt chains contacts into calendar attendee updates')
require_contains(functions_index, 'Calendar display rule: in confirmations and final replies, use the event title/summary', 'planner prompt forbids calendar event ID display')
require_contains(functions_index, "Edit calendar event ${quoteForConfirmation(a.title || a.name || 'selected event')}", 'calendar update confirmation uses human event title')
require_absent(functions_index, 'Edit calendar event ${quoteForConfirmation(a.eventId)}', 'calendar update confirmation must not show eventId')
require_contains(functions_index, 'Working memory JSON contains recently created or selected entities', 'planner prompt explains working memory')
require_contains(functions_index, 'resolve the reference from workingMemory or recent tool results', 'planner prompt requires reference resolution')
require_contains(functions_index, 'Never use phrases like that document', 'planner prompt forbids literal reference names')
require_contains(functions_index, 'Working memory JSON: ${JSON.stringify(workingMemory)', 'gateway sends working memory in prompt')
require_contains(functions_index, 'Time context JSON: ${JSON.stringify(timeContext)', 'gateway sends time context in prompt')
require_contains(functions_index, 'Calendar time rule: timeContext is the device clock', 'planner prompt has calendar clock contract')
require_contains(functions_index, 'do not ask for an exact time when the user already gave a relative time', 'planner prompt forbids relative-time punt')
require_contains(functions_index, 'resolveCalendarRelativeTimesFromContext(body, toolName, args)', 'gateway normalizes relative calendar times before dispatch')
require_contains(functions_index, 'function relativeOffsetMillis(value)', 'gateway has deterministic relative offset parser')
require_contains(functions_index, 'five minutes from now', 'calendar relative-time contract covers exact failing phrase')
require_contains(functions_index, '15 * 60000', 'calendar notification default duration is deterministic')
require_contains(functions_index, '30 * 60000', 'calendar ordinary event default duration is deterministic')
require_contains(functions_index, 'UNRESOLVED_REFERENCE_LITERALS', 'gateway has unresolved reference literal guard')
require_contains(functions_index, "'that document'", 'reference guard covers that document')
require_contains(functions_index, "'the thing we just made'", 'reference guard covers thing we just made')
require_contains(functions_index, "status: 'reference_unresolved'", 'gateway asks clarification instead of executing unresolved literal')
require_contains(functions_index, 'resolveToolArgsFromWorkingMemory(body, toolName, args)', 'gateway normalizes planner args from working memory before confirmation or dispatch')
require_contains(functions_index, 'function shouldFillResolvedValue(value)', 'gateway can replace literal reference values')
require_contains(functions_index, 'args.documentId = memory.lastDocument.fileId', 'remembered documents provide documentId alias')
require_contains(functions_index, "toolName === 'drive.update_metadata') args.addParentId = memory.lastFolder.fileId", 'remembered folders resolve move destination parent')
require_contains(functions_index, 'When resolving a remembered document, include both fileId and name', 'planner prompt requires confirmation-friendly resolved document args')
require_contains(functions_index, 'if (hasCompatibleMemory) return null;', 'compatible memory prevents false missing-reference clarification')
require_contains(functions_index, 'memory.lastContact && memory.lastContact.primaryEmail', 'gateway can resolve remembered contacts')
reference_flow_contracts = [
    {
        'input': 'Create a Google Doc called HomeCenter',
        'source_expectations': [
            'rememberEntity("lastDocument", toolName',
            '"google_doc_created"',
            'docsCreateWasRequested',
        ],
    },
    {
        'input': 'Replace the body of that document with Brain dump.',
        'source_expectations': [
            "'that document'",
            'resolveToolArgsFromWorkingMemory(body, toolName, args)',
            'args.documentId = memory.lastDocument.fileId',
        ],
    },
    {
        'input': 'Append "Second paragraph" to it.',
        'source_expectations': [
            "'it'",
            'rememberSingleFileResult("lastDocument", toolName, result.optJSONArray("files"))',
            'resolveToolArgsFromWorkingMemory(body, toolName, args)',
        ],
    },
    {
        'input': 'Update that document.',
        'source_expectations': [
            'Which item do you mean?',
            "status: 'reference_unresolved'",
        ],
    },
    {
        'input': 'Move HomeCenter into that folder.',
        'source_expectations': [
            'rememberEntity("lastFolder", toolName',
            "toolName === 'drive.update_metadata') args.addParentId = memory.lastFolder.fileId",
        ],
    },
    {
        'input': 'Create a calendar event called home center notification five minutes from now.',
        'source_expectations': [
            'Time context JSON: ${JSON.stringify(timeContext)',
            'Calendar time rule: timeContext is the device clock',
            'resolveCalendarRelativeTimesFromContext(body, toolName, args)',
            'relativeOffsetMillis(args.startTime)',
            'formatIsoWithOffset(startMs, context.timeZoneOffsetMillis)',
        ],
    },
    {
        'input': 'Add June Wren Clarke from my contacts to the event.',
        'source_expectations': [
            'contacts.search',
            'Contacts plus Calendar rule: to add a named contact to an event',
            'attendeesToAdd',
            'workingMemory.put("lastContact", memory)',
        ],
    },
]
for case in reference_flow_contracts:
    if not case['input']:
        fail('working-memory flow test is missing exact user input')
    for expected in case['source_expectations']:
        if expected not in functions_index and expected not in main_activity and expected not in drive_client:
            fail(f"working-memory flow '{case['input']}' is missing source expectation {expected}")
require_contains(functions_index, 'buildToolTrace(body, tools, parsed, toolName, tool, true)', 'gateway traces confirmation-required tool calls')
require_contains(functions_index, 'docsCreateAdvertised', 'gateway trace records docs.create advertisement')
require_contains(functions_index, 'docsCreateWasRequested', 'gateway trace records docs.create request')
require_contains(functions_index, 'parsedPlannerJson', 'gateway trace records parsed planner JSON')
require_contains(functions_index, 'Unavailable tool groups JSON', 'agentToolTurn sees missing scopes')
require_contains(functions_index, 'Set narration to the same text as reply', 'gateway prompt forbids mismatched TTS narration')
require_contains(functions_index, 'narration: safeText(parsed.reply || parsed.text, 12000)', 'gateway returns reply text as narration for installed APK compatibility')
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
require_contains(drive_client, 'google_docs_api_start tool=docs.create', 'Docs create logs API start')
require_contains(drive_client, 'google_docs_api_success tool=docs.create documentId=', 'Docs create logs API success with documentId')
require_contains(drive_client, '"drive_folder_created"', 'Drive create folder returns drive_folder_created status')
require_contains(drive_client, '"drive_metadata_updated"', 'Drive metadata update returns drive_metadata_updated status')
require_contains(sheets_client, 'SHEETS_URL = "https://sheets.googleapis.com/v4/spreadsheets"', 'Sheets client calls Sheets REST')
require_contains(sheets_client, '"google_sheet_created"', 'Sheets create returns google_sheet_created status')
require_contains(sheets_client, '"google_sheet_updated"', 'Sheets update returns google_sheet_updated status')
require_contains(gmail_client, 'BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me"', 'Gmail client calls Gmail REST')
require_contains(contacts_client, 'SEARCH_URL = "https://people.googleapis.com/v1/people:searchContacts"', 'Contacts client calls People API search')
require_contains(contacts_client, '"contacts.search".equals(toolName)', 'Contacts search dispatcher exists')
require_contains(contacts_client, 'primaryEmail', 'Contacts client returns primaryEmail for calendar attendees')
require_contains(calendar_client, 'BASE_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"', 'Calendar client calls Calendar REST')
require_contains(calendar_client, '"calendar.read".equals(toolName)', 'Calendar read dispatcher exists')
require_contains(calendar_client, 'eventResult("calendar.update_event", updated, eventId)', 'Calendar update result includes human title')
require_contains(calendar_client, '.put("eventTitle"', 'Calendar event results expose eventTitle')
for service in ['drive.googleapis.com', 'docs.googleapis.com', 'sheets.googleapis.com', 'gmail.googleapis.com', 'calendar-json.googleapis.com', 'people.googleapis.com']:
    require_contains(provider_smoke, service, f'provider smoke verifies {service} is enabled')
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
require_contains(main_activity, 'speak(displayedResponse)', 'Cartesia reads the exact displayed assistant response')
require_absent(main_activity, 'speak(narration == null || narration.trim().isEmpty() ? finalResponse : narration.trim())', 'Cartesia must not read mismatched short narration')
require_contains(main_activity, 'Long press to copy. Double tap to replay.', 'message interaction is exposed to accessibility')

if failures:
    print('Home Center regression tests failed:', file=sys.stderr)
    for item in failures:
        print(f'- {item}', file=sys.stderr)
    sys.exit(1)

print('Home Center tool contract regression tests: OK')
