# lhlinux 0.1

[한국어](README.md) | English

![lhlinux logo](docs/assets/lhlinux-logo.png)

An open-source WSL2 CLI distribution project based on Ubuntu 24.04 LTS that anyone can install and improve. It sets up Docker, Z3, binary analysis tools, and local AI through scripts that can be rerun to restore the configuration. The default user is `admin`.

Currently, only **x86-64 WSL2** on Windows is supported. ARM64, bare-metal PC installation, bootable VM images, and installation ISOs are not yet supported.

## Installation

WSL2 must already be installed on Windows. Check with `wsl --list --verbose` in PowerShell. An internet connection and at least 10 GB of free disk space are recommended. The current validation environment has approximately 4 GB of WSL memory.

Download this repository, then run the following from the repository directory:

```powershell
./scripts/New-Lhlinux.ps1
```

The default installation location is `%LOCALAPPDATA%\lhlinux\WSL\lhlinux`. To install on D: or another drive:

```powershell
./scripts/New-Lhlinux.ps1 -InstallRoot D:\WSL
```

During installation, **enter your own password for the admin account**. No shared default password is provided or stored in the source. `sudo` requires this password. WSL itself starts with your Windows user permissions, so it does not ask for a Linux login password every time. The admin account also belongs to the docker group to use Docker.

## Getting Started

In PowerShell:

```powershell
wsl -d lhlinux --cd ~
```

In the lhlinux terminal:

```bash
lhlinux-help
lab
workon
python3 solvers/solver.py
docker run --rm hello-world
ollama run qwen2.5-coder:0.5b
```

`workon` activates `~/lab/.venv`. Install additional Python packages in this environment with `pip install package-name`. Run `deactivate` to leave it.

### Checking Reverse Engineering Tools

```bash
lhlinux reversing check
lhlinux reversing list
lhlinux reversing missing
lhlinux reversing versions
```

`check` prints executable paths and installation counts for strings, readelf, objdump, gdb, radare2, r2ai, and python3. It also recognizes radare2 as `r2` and resolves symbolic links to their actual file paths. If no R2AI executable is found, it checks the path in the metadata of plugins loaded by radare2 and labels the result `(radare2 plugin)`. Without jq, it checks loaded plugin names and standard user and system plugin paths. Plugins loaded manually only through user startup scripts are not included in this check.

`list` prints only the names of the tools being checked, `missing` prints only missing tools, and `versions` shows paths and the first line of each version response. If a version lookup fails, it displays `Version unavailable`. Plugin and version queries each have a five-second timeout and do not send requests to an AI server. The checks require Bash and coreutils; when jq is available, they use exact plugin metadata.

Exit codes are `0` when all tools are installed, `1` when any are missing, and `2` for invalid command usage. `list` always returns `0`. The existing `lhlinux-check` command (full environment check) and `lhlinux-help` remain available.

### AI CLI Integration

```bash
lhlinux ai check
lhlinux ai check --json
lhlinux ai providers
lhlinux reversing ask codex ./chall
lhlinux reversing ask claude ./chall -- "Estimate the libc version"
lhlinux reversing ask ./chall --dry-run
lhlinux reversing ask local ./chall --model qwen2.5-coder:0.5b
lhlinux reversing ask r2ai ./chall
```

`ai check` checks PATH and execution permissions. Version detection runs `--version` with a maximum of three seconds. If it fails or the version cannot be determined, the installation status is preserved and the version is shown as `unknown`. Executable or runtime errors (126/127) are reported as `execution: unavailable` and excluded from automatic selection. Authentication success and billing status are not checked. Ollama installation status and daemon responsiveness (`reachable`/`unreachable`) are reported separately. Installations with only an R2AI plugin are also detected.

`ai providers` shows each provider's name, status, detected path, and command used to pass input through stdin. Both commands support `--json`. In JSON output, `installed` indicates whether the provider was found, and `available` indicates whether it is a candidate for execution; neither guarantees authentication or successful inference. If an R2AI executable exists but no loadable radare2 plugin is present, the result is `installed: true`, `available: false`, with `radare2 plugin required` in text output. A failed version check alone does not mark an installation as missing. The CLI's own output remains uncolored, so `NO_COLOR` and `--no-color` produce the same format.

