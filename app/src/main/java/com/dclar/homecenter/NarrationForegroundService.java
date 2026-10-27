package com.dclar.homecenter;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.media.AudioAttributes;
import android.media.AudioFocusRequest;
import android.media.AudioFormat;
import android.media.AudioManager;
import android.media.AudioTrack;
import android.media.session.MediaSession;
import android.media.session.PlaybackState;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

public final class NarrationForegroundService extends Service {
    static final String ACTION_START="com.dclar.homecenter.action.NARRATION_START";
    static final String ACTION_RENDER="com.dclar.homecenter.action.NARRATION_RENDER_V2";
    static final String ACTION_PLAY="com.dclar.homecenter.action.NARRATION_PLAY_V2";
    static final String ACTION_PAUSE="com.dclar.homecenter.action.NARRATION_PAUSE_V2";
    static final String ACTION_STOP="com.dclar.homecenter.action.NARRATION_STOP";
    static final String EXTRA_TITLE="title",EXTRA_DIRECTORY="directory",EXTRA_SECTION="section",EXTRA_SECTION_COUNT="sectionCount",EXTRA_OFFSET_BYTES="offsetBytes",EXTRA_RENDER_PLAN="renderPlan";
    private static final String CHANNEL_ID="drive_narration_playback_v2",PREFS="narration-playback-v2";
    private static final String PREF_ACTIVE_RENDER_PLAN="activeRenderPlan",PREF_ACTIVE_RENDER_TITLE="activeRenderTitle";
    private static final int NOTIFICATION_ID=1042,SAMPLE_RATE=24000;
    private final ExecutorService playback=Executors.newSingleThreadExecutor();
    private final ExecutorService rendering=Executors.newSingleThreadExecutor();
    private final ScheduledExecutorService monitor=Executors.newSingleThreadScheduledExecutor();
    private final AtomicLong generation=new AtomicLong();
    private final AtomicLong renderGeneration=new AtomicLong();
    private final List<Segment> segments=new ArrayList<>();
    private volatile AudioTrack track; private volatile long writtenFrames; private volatile boolean paused; private volatile boolean renderActive; private volatile String activeRenderPlan=""; private String title="Drive Narrate";
    private PowerManager.WakeLock wakeLock; private AudioManager audioManager; private AudioFocusRequest focusRequest; private MediaSession mediaSession;

    static final class Cursor { final String directory,state; final int section; final long offsetBytes,updatedAtMs; Cursor(String d,int s,long o,String st,long u){directory=d;section=s;offsetBytes=o;state=st;updatedAtMs=u;} }
    static Cursor cursor(Context context){SharedPreferences p=context.getSharedPreferences(PREFS,MODE_PRIVATE);return new Cursor(p.getString("directory",""),p.getInt("section",0),p.getLong("offsetBytes",0),p.getString("state","stopped"),p.getLong("updatedAtMs",0L));}
    private static final class Segment {final int section;final long trackStart,sourceOffset,length;Segment(int s,long t,long o,long l){section=s;trackStart=t;sourceOffset=o;length=l;}}

