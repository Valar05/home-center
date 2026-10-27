#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/home-center-sentence-chunker.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT HUP INT TERM
javac -d "$TMP_ROOT" \
  "$ROOT/app/src/main/java/com/dclar/homecenter/MarkdownSentenceChunker.java" \
  "$ROOT/tools/java/com/dclar/homecenter/MarkdownSentenceChunkerTest.java"
java -cp "$TMP_ROOT" com.dclar.homecenter.MarkdownSentenceChunkerTest
