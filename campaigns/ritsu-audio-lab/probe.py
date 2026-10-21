import json, sys, time, importlib.util, traceback, os
from pathlib import Path
stage, receipt_path = sys.argv[1:3]
receipt = Path(receipt_path)
events_path = receipt.with_name("clap-test-events.jsonl")
result = {"stage": stage, "timestamp": time.time(), "python": sys.version.split()[0], "packages": {}}
def mark(step, **details):
    event = {"time": time.time(), "step": step, "pid": os.getpid(), **details}
    with events_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
        f.flush()
        os.fsync(f.fileno())
    print(json.dumps(event), flush=True)
def finish(state, **details):
    result.update({"state": state, **details})
    receipt.write_text(json.dumps(result, indent=2), encoding="utf-8")
    mark("finish", state=state)
try:
    mark("probe_started", stage=stage)
    for name in ("torch", "torchaudio", "torchvision", "laion_clap", "soundfile"):
        result["packages"][name] = bool(importlib.util.find_spec(name))
    mark("packages_checked", packages=result["packages"])
    if stage == "test":
        mark("imports_started")
        import torch, laion_clap
        mark("imports_completed", torch=torch.__version__)
        result["torch"] = torch.__version__
        result["cuda"] = torch.cuda.is_available()
        result["device"] = torch.cuda.get_device_name(0) if result["cuda"] else "cpu"
        mark("model_constructor_started")
        model = laion_clap.CLAP_Module(enable_fusion=False, amodel="HTSAT-base")
        mark("model_constructor_completed")
        mark("checkpoint_load_started")
        model.load_ckpt()
        mark("checkpoint_load_completed")
        mark("embedding_started")
        scores = model.get_text_embedding(["a softly whispered intimate ASMR voice", "a robotic synthetic chorus voice"])
        result["embedding_shape"] = list(scores.shape)
        assert scores.shape[0] == 2
        mark("embedding_completed", shape=result["embedding_shape"])
    finish("passed")
except BaseException as e:
    mark("failed", error=repr(e), traceback=traceback.format_exc()[-8000:])
    finish("failed", error=repr(e))
    raise
