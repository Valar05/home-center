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

def require_order(source, needles, label):
    position = -1
    for needle in needles:
        found = source.find(needle, position + 1)
        if found < 0:
            fail(f"{label}: missing or out of order {needle}")
            return
        position = found

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
cartesia_client = read('app/src/main/java/com/dclar/homecenter/CartesiaSpeechProxyClient.java')
chat_system_shape = read('app/src/main/java/com/dclar/homecenter/ChatSystemShape.java')
drive_client = read('app/src/main/java/com/dclar/homecenter/GoogleDriveClient.java')
sheets_client = read('app/src/main/java/com/dclar/homecenter/GoogleSheetsClient.java')
gmail_client = read('app/src/main/java/com/dclar/homecenter/GoogleGmailClient.java')
calendar_client = read('app/src/main/java/com/dclar/homecenter/GoogleCalendarClient.java')
contacts_client = read('app/src/main/java/com/dclar/homecenter/GoogleContactsClient.java')
knowledge_client = read('app/src/main/java/com/dclar/homecenter/LocalKnowledgeClient.java')
local_log = read('app/src/main/java/com/dclar/homecenter/LocalLog.java')
tool_registry = read('app/src/main/java/com/dclar/homecenter/ToolRegistry.java')
functions_index = read('functions/index.js')
build_gradle = read('app/build.gradle')
provider_smoke = read('tools/home_center_provider_smoke.py')
run_regression = read('tools/run_regression_tests.sh')
metal_prompt_smoke = read('tools/home_center_metal_prompt_smoke.mjs')
creative_prompt_smoke = read('tools/home_center_creative_prompt_smoke.mjs')
turn_contract_smoke = read('tools/home_center_turn_contract_smoke.mjs')
google_tool_setup = read('tools/home_center_google_tool_setup.mjs')
user_path_red_test = read('tools/home_center_user_path_red_test.py')
doctrine = read('docs/HOME_CENTER_DOCTRINE.md')
agent_contract = read('docs/AGENT_CONTRACT.md')
contract = json.loads(read('tools/home_center_tool_contract.json'))
contract_tools = {tool['name']: tool for tool in contract['tools']}
contract_names = set(contract_tools)

submit = method_body(main_activity, 'private void submitMessage', 'private boolean ensureGoogleToolScopesForTurn')
require_contains(submit, 'if (tryHandleLocalCommand(clean))', 'deterministic local commands bypass GPT before agent turn')
require_order(submit, ['recordTranscriptTurn("user", clean);', 'if (tryHandleLocalCommand(clean))', 'sendAgentTurn(clean);'], 'submit records evidence, tries local bypass, then falls through to GPT')
require_absent(submit, 'tryHandleLocalStatusQuestion', 'typed chat must not run local status parser before GPT')
require_absent(main_activity, 'private boolean isDriveDiagnosticIntent', 'Drive keyword router removed')
require_contains(main_activity, 'private boolean tryHandleLocalCommand(String raw)', 'Android has a deterministic local-command bypass')
require_contains(main_activity, 'CommandParser.parse(raw)', 'local bypass uses the existing deterministic command grammar')
require_contains(main_activity, 'private boolean isSafeLocalCommand(Command command, String raw)', 'local bypass has a safety gate for broad parser patterns')
require_contains(main_activity, 'local_command_passthrough action=', 'ambiguous local parser matches fall through to GPT')
require_contains(main_activity, 'case Command.ADD_LIST_ITEM:', 'local bypass handles add-list commands only after safety gating')
require_contains(main_activity, 'return namesList;', 'broad add/read/remove parser matches require list wording before bypass')
require_contains(main_activity, 'local_command_bypass action=', 'local bypass logs OpenAI-free execution')
require_contains(main_activity, 'openaiCalls=0', 'local bypass records zero OpenAI calls')
require_contains(main_activity, 'direct_tool_finish tool=', 'successful write tool results can finish without an extra GPT summary call')
require_contains(main_activity, 'MAX_AGENT_TOOL_STEPS = 3', 'Android economy mode caps GPT-directed tool turns')
require_contains(functions_index, 'function economyToolPalette(message, tools, workingMemory = {}, toolResults = [])', 'gateway filters available tools per request')
require_contains(functions_index, 'const plannerTools = economyToolPalette(message, tools, workingMemory, toolResults)', 'gateway uses per-request planner tool palette')
require_contains(functions_index, 'JSON.stringify(plannerTools).slice(0, 12000)', 'gateway prompt sends filtered planner tools, not the whole registry')
require_contains(functions_index, 'function shouldEnableWebSearch(message, body = {})', 'gateway conditionally enables OpenAI web search')
require_contains(functions_index, 'webSearchEnabled: openAiTools.length > 0', 'gateway logs whether web search was enabled')
require_contains(functions_index, "const reasoningEffort = 'low'", 'normal agentToolTurn uses low reasoning by default')
require_contains(functions_index, 'reasoning: {effort: reasoningEffort}', 'normal agentToolTurn passes the logged low reasoning effort')
require_contains(functions_index, 'max_output_tokens: 700', 'normal agentToolTurn caps output so creative replies do not exceed the installed app transport window')
require_contains(functions_index, 'complete 250 to 400 word slice', 'normal agentToolTurn tells creative replies to finish a smaller complete scene')
require_contains(functions_index, 'input: promptText', 'legacy Firebase askOpenAI uses the assembled prompt text')
require_contains(functions_index, "reasoning: {effort: 'low'}", 'legacy Firebase askOpenAI uses low reasoning')
require_contains(functions_index, 'transcriptChars: transcript.length', 'gateway logs transcript size for cost telemetry')
require_contains(functions_index, 'summaryChars: summary.length', 'gateway logs summary size for cost telemetry')
require_contains(openai_client, 'body.put("reasoning", new JSONObject().put("effort", "low"))', 'Android direct fallback uses low reasoning')
require_contains(openai_client, 'private boolean shouldEnableDirectWebSearch(String message)', 'Android direct fallback gates web search by request')
require_contains(openai_client, 'if (shouldEnableDirectWebSearch(message))', 'Android direct fallback only enables web_search when needed')
require_absent(method_body(functions_index, 'async function askOpenAIToolTurn(body)', 'exports.health'), "tools: [{type: 'web_search'}]", 'agentToolTurn must not always enable OpenAI web_search')
require_absent(local_log, 'MediaStore', 'LocalLog must not block startup with public MediaStore writes')
require_absent(local_log, 'ContentResolver', 'LocalLog must not query content providers on the UI-thread log path')
require_contains(local_log, 'writePrivateFallback(line);', 'LocalLog writes to private app storage only')
require_contains(run_regression, 'node --check tools/home_center_metal_prompt_smoke.mjs', 'metal prompt smoke script is syntax-gated by regression suite')
require_contains(run_regression, 'node --check tools/home_center_google_tool_setup.mjs', 'Google tool setup script is syntax-gated by regression suite')
require_contains(functions_index, 'askOpenAIToolTurn(body)', 'Gateway metal smoke uses the same agentToolTurn planner function')
require_contains(metal_prompt_smoke, 'auth: \'google_access_token_mapped_to_firebase_user\'', 'metal prompt smoke uses Google identity mapped to the Firebase user')
require_contains(metal_prompt_smoke, 'metalPromptSmoke', 'metal prompt smoke calls the deployed server-side metal smoke endpoint')
require_contains(google_tool_setup, 'googleCliAuthExchange', 'Google tool setup posts OAuth code to gateway exchange endpoint')
require_contains(google_tool_setup, 'HOME_CENTER_GOOGLE_SETUP_REDIRECT_URI', 'Google tool setup supports explicit redirect URI')
require_contains(google_tool_setup, '--print-setup', 'Google tool setup can print setup instructions without opening OAuth')
require_contains(google_tool_setup, 'Authorized redirect URI', 'Google tool setup prints exact redirect URI')
require_contains(google_tool_setup, 'https://www.googleapis.com/auth/documents', 'Google tool setup requests Docs scope')
require_contains(google_tool_setup, 'https://www.googleapis.com/auth/drive', 'Google tool setup requests Drive scope')
require_contains(google_tool_setup, 'redirect_uri_mismatch', 'Google tool setup explains redirect mismatch failure')
require_contains(functions_index, 'exports.metalPromptSmoke', 'Gateway exposes server-side metal prompt smoke endpoint')
require_contains(functions_index, 'exports.googleCliAuthExchange', 'Gateway exposes CLI Google tool auth exchange endpoint')
require_contains(functions_index, "const GOOGLE_OAUTH_CLIENT_ID = defineSecret('GOOGLE_OAUTH_CLIENT_ID')", 'Gateway binds Google OAuth client id secret')
require_contains(functions_index, "const GOOGLE_OAUTH_CLIENT_SECRET = defineSecret('GOOGLE_OAUTH_CLIENT_SECRET')", 'Gateway binds Google OAuth client secret')
require_contains(functions_index, 'secrets: [GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET]', 'Google auth exchange has Google OAuth secrets bound')
require_contains(functions_index, 'secrets: [OPENAI_API_KEY, GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET]', 'Metal smoke has OpenAI and Google OAuth secrets bound')
require_contains(functions_index, 'googleEmailTokenRef(email)', 'Gateway stores Google tool credentials by verified email')
require_contains(functions_index, 'storeGoogleToolTokens(uid, email, tokens, \'cli_setup\')', 'Gateway stores CLI setup tokens through shared token helper')
require_contains(functions_index, 'requireSmokeUser(req)', 'Gateway metal smoke accepts Firebase ID tokens or verified Google account tokens')
require_contains(functions_index, 'getUserByEmail(email)', 'Gateway metal smoke maps verified Google identity to the Firebase user')
require_contains(functions_index, 'Home Center Smoke Sandbox', 'Gateway metal smoke uses a Drive sandbox root')
require_contains(functions_index, 'HC_SMOKE_RUN_', 'Gateway metal smoke creates isolated run folders')
require_contains(functions_index, 'confirm create', 'Gateway metal smoke confirms Docs create through the planner loop')
require_contains(functions_index, 'confirm edit', 'Gateway metal smoke confirms Docs edit through the planner loop')
require_contains(functions_index, 'docs.create', 'Gateway metal smoke exercises Docs create')
require_contains(functions_index, 'docs.update', 'Gateway metal smoke exercises Docs update')
require_contains(functions_index, "scenario === 'creative-doc-read-finalizes'", 'Gateway metal smoke covers creative docs.read finalization')
require_contains(functions_index, "['docs-create-update-read', 'creative-doc-read-finalizes'].includes(scenario)", 'Metal smoke endpoint allows creative docs scenario')
require_contains(functions_index, 'runCreativeDocReadFinalizesSmoke(host, evidence, runId)', 'Gateway metal smoke runs the issue 42 creative docs scenario')
require_contains(functions_index, 'Creative docs smoke did not execute docs.read before final prose.', 'Creative metal smoke requires real docs.read before prose')
require_contains(functions_index, "Now it's your turn.  Don't continue the story.  Pick it up at an arbitrary point that I interest you.", 'Creative metal smoke preserves exact issue 42 prompt')
require_contains(metal_prompt_smoke, 'creative-doc-read-finalizes', 'Metal prompt smoke CLI exposes the issue 42 scenario')
require_contains(functions_index, 'sandbox_violation', 'Gateway metal smoke fails on Drive sandbox violations')
require_contains(doctrine, 'Failed Prompts Become Smoke Tests', 'doctrine requires failed prompts to become smoke tests')
require_contains(doctrine, 'headless real-API smoke', 'doctrine requires headless real API prompt validation')
require_contains(agent_contract, 'tools/home_center_metal_prompt_smoke.mjs', 'agent contract documents the metal prompt smoke command')

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