    @Override public void onCreate(){super.onCreate();audioManager=(AudioManager)getSystemService(AUDIO_SERVICE);mediaSession=new MediaSession(this,"HomeCenterNarrationV2");mediaSession.setCallback(new MediaSession.Callback(){@Override public void onPlay(){resumeTrack();}@Override public void onPause(){pauseTrack();}@Override public void onStop(){stopPlayback();}});mediaSession.setActive(true);monitor.scheduleAtFixedRate(this::sampleCursor,250,250,TimeUnit.MILLISECONDS);}
    @Override public int onStartCommand(Intent intent,int flags,int startId){
        if(intent==null){LocalLog.warn("doc_audio","service_sticky_restart_rejected");stopSelf(startId);return START_NOT_STICKY;}
        String action=intent.getAction();
        String restoredTitle=getSharedPreferences(PREFS,MODE_PRIVATE).getString(PREF_ACTIVE_RENDER_TITLE,title);
        title=firstNonEmpty(intent.getStringExtra(EXTRA_TITLE),title);
        if(ACTION_STOP.equals(action)){cancelRender(true);stopPlayback();stopForeground(true);stopSelf();return START_NOT_STICKY;}
        try{startForeground(NOTIFICATION_ID,notification(title));}
        catch(RuntimeException ex){LocalLog.warn("doc_audio","service_foreground_start_rejected "+safe(ex.getMessage()));stopSelf(startId);return START_NOT_STICKY;}
        acquireWakeLock();
        if(ACTION_RENDER.equals(action)){
            startRender(intent.getStringExtra(EXTRA_RENDER_PLAN),title);
            return START_REDELIVER_INTENT;
        }else if(ACTION_PLAY.equals(action)){
            String dir=intent.getStringExtra(EXTRA_DIRECTORY);int section=Math.max(0,intent.getIntExtra(EXTRA_SECTION,0));int sectionCount=Math.max(section+1,intent.getIntExtra(EXTRA_SECTION_COUNT,section+1));long offset=Math.max(0,intent.getLongExtra(EXTRA_OFFSET_BYTES,0));startPlayback(dir,section,sectionCount,offset);
        }else if(ACTION_PAUSE.equals(action))pauseTrack();
        return START_NOT_STICKY;
    }
    @Override public IBinder onBind(Intent intent){return null;}
    @Override public void onDestroy(){renderGeneration.incrementAndGet();generation.incrementAndGet();sampleCursor();releaseTrack();abandonFocus();updateMediaState(PlaybackState.STATE_STOPPED,0);monitor.shutdownNow();playback.shutdownNow();rendering.shutdownNow();if(mediaSession!=null){mediaSession.release();mediaSession=null;}releaseWakeLock();super.onDestroy();}

    private synchronized void startRender(String planPath,String renderTitle){
        String clean=planPath==null?"":planPath.trim();
        if(clean.isEmpty())return;
        if(renderActive&&clean.equals(activeRenderPlan))return;
        if(renderActive&&!activeRenderPlan.isEmpty()&&!clean.equals(activeRenderPlan))markPlanStopped(activeRenderPlan);
        long token=renderGeneration.incrementAndGet();
        activeRenderPlan=clean;renderActive=true;title=firstNonEmpty(renderTitle,title);
        getSharedPreferences(PREFS,MODE_PRIVATE).edit().putString(PREF_ACTIVE_RENDER_PLAN,clean).putString(PREF_ACTIVE_RENDER_TITLE,title).apply();
        updateNotification(title+" · starting render");
        rendering.execute(()->runRenderPlan(token,new File(clean)));
    }

    private void runRenderPlan(long token,File planFile){
        GoogleDocAudioLibrary.Entry entry=null;int activeSection=0;
        try{
            JSONObject plan=new JSONObject(new String(Files.readAllBytes(planFile.toPath()),StandardCharsets.UTF_8));
            if(!"home-center-pocket-tts-render-plan-v1".equals(plan.optString("schema")))throw new IOException("Pocket TTS render plan schema is invalid");
            if(!PocketTtsNativeRenderer.CONTRACT_VERSION.equals(plan.optString("contractVersion")))throw new IOException("Pocket TTS render contract does not match the app");
            File entryDir=new File(plan.optString("entryDirectory",""));
            if(!entryDir.getCanonicalFile().equals(planFile.getParentFile().getCanonicalFile()))throw new IOException("Pocket TTS render plan directory does not match its manifest");
            GoogleDocAudioLibrary library=new GoogleDocAudioLibrary(this);entry=library.openExisting(entryDir);
            JSONArray sections=plan.optJSONArray("sections");int count=plan.optInt("sectionCount",0);
            if(sections==null||count!=entry.sectionCount||sections.length()!=count)throw new IOException("Pocket TTS render plan section count is invalid");
            for(int i=0;i<count;i++){
                activeSection=i;if(renderGeneration.get()!=token)throw new IOException("Pocket TTS render cancelled");
                if(entry.isDownloaded(i))continue;
                JSONObject section=sections.optJSONObject(i);
                if(section==null||section.optInt("index",-1)!=i)throw new IOException("Pocket TTS render plan order is invalid at section "+(i+1));
                String requestId=section.optString("requestId","");String text=section.optString("text","");
                if(requestId.isEmpty()||text.trim().isEmpty())throw new IOException("Pocket TTS render plan section is empty at "+(i+1));
                entry.markRenderProgress(i);updateNotification(title+" · rendering "+(i+1)+"/"+count);
                PocketTtsNativeRenderer.Result result=renderWithRecovery(requestId,text,()->renderGeneration.get()!=token||Thread.currentThread().isInterrupted());
                importSection(entry,i,result,token);
                LocalLog.info("doc_audio","service_render_section_imported fileId="+entry.fileId+" section="+i+" of="+count+" requestId="+requestId);
                updateNotification(title+" · saved "+(i+1)+"/"+count);
            }
            if(renderGeneration.get()!=token)throw new IOException("Pocket TTS render cancelled");
            entry.flushDeferredSectionMarks();entry.markRenderComplete();
            LocalLog.info("doc_audio","service_render_complete fileId="+entry.fileId+" sections="+entry.sectionCount);
            finishRender(token,true);
        }catch(Exception ex){
            boolean cancelled=renderGeneration.get()!=token||"Pocket TTS render cancelled".equals(ex.getMessage());
            if(entry!=null){entry.flushDeferredSectionMarks();if(cancelled)entry.markRenderStopped();else{entry.markFailed(activeSection,safe(ex.getMessage()));entry.markRenderFailed(activeSection,safe(ex.getMessage()));}}
            LocalLog.warn("doc_audio","service_render_"+(cancelled?"cancelled":"failed")+" section="+activeSection+" detail="+safe(ex.getMessage()));
            if(!cancelled){updateNotification(title+" · renderer unavailable at "+(activeSection+1));finishRender(token,false);}
        }
    }