`ask` accepts only readable regular files and does not execute the target file. It collects the filename, size, SHA256, and output from `file`, `strings -n 6`, and, for ELF files, `readelf -h -S -d` and `objdump -d` focused on key functions (main/_start), into Markdown. If key function symbols cannot be found, it uses a limited initial portion of the disassembly. If a tool is missing or does not finish within ten seconds, a warning is written to stderr and that section is omitted. Hash calculation also has a ten-second timeout, and transmission is aborted if the file changes during analysis. This repository does not currently implement `reversing scan`/`analyze`, so there are no existing results to reuse.

The prompt requests explanations of static behavior, function roles, and libraries, along with items to verify manually. It does not request automated vulnerability discovery or attack execution. Binary strings are identified as untrusted data. Additional questions after `--` are appended at the bottom. These instructions do not guarantee the accuracy of the model's response, so review the results yourself.

| Option | Default / Behavior |
| --- | --- |
| `--dry-run` | Prints only the prompt to stdout without running or detecting providers |
| `--max-bytes N` | Maximum total UTF-8 prompt size: 122880 bytes (120 KiB); range: 1024–10485760 |
| `--strings-limit N` | Maximum strings output: 300 lines; range: 1–1000000 |
| `--disasm-limit N` | Maximum disassembly size: 32768 bytes; range: 64–10485760 |
| `--timeout SECONDS` | Maximum provider runtime: 300 seconds; range: 1–86400 |
| `--model MODEL` | Passed unchanged as the required model argument for `local`; using it with another provider is an error |
| `--no-color` | Keeps output uncolored |
| `--json` | JSON output for `ai check` / `ai providers` |

Space is allocated to each section within the overall limit, and truncated content is marked with `[truncated]`. A small overall limit may take effect before individual section limits. If even the metadata cannot fit, the command exits with an error.

If no provider is specified, selection proceeds in the order codex → claude → local, with a one-line notice on stderr. Ollama is selected automatically only if its daemon responds. Because the Ollama CLI requires a model argument, you must specify one with `--model`. Use `ollama list` to see installed models. lhlinux does not automatically select or download models. `--dry-run` requires neither a model nor an installed provider.

Each adapter passes the prompt through stdin rather than argv and forwards provider stdout/stderr unchanged. Codex uses a read-only sandbox with shell/unified-exec disabled. Claude uses print mode with its default tools and MCP disabled. R2AI reads input through the loadable radare2 plugin using `r2ai -i /dev/stdin`; the prompt is not entered into the standalone REPL. If only the executable exists and no plugin is available, forwarding to R2AI fails with an error. R2AI 1.4.4 may return radare2 exit code 0 even for some internal errors. lhlinux does not alter that upstream exit code.

There are no configuration fields for API keys, and authentication environment variables are neither read nor logged. Each CLI manages authentication, model settings, and billing settings. The collected prompt is stored in a temporary file with restricted permissions and removed on exit. Each provider's own logging and retention behavior follows that CLI's settings. Use `--dry-run` to inspect the content before sending it.

AI checks return `0` if at least one available candidate exists, or `1` otherwise. For `ask`, target file problems return `1`; invalid options, uninstalled providers, and missing required models return `2`. The executed provider's exit code is propagated unchanged. Timeouts use coreutils timeout exit code `124` (`137` if forcibly killed). Bash and coreutils are required; JSON output and context collection also require Python 3.

Installation and integration documentation for each CLI:

