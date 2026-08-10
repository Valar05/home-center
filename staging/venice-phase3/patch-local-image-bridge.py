from pathlib import Path
import json, shutil, hashlib, datetime, re

ROOT = Path(r"C:\Users\dclar\Documents\Codex\2026-08-05\ven\work\venice-image-bridge")
EXPECTED = {
    ROOT / "bridge" / "bridge.py": "c360c86f65ee7d4c23486b5fbcebbd0e",
    ROOT / "tests" / "smoke_test.py": "58b3541f837bf65ab4ed811653f80ea2",
    ROOT / "extension" / "defaults.js": "0612cb2c1065983d92324e773f1159ca",
    ROOT / "extension" / "content.js": "122a7153a19758e4c2c214ba2b08a5d8",
    ROOT / "extension" / "background.js": "28af50074857b60dca88ccefec33de25",
}

def md5(path):
    return hashlib.md5(path.read_bytes()).hexdigest()

for p, expected in EXPECTED.items():
    actual = md5(p)
    if actual != expected:
        raise SystemExit(f"SOURCE_DRIFT {p}: {actual} != {expected}")

stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
backups = {}
for p in EXPECTED:
    backup = p.with_name(p.name + f".pre-image-contract-{stamp}")
    shutil.copy2(p, backup)
    backups[str(p)] = str(backup)

