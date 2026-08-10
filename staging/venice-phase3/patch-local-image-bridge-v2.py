from pathlib import Path
import json, shutil, hashlib, datetime

ROOT = Path(r"C:\Users\dclar\Documents\Codex\2026-08-05\ven\work\venice-image-bridge")
EXPECTED = {
    ROOT / "bridge" / "bridge.py": "c360c86f65ee7d4c23486b5fbcebbd0e",
    ROOT / "tests" / "smoke_test.py": "58b3541f837bf65ab4ed811653f80ea2",
    ROOT / "extension" / "defaults.js": "0612cb2c1065983d92324e773f1159ca",
    ROOT / "extension" / "content.js": "122a7153a19758e4c2c214ba2b08a5d8",
    ROOT / "extension" / "background.js": "28af50074857b60dca88ccefec33de25",
}

def md5(path): return hashlib.md5(path.read_bytes()).hexdigest()
def replace_once(text, old, new, label):
    if old not in text: raise RuntimeError(f"missing anchor: {label}")
    return text.replace(old, new, 1)

for p, expected in EXPECTED.items():
    actual = md5(p)
    if actual != expected: raise SystemExit(f"SOURCE_DRIFT {p}: {actual} != {expected}")

stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
backups = {}
for p in EXPECTED:
    b = p.with_name(p.name + f".pre-image-contract-{stamp}")
    shutil.copy2(p, b); backups[str(p)] = str(b)

