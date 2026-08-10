from pathlib import Path
import hashlib, shutil, datetime, re

ROOT = Path(r"G:\My Drive\Venice Runtime")
P = ROOT / "src" / "workstation-tools.mjs"
EXPECTED = "ecad17afa34e206a6e3186692c728793"

def md5(path): return hashlib.md5(path.read_bytes()).hexdigest()
actual = md5(P)
if actual != EXPECTED:
    raise SystemExit(f"SOURCE_DRIFT workstation-tools.mjs {actual} != {EXPECTED}")

stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
backup = P.with_name(P.name + f".pre-image-identity-args-{stamp}")
shutil.copy2(P, backup)
try:
    text = P.read_text(encoding="utf-8")
    import_anchor = 'import { generateLocalImage } from "./local-image.mjs";'
    if import_anchor not in text:
        raise RuntimeError("image import anchor missing")
    if 'from "./image-identity-intent.mjs"' not in text:
        text = text.replace(import_anchor, import_anchor + '\nimport { requestsVeniceIdentity } from "./image-identity-intent.mjs";', 1)

    primary = '        prompt,\n        negativePrompt,'
    primary_new = '        prompt,\n        includeIdentity: requestsVeniceIdentity(prompt),\n        negativePrompt,'
    if primary not in text:
        raise RuntimeError("primary image call anchor missing")
    text = text.replace(primary, primary_new, 1)

    panel = '            prompt: panelPrompt,\n            negativePrompt: anthropomorphicConditioning(panelPrompt).negative,'
    panel_new = '            prompt: panelPrompt,\n            includeIdentity: requestsVeniceIdentity(panelPrompt),\n            negativePrompt: anthropomorphicConditioning(panelPrompt).negative,'
    if panel not in text:
        raise RuntimeError("panel image call anchor missing")
    text = text.replace(panel, panel_new, 1)

    video = '            prompt: visualPrompts[index],\n            seed: Number.parseInt(seedBase.slice(index * 8, index * 8 + 8), 16),'
    video_new = '            prompt: visualPrompts[index],\n            includeIdentity: requestsVeniceIdentity(visualPrompts[index]),\n            seed: Number.parseInt(seedBase.slice(index * 8, index * 8 + 8), 16),'
    if video not in text:
        raise RuntimeError("video image call anchor missing")
    text = text.replace(video, video_new, 1)

    count = len(re.findall(r'includeIdentity:\s*requestsVeniceIdentity\(', text))
    if count != 3:
        raise RuntimeError(f"expected 3 explicit image identity call sites, found {count}")
    P.write_text(text, encoding="utf-8", newline="\n")
except Exception:
    shutil.copy2(backup, P)
    raise

print(f"ok before={actual} after={md5(P)} count=3 backup={backup}")