for forbidden in ['gmail.delete', 'calendar.delete', 'contacts.delete', 'lists.delete']:
    require_absent(tool_registry, f'"{forbidden}"', f'{forbidden} must not be registered')
    require_absent(functions_index, f"'{forbidden}'", f'{forbidden} must not be described by gateway')

for delete_tool in ['drive.delete', 'docs.delete', 'sheets.delete', 'gmail.trash', 'calendar.delete_event', 'lists.remove_item']:
    tool = contract_tools.get(delete_tool)
    if not tool:
        fail(f'{delete_tool} missing from tool contract')
        continue
    if not tool.get('confirmationRequired') or not tool.get('doubleConfirmationRequired'):
        fail(f'{delete_tool} must require double confirmation')
    if delete_tool != 'lists.remove_item' and tool.get('operation') != 'delete':
        fail(f'{delete_tool} must use delete operation')

require_contains(tool_registry, 'SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"', 'Sheets scope exists')
require_contains(tool_registry, 'new Scope(SHEETS_SCOPE)', 'Google sign-in scope list includes Sheets')
require_contains(tool_registry, 'github.create_issue', 'GitHub issue creation tool is registered')
require_contains(tool_registry, '"github", true, true', 'GitHub issue creation is a confirmed external write')
require_contains(tool_registry, 'knowledge.read', 'Local knowledge read tool is registered')
require_contains(tool_registry, 'knowledge.append', 'Local knowledge append tool is registered')
require_contains(tool_registry, '"knowledge", true, false', 'Local knowledge append is an unconfirmed local write')
require_contains(main_activity, 'localKnowledgeClient.runTool(toolName, arguments)', 'Android dispatches local knowledge tools')
require_contains(main_activity, 'workingMemory.put("lastKnowledgeFile", memory)', 'Android stores last local knowledge file in working memory')
require_contains(knowledge_client, 'home_center_knowledge', 'Local knowledge files are app-private')
require_contains(knowledge_client, 'seed("SKILLS.md"', 'Local knowledge seeds SKILLS.md')
require_contains(knowledge_client, 'seed("AGENTS.md"', 'Local knowledge seeds AGENTS.md')
require_contains(knowledge_client, 'seed("MEMORY.md"', 'Local knowledge seeds MEMORY.md')
require_contains(knowledge_client, 'sensitive_content_rejected', 'Local knowledge rejects obvious secrets')
require_contains(knowledge_client, 'bodyPreview', 'Local knowledge append returns generic body preview for memory hydration')
require_contains(functions_index, 'Local knowledge rule: use knowledge.append', 'Gateway planner can persist durable workflows and workarounds')
require_contains(functions_index, 'Choose SKILLS.md for repeatable procedures, AGENTS.md for agent steering, and MEMORY.md for durable facts', 'Gateway planner chooses the right local knowledge file')
require_absent(method_body(functions_index, 'async function askOpenAIToolTurn(body)', 'exports.health'), 'memoryAppendToolCall(body, tools, toolResults)', 'normal gateway turns must not pre-route memory writes before GPT judgment')
require_absent(functions_index, 'memoryWriteEnforced: true', 'gateway must not rely on forced memory write routing')
require_contains(tool_registry, 'drive.upload_file', 'Drive upload for attached files is registered')
require_contains(tool_registry, 'Arrays.asList("sessionFileId", "name", "folderId", "mimeType")', 'Drive upload tool uses session file id arguments')
require_contains(main_activity, 'REQUEST_FILE_ATTACH', 'Android has a file attachment picker request')
require_contains(main_activity, 'attachFileButton.setContentDescription("Attach file")', 'Composer has one accessible file intake button')
require_contains(main_activity, 'intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true)', 'File intake supports multiple selected files')
require_contains(main_activity, 'private final JSONArray attachedFiles = new JSONArray()', 'Android stores multiple attached files')
require_contains(main_activity, 'private final JSONArray activeFileIds = new JSONArray()', 'Android tracks active attachment references')
require_absent(main_activity, 'lastFile', 'Android must not use a single lastFile attachment contract')
require_contains(main_activity, 'workingMemory.put("attachedFiles", sanitizedAttachedFilesSnapshot())', 'Android sends sanitized attachments through working memory')
require_contains(main_activity, 'attachmentImagesSnapshot()', 'Android sends image attachments to the agent')
require_contains(openai_client, 'body.put("attachmentImages"', 'OpenAI client sends image attachment payloads')
require_contains(functions_index, "type: 'input_image'", 'Gateway passes image attachments as GPT image inputs')
require_contains(functions_index, 'imagePreviewAvailable is true', 'Gateway prompt treats image analysis as available accessibility context')
require_contains(functions_index, 'drive.upload_file only when the user asks to upload', 'Gateway keeps Drive upload explicit')
require_contains(drive_client, 'multipartUploadFile', 'Drive client can upload attached file bytes')
require_contains(drive_client, 'uploadType", "multipart"', 'Drive upload uses multipart upload')
require_contains(main_activity, 'evidenceContextSnapshot(clean)', 'Android sends evidence context to the planner')
require_contains(main_activity, 'recentConversationEvidence()', 'Android preserves recent conversation evidence')
require_contains(main_activity, 'recentToolTrace', 'Android preserves recent tool trace evidence')
require_contains(main_activity, 'rememberAgentTrace("gateway_request_started"', 'Android records gateway request start trace for reports')
require_contains(main_activity, 'rememberAgentTrace("gateway_response_received"', 'Android records gateway response trace for reports')
require_contains(main_activity, 'rememberAgentTrace("gateway_error"', 'Android records gateway error trace for reports')
require_contains(main_activity, 'openAiAgentClient.createGitHubIssue(idToken, arguments)', 'Android dispatches GitHub issue creation through the gateway')
require_contains(openai_client, 'body.put("evidenceContext"', 'OpenAI client sends Android evidence context')
require_contains(openai_client, 'postJson("githubCreateIssue"', 'OpenAI client can call GitHub issue gateway')
require_contains(functions_index, 'GITHUB_TOKEN', 'Gateway uses server-side GitHub token')
require_contains(functions_index, 'githubCreateIssue', 'Gateway exposes GitHub issue endpoint')
require_contains(functions_index, 'Feedback/report rule:', 'Gateway planner has feedback report rules')
require_contains(functions_index, 'only use github.create_issue when the latest user request explicitly asks', 'Gateway report flow is gated by latest explicit report intent')
require_contains(functions_index, 'function shouldIncludeEvidenceContext(message, body = {}, pending = null, toolResults = [])', 'Gateway planner gates evidence context by need')
require_contains(functions_index, 'includeEvidenceContext ? `Evidence context JSON', 'Gateway planner only sends evidence context when needed')
require_contains(functions_index, 'Create GitHub Issue', 'GitHub issue confirmation title is human-readable')
require_contains(functions_index, 'This will include the last few chat messages and app context.', 'GitHub issue confirmation summarizes evidence capture')
require_contains(functions_index, 'function findBalancedJsonObject(text)', 'Gateway recovers a tool-call JSON object when model adds prose')
require_contains(functions_index, 'looksLikeToolCallJson(text)', 'Gateway detects raw tool-call JSON parse failures')
require_contains(functions_index, 'return plannerParseFailureReply(text, err);', 'Gateway never returns raw malformed tool JSON after parse failure')
require_contains(functions_index, "toolContractVersion: 'google-github-knowledge-delete-cru-v1'", 'Gateway health exposes delete-capable contract version')
require_contains(main_activity, 'googleIdentitySignInClient = GoogleSignIn.getClient(this, identityOptions)', 'Google identity sign-in is separate from tool permissions')
require_contains(main_activity, 'for (Scope scope : ToolRegistry.signInScopes())', 'Full Google permission client requests registry scopes')
require_contains(main_activity, 'GoogleSignIn.requestPermissions(this, REQUEST_GOOGLE_TOOL_PERMISSIONS', 'Full Google tool scopes are requested through the explicit permission flow')
require_contains(main_activity, 'if (!hasAllGoogleToolScopes(account))', 'Android checks full Google tool scope grant before agent turns')
require_contains(main_activity, 'Google connected. Continuing the pending request.', 'Pending request resumes after Google tool permission approval')
require_contains(main_activity, 'requestGoogleToolPermissions(account);', 'Missing tool scopes launch the permission approval flow')
require_contains(main_activity, 'private final Runnable thinkingHapticPulse', 'MainActivity has a thinking haptic pulse')
require_contains(main_activity, 'updateThinkingHaptics(busyState)', 'Busy state drives thinking haptics')
require_contains(main_activity, 'performHapticFeedback(HapticFeedbackConstants.CLOCK_TICK)', 'Thinking haptics use platform haptic feedback')
require_contains(main_activity, 'main.removeCallbacks(thinkingHapticPulse)', 'Thinking haptics stop when busy ends')
require_contains(main_activity, 'workingIndicatorView.setVisibility(active ? View.VISIBLE : View.GONE)', 'Busy state shows a visible working indicator')
require_contains(main_activity, 'submitButton.setText(active ? "Working..." : "Send")', 'Send button visibly changes while working')
require_contains(main_activity, 'messageEdit.setEnabled(!active)', 'Composer input is disabled while Home Center is working')
require_contains(main_activity, 'messageEdit.setHint(active ? "Home Center is working..." : "Ask Home Center...")', 'Composer hint signals working state')
require_contains(main_activity, 'statusView.setText("Working...")', 'Status line signals working state')
require_contains(main_activity, 'new MediaSession(this, "Home Center Narration")', 'Narration registers an Android media session')
require_contains(main_activity, 'PlaybackState.ACTION_STOP | PlaybackState.ACTION_PAUSE', 'Narration media session exposes stop and pause actions')
require_contains(main_activity, 'speechMediaSession.setActive(playing)', 'Narration media session active state follows speech playback')
require_contains(main_activity, 'deviceTextToSpeech.stop();', 'Manual stop also stops device TTS fallback')
require_contains(main_activity, 'throw new IOException("Cartesia audio playback stalled: receivedBytes=" + pcm.length + " writtenBytes=" + writtenBytes)', 'Cartesia zero-write stall triggers fallback instead of silent truncation')
require_contains(main_activity, 'throw new IOException("Cartesia audio playback incomplete: receivedBytes=" + pcm.length + " writtenBytes=" + writtenBytes)', 'Cartesia incomplete PCM write triggers fallback instead of stream_complete')
require_contains(main_activity, 'looksLikeRawToolCallJson(finalResponse)', 'Android blocks raw tool-call JSON from chat and narration')
require_contains(main_activity, 'blocked_raw_tool_call_reply', 'Android logs raw tool-call reply suppression')
require_contains(main_activity, 'KEY_CONVERSATIONS_JSON = "conversations_json"', 'Android has a local conversation collection store')
require_contains(main_activity, 'KEY_ACTIVE_CONVERSATION_ID = "active_conversation_id"', 'Android tracks active conversation id')
require_contains(main_activity, 'private String activeConversationId', 'MainActivity keeps active conversation id')
require_contains(main_activity, 'migrateLegacyConversationIfNeeded(root, prefs)', 'Old single transcript migrates into conversation store')
require_contains(main_activity, 'conversationDrawerButton.setContentDescription("Open conversations")', 'Header has a top-left conversation opener')
require_contains(main_activity, 'conversationDrawerButton.setOnClickListener(v -> showConversationPanel())', 'Conversation opener launches the conversation panel')
require_contains(main_activity, 'private TextView conversationTitleView', 'Header displays the active conversation title')
require_contains(main_activity, 'refreshConversationHeader()', 'Active conversation changes refresh the header title')
conversation_panel = method_body(main_activity, 'private void showConversationPanel(String rawQuery)', 'private void showRenameConversationDialog()')
require_contains(conversation_panel, 'Search conversations or #tag', 'Conversation panel has search by text or tag')
require_contains(conversation_panel, 'button("New conversation"', 'Conversation panel can create a new conversation')
require_contains(conversation_panel, 'button("Rename current"', 'Conversation panel can rename the current conversation')
require_contains(conversation_panel, 'button("Edit tags"', 'Conversation panel can edit conversation tags')
require_contains(conversation_panel, 'switchConversation(id)', 'Conversation panel restores old conversations')
home_menu = method_body(main_activity, 'private void showHomeCenterMenu()', 'private void showHouseholdSettings()')
require_absent(home_menu, 'Search conversations', 'Default settings menu must not own conversation search')
require_absent(home_menu, 'Rename conversation', 'Default settings menu must not own conversation rename')
require_absent(home_menu, 'Edit tags', 'Default settings menu must not own conversation tags')
home_task_client = read('app/src/main/java/com/dclar/homecenter/HomeTaskClient.java')
firestore_rules = read('firebase/firestore.rules')
require_contains(home_task_client, 'list.put("visibility", "household")', 'List auto-bootstrap writes visible household metadata')
require_contains(home_task_client, 'list.put("ownerUid", user.getUid())', 'List auto-bootstrap writes an owner for rule repair')
require_contains(home_task_client, 'list.put("updatedBy", user.getUid())', 'List auto-bootstrap writes updater metadata')
require_contains(home_task_client, 'ensureListForAccess(householdRef, listRef, bucketCode, bucketId, listName, user)', 'List read/write paths bootstrap household membership and list metadata')
require_contains(firestore_rules, 'request.resource.data.visibility == "household"', 'Firestore rules allow member repair into household-visible list')
require_contains(firestore_rules, 'request.resource.data.visibility == "personal" && request.resource.data.ownerUid == request.auth.uid', 'Firestore rules allow member repair into personal-owned list')
require_contains(main_activity, 'query.startsWith("#")', 'Conversation search supports tag syntax')
require_contains(main_activity, 'conversationMatches(conversation, query)', 'Conversation search matches stored conversation content')
require_contains(main_activity, 'conversation.put("turns", chatTurnsJson())', 'Active conversation stores turns')
require_contains(main_activity, 'ToolRegistry.availableTools(account, hasSignedInHomeUser())', 'MainActivity advertises runtime registry tools')
require_contains(main_activity, 'LocalLog.info("agent_trace", "android_received_tool=" + turn.toolName)', 'Android logs received tool name')
require_contains(main_activity, 'android_dispatch_result tool=', 'Android logs dispatcher result')
require_contains(main_activity, 'documentId=', 'Android trace includes documentId')
require_contains(openai_client, 'body.put("debugTrace", true)', 'Android requests gateway trace details')
require_contains(openai_client, 'body.put("workingMemory", workingMemory == null ? new JSONObject() : workingMemory)', 'Android sends working memory to gateway')
require_contains(openai_client, 'body.put("timeContext", timeContext == null ? new JSONObject() : timeContext)', 'Android sends device time context to gateway')
require_contains(openai_client, 'final JSONObject taskStateUpdate;', 'OpenAI client parses task state updates')
require_contains(openai_client, 'response.optJSONObject("taskStateUpdate")', 'OpenAI client reads gateway task state update')
require_contains(main_activity, 'currentTimeContext()', 'Android builds current time context for agent turns')
require_contains(main_activity, 'json.put("nowEpochMillis", nowMillis)', 'time context includes epoch millis')
require_contains(main_activity, 'json.put("nowIso", iso.format(new Date(nowMillis)))', 'time context includes local ISO timestamp')
require_contains(main_activity, 'json.put("timeZoneId", zone.getID())', 'time context includes timezone id')
require_contains(main_activity, 'json.put("timeZoneOffsetMillis", zone.getOffset(nowMillis))', 'time context includes timezone offset')
require_contains(main_activity, 'private final JSONObject workingMemory = new JSONObject()', 'Android has session working memory')
require_contains(main_activity, 'workingMemorySnapshot()', 'Android snapshots working memory for agent turns')
require_absent(main_activity, 'hydrateRememberedWritingContext', 'Android must not hydrate memory from hardcoded transcript sniffing')
require_contains(main_activity, 'workingMemory.put("rememberedWritingContext", context)', 'Android stores generic remembered writing context only from knowledge results')
require_contains(main_activity, 'looksLikeWritingMemory', 'Android gates remembered writing context through generic writing terms')
require_absent(main_activity, 'Lexen', 'Android executable code must not hardcode project-specific writing memory')
require_absent(main_activity, 'Tanks for the Memories', 'Android executable code must not hardcode a personal project name')
require_absent(functions_index, 'Drew', 'Gateway executable code must not hardcode a user name in product copy')
require_absent(functions_index, 'lexen', 'Gateway executable code must not hardcode project-specific writing terms')
require_absent(functions_index, 'normandy', 'Gateway executable code must not hardcode project-specific writing terms')
require_contains(main_activity, 'applyTaskStateUpdate(turn.taskStateUpdate)', 'Android applies gateway task state update each agent step')
require_contains(main_activity, 'workingMemory.put("activeTask", task)', 'Android stores unfinished active task state')
require_contains(main_activity, 'workingMemory.remove("activeTask")', 'Android clears active task only on complete or cancelled')
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

