#!/data/data/com.termux/files/usr/bin/python3
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "tools" / "agent_scenarios" / "kitchen_agent.jsonl"


def write_temp(directory, name, text):
    path = directory / name
    path.write_text(text or "")
    return path


def compile_bridge(classes):
    subprocess.run([
        "javac", "-d", str(classes),
        str(ROOT / "app/src/main/java/com/dclar/homecenter/ChatSystemShape.java"),
        str(ROOT / "tools/AgentHarnessBridge.java"),
    ], check=True, cwd=ROOT)


def run_bridge(classes, args):
    result = subprocess.run([
        "java", "-cp", str(classes), "com.dclar.homecenter.AgentHarnessBridge", *args,
    ], check=True, cwd=ROOT, text=True, capture_output=True)
    return result.stdout


def scenario_label(scenario, surface):
    failure_class = scenario.get("failure_class", "unclassified")
    return f"{scenario['name']} [{failure_class}] {surface}"


def check_contains(label, text, must, must_not, failures):
    for needle in must or []:
        if needle not in text:
            failures.append(f"{label}: missing {needle!r}")
    for needle in must_not or []:
        if needle in text:
            failures.append(f"{label}: forbidden {needle!r}")


def load_scenarios(path):
    rows = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def main():
    parser = argparse.ArgumentParser(description="Replay deterministic Home Center agent scenarios.")
    parser.add_argument("--scenarios", default=str(SCENARIOS))
    parser.add_argument("--all", action="store_true", help="Run all scenarios; default behavior also runs all.")
    args = parser.parse_args()

    failures = []
    scenarios = load_scenarios(Path(args.scenarios))
    with tempfile.TemporaryDirectory(prefix="home-center-agent-") as tmp:
        tmpdir = Path(tmp)
        classes = tmpdir / "classes"
        classes.mkdir()
        compile_bridge(classes)
        for scenario in scenarios:
            name = scenario["name"]
            latest = write_temp(tmpdir, f"{name}.latest.txt", scenario.get("latest", ""))
            summary = write_temp(tmpdir, f"{name}.summary.txt", scenario.get("summary", ""))
            transcript = write_temp(tmpdir, f"{name}.transcript.txt", scenario.get("transcript", ""))
            model = write_temp(tmpdir, f"{name}.model.txt", scenario.get("model_response", ""))

            prompt = run_bridge(classes, ["prompt", scenario.get("mode", "main"), str(latest), str(summary), str(transcript)])
            shaped = run_bridge(classes, ["shape", str(model), str(latest)])
            managed = run_bridge(classes, ["managed", str(latest), str(transcript)])
            fallback = run_bridge(classes, ["fallback", str(latest)])
            check_contains(scenario_label(scenario, "prompt"), prompt, scenario.get("prompt_must"), scenario.get("prompt_must_not"), failures)
            check_contains(scenario_label(scenario, "response"), shaped, scenario.get("response_must"), scenario.get("response_must_not"), failures)
            check_contains(scenario_label(scenario, "managed context"), managed, scenario.get("managed_must"), scenario.get("managed_must_not"), failures)
            check_contains(scenario_label(scenario, "fallback"), fallback, scenario.get("fallback_must"), scenario.get("fallback_must_not"), failures)

    if failures:
        print("Home Center agent harness failed:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)
    print(f"Home Center agent harness: OK ({len(scenarios)} scenarios)")


if __name__ == "__main__":
    main()
