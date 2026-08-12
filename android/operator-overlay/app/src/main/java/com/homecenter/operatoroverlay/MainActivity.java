package com.homecenter.operatoroverlay;

import android.app.Activity;
import android.content.Intent;
import android.media.projection.MediaProjectionManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;

public class MainActivity extends Activity {
    private static final int OVERLAY_REQUEST=4107, CAPTURE_REQUEST=4108; private boolean requestedCapture;
    @Override protected void onCreate(Bundle savedInstanceState){super.onCreate(savedInstanceState);ensureOverlay();}
    @Override protected void onResume(){super.onResume();if(Settings.canDrawOverlays(this)){startOverlay();if(!requestedCapture){requestedCapture=true;requestCapture();}}}
    private void ensureOverlay(){if(Settings.canDrawOverlays(this)){startOverlay();return;} startActivityForResult(new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:"+getPackageName())),OVERLAY_REQUEST);}
    private void startOverlay(){OperatorState.setControlEnabled(this,false);OperatorState.setOverlayHidden(this,false);Intent s=new Intent(this,OperatorOverlayService.class).setAction(OperatorOverlayService.ACTION_RESTORE);if(Build.VERSION.SDK_INT>=26)startForegroundService(s);else startService(s);}
    private void requestCapture(){MediaProjectionManager m=(MediaProjectionManager)getSystemService(MEDIA_PROJECTION_SERVICE);startActivityForResult(m.createScreenCaptureIntent(),CAPTURE_REQUEST);}
    @Override protected void onActivityResult(int requestCode,int resultCode,Intent data){super.onActivityResult(requestCode,resultCode,data);if(requestCode==CAPTURE_REQUEST){if(resultCode==RESULT_OK&&data!=null){Intent s=new Intent(this,VeniceAudioCaptureService.class).putExtra(VeniceAudioCaptureService.EXTRA_RESULT_CODE,resultCode).putExtra(VeniceAudioCaptureService.EXTRA_RESULT_DATA,data);if(Build.VERSION.SDK_INT>=26)startForegroundService(s);else startService(s);}finish();}}
}
