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

def registry_tools(source):
    return set(re.findall(r'new ToolDefinition\("([^"]+)"', source))

def advertised_from_tests(source):
    return set(re.findall(r'"([a-z]+\.[a-z_]+)"', source))

main_activity = read('app/src/main/java/com/dclar/homecenter/MainActivity.java')
openai_client = read('app/src/main/java/com/dclar/homecenter/OpenAiAgentClient.java')
drive_client = read('app/src/main/java/com/dclar/homecenter/GoogleDriveClient.java')
gmail_client = read('app/src/main/java/com/dclar/homecenter/GoogleGmailClient.java')
calendar_client = read('app/src/main/java/com/dclar/homecenter/GoogleCalendarClient.java')
tool_registry = read('app/src/main/java/com/dclar/homecenter/ToolRegistry.java')
functions_index = read('functions/index.js')
build_gradle = read('app/build.gradle')

submit = method_body(main_activity, 'private void submitMessage', 'private void sendAgentTurn')
require_contains(submit, 'sendAgentTurn(clean);', 'typed chat enters GPT-5.5 first')
require_absent(submit, 'tryHandleLocalStatusQuestion', 'typed chat must not run local status parser before GPT')
require_absent(submit, 'tryHandleLocalCommand', 'typed chat must not run local command parser before GPT')
require_absent(main_activity, 'private boolean isDriveDiagnosticIntent', 'Drive keyword router removed')
require_absent(main_activity, 'CommandParser.parse(text)', 'typed chat no longer parses English commands locally')

registered = registry_tools(tool_registry)
expected = {
    'drive.search', 'drive.read', 'drive.create_doc', 'drive.update_doc',
    'gmail.search', 'gmail.read', 'gmail.create_draft', 'gmail.update_draft', 'gmail.send_draft', 'gmail.send_email',
    'calendar.search', 'calendar.create_event', 'calendar.update_event', 'calendar.respond_event',
    'lists.read', 'lists.create', 'lists.add_item', 'lists.update_item', 'lists.mark_done', 'lists.remove_item',
}
if registered != expected:
    fail(f'tool registry mismatch: missing={sorted(expected - registered)} extra={sorted(registered - expected)}')
for tool in registered:
    if tool.startswith('drive.'):
        require_contains(drive_client, f'"{tool}".equals(toolName)', f'{tool} has Drive dispatcher')
    elif tool.startswith('gmail.'):
        require_contains(gmail_client, f'"{tool}".equals(toolName)', f'{tool} has Gmail dispatcher')
    elif tool.startswith('calendar.'):
        require_contains(calendar_client, f'"{tool}".equals(toolName)', f'{tool} has Calendar dispatcher')
    elif tool.startswith('lists.'):
        require_contains(main_activity, f'"{tool}".equals(toolName)', f'{tool} has list dispatcher')

for source_name, source in {
    'Drive client': drive_client,
    'Gmail client': gmail_client,
    'Calendar client': calendar_client,
    'MainActivity': main_activity,
}.items():
    dispatched = set(re.findall(r'"([a-z]+\.[a-z_]+)"\.equals\(toolName\)', source))
    for tool in dispatched:
        if tool not in registered:
            fail(f'{source_name} dispatches unregistered tool {tool}')

require_contains(openai_client, 'body.put("tools", tools == null ? new JSONArray() : tools)', 'OpenAI client sends registry-provided tools')
require_contains(openai_client, 'body.put("unavailableToolGroups"', 'OpenAI client sends unavailable capability groups')
require_absent(openai_client, '.put("name", "drive.search")', 'OpenAI client must not hardcode advertised tools')
require_contains(main_activity, 'ToolRegistry.availableTools(account, hasSignedInHomeUser())', 'MainActivity advertises runtime registry tools')
require_contains(main_activity, 'ToolRegistry.unavailableToolGroups(account, hasSignedInHomeUser())', 'MainActivity reports missing scope groups')
require_contains(main_activity, 'ToolRegistry.definition(toolName)', 'MainActivity dispatch is registry-gated')
require_contains(main_activity, 'pendingAgentTurnAfterGoogleReconnect = clean == null ? "" : clean.trim()', 'missing Google scopes preserve pending user request')
require_contains(main_activity, 'Google needs one more approval for Drive, Docs, Gmail, and Calendar tools', 'missing Google scopes launch user-facing reconnect')
require_contains(main_activity, 'sendAgentTurn(pending);', 'Google reconnect resumes pending request')
require_contains(main_activity, 'for (Scope scope : ToolRegistry.signInScopes())', 'scope check is registry-driven')