try:
    bridge = ROOT / "bridge" / "bridge.py"
    s = bridge.read_text(encoding="utf-8")
    s = s.replace(
        '    def build_workflow(self, request_data: dict[str, Any]) -> tuple[dict[str, Any], int, int, int]:',
        '    def build_workflow(self, request_data: dict[str, Any]) -> tuple[dict[str, Any], int, int, int, dict[str, Any]]:',
        1,
    )
    old = '        include_identity_value = request_data.get("include_identity")\n        include_identity = bool(include_identity_value) if include_identity_value is not None else bool(re.search(r"\\bVenice\\b", prompt, re.IGNORECASE))'
    new = '        include_identity_value = request_data.get("include_identity")\n        include_identity = bool(include_identity_value) if include_identity_value is not None else False\n        identity_reason = "caller_explicit" if include_identity_value is not None else "default_off"'
    if old not in s:
        raise RuntimeError("bridge identity inference anchor missing")
    s = s.replace(old, new, 1)

    old = '        if include_identity:\n            if identity_prefix:\n                prompt = f"{identity_prefix}. Requested scene: {prompt}"\n            if identity_negative:\n                negative_prompt = f"{negative_prompt}, {identity_negative}" if negative_prompt else identity_negative\n            workflow[identity_loader_node]["inputs"]["model"] = [active_model_node, 0]\n            active_model_node = identity_apply_node\n\n        workflow[sampler_node]["inputs"]["model"] = [active_model_node, 0]'
    new = '        identity_image_node = str(nodes.get("identity_image", "10"))\n        identity_prepare_node = str(nodes.get("identity_prepare", "11"))\n        identity_nodes = [identity_image_node, identity_prepare_node, identity_loader_node, identity_apply_node]\n        if include_identity:\n            if identity_prefix:\n                prompt = f"{identity_prefix}. Requested scene: {prompt}"\n            if identity_negative:\n                negative_prompt = f"{negative_prompt}, {identity_negative}" if negative_prompt else identity_negative\n            workflow[identity_loader_node]["inputs"]["model"] = [active_model_node, 0]\n            active_model_node = identity_apply_node\n        else:\n            for node_id in identity_nodes:\n                workflow.pop(node_id, None)\n\n        workflow[sampler_node]["inputs"]["model"] = [active_model_node, 0]'
    if old not in s:
        raise RuntimeError("bridge identity subgraph anchor missing")
    s = s.replace(old, new, 1)

    old = '        workflow[positive_node]["inputs"]["text"] = prompt\n        workflow[negative_node]["inputs"]["text"] = negative_prompt\n\n        return workflow, seed, width, height'
    new = '        workflow[positive_node]["inputs"]["text"] = prompt\n        workflow[negative_node]["inputs"]["text"] = negative_prompt\n        conditioning = {\n            "identityApplied": include_identity,\n            "identityReason": identity_reason,\n            "framingApplied": bool(include_identity and framing_prefix),\n            "styleApplied": include_style,\n            "finalPrompt": prompt,\n        }\n\n        return workflow, seed, width, height, conditioning'
    if old not in s:
        raise RuntimeError("bridge workflow return anchor missing")
    s = s.replace(old, new, 1)

    old = '        workflow, seed, width, height = self.build_workflow(request_data)'
    new = '        workflow, seed, width, height, conditioning = self.build_workflow(request_data)'
    if old not in s:
        raise RuntimeError("bridge generate tuple anchor missing")
    s = s.replace(old, new, 1)

    old = '                "height": height,\n                "image_data_url": f"data:{mime};base64,{encoded}",'
    new = '                "height": height,\n                "conditioning": conditioning,\n                "image_data_url": f"data:{mime};base64,{encoded}",'
    if old not in s:
        raise RuntimeError("bridge response conditioning anchor missing")
    s = s.replace(old, new, 1)

    old = '    workflow, seed, width, height = client.build_workflow({"prompt": "self test", "seed": 1})\n    assert workflow and seed == 1 and width % 64 == 0 and height % 64 == 0\n    print(json.dumps({"ok": True, "version": APP_VERSION, "workflow": str(client.workflow_path), "width": width, "height": height}))'
    new = '    workflow, seed, width, height, conditioning = client.build_workflow({"prompt": "self test", "seed": 1, "include_identity": False})\n    assert workflow and seed == 1 and width % 64 == 0 and height % 64 == 0\n    assert conditioning["identityApplied"] is False and conditioning["framingApplied"] is False\n    assert all(node not in workflow for node in ("10", "11", "12", "13"))\n    print(json.dumps({"ok": True, "version": APP_VERSION, "workflow": str(client.workflow_path), "width": width, "height": height, "conditioning": conditioning}))'
    if old not in s:
        raise RuntimeError("bridge self-test anchor missing")
    s = s.replace(old, new, 1)
    bridge.write_text(s, encoding="utf-8")

    smoke = ROOT / "tests" / "smoke_test.py"
    s = smoke.read_text(encoding="utf-8")
    s = s.replace('workflow, seed, width, height = client.build_workflow(', 'workflow, seed, width, height, conditioning = client.build_workflow(')
    first_assert = 'assert workflow[identity_loader]["inputs"]["model"] == [style_node, 0]\n'
    if first_assert in s and 'conditioning["identityApplied"] is True' not in s:
        s = s.replace(first_assert, first_assert + 'assert conditioning["identityApplied"] is True\nassert conditioning["framingApplied"] is True\n', 1)
    second_assert = 'assert workflow[positive_node]["inputs"]["clip"] == [style_node, 1]\n'
    if second_assert in s:
        pos = s.find(second_assert, s.find(first_assert) + len(first_assert))
        if pos != -1:
            end = pos + len(second_assert)
            s = s[:end] + 'assert conditioning["identityApplied"] is False\nassert conditioning["framingApplied"] is False\nassert all(node not in workflow for node in ("10", "11", "12", "13"))\n' + s[end:]
    neutral = '''\nneutral_workflow, _, _, _, neutral_conditioning = client.build_workflow({\n    "prompt": "a red tractor crossing a muddy field at sunrise",\n    "include_identity": False,\n})\nassert neutral_conditioning["identityApplied"] is False\nassert neutral_conditioning["framingApplied"] is False\nassert "Venice" not in neutral_conditioning["finalPrompt"]\nassert all(node not in neutral_workflow for node in ("10", "11", "12", "13"))\n\n'''
    marker = 'wrong_token = "0" * max(32, len(token))\n'
    if marker not in s:
        raise RuntimeError("smoke neutral insertion anchor missing")
    if 'neutral_conditioning' not in s:
        s = s.replace(marker, neutral + marker, 1)
    smoke.write_text(s, encoding="utf-8")

    defaults = ROOT / "extension" / "defaults.js"
    s = defaults.read_text(encoding="utf-8")
    if 'autoGenerateSpontaneous: true' not in s:
        raise RuntimeError("extension spontaneous default anchor missing")
    s = s.replace('autoGenerateSpontaneous: true', 'autoGenerateSpontaneous: false', 1)
    defaults.write_text(s, encoding="utf-8")

    content = ROOT / "extension" / "content.js"
    s = content.read_text(encoding="utf-8")
    old = 'const autoEnabled = prefs.autoGenerateSpontaneous ?? true;'
    if old not in s:
        raise RuntimeError("extension auto fallback anchor missing")
    s = s.replace(old, 'const autoEnabled = prefs.autoGenerateSpontaneous ?? false;', 1)
    helper_anchor = 'function hyperbolicPrompt(text) {'
    helper = '''function requestsVeniceIdentity(prompt) {\n  const text = String(prompt || "").replace(/\\s+/g, " ").trim();\n  if (!/\\bVenice\\b/i.test(text)) return false;\n  const city = /\\b(?:city|canals?|gondolas?|lagoon|italy|italian|piazza|san marco|rialto|adriatic|flooded streets?)\\b/i.test(text);\n  const person = /\\b(?:woman|girl|person|character|her|she|herself|face|eyes|hair|wearing|dressed|portrait|selfie|body|standing|sitting|walking|smiling|looking)\\b/i.test(text);\n  return !(city && !person);\n}\n\n'''
    if helper_anchor not in s:
        raise RuntimeError("extension identity helper anchor missing")
    if 'function requestsVeniceIdentity' not in s:
        s = s.replace(helper_anchor, helper + helper_anchor, 1)
    old = 'const response = await chrome.runtime.sendMessage({ action: "generate", prompt: request.prompt, negative_prompt: request.negative_prompt });'
    new = 'const response = await chrome.runtime.sendMessage({ action: "generate", prompt: request.prompt, negative_prompt: request.negative_prompt, includeIdentity: request.include_identity ?? requestsVeniceIdentity(request.prompt) });'
    if old not in s:
        raise RuntimeError("extension generate message anchor missing")
    s = s.replace(old, new, 1)
    old = 'const request = { prompt: hyperbolicPrompt(text), negative_prompt: "low detail, blurry, watermark, text artifacts" };'
    new = 'const request = { prompt: hyperbolicPrompt(text), negative_prompt: "low detail, blurry, watermark, text artifacts", include_identity: true };'
    if old not in s:
        raise RuntimeError("extension spontaneous request anchor missing")
    s = s.replace(old, new, 1)
    content.write_text(s, encoding="utf-8")

    background = ROOT / "extension" / "background.js"
    s = background.read_text(encoding="utf-8")
    old = 'body: JSON.stringify({ prompt: message.prompt, negative_prompt: message.negative_prompt })'
    new = 'body: JSON.stringify({ prompt: message.prompt, negative_prompt: message.negative_prompt, include_identity: message.includeIdentity === true })'
    if old not in s:
        raise RuntimeError("extension bridge body anchor missing")
    s = s.replace(old, new, 1)
    background.write_text(s, encoding="utf-8")

except Exception:
    for p_str, backup_str in backups.items():
        shutil.copy2(backup_str, p_str)
    raise

print(json.dumps({
    "ok": True,
    "backups": backups,
    "hashes": {str(p): {"md5": md5(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in EXPECTED},
}, indent=2))
