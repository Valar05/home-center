package com.homecenter.operatoroverlay;

import android.app.*;
import android.content.Intent;
import android.media.*;
import android.media.projection.MediaProjection;
import android.media.projection.MediaProjectionManager;
import android.os.IBinder;

/** Captures eligible app playback into a short in-memory PCM buffer only. No audio is written to disk. */
public class VeniceAudioCaptureService extends Service {
    static final String EXTRA_RESULT_CODE="resultCode", EXTRA_RESULT_DATA="resultData";
    private volatile boolean running; private AudioRecord record; private MediaProjection projection; private Thread worker;
    @Override public int onStartCommand(Intent intent,int flags,int id){
        startForeground(4110,notification());
        if(intent==null)return START_NOT_STICKY;
        int code=intent.getIntExtra(EXTRA_RESULT_CODE,Activity.RESULT_CANCELED); Intent data=intent.getParcelableExtra(EXTRA_RESULT_DATA);
        if(code!=Activity.RESULT_OK||data==null){stopSelf();return START_NOT_STICKY;}
        MediaProjectionManager m=(MediaProjectionManager)getSystemService(MEDIA_PROJECTION_SERVICE); projection=m.getMediaProjection(code,data); startCapture(); return START_NOT_STICKY;
    }
    private void startCapture(){
        AudioPlaybackCaptureConfiguration capture=new AudioPlaybackCaptureConfiguration.Builder(projection).addMatchingUsage(AudioAttributes.USAGE_MEDIA).addMatchingUsage(AudioAttributes.USAGE_GAME).build();
        AudioFormat format=new AudioFormat.Builder().setEncoding(AudioFormat.ENCODING_PCM_16BIT).setSampleRate(16000).setChannelMask(AudioFormat.CHANNEL_IN_MONO).build();
        int min=Math.max(AudioRecord.getMinBufferSize(16000,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT),4096);
        record=new AudioRecord.Builder().setAudioFormat(format).setBufferSizeInBytes(min*2).setAudioPlaybackCaptureConfig(capture).build(); running=true; record.startRecording();
        worker=new Thread(()->{short[] pcm=new short[min/2]; while(running){int n=record.read(pcm,0,pcm.length,AudioRecord.READ_BLOCKING); if(n>0){VeniceAudioAnalyzer.Features f=VeniceAudioAnalyzer.analyze(pcm,n); OperatorState.updateText(this,"Venice audio",f.compact(),System.currentTimeMillis());}}},"venice-audio"); worker.start();
    }
    private Notification notification(){String id="venice_audio"; NotificationManager nm=getSystemService(NotificationManager.class); nm.createNotificationChannel(new NotificationChannel(id,"Venice listening",NotificationManager.IMPORTANCE_LOW)); return new Notification.Builder(this,id).setSmallIcon(android.R.drawable.ic_btn_speak_now).setContentTitle("Venice listens").setContentText("Analyzing playback in memory; no audio saved").setOngoing(true).build();}
    @Override public void onDestroy(){running=false; if(record!=null){try{record.stop();}catch(Exception ignored){} record.release();} if(projection!=null)projection.stop(); super.onDestroy();}
    @Override public IBinder onBind(Intent intent){return null;}
}
