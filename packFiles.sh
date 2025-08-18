#!/bin/bash
# Usage: ./packFiles.sh file1 file2 ...
# Collect files into files.txt with filename headers and test outputs

OUTPUT="files.txt"
> "$OUTPUT"

for file in "$@"; do
  if [ -f "$file" ]; then
    realfile="$file"
  elif [ -f "app/$file" ]; then
    realfile="app/$file"
  else
    echo "$file:" >> "$OUTPUT"
    echo "[ERROR] File not found: $file" >> "$OUTPUT"
    echo >> "$OUTPUT"
    continue
  fi

  echo "$file:" >> "$OUTPUT"
  cat "$realfile" >> "$OUTPUT"
  echo >> "$OUTPUT"
done

echo >> "$OUTPUT"
echo "=== PYTHON TEST OUTPUT ===" >> "$OUTPUT"
echo "cmd: venv/bin/pytest -q" >> "$OUTPUT"
venv/bin/pytest -q >> "$OUTPUT" 2>&1

echo >> "$OUTPUT"
echo "=== NODE TEST OUTPUT (app/) ===" >> "$OUTPUT"
echo "cmd: (cd app && )npm test --silent -- --watchAll=false | cat" >> "$OUTPUT"
(cd app && npm test --silent -- --watchAll=false | cat) >> "$OUTPUT" 2>&1

echo "Packed $# file(s) and test outputs into $OUTPUT"
