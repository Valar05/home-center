from pathlib import Path
r=Path(__file__).resolve().parents[2]
p=r/'android/ritsu-control/app/src/main/java/com/homecenter/ritsucontrol'
main=(p/'MainActivity.java').read_text();sync=(p/'RitsuLocalSync.java').read_text();ledger=(p/'ConversationLedger.java').read_text();stop=(p/'RitsuRemoteStop.java').read_text();bridge=(r/'tools/campaigns/ritsu_control_playwright_bridge.mjs').read_text();server=(r/'tools/ritsu-local-server/server.mjs').read_text()
assert 'stopSelectedGenerating()' in main
assert 'Copy complete ' in main and 'ClipData.newPlainText("Ritsu message",entry.text)' in main
assert 'Pocket requested ON' in main and 'Pocket requested OFF' in main
assert '"/v1/ritsu/turn/stop"' in stop and 'STOP_RECEIPT_NOT_VERIFIED' in stop
assert '"stopped".equals(type)' in sync and '"stop_unconfirmed".equals(type)' in sync
assert 'text.length()>64000' in sync and 'message.length()>64000' in ledger
assert '/v1/ritsu/turn/stop' in server and 'stopControlGone' in bridge
assert 'RitsuConversationDeck' in main and 'rememberReadingPosition()' in main
print('RITSU_SOURCE_INTEGRATION_REGRESSION=PASS')