require_contains(openai_client, 'Home Center doctrine: Home Center is a life-operations system', 'direct fallback prompt includes doctrine steering')
require_contains(openai_client, 'The model reasons, the app executes, the storage layer remembers', 'direct fallback prompt includes execution doctrine')
require_contains(openai_client, 'Never imply a capability that is not advertised by the tool registry', 'direct fallback prompt includes capability honesty doctrine')
require_contains(openai_client, 'body.put("tools", tools == null ? new JSONArray() : tools)', 'OpenAI client sends registry-provided tools')
require_contains(openai_client, 'body.put("unavailableToolGroups"', 'OpenAI client sends unavailable capability groups')
require_contains(openai_client, 'google:drive_docs_sheets_gmail_calendar_contacts', 'legacy capability text includes full Google contract')
require_absent(openai_client, 'google:drive_docs_gmail_calendar', 'legacy capability text must not omit Sheets')
require_absent(openai_client, 'google:drive_docs_sheets_gmail_calendar"', 'legacy capability text must not omit Contacts')
require_absent(openai_client, '.put("name", "drive.search")', 'OpenAI client must not hardcode advertised tools')

require_contains(functions_index, 'HOME_CENTER_DOCTRINE_STEERING', 'gateway defines Home Center doctrine steering')
require_contains(functions_index, 'function shouldIncludeFullDoctrine(message, body = {})', 'gateway gates full doctrine steering by request type')
require_contains(functions_index, 'includeFullDoctrine ? HOME_CENTER_DOCTRINE_STEERING', 'gateway does not inject full doctrine into every normal turn')
require_contains(functions_index, 'Doctrine summary: Home Center reasons with GPT', 'gateway has short doctrine fallback for economy mode')
require_contains(functions_index, 'Home Center doctrine: Home Center is a life-operations system', 'gateway prompt includes doctrine steering')
require_contains(functions_index, 'the model reasons, the app executes, the storage layer remembers', 'gateway prompt includes execution doctrine')
require_contains(functions_index, 'Android owns capabilities and permissions; GPT owns judgment', 'gateway prompt keeps app as hands and GPT as planner')
require_contains(functions_index, 'never imply a capability that is not advertised by the tool registry', 'gateway prompt includes capability honesty doctrine')
require_contains(functions_index, 'Available tools JSON', 'agentToolTurn prompt is registry-driven')
require_contains(functions_index, 'OpenAI web_search for public web pages, including public GitHub repositories', 'planner prompt routes public GitHub through web search')
require_contains(functions_index, 'Do not claim a GitHub tool is required for public GitHub repositories', 'planner prompt forbids false missing-GitHub-tool refusal')
require_contains(functions_index, 'Repository orientation rule: if the user names an owner/repo such as Valar05/tanks-for-the-memories', 'planner prompt handles public GitHub owner/repo orientation')
require_contains(functions_index, 'search the exact GitHub URL github.com/owner/repo and raw.githubusercontent.com/owner/repo', 'repository orientation uses exact GitHub/raw URLs before failing')
require_contains(functions_index, 'unrelated same-title web results are not evidence that the target repo is unavailable', 'repository orientation forbids unrelated search-result proof')
require_contains(functions_index, 'Say the lookup timed out, search was inconclusive, or direct URL is needed', 'repository orientation distinguishes timeout/inconclusive lookup from repo-not-found')
require_contains(functions_index, 'Agent error-handling rule: when a task fails, distinguish source of problem', 'planner prompt requires source-specific error handling')
require_contains(functions_index, 'Include a workaround and say when to report/file an issue', 'planner prompt requires workaround and issue-report guidance')
require_contains(functions_index, 'Latest intent rule: the latest user request controls', 'planner prompt prioritizes latest user intent')
require_contains(functions_index, 'Document cleanup rule: if the latest request asks to clean up', 'planner prompt turns document cleanup requests into docs.update work')
require_contains(functions_index, 'Document synthesis/update rule: if the latest request asks to update, rewrite, reflect, merge, copy, append, replace, or revise one Google Doc using content from another Google Doc', 'planner prompt continues doc-to-doc update workflows through docs.update')
require_contains(functions_index, 'Do not stop after saying you found or read the documents.', 'planner prompt forbids stopping after intermediate docs reads')
require_contains(functions_index, 'private repo access, authenticated GitHub writes, issues, pull requests, or repository mutations', 'planner prompt limits GitHub-tool requirement to authenticated operations')
require_contains(functions_index, 'Google Docs rule: for a request to create a Google Doc, call docs.create', 'planner prompt forces Google Doc creation to docs.create')
require_contains(functions_index, 'Contacts rule: if the user names a person from contacts, call contacts.search', 'planner prompt searches contacts by name')
require_contains(functions_index, 'Do not ask for an email address while contacts.search is available', 'planner prompt forbids false missing-contacts refusal')
require_contains(functions_index, 'Contacts plus Calendar rule: to add a named contact to an event', 'planner prompt chains contacts into calendar attendee updates')
require_contains(functions_index, 'Calendar display rule: in confirmations and final replies, use the event title/summary', 'planner prompt forbids calendar event ID display')
require_contains(functions_index, 'Reading recommendation rule: when the user asks for a new audiobook', 'planner prompt answers audiobook recommendation requests from reading-log context')
require_contains(functions_index, "Edit calendar event ${quoteForConfirmation(a.title || a.name || 'selected event')}", 'calendar update confirmation uses human event title')
require_absent(functions_index, 'Edit calendar event ${quoteForConfirmation(a.eventId)}', 'calendar update confirmation must not show eventId')
require_contains(functions_index, 'Working memory JSON contains recently created or selected entities', 'planner prompt explains working memory')
require_contains(functions_index, 'resolve the reference from workingMemory or recent tool results', 'planner prompt requires reference resolution')
require_contains(functions_index, 'Active task rule: workingMemory.activeTask is an unfinished user objective.', 'Gateway receives generalized active task continuation rule')
require_contains(functions_index, 'resume the originalUserRequest/objective immediately', 'Gateway resumes original task after missing detail/source arrives')
require_contains(functions_index, 'A saved source, found folder, read document, or answered clarification is progress, not completion.', 'Gateway treats blocker resolution as progress, not completion')
require_contains(functions_index, 'function activeTaskContinuationRequest(body, toolResults)', 'Gateway has code-level active-task continuation guard')
require_contains(functions_index, "['knowledge.append', 'docs.read', 'docs.search', 'drive.search', 'web.search'].includes(latestTool)", 'Gateway treats successful blocker-resolution tools as continuation triggers')
require_contains(functions_index, 'continuationRequest', 'Gateway turn kernel traces active task continuation state')
require_absent(functions_index, 'Unfinished active task to resume after saving this memory', 'gateway must not use pre-GPT memory append wording as control flow')
require_contains(functions_index, 'Local knowledge rule: use knowledge.append', 'planner receives memory persistence instructions through the tool contract')
require_contains(functions_index, 'Active task continuation override: the latest tool result resolved a blocker.', 'Planner receives explicit active-task continuation override')
require_contains(functions_index, 'taskStateUpdateFromParsed', 'Gateway sanitizes task state updates')
require_contains(functions_index, 'attachTaskState', 'Gateway attaches task state to planner responses')
require_contains(functions_index, '"taskStateUpdate":{"status":"in_progress"', 'Gateway tool-call schema includes task state update')
require_contains(functions_index, '"taskStateUpdate":{"status":"complete"', 'Gateway final schema includes task completion update')
require_contains(functions_index, 'awaiting_detail', 'Gateway task state supports missing detail continuation')
require_contains(functions_index, 'awaiting_source', 'Gateway task state supports missing source continuation')
require_absent(functions_index, 'Lexens first cigarette', 'Gateway continuation fix must not be a Lexen-specific patch')
require_absent(functions_index, 'Tanks for the Memories source was provided', 'Gateway continuation fix must not be a Tanks-specific patch')
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
require_contains(functions_index, 'buildToolTrace(body, plannerTools, parsed, toolName, tool, true)', 'gateway traces confirmation-required tool calls against planner palette')
require_contains(functions_index, 'function compactParsedForTrace(parsed)', 'gateway compacts long final replies before debug trace transport')
require_contains(functions_index, 'parsedPlannerJson: compactParsedForTrace(parsed)', 'gateway debug trace does not return full long creative prose twice')
require_contains(functions_index, 'const FINAL_REPLY_MAX_CHARS = 32000', 'gateway final replies are not capped at the old false-green 12000 chars')
require_contains(functions_index, 'function finalReplyLooksTruncated(reply)', 'gateway detects cut-off final replies')
require_contains(functions_index, 'repairTruncatedFinalReply(body, finalReply, promptText)', 'gateway attempts one repair for cut-off final replies')
require_contains(functions_index, 'truncatedFinalRepaired: true', 'gateway traces repaired truncated finals')
require_contains(functions_index, 'max_output_tokens: repair ? 1200 : 1800', 'evidence finalizer uses an installed-app-safe budget for complete creative scenes without gateway timeout')
require_contains(functions_index, 'hard limit 450 to 700 words', 'evidence finalizer asks for bounded complete creative output instead of unbounded prose')
require_contains(functions_index, 'choose a smaller complete slice', 'evidence finalizer must prefer complete smaller scenes over unfinished long chapters')
require_contains(functions_index, 'Creative completion rule: do not stop mid-scene, mid-exchange, or on an unanswered dialogue line.', 'evidence finalizer is explicitly forbidden from ending mid-scene')
require_contains(functions_index, '/[,;]$/.test(text)', 'truncation detector rejects long prose ending with comma or semicolon')
require_contains(functions_index, '^["“][^"”]{1,180}[?!.]["”]?$', 'truncation detector rejects long prose ending on a bare dialogue line')
require_contains(functions_index, 'docsCreateAdvertised', 'gateway trace records docs.create advertisement')
require_contains(functions_index, 'docsCreateWasRequested', 'gateway trace records docs.create request')
require_contains(functions_index, 'parsedPlannerJson', 'gateway trace records parsed planner JSON')
require_contains(functions_index, 'Unavailable tool groups JSON', 'agentToolTurn sees missing scopes')
require_contains(functions_index, 'Tool limit recovery rule: when Available tools JSON is empty and Tool results JSON is non-empty', 'gateway can recover final answers from accumulated tool results')
require_contains(functions_index, 'function compactToolEvidence(toolResults)', 'gateway compacts accumulated tool results for long recovery tasks')
require_contains(functions_index, "retentionPolicy: 'latest useful evidence plus failures; long docs compacted with headings and truncated marker'", 'tool evidence digest documents retention policy')
require_contains(functions_index, 'const latest = entries.slice(-10).map(compactToolResultForPrompt)', 'tool evidence digest keeps latest results instead of earliest results')
require_contains(functions_index, 'const failures = entries', 'tool evidence digest preserves failures even when older')
require_contains(functions_index, 'compactTextWithHeadings(result.text)', 'docs.read text is compacted before planner prompt transport')
require_contains(functions_index, 'originalCharCount: normalized.length', 'compacted docs preserve original character count')
require_contains(functions_index, 'truncated: normalized.length > maxChars', 'compacted docs mark truncation explicitly')
require_contains(functions_index, 'const includeToolDigest = toolResults.length > 0', 'gateway only sends tool digest when tool results exist')
require_contains(functions_index, 'includeToolDigest ? `Tool evidence digest JSON', 'gateway gates tool evidence digest prompt section')
require_absent(functions_index, 'Tool results JSON retained only for compatibility; use Tool evidence digest first', 'gateway removed compatibility raw tool results prompt section')
require_contains(functions_index, 'function shouldUseEvidenceFinalizer(body, toolResults)', 'gateway has evidence finalizer trigger after successful context reads')
require_contains(functions_index, 'askOpenAIEvidenceFinalizer(body, turnKernel, toolEvidenceDigest)', 'gateway finalizes active tasks from accumulated evidence')
require_contains(functions_index, 'Available tools JSON: []', 'evidence finalizer withholds tools')
require_contains(functions_index, 'Answer the active task from Tool evidence digest', 'evidence finalizer uses compacted tool evidence as source')
require_contains(functions_index, 'evidenceFinalizerApplied: true', 'gateway traces evidence finalizer application')
require_contains(functions_index, 'latestSuccessfulToolResult(toolResults)', 'gateway detects latest successful context tool result')
require_contains(functions_index, "['docs.read', 'knowledge.read', 'web.search'].includes(latestTool)", 'evidence finalizer only triggers after content-bearing evidence')
require_contains(functions_index, 'return isCreativeWritingRequest(message) && !isExplicitNonCreativeToolRequest(message)', 'creative requests finalize after context reads even without activeTask')
require_contains(functions_index, '|| safeText(body && body.message, 4000)', 'evidence finalizer falls back to latest user request as objective')
require_contains(functions_index, 'Holocron/resync recovery rule: when recovering lost conversation, Drive brain, or Holocron context', 'planner prompt handles Holocron resync as recovery task')
require_contains(functions_index, 'do not stop after partial Google Docs reads', 'planner prompt forbids partial-read stopping in Holocron recovery')
require_absent(functions_index, 'body.toolResults.slice(0, 8)', 'gateway must not keep only the first eight tool results')
require_absent(functions_index, 'Tool results JSON: ${JSON.stringify(toolResults).slice(0, 16000)}', 'gateway must not raw-truncate accumulated tool results at 16k')
require_contains(main_activity, 'finishFromToolResultsAfterLimit(idToken, clean, toolResults)', 'Android recovers from tool loop limit through GPT final answer pass')
require_contains(main_activity, 'tool_loop_limit_recovery_start', 'Android logs tool loop recovery start')
require_contains(main_activity, 'MAX_AGENT_TOOL_STEPS = 3', 'Android tool loop is capped for economy mode')
require_absent(main_activity, 'step < 6', 'Android tool loop must not stop after six tool calls')
require_contains(main_activity, 'containsForbiddenToolPlanPhrase(reply)', 'Android blocks forbidden convergence phrase from recovery replies')
require_contains(main_activity, 'synthesizeToolLoopProgressReply(toolResults)', 'Android synthesizes concrete progress report on tool-loop exhaustion')
require_contains(main_activity, 'Succeeded before it:', 'Android tool-loop fallback reports prior successes')
require_contains(main_activity, 'Next action needed:', 'Android tool-loop fallback reports a concrete next action')
require_contains(functions_index, 'sanitizeFinalPlannerReply(body', 'Gateway sanitizes final planner replies before returning them')
require_contains(functions_index, 'containsForbiddenToolPlanPhrase(reply)', 'Gateway detects forbidden convergence phrase in final planner replies')
require_contains(functions_index, 'synthesizeToolLoopProgressReply(Array.isArray(body && body.toolResults)', 'Gateway uses accumulated tool results for progress fallback')
require_contains(functions_index, 'tool_loop_progress_fallback', 'Gateway marks sanitized convergence replies')
require_absent(main_activity, 'finishAgentReply(clean, "I could not finish that request because the tool plan did not converge."', 'Android must not directly show generic convergence failure')
require_contains(functions_index, 'function userFacingFailure(source, detail', 'gateway has structured user-facing failure messages')
require_contains(functions_index, 'errorSource: sourceLabel', 'gateway failure payload includes error source')
require_contains(functions_index, 'errorCategory: category', 'gateway failure payload includes error category')
require_contains(functions_index, 'Workaround:', 'gateway failure copy includes workaround support')
require_contains(functions_index, 'ask me to file a bug', 'gateway failure copy can promote repeated failures to issues without seeding report trigger phrases')
require_contains(functions_index, "userFacingFailure('Home Center gateway', err.message || String(err), 'gateway_error')", 'gateway catch blocks return structured failure copy')
require_absent(functions_index, "reply: `Gateway failed: ${err.message || String(err)}`", 'gateway catch blocks must not return raw failure copy')
require_contains(main_activity, 'agentFailureMessage("Home Center gateway", ex.getMessage())', 'Android gateway exceptions use structured failure copy')
require_contains(main_activity, 'What failed:', 'Android failure copy identifies source detail')
require_contains(main_activity, 'Workaround:', 'Android failure copy includes workaround support')
require_absent(main_activity, 'showAssistantMessage("The agent gateway failed: " + shortMessage(ex.getMessage()))', 'Android must not show vague gateway failure copy')
require_contains(openai_client, 'AGENT_READ_TIMEOUT_MS = 130000', 'Android agent read timeout exceeds 120-second Firebase agent function window')
require_contains(openai_client, 'connection.setReadTimeout(AGENT_READ_TIMEOUT_MS)', 'Android gateway calls use the shared agent read timeout')
require_absent(openai_client, 'connection.setReadTimeout(45000)', 'Android agent client must not timeout before gateway function window')
require_contains(openai_client, 'for (int attempt = 1; attempt <= 2; attempt++)', 'Android gateway client retries one transient transport failure on the real app path')
require_contains(openai_client, 'isTransientGatewayTransportError(ex)', 'Android gateway retry is limited to transient connection abort/reset/end-of-stream failures')
require_contains(openai_client, 'software caused connection abort', 'Android retries the observed installed-app gateway abort')
require_contains(openai_client, 'unexpected end of stream', 'Android retries the observed installed-app end-of-stream failure')
require_absent(chat_system_shape, 'tell me the main ingredient or constraint first.', 'generic next-step fallback must not mention recipe ingredients')
require_absent(chat_system_shape, 'tell me the second constraint or second ingredient.', 'generic next-step fallback must not mention recipe ingredients')
require_absent(chat_system_shape, 'tell me the task, ingredient, or constraint you want to work around.', 'generic help fallback must not mention recipe ingredients')
require_contains(chat_system_shape, 'removeTrailingNextStepBlock(shaped)', 'response shaping strips routine next-step footers')
require_contains(chat_system_shape, 'Do not add a routine Next step or Next steps footer.', 'prompts forbid routine next-step footers')
require_absent(chat_system_shape, 'Always end with a Next step or Next steps block', 'prompts must not require next-step footers')
require_absent(chat_system_shape, 'Always end with Next steps:', 'brainstorm prompt must not require next-step footers')
require_absent(chat_system_shape, 'private static boolean shouldForceNextStep', 'app must not force next-step footers')
require_absent(chat_system_shape, 'private static String suggestedNextSteps', 'app must not synthesize next-step footers')
red_build_tool_loop_contract = {
    'input': "Run a red-build self-test. Read my Home Center Live items list. Add this item to Shipyard. Find June's Holocron. Find my Reading Log. Find Final and Vacation of a Lifetime Story Bible. If anything fails, do not say tool plan did not converge.",
    'source_expectations': [
        'MAX_AGENT_TOOL_STEPS = 3',
        'containsForbiddenToolPlanPhrase(reply)',
        'synthesizeToolLoopProgressReply(toolResults)',
        'Succeeded before it:',
        'Next action needed:',
        'sanitizeFinalPlannerReply(body',
        'tool_loop_progress_fallback',
    ],
}
if not red_build_tool_loop_contract['input']:
    fail('red-build tool-loop contract is missing exact user input')