require_contains(main_activity, 'definition.confirmationRequired', 'Android refuses unconfirmed dangerous tools')
require_contains(main_activity, 'arguments.optBoolean("_confirmedByGateway", false)', 'Android requires gateway confirmation marker')
require_contains(openai_client, 'body.put("pendingConfirmation", pendingConfirmation)', 'Android sends pending confirmation payload to gateway')
require_contains(openai_client, 'response.optJSONObject("pendingConfirmation")', 'Android parses pending confirmation payload from gateway')
require_contains(main_activity, 'private volatile JSONObject pendingToolConfirmation', 'Android stores pending confirmation state')
require_contains(main_activity, 'appendPendingConfirmationCard(pendingForUi)', 'Android renders pending confirmation card in chat')
require_contains(main_activity, 'submitMessage("confirm " +', 'Confirm button submits short confirmation text')
require_contains(main_activity, 'cancelPendingToolConfirmation()', 'Confirmation card exposes cancel action')

require_contains(tool_registry, 'DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"', 'Drive uses full Drive scope')
require_contains(tool_registry, 'DOCS_SCOPE = "https://www.googleapis.com/auth/documents"', 'Drive doc writes require Docs scope')
require_contains(tool_registry, 'GMAIL_MODIFY_SCOPE = "https://www.googleapis.com/auth/gmail.modify"', 'Gmail read/search scope exists')
require_contains(tool_registry, 'GMAIL_COMPOSE_SCOPE = "https://www.googleapis.com/auth/gmail.compose"', 'Gmail draft scope exists')
require_contains(tool_registry, 'GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"', 'Gmail send scope exists')
require_contains(tool_registry, 'CALENDAR_EVENTS_SCOPE = "https://www.googleapis.com/auth/calendar.events"', 'Calendar event scope exists')
require_absent(tool_registry, 'drive.readonly', 'Drive write registry must not use readonly scope')
require_absent(drive_client, 'auth/drive.readonly', 'Drive client must not request readonly token for write host')
require_contains(tool_registry, 'Arrays.asList(DRIVE_SCOPE, DOCS_SCOPE)', 'Drive write tools require Drive plus Docs scopes')
require_contains(tool_registry, 'Arrays.asList(GMAIL_COMPOSE_SCOPE)', 'Gmail draft tools require compose scope')
require_contains(tool_registry, 'Arrays.asList(GMAIL_SEND_SCOPE)', 'Gmail send tools require send scope')
require_contains(tool_registry, 'Arrays.asList(CALENDAR_EVENTS_SCOPE)', 'Calendar tools require calendar event scope')
require_contains(main_activity, 'new Scope(ToolRegistry.DRIVE_SCOPE)', 'Google sign-in requests Drive scope')
require_contains(main_activity, 'new Scope(ToolRegistry.GMAIL_SEND_SCOPE)', 'Google sign-in requests Gmail send scope')
require_contains(main_activity, 'new Scope(ToolRegistry.CALENDAR_EVENTS_SCOPE)', 'Google sign-in requests Calendar scope')

for forbidden in ['drive.delete', 'gmail.delete', 'calendar.delete', 'lists.delete']:
    require_absent(tool_registry, forbidden, f'{forbidden} must not be registered')

require_contains(functions_index, 'Available tools JSON', 'agentToolTurn prompt is registry-driven')
require_contains(functions_index, 'Unavailable tool groups JSON', 'agentToolTurn sees missing scopes')
require_absent(functions_index, 'Available Android tools: drive.search', 'gateway must not hardcode Drive-only tools')
require_contains(functions_index, 'toolByName(tools, toolName)', 'gateway rejects unadvertised tool calls')
require_contains(functions_index, 'tool.confirmationRequired && !messageConfirms(message)', 'gateway enforces confirmation outside prompt prose')
require_contains(functions_index, 'args._confirmedByGateway = true', 'gateway marks confirmed dangerous tool calls')
require_contains(functions_index, 'Say "confirm ${action}" or press Confirm.', 'confirmation copy uses short confirm phrase')
require_contains(functions_index, 'pendingConfirmation: pendingConfirmation(toolName, args)', 'gateway returns hidden pending confirmation payload')
require_contains(functions_index, 'pendingConfirmationFromBody(body, tools)', 'gateway resumes pending confirmation from Android payload')
agent_turn = method_body(functions_index, 'exports.agentTurn', 'async function synthesizeCartesia')
require_absent(agent_turn, 'wantsConfirmedCreateDoc', 'legacy agentTurn create-doc route is bypassed')

require_contains(drive_client, '"google_doc_created"', 'Drive create returns google_doc_created status')
require_contains(drive_client, 'webViewLink', 'Drive create/update returns document link')
require_contains(gmail_client, 'BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me"', 'Gmail client calls Gmail REST')
require_contains(calendar_client, 'BASE_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"', 'Calendar client calls Calendar REST')
require_contains(calendar_client, 'attendee_not_found', 'Calendar RSVP has attendee failure mode')
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

if failures:
    print('Home Center regression tests failed:', file=sys.stderr)
    for item in failures:
        print(f'- {item}', file=sys.stderr)
    sys.exit(1)

print('Home Center tool capability regression tests: OK')
