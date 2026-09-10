#!/usr/bin/env bash
set -euo pipefail
lhlinux-check
[[ $(id -un) == admin ]]
[[ $(hostname) == lhlinux ]]
docker run --rm hello-world
gcc -g -O0 "$HOME/lab/samples/hello.c" -o "$HOME/lab/results/hello"
"$HOME/lab/results/hello" | grep -F 'Hello from lhlinux'
strings "$HOME/lab/results/hello" | grep -F 'Hello from lhlinux'
readelf -h "$HOME/lab/results/hello" | grep ELF64
objdump -d "$HOME/lab/results/hello" | grep '<main>:'
gdb -batch -ex 'break main' -ex run -ex 'print 7+3' "$HOME/lab/results/hello" | grep '= 10'
r2 -q -c 'aaa; afl' "$HOME/lab/results/hello" 2>/dev/null | grep main
curl -fsS --max-time 180 http://127.0.0.1:11434/api/generate \
  -d '{"model":"qwen2.5-coder:0.5b","prompt":"What is 2 + 2? Answer briefly.","stream":false,"options":{"num_predict":32}}' \
  | jq -e '.done == true and (.response | length > 0)'
timeout 180 r2 -q -c 'r2ai What is 2 plus 2? Reply briefly.' -- > "$HOME/lab/results/r2ai-smoke.txt" 2>&1
cat "$HOME/lab/results/r2ai-smoke.txt"
echo 'Functional smoke tests completed; inspect the R2AI reply above.'
