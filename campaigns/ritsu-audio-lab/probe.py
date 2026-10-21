import json, sys, time, importlib.util
from pathlib import Path
stage, receipt_path = sys.argv[1:3]
result = {"stage": stage, "timestamp": time.time(), "python": sys.version.split()[0], "packages": {}}
for name in ("torch", "torchaudio", "laion_clap", "soundfile"):
    result["packages"][name] = bool(importlib.util.find_spec(name))
if stage == "test":
    import torch, laion_clap
    result["torch"] = torch.__version__
    result["cuda"] = torch.cuda.is_available()
    result["device"] = torch.cuda.get_device_name(0) if result["cuda"] else "cpu"
    model = laion_clap.CLAP_Module(enable_fusion=False, amodel="HTSAT-base")
    model.load_ckpt()
    scores = model.get_text_embedding(["a softly whispered intimate ASMR voice", "a robotic synthetic chorus voice"])
    result["embedding_shape"] = list(scores.shape)
    assert scores.shape[0] == 2
Path(receipt_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