- [Codex CLI](https://developers.openai.com/codex/cli/) · [Non-interactive execution through stdin](https://learn.chatgpt.com/docs/non-interactive-mode) · [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
- [Claude Code setup](https://code.claude.com/docs/en/setup) · [CLI options](https://code.claude.com/docs/en/cli-reference)
- [Ollama installation](https://docs.ollama.com/linux)
- [R2AI source](https://github.com/radareorg/r2ai)

## Configuration

| Component | Configuration |
| --- | --- |
| Base | Ubuntu Base 24.04.4 amd64 + Ubuntu packages available at installation time |
| WSL data | `<installation path>\lhlinux\ext4.vhdx` |
| User | `admin`, password-required sudo, docker group |
| Containers | Ubuntu's docker.io, Docker Compose v2 |
| Analysis | binutils (strings/readelf/objdump), GDB, radare2 6.2.2 |
| Solving | Python 3, venv, Z3 CLI, python3-z3 |
| AI | R2AI commit `9f9a3b87ae3318e63fe415ede1d2afe5d17688c0`, Ollama 0.33.3 |
| Default model | qwen2.5-coder:0.5b, a small coding model |
| Services | systemd, Docker, Ollama |
| Working directories | `~/lab/samples`, `~/lab/solvers`, `~/lab/results` |

Ollama binds to `127.0.0.1:11434`. It is configured for one model at a time, a context length of 2048, and one parallel request. The small model has limited accuracy for complex code analysis. R2AI provider settings are stored in `~/.config/r2ai/rc`.

To compile and inspect the included sample:

```bash
gcc -g -O0 ~/lab/samples/hello.c -o ~/lab/results/hello
~/lab/results/hello
readelf -h ~/lab/results/hello
gdb ~/lab/results/hello
r2 ~/lab/results/hello
```

Inside radare2, run `r2ai -h` for help. AI is configured to use local Ollama and does not require an API key. The solver example solves the integer equations `x+y=10` and `x-y=4`.

## Rerunning the Setup

To resume an interrupted lhlinux installation created by this project:

```powershell
./scripts/New-Lhlinux.ps1 -Resume
```

An existing distribution with the same name or an existing destination directory is not automatically deleted. `-Resume` reapplies packages and project settings and restarts lhlinux, so save your work inside lhlinux first. It does not change Ubuntu's designation as the default distribution.

The examples `~/lab/solvers/solver.py` and `~/lab/samples/hello.c` are installed only if absent. Existing files and symbolic links are preserved, so modified examples are not overwritten when resuming. The latest original examples are available in the repository's `examples/` directory. If the Ubuntu download was interrupted or the cached file has a mismatched checksum, it is downloaded again; only files that pass verification are used for import.

If you have the luka account from an early development version, close all lhlinux sessions and terminate that distribution before resuming. The account and home directory are migrated to admin while preserving the existing UID, files, and Python virtual environment packages. An already configured admin password is not changed when resuming.

The Ubuntu image's SHA256 is compared with the official checksum file served over HTTPS. The radare2 and Ollama binaries use pinned versions and SHA256 hashes. R2AI is built from a pinned source commit. Ubuntu repository packages change with security updates, so builds are not byte-for-byte identical. The actual package list is recorded in `/opt/lhlinux/packages.tsv`.

```bash
lhlinux-check
systemctl status docker ollama --no-pager
```

## Backups and a Future VM Version

After saving your work, create a WSL backup from PowerShell:

```powershell
wsl --terminate lhlinux
wsl --export lhlinux D:\WSL\lhlinux-backup.tar
```

This tar file is a WSL backup containing personal data and account settings. It is not a public distribution artifact, a bootable VM image, or an installation ISO. A VM version could reuse the common packages in `bootstrap.sh` and `install-tools.sh`, but would require separate configuration for the kernel, bootloader, disks, networking, and user authentication. For compatibility, `/etc/os-release` retains Ubuntu information, while lhlinux product information is recorded in `/etc/lhlinux-release`.

## License and Contributing

Scripts, examples, and documentation authored by lhlinux are released under the [MIT License](LICENSE). External programs and models retain their respective licenses. See [Third-party components](THIRD_PARTY.md), [Contributing](CONTRIBUTING.md), and [Actual validation results](VALIDATION.md).

lhlinux is an independent community project, not an official Canonical distribution. GitHub contains source code and documentation; personal WSL disks, backups, passwords, and API keys are excluded.

## Official References

- [Microsoft: Import a custom WSL distribution](https://learn.microsoft.com/en-us/windows/wsl/use-custom-distro)
- [Ubuntu Base downloads](https://cdimage.ubuntu.com/ubuntu-base/releases/24.04/release/)
- [radare2 release](https://github.com/radareorg/radare2/releases/tag/6.2.2)
- [R2AI](https://github.com/radareorg/r2ai)
- [Ollama Linux installation](https://docs.ollama.com/linux)
- [Default model](https://ollama.com/library/qwen2.5-coder:0.5b)