for expected in red_build_tool_loop_contract['source_expectations']:
    if expected not in functions_index and expected not in main_activity:
        fail(f"red-build tool-loop contract is missing source expectation {expected}")
holocron_resync_contract = {
    'input': 'try to resync with Google drive again after losing Holocron conversation history',
    'source_expectations': [
        'function compactToolEvidence(toolResults)',
        'const latest = entries.slice(-10).map(compactToolResultForPrompt)',
        'includeToolDigest ? `Tool evidence digest JSON',
        'Holocron/resync recovery rule: when recovering lost conversation, Drive brain, or Holocron context',
        'do not stop after partial Google Docs reads',
        'truncated: normalized.length > maxChars',
        'originalCharCount: normalized.length',
    ],
}
if not holocron_resync_contract['input']:
    fail('Holocron resync contract is missing exact user input')
for expected in holocron_resync_contract['source_expectations']:
    if expected not in functions_index:
        fail(f"Holocron resync contract is missing source expectation {expected}")
repo_orientation_error_contract = {
    'input': 'Orient to Valar05/tanks-for-the-memories',
    'source_expectations': [
        'github.com/owner/repo',
        'raw.githubusercontent.com/owner/repo',
        'unrelated same-title web results are not evidence',
        'lookup timed out',
        'search was inconclusive',
        'direct URL is needed',
        'Agent error-handling rule: when a task fails, distinguish source of problem',
        'Include a workaround and say when to report/file an issue',
    ],
}
if not repo_orientation_error_contract['input']:
    fail('repository orientation error contract is missing exact user input')
