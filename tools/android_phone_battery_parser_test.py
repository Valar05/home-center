#!/usr/bin/env python3
import ast
from pathlib import Path

source = Path(__file__).with_name("android_phone_hands_bridge.py").read_text(encoding="utf-8")
module = ast.parse(source)
selected = [node for node in module.body if isinstance(node, (ast.Assign, ast.FunctionDef)) and (
    isinstance(node, ast.FunctionDef) and node.name == "parse_battery_dump" or
    isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id in {"BATTERY_KEYS", "BATTERY_PATTERN"} for target in node.targets)
)]
namespace = {"re": __import__("re")}
exec(compile(ast.Module(body=selected, type_ignores=[]), "battery-parser", "exec"), namespace)
parse = namespace["parse_battery_dump"]
normal = parse("AC powered: false\nUSB powered: true\nWireless powered: false\nstatus: 2\nlevel: 72\ntemperature: 321\n")
assert normal == {"AC powered":"false","USB powered":"true","Wireless powered":"false","status":"2","level":"72","temperature":"321"}
collapsed = parse("AC powered: false  status: 3  level: 72  temperature: 310")
assert collapsed == {"AC powered":"false","status":"3","level":"72","temperature":"310"}
print("Android phone battery parser tests passed")