try:
    p = ROOT / "bridge" / "bridge.py"
    s = p.read_text(encoding="utf-8")
    s = replace_once(s,
        '    def build_workflow(self, request_data: dict[str, Any]) -> tuple[dict[str, Any], int, int, int]:',
        '    def build_workflow(self, request_data: dict[str, Any]) -> tuple[dict[str, Any], int, int, int, dict[str, Any]]:',
        'build_workflow signature')
    s = replace_once(s,
        '        include_identity_value = request_data.get("include_identity")\n        include_identity = bool(include_identity_value) if include_identity_value is not None else bool(re.search(r"\\bVenice\\b", prompt, re.IGNORECASE))',
        '        include_identity_value = request_data.get("include_identity")\n        include_identity = bool(include_identity_value) if include_identity_value is not None else False\n        identity_reason = "caller_explicit" if include_identity_value is not None else "default_off"',
        'identity default')
    s = replace_once(s,
        '        if not include_identity:\n            workflow[sampler_node]["inputs"]["model"] = [active_model_node, 0]',
        '        if not include_identity:\n            for node_id in (str(nodes.get("identity_image", "10")), str(nodes.get("identity_prepare", "11")), identity_loader_node, identity_apply_node):\n                workflow.pop(node_id, None)\n            workflow[sampler_node]["inputs"]["model"] = [active_model_node, 0]',
        'neutral identity subgraph removal')
    s = replace_once(s,
        '        if checkpoint:\n            workflow[checkpoint_node]["inputs"]["ckpt_name"] = checkpoint\n        return workflow, seed, width, height',
        '        if checkpoint:\n            workflow[checkpoint_node]["inputs"]["ckpt_name"] = checkpoint\n        conditioning = {\n            "identityApplied": include_identity,\n            "identityReason": identity_reason,\n            "framingApplied": bool(include_identity and framing_prefix),\n            "styleApplied": include_style,\n            "finalPrompt": prompt,\n        }\n        return workflow, seed, width, height, conditioning',
        'conditioning return')
    s = replace_once(s,
        '        workflow, seed, width, height = self.build_workflow(request_data)',
        '        workflow, seed, width, height, conditioning = self.build_workflow(request_data)',
        'generate tuple')
    s = replace_once(s,
        '                "height": height,\n                "image_data_url": f"data:{mime};base64,{encoded}",',
        '                "height": height,\n                "conditioning": conditioning,\n                "image_data_url": f"data:{mime};base64,{encoded}",',
        'response receipt')
    s = replace_once(s,
        '    workflow, seed, width, height = client.build_workflow({"prompt": "self test", "seed": 1})\n    assert workflow and seed == 1 and width % 64 == 0 and height % 64 == 0\n    print(json.dumps({"ok": True, "version": APP_VERSION, "workflow": str(client.workflow_path), "width": width, "height": height}))',
        '    workflow, seed, width, height, conditioning = client.build_workflow({"prompt": "self test", "seed": 1, "include_identity": False})\n    assert workflow and seed == 1 and width % 64 == 0 and height % 64 == 0\n    assert conditioning["identityApplied"] is False and conditioning["framingApplied"] is False\n    assert all(node not in workflow for node in ("10", "11", "12", "13"))\n    print(json.dumps({"ok": True, "version": APP_VERSION, "workflow": str(client.workflow_path), "width": width, "height": height, "conditioning": conditioning}))',
        'self-test')
    p.write_text(s, encoding="utf-8")

    p = ROOT / "tests" / "smoke_test.py"
    s = p.read_text(encoding="utf-8")
    s = s.replace('workflow, seed, width, height = client.build_workflow(', 'workflow, seed, width, height, conditioning = client.build_workflow(')
    marker = 'wrong_token = "0" * max(32, len(token))\n'
    if marker not in s: raise RuntimeError('missing smoke wrong-token marker')
    neutral = '''neutral_workflow, _, _, _, neutral_conditioning = client.build_workflow({\n    "prompt": "a red tractor crossing a muddy field at sunrise",\n    "include_identity": False,\n})\nassert neutral_conditioning["identityApplied"] is False\nassert neutral_conditioning["framingApplied"] is False\nassert "Venice" not in neutral_conditioning["finalPrompt"]\nassert all(node not in neutral_workflow for node in ("10", "11", "12", "13"))\n\n'''
    if 'neutral_conditioning' not in s: s = s.replace(marker, neutral + marker, 1)
    p.write_text(s, encoding="utf-8")

    p = ROOT / "extension" / "defaults.js"
    s = p.read_text(encoding="utf-8")
    s = replace_once(s, 'autoGenerateSpontaneous: true', 'autoGenerateSpontaneous: false', 'spontaneous default')
    p.write_text(s, encoding="utf-8")

    p = ROOT / "extension" / "content.js"
    s = p.read_text(encoding="utf-8")
    s = replace_once(s, 'const autoEnabled = prefs.autoGenerateSpontaneous ?? true;', 'const autoEnabled = prefs.autoGenerateSpontaneous ?? false;', 'spontaneous fallback')
    helper_anchor = 'function hyperbolicPrompt(text) {'
    helper = '''function requestsVeniceIdentity(prompt) {\n  const text = String(prompt || "").replace(/\\s+/g, " ").trim();\n  if (!/\\bVenice\\b/i.test(text)) return false;\n  const city = /\\b(?:city|canals?|gondolas?|lagoon|italy|italian|piazza|san marco|rialto|adriatic|flooded streets?)\\b/i.test(text);\n  const person = /\\b(?:woman|girl|person|character|her|she|herself|face|eyes|hair|wearing|dressed|portrait|selfie|body|standing|sitting|walking|smiling|looking)\\b/i.test(text);\n  return !(city && !person);\n}\n\n'''
    if helper_anchor not in s: raise RuntimeError('missing content helper anchor')
    if 'function requestsVeniceIdentity' not in s: s = s.replace(helper_anchor, helper + helper_anchor, 1)
    s = replace_once(s,
        'const response = await chrome.runtime.sendMessage({ action: "generate", prompt: request.prompt, negative_prompt: request.negative_prompt });',
        'const response = await chrome.runtime.sendMessage({ action: "generate", prompt: request.prompt, negative_prompt: request.negative_prompt, includeIdentity: request.include_identity ?? requestsVeniceIdentity(request.prompt) });',
        'content generate identity')
    s = replace_once(s,
        'const request = { prompt: hyperbolicPrompt(text), negative_prompt: "low detail, blurry, watermark, text artifacts" };',
        'const request = { prompt: hyperbolicPrompt(text), negative_prompt: "low detail, blurry, watermark, text artifacts", include_identity: true };',
        'content spontaneous identity')
    p.write_text(s, encoding="utf-8")

    p = ROOT / "extension" / "background.js"
    s = p.read_text(encoding="utf-8")
    s = replace_once(s,
        'body: JSON.stringify({ prompt: message.prompt, negative_prompt: message.negative_prompt })',
        'body: JSON.stringify({ prompt: message.prompt, negative_prompt: message.negative_prompt, include_identity: message.includeIdentity === true })',
        'background identity body')
    p.write_text(s, encoding="utf-8")
except Exception:
    for p_str, b_str in backups.items(): shutil.copy2(b_str, p_str)
    raise

print(json.dumps({"ok": True, "backups": backups, "hashes": {str(p): {"md5": md5(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in EXPECTED}}, indent=2))