for expected in repo_orientation_error_contract['source_expectations']:
    if expected not in functions_index:
        fail(f"repository orientation error contract is missing source expectation {expected}")
creative_synthesis_contract = {
    'input': "Generate the next scene",
    'source_expectations': [
        'Creative writing rule: if the latest request asks to write, draft, compose, generate, narrate, expand, create a scene, continue a story, or synthesize prose',
        'produce the prose directly as a final answer from transcript, workingMemory, attachments, and tool evidence',
        'Remembered writing context rule: workingMemory.rememberedWritingContext is durable writing steering restored from prior conversation evidence',
        'Creative context rule: if workingMemory names a remembered canon document or durable knowledge file, use one best available context read before final prose',
        'Creative validation rule: preserve explicit user premises, character roles, POV, vehicle/location relationships, and historical constraints',
        'Do not call docs.search, drive.search, or docs.create unless the latest request explicitly asks to find/read a source document or save/update/create a Google Doc',
        'after a successful docs.create or docs.update, a new request like "write the scene" is a new writing task',
        'not permission to keep searching Drive',
    ],
}
if not creative_synthesis_contract['input']:
    fail('creative synthesis contract is missing exact user input')
for expected in creative_synthesis_contract['source_expectations']:
    if expected not in functions_index:
        fail(f"creative synthesis contract is missing source expectation {expected}")