    private PocketTtsNativeRenderer.Result renderWithRecovery(String requestId,String text,PocketTtsNativeRenderer.CancelCheck cancel)throws IOException{
        IOException last=null;
        for(int attempt=1;attempt<=3;attempt++){
            if(cancel.cancelled())throw new IOException("Pocket TTS render cancelled");
            if(attempt>1){try{Thread.sleep((1L<<(attempt-2))*1000L);}catch(InterruptedException ex){Thread.currentThread().interrupt();throw new IOException("Pocket TTS render cancelled",ex);}}
            try{return PocketTtsNativeRenderer.render(this,requestId,text,cancel);}catch(IOException ex){last=ex;LocalLog.warn("doc_audio","service_render_retry requestId="+requestId+" attempt="+attempt+" detail="+safe(ex.getMessage()));}
        }
        throw last==null?new IOException("Pocket TTS render failed"):last;
    }

    private void importSection(GoogleDocAudioLibrary.Entry entry,int index,PocketTtsNativeRenderer.Result result,long token)throws Exception{
        if(renderGeneration.get()!=token)throw new IOException("Pocket TTS render cancelled");
        File wav=entry.sectionFile(index);File parent=wav.getParentFile();if(parent!=null&&!parent.exists())parent.mkdirs();
        File part=new File(parent,wav.getName()+"."+token+".part");
        Files.copy(result.wav.toPath(),part.toPath(),StandardCopyOption.REPLACE_EXISTING);
        try{Files.move(part.toPath(),wav.toPath(),StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);}
        catch(AtomicMoveNotSupportedException ex){Files.move(part.toPath(),wav.toPath(),StandardCopyOption.REPLACE_EXISTING);}
        long pcmBytes=Math.max(0L,wav.length()-44L);
        entry.markDownloadedValidated(index,pcmBytes,result.sampleRate,result.artifactSha256,result.realTimeFactor,false);
    }

    private synchronized void finishRender(long token,boolean complete){
        if(renderGeneration.get()!=token)return;
        renderActive=false;activeRenderPlan="";
        getSharedPreferences(PREFS,MODE_PRIVATE).edit().remove(PREF_ACTIVE_RENDER_PLAN).remove(PREF_ACTIVE_RENDER_TITLE).apply();
        if(complete)updateNotification(title+" · render complete");
        if(track==null&&!paused){stopForeground(true);stopSelf();}
    }

    private synchronized void cancelRender(boolean markStopped){
        renderGeneration.incrementAndGet();String old=activeRenderPlan;renderActive=false;activeRenderPlan="";
        getSharedPreferences(PREFS,MODE_PRIVATE).edit().remove(PREF_ACTIVE_RENDER_PLAN).remove(PREF_ACTIVE_RENDER_TITLE).apply();
        if(markStopped&&!old.isEmpty())markPlanStopped(old);
    }

    private void markPlanStopped(String planPath){
        try{JSONObject plan=new JSONObject(new String(Files.readAllBytes(new File(planPath).toPath()),StandardCharsets.UTF_8));new GoogleDocAudioLibrary(this).openExisting(new File(plan.optString("entryDirectory",""))).markRenderStopped();}
        catch(Exception ex){LocalLog.warn("doc_audio","service_render_stop_mark_failed "+safe(ex.getMessage()));}
    }

