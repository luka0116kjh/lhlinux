#!/usr/bin/env bash
# Optional pinned Python environment; never replace Ubuntu's Python or ~/lab/.venv.
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
profile=$repo/environments/nes-py-9.0.1
base=$HOME/.local/share/lhlinux
uv_env=$base/tools/uv-0.12.13
uv=$uv_env/bin/uv
environment=$base/envs/nes-py-9.0.1
mode=${1:-setup}
[[ $# -le 1 && ( $mode == setup || $mode == --check ) ]] || {
  printf 'Usage: bash scripts/setup-nes-env.sh [--check]\n' >&2; exit 2;
}
[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] || {
  printf 'This lock targets Linux x86-64.\n' >&2; exit 2;
}
version=$(cat "$profile/.python-version")
export UV_PYTHON_INSTALL_DIR=$base/python UV_PYTHON_BIN_DIR=$base/python-bin

owned() {
  [[ ! -L $1 && -f $1/.lhlinux-managed && ! -L $1/.lhlinux-managed && $(cat "$1/.lhlinux-managed") == "$2" ]]
}

verify() {
  "$environment/bin/python" -I "$profile/check.py" "$profile/requirements.lock" "$version"
  "$uv" --no-config pip check --python "$environment/bin/python"
}

if [[ $mode == --check ]]; then
  owned "$environment" lhlinux-nes-v1 || { printf 'Managed NES environment is not installed.\n' >&2; exit 1; }
  verify
  exit
fi

umask 077
mkdir -p "$base"
exec 9> "$base/setup-nes.lock"
flock -n 9 || { printf 'Another NES environment setup is running.\n' >&2; exit 1; }
for item in "$uv_env" "$environment"; do
  label=lhlinux-nes-v1
  [[ $item != "$uv_env" ]] || label=lhlinux-uv-v1
  if [[ -e $item || -L $item ]]; then
    owned "$item" "$label" || { printf 'Refusing to modify unmanaged environment: %s\n' "$item" >&2; exit 1; }
  else
    mkdir -p "$item"
    printf '%s\n' "$label" > "$item/.lhlinux-managed"
  fi
done

uv_version=''
[[ ! -x $uv ]] || uv_version=$("$uv" --version)
if [[ $uv_version != 'uv 0.12.13' && $uv_version != 'uv 0.12.13 ('* ]]; then
  python3 -m venv "$uv_env"
  "$uv_env/bin/python" -m pip --isolated install --disable-pip-version-check \
    --index-url https://pypi.org/simple --only-binary=:all: --require-hashes \
    -r "$repo/environments/uv-requirements.lock"
fi

# Reuse the environment without downloads when the manifest and health checks match.
digest=$(sha256sum "$profile/requirements.lock" | cut -d ' ' -f 1)
if [[ -f $environment/.lhlinux-lock && $(cat "$environment/.lhlinux-lock") == "$digest" ]]; then
  if verify; then
    printf 'Ready (reused): %s/bin/python\n' "$environment"
    exit
  fi
  printf 'Existing managed environment needs repair.\n' >&2
fi

"$uv" --no-config python install "$version"
if [[ ! -x $environment/bin/python ]]; then
  "$uv" --no-config venv --allow-existing --python "$version" "$environment"
fi
actual=$("$environment/bin/python" -I -c 'import platform; print(platform.python_version())')
[[ $actual == "$version" ]] || {
  printf 'Existing interpreter is %s; expected %s. Preserving it.\n' "$actual" "$version" >&2; exit 1;
}
"$uv" --no-config pip sync --python "$environment/bin/python" \
  --index-url https://pypi.org/simple --only-binary=:all: --require-hashes "$profile/requirements.lock"
verify
printf '%s\n' "$digest" > "$environment/.lhlinux-lock"
printf 'Ready: %s/bin/python\n' "$environment"
printf 'Package versions/imports checked; challenge-server core equivalence remains unverified.\n'
