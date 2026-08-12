package com.homecenter.operatoroverlay;

/** Tiny deterministic PCM analyzer. Keeps no audio and allocates no history. */
final class VeniceAudioAnalyzer {
    static final class Features {
        final double rms, peak, zcr, transientDensity;
        final String texture;
        Features(double rms,double peak,double zcr,double transientDensity,String texture){this.rms=rms;this.peak=peak;this.zcr=zcr;this.transientDensity=transientDensity;this.texture=texture;}
        String compact(){return String.format(java.util.Locale.US,"rms=%.3f peak=%.3f zcr=%.3f transients=%.3f texture=%s",rms,peak,zcr,transientDensity,texture);}
    }
    private VeniceAudioAnalyzer() {}
    static Features analyze(short[] pcm,int count){
        if(pcm==null||count<=1)return new Features(0,0,0,0,"silence");
        count=Math.min(count,pcm.length); double sum=0,peak=0; int crossings=0,transients=0; short prev=pcm[0];
        for(int i=0;i<count;i++){
            double x=pcm[i]/32768.0; sum+=x*x; peak=Math.max(peak,Math.abs(x));
            if(i>0){ if((pcm[i]>=0)!=(prev>=0))crossings++; if(Math.abs(pcm[i]-prev)>9000)transients++; prev=pcm[i]; }
        }
        double rms=Math.sqrt(sum/count), zcr=(double)crossings/(count-1), td=(double)transients/(count-1);
        String texture=rms<0.008?"silence":td>0.08?"impact-heavy":zcr>0.22?"noisy-bright":zcr<0.045?"tonal-low":"mixed";
        return new Features(rms,peak,zcr,td,texture);
    }
}
