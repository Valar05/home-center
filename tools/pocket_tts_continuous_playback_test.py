#!/data/data/com.termux/files/usr/bin/python3
from pathlib import Path
root=Path(__file__).resolve().parents[1]
activity=(root/'app/src/main/java/com/dclar/homecenter/MainActivity.java').read_text()
service=(root/'app/src/main/java/com/dclar/homecenter/NarrationForegroundService.java').read_text()
policy=(root/'app/src/main/java/com/dclar/homecenter/NarrationBufferPolicy.java').read_text()
target_start=activity.index('    private void playDocumentAudioTarget(');target_end=activity.index('    private void playDocumentWavSequence(',target_start);target=activity[target_start:target_end]
legacy_start=target_end;legacy_end=activity.index('    private void startNarrationServicePlayback(',legacy_start);legacy=activity[legacy_start:legacy_end]
assert 'if (USE_POCKET_TTS_READER)' in target and 'startNarrationServicePlayback(reader, section, offset);' in target
assert target.index('startNarrationServicePlayback(reader, section, offset);') < target.index('documentAudioExecutor.execute')
assert 'startNarrationServicePlayback' not in legacy
assert 'reconcilePocketTtsServicePlayback(reader);' in activity
assert activity.index('reconcilePocketTtsServicePlayback(reader);') < activity.index('restartDocumentPlaybackFromSavedPosition(reader, reason)')
assert service.count('createTrack()')==2  # one call plus declaration
assert 'for(int section=startSection' in service and 'section-%04d.wav' in service
assert 'getPlaybackHeadPosition' in service and 'persist(old.directory,found.section' in service
assert 'AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN)' in service
assert 'new MediaSession(this,"HomeCenterNarrationV2")' in service
assert 'ACTION_PAUSE' in service and 'waiting_for_render' in service
assert 'return START_NOT_STICKY;' in service and 'return START_STICKY;' not in service
assert 'service_sticky_restart_rejected' in service and 'service_foreground_start_rejected' in service
assert 'cursor.updatedAtMs' in activity and 'DOC_READER_SERVICE_CURSOR_STALE_MS' in activity
assert 'requiredAheadSeconds' in policy and '0.8 * minimum' in policy and 'productionRatios.size() - 8' in policy
assert 'stopService(new Intent(this, NarrationForegroundService.class));' in activity
assert 'preserveNarration' in activity
# Deterministic segment/cursor reference tape: played frames, never queued bytes, own resume cursor.
segments=[(3,0,120,1000),(4,1000,0,800)]
def cursor(head):
 found=None
 for section,start,offset,length in segments:
  if head>=start:found=(section,start,offset,length)
  else:break
 if found is None:return None
 section,start,offset,length=found
 return section,offset+max(0,min(length,head-start))*2
assert cursor(0)==(3,120) and cursor(500)==(3,1120) and cursor(1000)==(4,0) and cursor(1700)==(4,1400)
print('Pocket TTS service-owned continuous playback contract: OK')
