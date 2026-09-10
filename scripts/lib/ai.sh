#!/usr/bin/env bash
# Sourced by lhlinux: reuse executable_path, find_r2ai_plugin and plain printf output.
ai_providers=(codex claude local r2ai)
declare -gA ai_names=([codex]=codex [claude]=claude [local]=ollama [r2ai]=r2ai)
declare -gA ai_paths=() ai_versions=() ai_version_ok=() ai_daemons=() ai_kinds=()
declare -gA ai_execution=()
declare -gA ai_install_urls=(
  [codex]='https://developers.openai.com/codex/cli/'
  [claude]='https://code.claude.com/docs/en/setup'
  [local]='https://docs.ollama.com/linux'
  [r2ai]='https://github.com/radareorg/r2ai'
)
ai_radare=''

ai_log() { printf '[lhlinux] %s\n' "$*" >&2; }

ai_plain_version() {
  local value=${1%%$'\n'*} ansi=$'\e''\[[0-?]*[ -/]*[@-~]'
  while [[ $value =~ $ansi ]]; do value=${value/"${BASH_REMATCH[0]}"/}; done
  value=${value//$'\r'/}
  value=${value//$'\e'/}
  printf '%s' "$value"
}

ai_probe() {
  local limiter
  limiter=$(executable_path timeout) || return 1
  # Drain excess output so head does not turn a successful probe into SIGPIPE.
  "$limiter" -k 1s 3s "$@" </dev/null 2>/dev/null | { head -c 4096; cat >/dev/null; }
}

ai_detect() {
  local provider path version code
  for provider in "${ai_providers[@]}"; do
    ai_versions[$provider]=unknown
    ai_version_ok[$provider]=false
    ai_daemons[$provider]=not_applicable
    ai_execution[$provider]=not_installed
    if path=$(executable_path "${ai_names[$provider]}"); then
      ai_paths[$provider]=$path
      ai_kinds[$provider]=executable
      ai_execution[$provider]=unverified
      if version=$(ai_probe "$path" --version); then
        ai_execution[$provider]=runnable
        if [[ $version =~ [0-9]+\.[0-9]+ ]]; then
          ai_versions[$provider]=$(ai_plain_version "$version")
          ai_version_ok[$provider]=true
        fi
      else
        code=$?
        if [[ $code == 126 || $code == 127 ]]; then ai_execution[$provider]=unavailable; fi
      fi
      if [[ $provider == local ]]; then
        ai_daemons[$provider]=unreachable
        if ai_probe "$path" list >/dev/null; then ai_daemons[$provider]=reachable; fi
      fi
    fi
  done
  ai_radare=$(executable_path radare2 || executable_path r2) || ai_radare=''
  if [[ -n $ai_radare ]] && find_r2ai_plugin "$ai_radare"; then
    if [[ -z ${ai_paths[r2ai]:-} ]]; then
      ai_paths[r2ai]=${paths[r2ai]}
      ai_kinds[r2ai]=plugin
      ai_execution[r2ai]=runnable
      ai_versions[r2ai]=${plugin_versions[r2ai]:-unknown}
    fi
  fi
}

ai_ready() {
  [[ -n ${ai_paths[$1]:-} ]] || return 1
  [[ ${ai_execution[$1]} != unavailable ]] || return 1
  [[ $1 != r2ai || ( -n $ai_radare && ${kinds[r2ai]:-} == plugin ) ]] || return 1
  [[ $1 != local || ${ai_daemons[local]} == reachable ]]
}

# All provider arguments are arrays. The generated prompt is ONLY supplied on stdin.
ai_adapter() {
  local provider=$1 model=${2:-}
  case "$provider" in
    codex) ai_argv=("${ai_paths[codex]}" exec --sandbox read-only --skip-git-repo-check
      --ephemeral -c features.shell_tool=false -c features.unified_exec=false
      -c 'web_search="disabled"' -) ;;
    claude) ai_argv=("${ai_paths[claude]}" --print --output-format text --tools ''
      --strict-mcp-config --mcp-config '{"mcpServers":{}}' --no-session-persistence) ;;
    local) ai_argv=("${ai_paths[local]}" run "$model" --nowordwrap) ;;
    r2ai)
      [[ -n $ai_radare && ${kinds[r2ai]:-} == plugin ]] || {
        ai_log 'r2ai stdin delivery requires its loadable radare2 plugin. Standalone REPL input is not supported.'
        return 2
      }
      ai_argv=("$ai_radare" -N -q -e scr.color=0 -c 'r2ai -i /dev/stdin' --) ;;
  esac
}

