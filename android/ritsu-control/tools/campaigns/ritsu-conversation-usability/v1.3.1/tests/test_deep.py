import base64,pathlib,subprocess,sys,tempfile,unittest
P=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
import onego,patch_android
class Integration(unittest.TestCase):
 def test_courier_all_chunks_within_limit(self):
  with tempfile.TemporaryDirectory() as td:
   old=onego.RUN
   try:
    onego.RUN=pathlib.Path(td)
    blob=base64.b64encode(onego.packet_for_windows()).decode()
    for n,i in enumerate(range(0,len(blob),330)):
     chunk=blob[i:i+330]
     payload=onego.PFX+fr'''$o=@{{phase='WINDOWS_PACKET_{n}';result='';error=''}};try{{
$f=Join-Path $env:USERPROFILE '.ritsu-control\usability-packet-v1.3.1\packet.b64';
$s=[IO.File]::ReadAllText($f);$c='{chunk}';$i={i};
if($s.Length -eq $i){{[IO.File]::AppendAllText($f,$c);$o.result='APPENDED'}}
elseif($s.Length -ge ($i+$c.Length) -and $s.Substring($i,$c.Length) -ceq $c){{$o.result='REUSED'}}
else{{$o.error='CONFLICT'}}
}}catch{{$o.error='WRITE_FAILED'}};Emit $o'''
     self.assertLessEqual(len(onego.ps_command(payload)),3400)
   finally:onego.RUN=old
 def test_accepted_main_ui_anchors(self):
  with tempfile.TemporaryDirectory() as td:
   j=pathlib.Path(td)/'app/src/main/java/com/homecenter/ritsucontrol';j.mkdir(parents=True)
   lines=[
    '    private ScrollView feedScroll;',
    '        TextView title = label("Ritsu  ·  Conversation Hub", 21, true);',
    '        root.addView(title);',
    '        root.addView(headerStatus);',
    '        root.addView(button("Campaigns", v->startActivity(new Intent(this, CampaignActivity.class))));',
    '        root.addView(outboxWarning);',
    '        root.addView(sessions);',
    '        root.addView(machineRow);',
    '        root.addView(tabs);',
    '        root.addView(controls);',
    '        renderFeed();','        refreshStatus();','        send(RitsuControlService.ACTION_SYNC_NOW);',
    '    private void renderFeed() {','       transcriptRows.removeAllViews();','    }',
    '    private void showDirectLinkStatus() {','    }',
    '        // The operator already pressed Send. No second confirmation:',
    '            composer.setText("");','            renderFeed();',
    '                    workspace.create(name.getText().toString());',
    '                    refreshConversationSelectors();',
    '        renderFeed();','    }','',
    '    @Override protected void onPause(){',
    '        updates.removeCallbacks(redraw);','        super.onPause();','    }'
   ]
   (j/'MainActivity.java').write_text('\n'.join(lines))
   (j/'RitsuWorkspace.java').write_text('if(raw.length()>=12)throw new IllegalStateException("12 conversation tabs maximum");')
   for name in ['RitsuPairing.java','RitsuLocalSync.java','ConversationLedger.java']:(j/name).write_text('class Stub {}')
   patch_android.patch(pathlib.Path(td),P)
   a=(j/'MainActivity.java').read_text()
   self.assertIn('RITSU_CONVERSATION_USABILITY_V1_3_1',a)
   self.assertIn('conversationDeck.showDrawer()',a)
   self.assertIn('rememberReadingPosition',a)
   self.assertNotIn('root.addView(button("Campaigns"',a)
   with self.assertRaises(RuntimeError):patch_android.patch(pathlib.Path(td),P)
if __name__=='__main__':unittest.main()
