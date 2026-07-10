#!/usr/bin/env python3
"""Live acceptance check for Home Drive Bridge workbook_import_xlsx.

This mutates Drive by creating a converted native Google Sheet through the MCP
bridge. It uses Python stdlib only for source .xlsx inspection.
"""
import argparse
import base64
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
import zipfile
import xml.etree.ElementTree as ET

NS_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NS_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
NS_PACKAGE_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
DEFAULT_MCP_URL = "https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/mcp"
EXPECTED_LEXEN_TABS = [
    "README", "CANON", "HISTORICAL_RAILS", "FACTORS", "STATE", "CASES",
    "ACTIONS", "CONTROL", "ENGINE", "TRACE", "SOURCES",
]


def parse_workbook(path):
    with zipfile.ZipFile(path) as zf:
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rel_by_id = {rel.attrib.get("Id"): rel.attrib.get("Target", "") for rel in rels.findall(f"{NS_PACKAGE_REL}Relationship")}
        sheets = []
        for sheet in workbook.findall(f"{NS_MAIN}sheets/{NS_MAIN}sheet"):
            name = sheet.attrib.get("name", "")
            rel_id = sheet.attrib.get(f"{NS_REL}id", "")
            target = rel_by_id.get(rel_id, "")
            sheet_path = target.lstrip("/") if target.startswith("/") else (target if target.startswith("xl/") else "xl/" + target.lstrip("/"))
            sheets.append({"name": name, "path": sheet_path, "populatedCells": count_populated_cells(zf, sheet_path)})
        return sheets


def count_populated_cells(zf, sheet_path):
    if sheet_path not in zf.namelist():
        return 0
    root = ET.fromstring(zf.read(sheet_path))
    count = 0
    for cell in root.findall(f".//{NS_MAIN}c"):
        if cell.find(f"{NS_MAIN}f") is not None or cell.find(f"{NS_MAIN}v") is not None or cell.find(f"{NS_MAIN}is") is not None:
            count += 1
    return count


def bearer_token(config_path=""):
    env_token = os.environ.get("HOME_CENTER_MCP_BEARER_TOKEN", "").strip()
    if env_token:
        return env_token
    if config_path and os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        for key in ("homeCenterBearerToken", "bearerToken", "accessToken", "token"):
            value = str(config.get(key, "")).strip()
            if value:
                return value
    proc = subprocess.run(["gcloud", "auth", "print-access-token"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    if proc.returncode != 0:
        raise RuntimeError("gcloud auth print-access-token failed: " + proc.stderr.strip())
    token = proc.stdout.strip()
    if not token:
        raise RuntimeError("gcloud returned an empty access token")
    return token


def parse_mcp_response(text):
    if text.lstrip().startswith("{"):
        return json.loads(text)
    chunks = [line[5:].strip() for line in text.splitlines() if line.startswith("data:")]
    if not chunks:
        raise RuntimeError("MCP response was not JSON or SSE JSON: " + text[:500])
    return json.loads("\n".join(chunks))


def fetch_json(url, payload, token):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "authorization": "Bearer " + token,
        "content-type": "application/json",
        "accept": "application/json, text/event-stream",
    })
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return parse_mcp_response(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as err:
        text = err.read().decode("utf-8", "replace")
        raise RuntimeError(f"MCP HTTP {err.code}: {text[:1200]}")


def tool_result_payload(response):
    if "error" in response:
        raise RuntimeError("MCP error: " + json.dumps(response["error"], indent=2))
    content = response.get("result", {}).get("content", [])
    if not content:
        raise RuntimeError("MCP response had no tool content: " + json.dumps(response)[:500])
    text = content[0].get("text", "")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Tool returned non-JSON text: " + text[:1000]) from exc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", nargs="?", default="/storage/emulated/0/Download/Lexen_Vigil_Judgment_Engine.xlsx")
    parser.add_argument("--mcp-url", default=DEFAULT_MCP_URL)
    parser.add_argument("--parent-folder-id", default="")
    parser.add_argument("--source-file-id", default="", help="Existing Drive .xlsx file ID. When supplied, no base64 upload is sent.")
    parser.add_argument("--source-file-name", default="", help="Existing Drive .xlsx filename to resolve. When supplied, no base64 upload is sent.")
    parser.add_argument("--source-folder-id", default="", help="Drive folder to search for --source-file-name.")
    parser.add_argument("--title", default="Lexen Vigil Judgment Engine")
    parser.add_argument("--request-id", default="workbook-import-lexen-" + time.strftime("%Y%m%d%H%M%S"))
    parser.add_argument("--token-config", default=os.path.expanduser("~/.config/home-center/codex-hub.json"), help="Optional local config containing a Home Center MCP bearer token. Env HOME_CENTER_MCP_BEARER_TOKEN wins.")
    args = parser.parse_args()

    if not os.path.exists(args.workbook):
        raise SystemExit("Workbook not found: " + args.workbook)
    sheets = parse_workbook(args.workbook)
    names = [sheet["name"] for sheet in sheets]
    counts = {sheet["name"]: sheet["populatedCells"] for sheet in sheets}
    missing_expected = [name for name in EXPECTED_LEXEN_TABS if name not in names]
    if missing_expected:
        raise SystemExit("Source workbook is missing expected tabs: " + ", ".join(missing_expected))

    arguments = {
        "fileName": os.path.basename(args.workbook),
        "title": args.title,
        "expectedSheetNames": names,
        "expectedPopulatedCellCounts": counts,
        "requestId": args.request_id,
        "callerNote": "Live acceptance import of Lexen_Vigil_Judgment_Engine.xlsx",
    }
    if args.source_file_id:
        arguments["sourceFileId"] = args.source_file_id
    elif args.source_file_name:
        arguments["sourceFileName"] = args.source_file_name
        if args.source_folder_id:
            arguments["sourceFolderId"] = args.source_folder_id
    else:
        with open(args.workbook, "rb") as f:
            arguments["workbookBase64"] = base64.b64encode(f.read()).decode("ascii")
    if args.parent_folder_id:
        arguments["parentFolderId"] = args.parent_folder_id
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "workbook_import_xlsx", "arguments": arguments}}
    result = tool_result_payload(fetch_json(args.mcp_url, payload, bearer_token(args.token_config)))
    destination_names = result.get("sheetNames", [])
    missing_destination = [name for name in EXPECTED_LEXEN_TABS if name not in destination_names]
    diffs = result.get("populatedCellCountDiffs", [])
    changed = [diff for diff in diffs if diff.get("difference") not in (0, None) or diff.get("status") != "matched"]
    report = {
        "ok": not missing_destination and not changed,
        "spreadsheetId": result.get("spreadsheetId", ""),
        "sourceSheetNames": names,
        "destinationSheetNames": destination_names,
        "missingDestinationTabs": missing_destination,
        "populatedCellCountDiffs": diffs,
        "warnings": result.get("warnings", []),
        "auditRequestId": result.get("auditRequestId", args.request_id),
    }
    print(json.dumps(report, indent=2))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