agent_tool_turn_body = method_body(functions_index, 'async function askOpenAIToolTurn(body)', 'exports.health')
require_contains(functions_index, 'function creativeReplyNeedsRepair(message, reply)', 'gateway detects punted creative writing replies')
require_absent(agent_tool_turn_body, 'askOpenAICreativeRepair(repairBody, finalReply)', 'normal gateway turns must not repair creative replies with local intent regex')
require_contains(functions_index, 'if (/\\b(write|draft|compose|continue|narrate|expand)\\b/.test(text)) return true;', 'gateway treats direct write/draft/compose requests as creative even without scene keyword')
require_contains(functions_index, '\\b(generate|tell|simulate)\\b', 'gateway treats generate/tell/simulate plus scene terms as creative')
require_contains(functions_index, '\\b(scene|story|chapter|prose|draft|passage|moment|dialogue|first contact|d-day)\\b', 'gateway recognizes general creative domain terms without project names')
require_contains(functions_index, 'function creativeContextToolCall(body, tools, toolResults)', 'gateway has creative context acquisition guard')
require_contains(functions_index, 'creativeContextToolCallApplied: true', 'gateway applies creative context acquisition before report-contaminated planner turns')
require_contains(functions_index, "toolName: 'docs.read'", 'creative pipeline reads remembered canon document before prose')
require_contains(functions_index, "name: 'docs.read',\n      confirmationRequired: false", 'turn-contract smoke registry includes docs.read so creative context tests can prove real tool-call routing')
require_contains(functions_index, "toolName: 'knowledge.read'", 'creative pipeline reads remembered durable knowledge before prose')
require_contains(functions_index, 'Do not chain multiple context reads before writing.', 'creative pipeline forbids multi-read stalls before prose')
require_contains(functions_index, 'A remembered document is enough context for this creative turn.', 'creative context acquisition stops after remembered document is already read')
require_absent(agent_tool_turn_body, 'const pureCreativeRequest = isCreativeWritingRequest(plannerMessage) && !isExplicitNonCreativeToolRequest(plannerMessage)', 'normal gateway turns must not pre-route creative requests before GPT judgment')
require_absent(agent_tool_turn_body, 'askOpenAICreativeDraft(creativeBody)', 'normal gateway turns must not use dedicated creative shortcut before GPT judgment')
require_contains(functions_index, 'If workingMemory.rememberedWritingContext exists, treat it as durable writing steering from prior turns.', 'creative draft uses hydrated writing memory directly')
require_contains(functions_index, 'async function askOpenAICreativeDraft(body)', 'creative provider smoke can still test dedicated creative generation')
require_contains(functions_index, 'CREATIVE_OPENAI_TIMEOUT_MS = 85000', 'creative drafting has enough budget for long prose without changing global gateway timeout')
require_contains(functions_index, 'CREATIVE_SALVAGE_TIMEOUT_MS = 25000', 'creative drafting has a bounded salvage attempt under the function timeout')
require_contains(functions_index, "max_output_tokens: salvage ? 1400 : 2600", 'creative drafting caps output to avoid stream stalls')
require_contains(functions_index, "reasoning: {effort: salvage ? 'low' : 'low'}", 'creative drafting avoids slow high-reasoning prose calls')
require_contains(functions_index, 'creativeDraftPrompt(body, \'salvage\'', 'creative drafting retries with a shorter salvage prompt')
require_contains(functions_index, 'creative_salvage_complete', 'creative salvage success has a visible status')
require_contains(functions_index, 'Timed out after ${timeoutMs}ms before producing prose.', 'creative timeout failure is visible and specific')
require_contains(functions_index, 'EVIDENCE_FINALIZER_TIMEOUT_MS = 45000', 'evidence finalizer must abort before the installed app one-minute transport cliff')
require_contains(functions_index, 'EVIDENCE_FINALIZER_REPAIR_TIMEOUT_MS = 12000', 'evidence finalizer repair has a short bounded timeout')
require_contains(functions_index, 'signal: controller.signal', 'evidence finalizer provider uses AbortController instead of hanging the app request')
require_contains(functions_index, 'max_output_tokens: repair ? 1200 : 1800', 'evidence finalizer output is capped for installed-app response time')
require_contains(functions_index, "reasoning: {effort: 'low'}", 'evidence finalizer avoids medium reasoning stalls on installed app path')
require_contains(functions_index, 'hard limit 450 to 700 words', 'creative evidence finalizer produces a complete smaller scene instead of a one-minute chapter')
require_contains(functions_index, 'evidence_finalizer_timeout', 'evidence finalizer timeout is explicit instead of a closed stream')
require_contains(functions_index, 'Creative writing provider failed before producing prose', 'gateway gives descriptive creative provider failure')
require_contains(functions_index, 'attachCreativeTaskComplete', 'creative final or failure completes stale active task state')
require_absent(agent_tool_turn_body, 'creativeDraftFailed: draftFailed', 'normal gateway turns must not use creative draft failure traces')
require_contains(functions_index, 'exports.creativePromptSmoke', 'gateway exposes authenticated creative prompt smoke')
require_contains(functions_index, 'creativePromptSmoke requires prompt', 'gateway creative smoke accepts fixture text from the runner instead of hardcoding project prose')
require_contains(functions_index, 'requestBody.pendingConfirmation = body.pendingConfirmation', 'creative smoke can reproduce stale pending confirmation state')
require_contains(functions_index, 'exports.turnContractSmoke', 'gateway exposes authenticated turn-contract smoke')
require_contains(functions_index, 'runTurnContractSmoke(req.body || {})', 'turn-contract smoke exercises the normal gateway turn path')
require_contains(functions_index, 'body && body.skipDefaults === true', 'turn-contract smoke can isolate external issue cases')
require_contains(turn_contract_smoke, 'turnContractSmoke', 'CLI can run turn-contract smoke against deployed gateway')
require_contains(turn_contract_smoke, 'Home Center turn contract smoke', 'turn-contract smoke reports a clear result')
require_contains(turn_contract_smoke, 'skipDefaults: true', 'turn-contract smoke runner isolates issue cases to avoid long batched requests')
require_contains(turn_contract_smoke, 'defaultResult', 'turn-contract smoke runner still executes generic defaults separately')
require_contains(creative_prompt_smoke, 'Next scene uses kinetic compression to show how the first panzer fight goes.', 'creative prompt smoke uses exact issue 36 failing prompt')
require_contains(creative_prompt_smoke, 'creativePromptSmoke', 'CLI can run creative prompt smoke against deployed gateway')
require_contains(creative_prompt_smoke, 'issue38-stale-github-confirmation', 'creative smoke includes issue 38 stale confirmation scenario')
require_contains(creative_prompt_smoke, 'Simulate a new chapter with perfect adherence to simulation doctrine.  Lexen.  On Normandy.  In a tank.  When a panzer is spotted.', 'creative smoke includes exact issue 38 prompt')
require_contains(creative_prompt_smoke, "toolName: 'github.create_issue'", 'creative smoke sends stale GitHub issue pending confirmation')
require_contains(run_regression, 'node --check tools/home_center_creative_prompt_smoke.mjs', 'regression harness syntax-checks creative prompt smoke runner')
require_contains(run_regression, 'node --check tools/home_center_turn_contract_smoke.mjs', 'regression harness syntax-checks turn-contract smoke runner')
require_contains(main_activity, 'gateway connection closed before response', 'Android reports unexpected stream close as gateway connection failure')
require_absent(agent_tool_turn_body, 'creativeDedicatedDraft: true', 'normal gateway turns must not depend on creative shortcut traces')
require_absent(functions_index, 'I did not get a useful GPT-5.5 response.', 'gateway must not emit vague useful-response fallback')
require_absent(main_activity, 'I did not get a useful reply from GPT-5.5.', 'Android must not emit vague useful-response fallback')
require_absent(agent_tool_turn_body, 'shouldBlockCreativePlannerToolCall(message)', 'normal gateway turns must not block tool calls with local creative intent regex')
require_absent(agent_tool_turn_body, 'creativeToolCallBlocked: true', 'normal gateway turns must not use creative tool-call block traces')
require_absent(agent_tool_turn_body, 'creativeValidationApplied: true', 'normal gateway turns must not post-route creative validation with local intent regex')
require_contains(functions_index, 'function validateCreativeFinal(body, draft)', 'creative provider smoke retains premise validation helpers')
require_contains(functions_index, 'making a tank commander into infantry outside the tank', 'creative validator guards issue 28 role inversion')
require_contains(functions_index, 'Do not ask another clarification question. Do not provide next steps. Do not call tools. Do not report an issue.', 'creative repair forbids another stall/report/tools loop')
require_absent(agent_tool_turn_body, 'creativeRepairApplied: true', 'normal gateway turns must not use creative repair traces')
require_contains(functions_index, 'If context is thin, write a short grounded draft around confirmed names/actions and avoid unsupported biography.', 'creative repair writes instead of punting on thin context')
require_absent(functions_index, 'creativeDirectApplied', 'gateway must not bypass canon gathering with creative direct shortcut')
require_contains(functions_index, 'Set narration to the same text as reply', 'gateway prompt forbids mismatched TTS narration')
require_contains(functions_index, 'narration: finalReply ||', 'gateway returns normalized final reply text as narration for installed APK compatibility')
require_contains(functions_index, 'toolByName(plannerTools, toolName)', 'gateway rejects unadvertised planner tool calls')
require_contains(functions_index, 'function finalReplyText(parsed, rawText = \'\', depth = 0)', 'gateway normalizes final answer JSON shapes')
for final_alias in ['parsed.answer', 'parsed.message', 'parsed.content', 'parsed.final', 'parsed.finalAnswer', 'parsed.final_response', 'parsed.response']:
    require_contains(functions_index, final_alias, f'gateway accepts final reply alias {final_alias}')
