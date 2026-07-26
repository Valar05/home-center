#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
output_dir=$(mktemp -d)
trap 'rm -rf "$output_dir"' EXIT INT TERM

javac -d "$output_dir" \
  "$repo_root/app/src/main/java/com/dclar/homecenter/VoiceScriptPlanner.java" \
  "$repo_root/tools/java/com/dclar/homecenter/VoiceScriptPlannerTest.java"
java -cp "$output_dir" com.dclar.homecenter.VoiceScriptPlannerTest