    private void updateNotification(String text){NotificationManager manager=(NotificationManager)getSystemService(Context.NOTIFICATION_SERVICE);if(manager!=null)manager.notify(NOTIFICATION_ID,notification(text));}

    private void startPlayback(String directory,int section,int sectionCount,long offsetBytes){long token=generation.incrementAndGet();releaseTrack();paused=false;requestFocus();synchronized(segments){segments.clear();}writtenFrames=0;persist(directory,section,offsetBytes,"starting");playback.execute(()->playLoop(token,new File(directory),section,sectionCount,offsetBytes));}
    private void playLoop(long token,File directory,int startSection,int sectionCount,long offsetBytes){AudioTrack local=null;try{local=createTrack();track=local;local.play();for(int section=startSection;generation.get()==token&&section<sectionCount;section++){File wav=new File(directory,String.format(Locale.US,"section-%04d.wav",section+1));while(generation.get()==token&&!paused&&(!wav.isFile()||wav.length()<=44)){Cursor waiting=cursor(this);persist(directory.getAbsolutePath(),section,0,"waiting_for_render");Thread.sleep(250);}if(generation.get()!=token||paused)break;long pcm=Math.max(0,wav.length()-44);long offset=section==startSection?Math.min(pcm,offsetBytes)&~1L:0;long length=(pcm-offset)/2; synchronized(segments){segments.add(new Segment(section,writtenFrames,offset,length));}writeWav(local,wav,offset,token);writtenFrames+=length;}while(generation.get()==token&&!paused&&Integer.toUnsignedLong(local.getPlaybackHeadPosition())<writtenFrames)Thread.sleep(50);if(generation.get()==token&&!paused){Cursor c=cursor(this);persist(directory.getAbsolutePath(),c.section,c.offsetBytes,"complete");}}catch(Exception ex){if(generation.get()==token){Cursor c=cursor(this);persist(directory.getAbsolutePath(),c.section,c.offsetBytes,"failed:"+safe(ex.getMessage()));}}finally{if(track==local)releaseTrack();if(generation.get()==token&&!paused&&!renderActive){stopForeground(true);stopSelf();}}}
    private AudioTrack createTrack()throws IOException{int min=AudioTrack.getMinBufferSize(SAMPLE_RATE,AudioFormat.CHANNEL_OUT_MONO,AudioFormat.ENCODING_PCM_16BIT);if(min<=0)throw new IOException("AudioTrack buffer unavailable");AudioTrack value=new AudioTrack.Builder().setAudioAttributes(new AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA).setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build()).setAudioFormat(new AudioFormat.Builder().setSampleRate(SAMPLE_RATE).setEncoding(AudioFormat.ENCODING_PCM_16BIT).setChannelMask(AudioFormat.CHANNEL_OUT_MONO).build()).setBufferSizeInBytes(Math.max(min*4,SAMPLE_RATE*2*4)).setTransferMode(AudioTrack.MODE_STREAM).build();if(value.getState()!=AudioTrack.STATE_INITIALIZED){value.release();throw new IOException("AudioTrack initialization failed");}return value;}
    private void writeWav(AudioTrack audio,File wav,long offset,long token)throws Exception{byte[] buffer=new byte[16384];try(FileInputStream in=new FileInputStream(wav)){long skip=44+offset,done=0;while(done<skip){long n=in.skip(skip-done);if(n<=0)throw new IOException("WAV seek failed");done+=n;}int read;while(generation.get()==token&&(read=in.read(buffer))>=0){int usable=read&~1,at=0;while(at<usable&&generation.get()==token){int n=audio.write(buffer,at,usable-at,AudioTrack.WRITE_BLOCKING);if(n<0)throw new IOException("AudioTrack write failed "+n);at+=n;}}}}
    private void sampleCursor(){AudioTrack local=track;if(local==null)return;long head=Integer.toUnsignedLong(local.getPlaybackHeadPosition());Segment found=null; synchronized(segments){for(Segment segment:segments){if(head>=segment.trackStart)found=segment;else break;}}if(found==null)return;long within=Math.max(0,Math.min(found.length,head-found.trackStart));Cursor old=cursor(this);persist(old.directory,found.section,found.sourceOffset+within*2,paused?"paused":"playing");updateMediaState(paused?PlaybackState.STATE_PAUSED:PlaybackState.STATE_PLAYING,found.sourceOffset/2+within);}
    private void pauseTrack(){paused=true;AudioTrack local=track;if(local!=null)try{local.pause();}catch(Exception ignored){}sampleCursor();updateMediaState(PlaybackState.STATE_PAUSED,0);}
    private void resumeTrack(){paused=false;AudioTrack local=track;if(local!=null){try{local.play();updateMediaState(PlaybackState.STATE_PLAYING,0);return;}catch(Exception ignored){}}Cursor c=cursor(this);if(!c.directory.isEmpty())startPlayback(c.directory,c.section,Integer.MAX_VALUE,c.offsetBytes);}
    private void stopPlayback(){generation.incrementAndGet();sampleCursor();Cursor c=cursor(this);persist(c.directory,c.section,c.offsetBytes,"stopped");releaseTrack();abandonFocus();updateMediaState(PlaybackState.STATE_STOPPED,0);}
    private synchronized void releaseTrack(){AudioTrack old=track;track=null;if(old!=null){try{old.pause();old.flush();old.stop();}catch(Exception ignored){}old.release();}}
    private void persist(String directory,int section,long offset,String state){getSharedPreferences(PREFS,MODE_PRIVATE).edit().putString("directory",directory==null?"":directory).putInt("section",Math.max(0,section)).putLong("offsetBytes",Math.max(0,offset)).putString("state",state).putLong("updatedAtMs",System.currentTimeMillis()).apply();}
    private void requestFocus(){if(audioManager==null)return;AudioAttributes attrs=new AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA).setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build();focusRequest=new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN).setAudioAttributes(attrs).setOnAudioFocusChangeListener(change->{if(change==AudioManager.AUDIOFOCUS_GAIN)resumeTrack();else if(change==AudioManager.AUDIOFOCUS_LOSS_TRANSIENT||change==AudioManager.AUDIOFOCUS_LOSS_TRANSIENT_CAN_DUCK)pauseTrack();else if(change==AudioManager.AUDIOFOCUS_LOSS)stopPlayback();}).build();audioManager.requestAudioFocus(focusRequest);}
    private void abandonFocus(){if(audioManager!=null&&focusRequest!=null)audioManager.abandonAudioFocusRequest(focusRequest);focusRequest=null;}
    private void updateMediaState(int state,long frames){if(mediaSession==null)return;long actions=PlaybackState.ACTION_PLAY|PlaybackState.ACTION_PAUSE|PlaybackState.ACTION_STOP;mediaSession.setPlaybackState(new PlaybackState.Builder().setActions(actions).setState(state,frames*1000/SAMPLE_RATE,state==PlaybackState.STATE_PLAYING?1f:0f).build());}
    private Notification notification(String text){NotificationManager manager=(NotificationManager)getSystemService(Context.NOTIFICATION_SERVICE);if(Build.VERSION.SDK_INT>=26&&manager!=null){NotificationChannel channel=new NotificationChannel(CHANNEL_ID,"Drive Narrate",NotificationManager.IMPORTANCE_LOW);manager.createNotificationChannel(channel);}Intent open=new Intent(this,MainActivity.class).setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP|Intent.FLAG_ACTIVITY_CLEAR_TOP);PendingIntent content=PendingIntent.getActivity(this,0,open,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);Notification.Builder b=Build.VERSION.SDK_INT>=26?new Notification.Builder(this,CHANNEL_ID):new Notification.Builder(this);return b.setSmallIcon(android.R.drawable.ic_media_play).setContentTitle(renderActive?"Drive Narrate is rendering":"Drive Narrate is reading").setContentText(text).setContentIntent(content).setOngoing(true).setShowWhen(false).build();}
    private void acquireWakeLock(){if(wakeLock!=null&&wakeLock.isHeld())return;PowerManager pm=(PowerManager)getSystemService(POWER_SERVICE);if(pm!=null){wakeLock=pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"HomeCenter:DriveNarrateV2");wakeLock.setReferenceCounted(false);wakeLock.acquire(6L*60L*60L*1000L);}}
    private void releaseWakeLock(){if(wakeLock!=null&&wakeLock.isHeld())wakeLock.release();wakeLock=null;}
    private static String firstNonEmpty(String value,String fallback){return value==null||value.trim().isEmpty()?fallback:value.trim();}
    private static String safe(String value){return value==null?"":value.replaceAll("[\\r\\n]+"," ");}
}
