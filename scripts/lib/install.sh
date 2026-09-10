#!/usr/bin/env bash
# Installation helpers; sourcing this file does not change the system.

fetch() {
  local url=$1 target=$2 hash=$3
  if [[ ! -f $target ]] || ! printf '%s  %s\n' "$hash" "$target" | sha256sum -c --status; then
    curl -fL --retry 3 -o "$target.part" "$url" || return
    printf '%s  %s\n' "$hash" "$target.part" | sha256sum -c - || return
    mv -- "$target.part" "$target" || return
  fi
}

install_example() {
  local source=$1 target=$2 owner=$3 group=$4
  # Examples become user work after installation, including dangling symlinks.
  [[ ! -e $target && ! -L $target ]] || return 0
  install -o "$owner" -g "$group" -m644 -- "$source" "$target"
}