ai_command() {
  local action=${1:-} json=false provider mark status any=false parser command
  if [[ -z $action || $action == --help || $action == -h ]]; then
    printf 'Usage: lhlinux ai {check|providers} [--json] [--no-color]\n'
    printf 'Providers: codex, claude, local (= ollama), r2ai\n'
    return 0
  fi
  shift
  [[ $action == check || $action == providers ]] || { ai_log 'Unknown ai command'; return 2; }
  while [[ $# -gt 0 ]]; do
    case "$1" in --json) json=true ;; --no-color) : ;; *) ai_log 'Unknown ai option'; return 2 ;; esac
    shift
  done
  ai_detect
  if [[ $json == true ]]; then
    parser=$(executable_path python3) || { ai_log '--json requires python3'; return 2; }
    local rows=()
    for provider in "${ai_providers[@]}"; do
      status=false
      if ai_ready "$provider"; then status=true; any=true; fi
      command=$(ai_command_description "$provider")
      rows+=("$provider" "${ai_names[$provider]}" "${ai_paths[$provider]:-}" "${ai_versions[$provider]}"
        "${ai_version_ok[$provider]}" "${ai_daemons[$provider]}" "$status" "$command" "${ai_execution[$provider]}")
    done
    "$parser" "$LH_LIB_DIR/context.py" providers-json "${rows[@]}"
  else
    if [[ $action == check ]]; then printf '[lhlinux] AI CLI Check\n\n'; else printf '[lhlinux] AI Providers\n\n'; fi
    for provider in "${ai_providers[@]}"; do
      mark='✗'; status='Not installed'
      if [[ -n ${ai_paths[$provider]:-} ]]; then
        mark='✓'; status=${ai_paths[$provider]}
        status+=" (version: ${ai_versions[$provider]})"
        [[ ${ai_execution[$provider]} != unavailable ]] || status+=' [execution: unavailable]'
        [[ $provider != local ]] || status+=" [daemon: ${ai_daemons[$provider]}]"
        [[ ${ai_kinds[$provider]} != plugin ]] || status+=' [radare2 plugin]'
        [[ $provider != r2ai || ${kinds[r2ai]:-} == plugin ]] || status+=' [radare2 plugin required]'
      fi
      if ai_ready "$provider"; then any=true; fi
      printf '[%s] %-12s %s\n' "$mark" "${ai_names[$provider]}" "$status"
      if [[ $action == providers ]]; then
        printf '    provider: %-7s command: %s\n' "$provider" "$(ai_command_description "$provider")"
      fi
    done
  fi
  [[ $any == true ]]
}

ai_command_description() {
  case "$1" in
    codex) printf 'codex exec --sandbox read-only --skip-git-repo-check --ephemeral -c features.shell_tool=false -c features.unified_exec=false -c web_search="disabled" -' ;;
    claude) printf 'claude --print --output-format text --tools "" --strict-mcp-config --mcp-config {"mcpServers":{}} --no-session-persistence' ;;
    local) printf 'ollama run <MODEL> --nowordwrap' ;;
    r2ai) printf 'radare2 -N -q -e scr.color=0 -c "r2ai -i /dev/stdin" -- (plugin required)' ;;
  esac
}

reversing_ask() (
  local provider='' target='' question='' dry=false model='' max_bytes=122880 strings_limit=300 disasm_limit=32768 duration=300
  local argument parser temporary limiter result=0
  local positional=() ai_argv=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --help|-h) reversing_usage; return 0 ;;
      --dry-run) dry=true; shift ;;
      --no-color) shift ;;
      --) shift; question="$*"; break ;;
      --max-bytes|--strings-limit|--disasm-limit|--timeout|--model)
        [[ $# -ge 2 && -n $2 ]] || { ai_log 'Missing option value'; return 2; }
        argument=$1
        if [[ $argument != --model && ! $2 =~ ^[0-9]+$ ]]; then ai_log 'Limits must be positive integers'; return 2; fi
        case "$argument" in
          --max-bytes) max_bytes=$2 ;; --strings-limit) strings_limit=$2 ;;
          --disasm-limit) disasm_limit=$2 ;; --timeout) duration=$2 ;; --model) model=$2 ;;
        esac
        shift 2 ;;
      --*) ai_log 'Unknown ask option'; return 2 ;;
      *) positional+=("$1"); shift ;;
    esac
  done
  case ${#positional[@]} in
    1) target=${positional[0]} ;;
    2) provider=${positional[0]}; target=${positional[1]} ;;
    *) reversing_usage >&2; return 2 ;;
  esac
  case "$provider" in ''|codex|claude|local|r2ai) ;; *) ai_log 'Unknown provider (codex, claude, local, r2ai)'; return 2 ;; esac
  [[ -f $target && -r $target ]] || { ai_log 'Target must be an existing, readable regular file'; return 1; }
  parser=$(executable_path python3) || { ai_log 'Context collection requires python3'; return 2; }
  # Private storage also makes /dev/stdin seekable for the R2AI plugin adapter.
  umask 077
  temporary=$(mktemp -d) || return 1
  trap 'rm -rf -- "$temporary"' EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  "$parser" "$LH_LIB_DIR/context.py" build "$target" "$max_bytes" "$strings_limit" "$disasm_limit" "$duration" "$question" > "$temporary/prompt" || return $?
  if [[ $dry == true ]]; then cat -- "$temporary/prompt"; return 0; fi
  ai_detect
  if [[ -z $provider ]]; then
    for argument in codex claude local; do
      if ai_ready "$argument"; then provider=$argument; break; fi
    done
    [[ -n $provider ]] || { ai_log "No automatic provider (codex/claude/local). Install: ${ai_install_urls[codex]}"; return 2; }
    ai_log "Selected provider: $provider"
  fi
  [[ -n ${ai_paths[$provider]:-} ]] || { ai_log "Provider not installed. Install: ${ai_install_urls[$provider]}"; return 2; }
  if [[ $provider == local && -z $model ]]; then ai_log 'Ollama requires --model MODEL; choose an installed model with ollama list.'; return 2; fi
  if [[ $provider == local && ( $model == -* || $model =~ [[:space:]] ) ]]; then ai_log 'Use a model name, not a CLI option or whitespace-separated arguments.'; return 2; fi
  if [[ $provider != local && -n $model ]]; then ai_log '--model is only for local; configure other models in their own CLI.'; return 2; fi
  ai_adapter "$provider" "$model" || return $?
  limiter=$(executable_path timeout) || { ai_log 'Provider execution requires coreutils timeout'; return 2; }
  # Do not capture/filter provider stdout or stderr, or inject authentication variables.
  "$limiter" -k 2s "${duration}s" "${ai_argv[@]}" < "$temporary/prompt" || result=$?
  return "$result"
)
