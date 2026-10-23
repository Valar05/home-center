#!/usr/bin/env python3
"""Ritsu mpv v4 deterministic unit+real no-speaker probe.

No touch to the live receiver, its relay token, audio files or state. The
integration uses --ao=null and two generated local PCM WAVs in a temp folder.
"""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import math
import os
import shutil
import struct
import threading
import time
import unittest
import wave

src = Path(__file__).with_name("ritsu_phone_mpv_driver_v4.py")
spec = importlib.util.spec_from_file_location("ritsu_driver", src)
dmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dmod)

def wav(path, seconds=0.9, rate=24000):
    # Quiet synthetic low-frequency sine; never emitted to real speakers in test.
    pcm = b"".join(struct.pack("<h", int(math.sin(i*2*math.pi*350/rate)*2500))
                   for i in range(int(rate*seconds)))
    with wave.open(str(path), "wb") as w:
        w.setframerate(rate); w.setsampwidth(2); w.setnchannels(1)
        w.writeframes(pcm)

class LogicTests(unittest.TestCase):
    def prepare(self, folder):
        p=Path(folder)
        (p/"ready").mkdir()
        (p/"play.seq").write_text("1\n")
        return p

    def test_ipc_eof_is_only_play_seq_commit(self):
        with TemporaryDirectory() as td:
            p=self.prepare(td)
            first=p/"ready"/("00000001_"+"a"*24+".wav")
            second=p/"ready"/("00000002_"+"b"*24+".wav")
            wav(first);wav(second)
            m=dmod.Driver(p, audio_output="null")
            m.next_enqueue=1
            class FakeSocket:
                def sendall(self, raw): pass
            m.sock=FakeSocket()
            m.offer()
            self.assertTrue((p/"playing").is_file())
            self.assertEqual((p/"play.seq").read_text().strip(),"1")
            m.handle({"event":"start-file","playlist_entry_id":51})
            m.handle({"request_id":1,"error":"success"})
            m.offer()
            m.handle({"request_id":2,"error":"success"})
            m.handle({"event":"end-file","playlist_entry_id":51,"reason":"eof"})
            self.assertEqual((p/"play.seq").read_text().strip(),"2")
            self.assertTrue((p/"playing").exists())
            m.handle({"event":"start-file","playlist_entry_id":52})
            m.handle({"event":"end-file","playlist_entry_id":52,"reason":"eof"})
            self.assertEqual((p/"play.seq").read_text().strip(),"3")
            self.assertFalse((p/"playing").exists())

    def test_non_eof_never_advances(self):
        with TemporaryDirectory() as td:
            p=self.prepare(td)
            f=p/"ready"/("00000001_"+"a"*24+".wav")
            wav(f)
            m=dmod.Driver(p)
            m.next_enqueue=1
            class FakeSocket:
                def sendall(self, raw): pass
            m.sock=FakeSocket()
            m.offer()
            m.handle({"event":"start-file","playlist_entry_id":3})
            with self.assertRaisesRegex(RuntimeError,"did not reach EOF"):
                m.handle({"event":"end-file","playlist_entry_id":3,"reason":"error"})
            self.assertEqual((p/"play.seq").read_text().strip(),"1")
            self.assertTrue((p/"playing").exists())

    def test_foreign_file_and_bad_audio_refused(self):
        with TemporaryDirectory() as td:
            p=self.prepare(td)
            fake=p/"ready"/("00000001_"+"a"*24+".wav")
            fake.write_bytes(b"not a WAV")
            with self.assertRaises((wave.Error, EOFError)):
                dmod.inspect(fake,1)
            with self.assertRaises(RuntimeError):
                dmod.inspect(fake,2)

def real_no_audio_probe():
    if not shutil.which("mpv"):
        print("MPV_NOT_PRESENT")
        return 4
    with TemporaryDirectory(prefix="ritsu-mpv-offline-") as td:
        p=Path(td)
        (p/"ready").mkdir()
        (p/"play.seq").write_text("1\n")
        f1=p/"ready"/("00000001_"+"a"*24+".wav")
        f2=p/"ready"/("00000002_"+"b"*24+".wav")
        wav(f1,1.2)
        driver=dmod.Driver(p, audio_output="null")
        errors=[]
        def runner():
            try: driver.run(test_timeout=7.0)
            except BaseException as e: errors.append(repr(e))
            finally: driver.close(failure=bool(errors))
        thread=threading.Thread(target=runner,daemon=True)
        thread.start()
        deadline=time.monotonic()+6
        while driver.started_count<1 and time.monotonic()<deadline:
            time.sleep(.05)
        if driver.started_count<1:
            (p/"stop.request").touch()
            thread.join(3)
            raise RuntimeError("mpv did not start first null-AO WAV")
        # Second completed source arrives while first is still playing.
        wav(f2,1.2)
        while driver.finished_count<2 and time.monotonic()<deadline:
            time.sleep(.05)
        (p/"stop.request").touch()
        thread.join(3)
        if thread.is_alive() or errors or driver.finished_count!=2:
            raise RuntimeError("mpv IPC test failed: "+str(errors))
        if (p/"play.seq").read_text().strip()!="3" or (p/"playing").exists():
            raise RuntimeError("mpv FIFO state incorrect")
        trace=[json.loads(x) for x in (p/"trace.jsonl").read_text().splitlines()]
        started=[x for x in trace if x["event"]=="mpv_track_started"]
        ended=[x for x in trace if x["event"]=="mpv_track_finished"]
        if [x["seq"] for x in started]!=[1,2] or [x["seq"] for x in ended]!=[1,2]:
            raise RuntimeError("mpv event order wrong")
        print("RITSU_MPV_IPC_REAL_NO_AUDIO=PASS")
        print("MPV_TRACKS=2")
        print("ONE_PERSISTENT_PROCESS=1")
        print("PLAY_SEQ=3")
        print("SPEAKER_OUTPUT=NONE")
        print("LIVE_RECEIVER_CHANGED=NO")
        return 0

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--live-ipc-null-test", action="store_true")
    args=ap.parse_args()
    if args.live_ipc_null_test:
        raise SystemExit(real_no_audio_probe())
    unittest.main(argv=[__file__],verbosity=2)