require_contains(functions_index, 'return extractJsonObject(nested)', 'gateway unwraps double-encoded planner JSON before falling back to visible text')
require_contains(functions_index, 'const nestedReply = finalReplyText(nested, \'\', depth + 1)', 'gateway unwraps nested JSON final replies before display or narration')
require_contains(functions_index, 'function salvageTruncatedFinalJsonObject(text)', 'gateway salvages truncated final JSON replies from long creative responses')
require_contains(functions_index, 'if (!raw.includes(\'"type"\') || !raw.includes(\'"final"\') || !raw.includes(\'"reply"\')) return null;', 'truncated JSON salvage only applies to final replies, not tool calls')
require_contains(functions_index, 'narration: finalReplyText({reply: parsed.narration}, \'\', 0) || reply', 'gateway normalizes nested JSON narration before TTS')
require_contains(turn_contract_smoke, "status: 'evidence_finalized'", 'live turn-contract smoke rejects parser-error finals for evidence finalizer cases')
require_contains(functions_index, 'const finalReply = finalReplyText(parsed, text)', 'agentToolTurn uses normalized final reply text')
require_absent(functions_index, "reply: safeText(parsed.reply || parsed.text, 12000) || 'I did not get a useful GPT-5.5 response.'", 'agentToolTurn must not emit useless valid-response fallback for alternate final JSON fields')
require_contains(functions_index, 'tool.confirmationRequired && !messageConfirms(message)', 'gateway enforces confirmation outside prompt prose')
require_contains(functions_index, 'sanitizedArgs._confirmedByGateway = true', 'gateway marks confirmed dangerous tool calls after sanitization')
require_contains(functions_index, 'Say "confirm ${action}" or press Confirm.', 'confirmation copy uses short confirm phrase')
require_contains(functions_index, 'pendingConfirmation: pendingConfirmation(toolName, sanitizedArgs)', 'gateway returns sanitized hidden pending confirmation payload')
require_contains(functions_index, 'pendingConfirmationFromBody(body, tools)', 'gateway resumes pending confirmation from Android payload')
require_contains(functions_index, 'function turnKernelFromBody(body, tools, toolResults)', 'gateway has a deterministic turn kernel')
require_contains(functions_index, 'confirmationId: confirmationIdFor(toolName, args, confirmationStage)', 'pending confirmations include a stable confirmation id')
require_contains(functions_index, 'function messageCancels(message)', 'gateway can cancel stale pending confirmations explicitly')
require_contains(functions_index, 'stalePendingDropped', 'gateway ignores pending confirmation when latest user request is not a confirmation')
require_contains(functions_index, 'A stale pending confirmation was discarded by the turn kernel', 'stale pending confirmation is hidden from planner prompt')
require_absent(functions_index, "JSON.stringify({toolName: rawPending.toolName, action: rawPending.action})", 'discarded pending confirmation details are not leaked into planner prompt')
require_contains(functions_index, 'pendingConfirmationCancelled', 'gateway traces explicit pending confirmation cancellation')
require_contains(turn_contract_smoke, 'external_stale_github_pending_creative_request', 'turn-contract runner covers stale GitHub issue pending plus creative request')
require_contains(functions_index, 'confirm_pending_doc_create', 'turn-contract smoke covers explicit confirm resuming pending write')
require_contains(functions_index, 'cancel_pending_doc_create', 'turn-contract smoke covers explicit pending cancellation')
require_contains(functions_index, 'correction_is_not_cancel', 'turn-contract smoke covers correction text that must not cancel new work')
require_contains(functions_index, 'creative_docs_read_finalizer', 'turn-contract smoke covers creative finalization after docs.read')
require_contains(functions_index, 'creative_docs_read_finalizer_without_active_task', 'turn-contract smoke covers issue 41 docs.read finalization without activeTask')
require_contains(turn_contract_smoke, 'external_issue39_docs_read_finalizer', 'turn-contract runner covers issue 39 docs.read finalization')
require_contains(turn_contract_smoke, 'external_issue40_docs_read_finalizer_from_beginning', 'turn-contract runner covers issue 40 from-beginning docs.read finalization')
require_contains(turn_contract_smoke, 'external_issue41_docs_read_finalizer_without_active_task', 'turn-contract runner covers issue 41 docs.read finalization without activeTask')
require_contains(turn_contract_smoke, 'external_issue42_exact_active_task_docs_read_finalizer', 'turn-contract runner covers issue 42 activeTask docs.read finalization')
require_contains(turn_contract_smoke, 'external_issue43_critique_response_not_truncated', 'turn-contract runner covers issue 43 critique truncation')
require_contains(turn_contract_smoke, 'external_issue44_report_contaminated_prompt_reads_remembered_doc', 'turn-contract runner covers issue 44 contaminated prompt context read')
require_contains(turn_contract_smoke, 'external_issue44_after_docs_read_finalizes_despite_report_history', 'turn-contract runner covers issue 44 finalization after report contamination')
require_contains(turn_contract_smoke, 'Now show how he wins. Simulated. But forgone. Not clean. Not easy.', 'turn-contract runner includes exact issue 39 prompt')
require_contains(turn_contract_smoke, 'Lexen vigil. Green commander doc. Now show how he wins. Simulated. But forgone. Not clean. Not easy. Against first panzer. From the beginning', 'turn-contract runner includes exact issue 40 prompt')
require_contains(turn_contract_smoke, 'Pick it up at an arbitrary point that interests you', 'turn-contract runner includes exact issue 41 prompt')
require_contains(turn_contract_smoke, 'Pick it up at an arbitrary point that I interest you', 'turn-contract runner includes exact issue 42 typo/prompt')
require_contains(turn_contract_smoke, 'Done: Assistant response was cut off during Lexen critique follow-up.', 'issue 44 replay includes prior report-confirmation contamination')
require_contains(turn_contract_smoke, 'replyNotTruncated: true', 'issue prompt smokes reject mid-scene truncation')
require_contains(functions_index, 'if (expected.replyNotTruncated)', 'turn-contract smoke can reject cut-off visible replies')
require_contains(functions_index, 'if (expected.minReplyChars)', 'turn-contract smoke can require minimum prose length')
require_contains(user_path_red_test, 'def expected_build_version()', 'installed user-path smoke derives expected version from build.gradle')
require_contains(user_path_red_test, "versionName={expected_version_name} versionCode={expected_version_code}", 'installed user-path smoke version marker is not hardcoded')
require_absent(user_path_red_test, "EXPECTED_VERSION_NAME = '0.2.14'", 'installed user-path smoke must not keep stale hardcoded versionName')
require_absent(user_path_red_test, "EXPECTED_VERSION_CODE = '18'", 'installed user-path smoke must not keep stale hardcoded versionCode')
issue_38_stale_confirmation_contract = {
    'inputs': [
        'That was a request for a chapter with doctrine in mind, not a doctrine update',
        'Simulate a new chapter with perfect adherence to simulation doctrine.  Lexen.  On Normandy.  In a tank.  When a panzer is spotted.',
    ],
    'source_expectations': [
        'const rawPending = pendingConfirmationFromBody(body, tools)',
        'const pending = rawPending && confirms ? rawPending : null',
        'Latest intent rule: the latest user request controls.',
    ],
}
if not all(issue_38_stale_confirmation_contract['inputs']):
    fail('issue 38 stale confirmation contract is missing exact user input')
