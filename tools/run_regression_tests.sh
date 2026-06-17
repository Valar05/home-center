#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

sh tools/check_no_secrets.sh
python3 tools/home_center_regression_tests.py

tmp="${TMPDIR:-/tmp}/home-center-regression-$$"
rm -rf "$tmp"
mkdir -p "$tmp/classes"

javac -d "$tmp/classes" \
  app/src/main/java/com/dclar/homecenter/Command.java \
  app/src/main/java/com/dclar/homecenter/CommandParser.java \
  tools/CommandParserHarness.java
java -cp "$tmp/classes" com.dclar.homecenter.CommandParserHarness
rm -rf "$tmp"

echo "Home Center regression harness: OK"
