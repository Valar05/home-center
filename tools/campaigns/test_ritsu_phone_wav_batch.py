"""Offline regression for byte-perfect receiver batch input in one player WAV."""
import importlib.util, pathlib, tempfile, unittest, wave
from array import array
spec=importlib.util.spec_from_file_location("batch",pathlib.Path(__file__).with_name("ritsu_phone_wav_batch.py"))
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
def write(path,samples):
    with wave.open(str(path),"wb") as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000)
        w.writeframes(array("h",samples).tobytes())
class BatchTests(unittest.TestCase):
    def test_exact_samples_and_no_changes_to_sources(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)
            a=p/("00000031_"+"1"*24+".wav"); b2=p/("00000032_"+"2"*24+".wav");c=p/("00000033_"+"3"*24+".wav")
            samples=[([100]*1000),([0]*300+[333]*200),([-1234]*400)]
            for f,s in zip((a,b2,c),samples):write(f,s)
            before=[f.read_bytes() for f in (a,b2,c)]
            out=p/"batch.wav"
            rec=b.build([a,b2,c],out)
            self.assertEqual(rec["status"],"verified")
            self.assertEqual(rec["firstSeq"],31);self.assertEqual(rec["lastSeq"],33)
            self.assertEqual(rec["sourceSamplesTrimmed"],0)
            with wave.open(str(out),"rb") as w:self.assertEqual(w.readframes(w.getnframes()),array("h",sum(samples,[])).tobytes())
            self.assertEqual(before,[f.read_bytes() for f in (a,b2,c)])
            with self.assertRaises(FileExistsError):b.build([a,b2],out)
    def test_out_of_order_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d);a=p/("00000001_"+"1"*24+".wav");z=p/("00000003_"+"3"*24+".wav")
            write(a,[100]*5);write(z,[200]*5)
            with self.assertRaises(ValueError):b.build([a,z],p/"out.wav")
            self.assertFalse((p/"out.wav").exists())
    def test_single_file_refused(self):
        with self.assertRaises(ValueError):b.build([pathlib.Path("nonexistent")],pathlib.Path("noout"))
    def test_format_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d);a=p/("00000001_"+"1"*24+".wav");c=p/("00000002_"+"2"*24+".wav")
            write(a,[2]*4)
            with wave.open(str(c),"wb") as w:
                w.setnchannels(2);w.setsampwidth(2);w.setframerate(24000);w.writeframes(b"\0"*100)
            with self.assertRaises(ValueError):b.build([a,c],p/"out.wav")
            self.assertFalse((p/"out.wav").exists())
if __name__=="__main__":unittest.main(verbosity=2)
