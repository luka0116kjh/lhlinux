#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Run as root'; exit 1; }
[[ -f /etc/lhlinux-release ]] || { echo 'Bootstrap lhlinux first'; exit 1; }
export DEBIAN_FRONTEND=noninteractive
apt-get install -y --no-install-recommends dbus-user-session libpam-systemd ripgrep
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source "$repo/scripts/lib/install.sh"
cache=/var/cache/lhlinux
mkdir -p "$cache" /opt/lhlinux
r2base=https://github.com/radareorg/radare2/releases/download/6.2.2
fetch "$r2base/radare2_6.2.2_amd64.deb" "$cache/radare2.deb" 09234e4139bf8dfcbb7fc1fdb2519859ad516e63c19d3c27d92aaecdf463b1ad
fetch "$r2base/radare2-dev_6.2.2_amd64.deb" "$cache/radare2-dev.deb" cbc9278e90fde572df7dd721f22056515c8c28f63c2d0c6d44ab321b5f4e6f43
apt-get install -y "$cache/radare2.deb" "$cache/radare2-dev.deb"
r2ai_commit=9f9a3b87ae3318e63fe415ede1d2afe5d17688c0
if [[ ! -d /opt/lhlinux/r2ai/.git ]]; then
  git init /opt/lhlinux/r2ai
  git -C /opt/lhlinux/r2ai remote add origin https://github.com/radareorg/r2ai.git
fi
git -C /opt/lhlinux/r2ai fetch --depth 1 origin "$r2ai_commit"
git -C /opt/lhlinux/r2ai checkout --detach "$r2ai_commit"
make -C /opt/lhlinux/r2ai -j2
install -Dm755 /opt/lhlinux/r2ai/src/r2ai.so "$(r2 -NNH R2_LIBR_PLUGINS)/r2ai.so"
install -Dm755 /opt/lhlinux/r2ai/src/r2ai /usr/local/bin/r2ai
fetch https://github.com/ollama/ollama/releases/download/v0.33.3/ollama-linux-amd64.tar.zst \
  "$cache/ollama-linux-amd64.tar.zst" c13cea8f3389db4145f8a6cb88d1747242a48639d7c13e3bda7c1ebdc6eebb2f
if [[ ! -f /opt/lhlinux/ollama-0.33.3.installed ]]; then
  tar --zstd -xf "$cache/ollama-linux-amd64.tar.zst" -C /usr
  touch /opt/lhlinux/ollama-0.33.3.installed
fi
id ollama &>/dev/null || useradd -r -s /usr/sbin/nologin -U -m -d /usr/share/ollama ollama
cat > /etc/systemd/system/ollama.service <<'EOF'
[Unit]
Description=lhlinux local Ollama
After=network-online.target
[Service]
ExecStart=/usr/bin/ollama serve
User=ollama
Group=ollama
Restart=on-failure
RestartSec=3
Environment=OLLAMA_HOST=127.0.0.1:11434
Environment=OLLAMA_NUM_PARALLEL=1
Environment=OLLAMA_MAX_LOADED_MODELS=1
Environment=OLLAMA_CONTEXT_LENGTH=2048
Environment=OLLAMA_KEEP_ALIVE=2m
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now docker ollama
ready=0
for attempt in {1..30}; do
  if curl -fsS http://127.0.0.1:11434/api/tags >/dev/null; then ready=1; break; fi
  sleep 1
done
[[ $ready == 1 ]] || { echo 'Ollama did not start'; exit 1; }
ollama pull qwen2.5-coder:0.5b
install -d -o admin -g admin /home/admin/lab /home/admin/lab/{samples,solvers,results} /home/admin/.config /home/admin/.config/r2ai
if [[ ! -f /home/admin/.config/r2ai/rc ]]; then
  cat > /home/admin/.config/r2ai/rc <<'EOF'
r2ai -e api=ollama
r2ai -e model=qwen2.5-coder:0.5b
r2ai -e baseurl=http://127.0.0.1:11434/api
r2ai -e max_tokens=512
EOF
  chown admin:admin /home/admin/.config/r2ai/rc
fi
runuser -u admin -- python3 -m venv --system-site-packages /home/admin/lab/.venv
install_example "$repo/examples/solver.py" /home/admin/lab/solvers/solver.py admin admin
install_example "$repo/examples/hello.c" /home/admin/lab/samples/hello.c admin admin
install -m755 "$repo/scripts/lhlinux-help" /usr/local/bin/lhlinux-help
install -m755 "$repo/scripts/lhlinux-check" /usr/local/bin/lhlinux-check
install -m755 "$repo/scripts/lhlinux" /usr/local/bin/lhlinux
install -m755 "$repo/scripts/lhlinux-nes-python" /usr/local/bin/lhlinux-nes-python
install -Dm644 "$repo/scripts/lib/ai.sh" /usr/local/lib/lhlinux/ai.sh
install -Dm644 "$repo/scripts/lib/context.py" /usr/local/lib/lhlinux/context.py
install -Dm644 "$repo/scripts/lib/workspace.py" /usr/local/lib/lhlinux/workspace.py
install -Dm644 "$repo/scripts/lib/run.py" /usr/local/lib/lhlinux/run.py
if ! grep -q '# lhlinux shell' /home/admin/.bashrc; then
  cat >> /home/admin/.bashrc <<'EOF'

# lhlinux shell
export PS1='\[\e[1;36m\]\u@lhlinux\[\e[0m\]:\w\$ '
alias lab='cd ~/lab'
alias workon='source ~/lab/.venv/bin/activate'
EOF
fi
dpkg-query -W > /opt/lhlinux/packages.tsv
printf '%s\n' "$r2ai_commit" > /opt/lhlinux/r2ai-commit.txt
apt-get clean