for expected in issue_38_stale_confirmation_contract['source_expectations']:
    if expected not in functions_index:
        fail(f"issue 38 stale confirmation contract is missing source expectation {expected}")
require_contains(functions_index, 'function sanitizeToolArguments(tool, args)', 'gateway sanitizes tool args against advertised schema')
require_contains(functions_index, "allowed.has(key) || key === '_confirmedByGateway'", 'gateway preserves only schema args and confirmation marker')
require_contains(functions_index, "key === '_doubleConfirmedByGateway'", 'gateway preserves double confirmation marker')
require_contains(functions_index, 'pendingTool.doubleConfirmationRequired', 'gateway detects double-confirm tools')
require_contains(functions_index, 'double_confirmation_required', 'gateway requires second confirmation for delete tools')
require_contains(main_activity, 'definition.doubleConfirmationRequired', 'Android enforces double-confirm tools')
require_contains(main_activity, 'arguments.optBoolean("_doubleConfirmedByGateway", false)', 'Android requires gateway double confirmation marker')
require_contains(functions_index, 'pendingConfirmation(pending.toolName, sanitizeToolArguments(tool, args)', 'pending confirmation cannot preserve stale extra args')
require_contains(functions_index, 'const sanitizedArgs = sanitizeToolArguments(tool, args)', 'tool dispatch uses sanitized args')
require_contains(functions_index, "toolName !== 'drive.update_metadata') args.folderId", 'drive.update_metadata does not leak folderId alias')
require_contains(functions_index, "toolName !== 'drive.update_metadata') args.folderName", 'drive.update_metadata does not leak folderName alias')
for group in contract['requiredGroups']:
    require_contains(functions_index, f"'{group}'", f'gateway health exposes {group} group')
agent_turn = method_body(functions_index, 'exports.agentTurn', 'async function openCartesiaStream')
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
require_contains(main_activity, 'speech_request displayedResponseLength=', 'speech logs displayed and TTS text lengths')
require_contains(main_activity, 'pendingForUi != null', 'confirmation replies are detected before response shaping')
require_contains(main_activity, 'appendAssistantMessageRaw(responseForUi)', 'confirmation replies bypass kitchen next-step shaping')
require_contains(main_activity, 'private String appendAssistantMessageRaw(String text)', 'raw assistant append path exists for tool confirmations')
require_absent(main_activity, 'speak(narration == null || narration.trim().isEmpty() ? finalResponse : narration.trim())', 'Cartesia must not read mismatched short narration')
require_contains(main_activity, 'TextToSpeech.OnInitListener', 'Android has built-in TTS fallback for narration')
require_contains(main_activity, 'setOnUtteranceProgressListener', 'Device TTS fallback uses completion callbacks instead of a truncating timer')
require_contains(main_activity, 'device_tts_complete utteranceId=', 'Device TTS completion is logged from callback')
require_contains(main_activity, 'speakWithDeviceTtsFallback(message, utteranceId, sequence, cause)', 'Cartesia failure falls back to device TTS')
require_contains(main_activity, 'device_tts_fallback cause=', 'Device TTS fallback is logged with Cartesia failure cause')
require_contains(cartesia_client, 'return openProxySpeechStream(text);', 'Cartesia uses hosted proxy as authoritative when configured')
require_absent(cartesia_client, 'proxyFailure = ex', 'Cartesia must not hide hosted proxy failures by falling through to direct Android DNS')
require_contains(cartesia_client, 'connection.setReadTimeout(60000)', 'Cartesia hosted proxy read timeout allows normal assistant responses')
require_absent(main_activity, 'AUDIOFOCUS_GAIN_TRANSIENT_EXCLUSIVE', 'Narration must not request exclusive audio focus')
require_contains(main_activity, 'new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT)', 'Narration uses transient non-exclusive audio focus')
require_contains(main_activity, 'audio_focus_request type=transient', 'Audio focus request logs transient focus type')
require_contains(main_activity, 'audio_focus_abandoned', 'Speech cleanup logs abandoned audio focus')
require_contains(main_activity, 'media_key_handoff_disabled reason=', 'Speech cleanup logs that media-key handoff is disabled')
require_contains(main_activity, 'speech_cleanup reason=', 'Speech cleanup logs completion reason')
require_absent(main_activity, 'KEYCODE_MEDIA_PAUSE', 'Narration must not send media pause commands')
require_absent(main_activity, 'KEYCODE_MEDIA_PLAY', 'Narration must not send media play commands')
require_absent(main_activity, 'dispatchMediaKeyEvent', 'Narration must not control the previous media player with media keys')
require_absent(main_activity, 'pauseExternalPlaybackForSpeech', 'Narration must not manually pause external media')
require_absent(main_activity, 'resumeExternalPlaybackAfterSpeech', 'Narration must not manually resume external media')
require_absent(main_activity, 'externalPlaybackPausedForSpeech', 'Narration must not track stale external media ownership')
require_contains(main_activity, 'finishSpeechPlaybackFor(utteranceId, "stream_complete")', 'Cartesia stream completion uses shared speech cleanup')
require_contains(main_activity, 'finishSpeechPlaybackFor(utteranceId, "speech_unavailable")', 'Speech unavailable path uses shared speech cleanup')
require_contains(main_activity, 'finishSpeechPlaybackFor(utteranceId, "device_tts_complete")', 'Device TTS completion uses shared speech cleanup')
require_contains(main_activity, 'finishSpeechPlaybackFor(utteranceId, "device_tts_error")', 'Device TTS error uses shared speech cleanup')
require_contains(main_activity, 'finishSpeechPlayback("user_stop")', 'Manual stop uses shared speech cleanup')
finish_speech = method_body(main_activity, 'private void finishSpeechPlayback(String reason)', '    private void abandonSpeechFocus()')
require_order(finish_speech, [
    'media_key_handoff_disabled reason=',
    'speech_cleanup reason=',
    'setSpeechPlaying(false);',
    'abandonSpeechFocus();',
], 'Speech cleanup logs, deactivates media session, and abandons focus without media-key handoff')
require_order(method_body(main_activity, 'private void updateSpeechMediaSession(boolean playing)', '    private String shortMessage'), [
    'speechMediaSession.setPlaybackState',
    'speechMediaSession.setActive(playing);',
], 'Media session active state follows explicit playback state updates')
require_contains(functions_index, 'safeText(req.body && req.body.text, 12000)', 'Hosted Cartesia endpoint accepts full long narration text')
require_absent(functions_index, 'safeText(req.body && req.body.text, 1200)', 'Hosted Cartesia endpoint must not truncate narration at 1200 chars')
require_contains(functions_index, 'openCartesiaStream(text)', 'Hosted Cartesia endpoint opens an upstream stream')
require_contains(functions_index, 'audioResponse.body.pipeTo(Writable.toWeb(res))', 'Hosted Cartesia endpoint streams audio to Android instead of buffering')
require_absent(functions_index, 'return Buffer.from(await response.arrayBuffer())', 'Hosted Cartesia endpoint must not buffer full long audio before responding')
require_contains(functions_index, "res.set('X-Audio-Format', 'pcm_s16le')", 'Hosted Cartesia endpoint advertises PCM format')
require_contains(functions_index, "res.set('Connection', 'close')", 'Hosted Cartesia endpoint closes response explicitly for Android playback')
require_contains(main_activity, 'lastSpoken = startupGreeting;', 'Startup greeting is remembered without auto-speaking over first response')
require_absent(main_activity, 'main.post(() -> speak(startupGreeting))', 'Startup must not auto-speak and truncate first real response')
require_contains(main_activity, 'Long press to copy. Double tap to replay.', 'message interaction is exposed to accessibility')

if failures:
    print('Home Center regression tests failed:', file=sys.stderr)
    for item in failures:
        print(f'- {item}', file=sys.stderr)
    sys.exit(1)

print('Home Center tool contract regression tests: OK')
