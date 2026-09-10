# lhlinux 0.1

한국어 | [English](README.en.md)

![lhlinux 로고](docs/assets/lhlinux-logo.png)

누구나 설치하고 개선할 수 있는 Ubuntu 24.04 LTS 기반 오픈소스 WSL2 CLI 배포판 프로젝트입니다. Docker, Z3, 바이너리 분석 도구와 로컬 AI를 재설치 가능한 스크립트로 구성합니다. 기본 사용자는 `admin`입니다.

현재 지원 범위는 Windows의 **x86-64 WSL2**입니다. ARM64, 일반 PC 직접 설치, VM 부팅 이미지와 설치 ISO는 아직 지원하지 않습니다.

## 설치

Windows에 WSL2가 설치되어 있어야 합니다. PowerShell에서 `wsl --list --verbose`로 확인하세요. 인터넷 연결과 최소 10GB의 여유 디스크 공간을 권장하며, 현재 검증 환경의 WSL 메모리는 약 4GB입니다.

이 저장소를 내려받은 뒤 저장소 폴더에서 실행합니다:

```powershell
./scripts/New-Lhlinux.ps1
```

기본 저장 위치는 `%LOCALAPPDATA%\lhlinux\WSL\lhlinux`입니다. D: 등에 설치하려면:

```powershell
./scripts/New-Lhlinux.ps1 -InstallRoot D:\WSL
```

설치 도중 **admin 계정의 비밀번호를 직접 입력**합니다. 공통 기본 비밀번호는 제공하거나 소스에 저장하지 않습니다. `sudo`는 이 비밀번호를 요구합니다. WSL 시작 자체는 Windows 사용자 권한으로 실행되므로 매번 Linux 로그인 비밀번호를 묻지는 않습니다. Docker 사용을 위해 admin은 docker 그룹에도 속합니다.

## 시작

PowerShell에서:

```powershell
wsl -d lhlinux --cd ~
```

lhlinux 터미널에서:

```bash
lhlinux-help
lab
workon
python3 solvers/solver.py
docker run --rm hello-world
ollama run qwen2.5-coder:0.5b
```

`workon`은 `~/lab/.venv`를 활성화합니다. 추가 Python 패키지는 이 환경에서 `pip install 패키지명`으로 설치합니다. `deactivate`로 나옵니다.

### 리버싱 도구 점검

```bash
lhlinux reversing check
lhlinux reversing list
lhlinux reversing missing
lhlinux reversing versions
```

`check`는 strings, readelf, objdump, gdb, radare2, r2ai, python3의 실행 경로와 설치 개수를 출력합니다. radare2의 `r2` 이름도 인식하며, 심볼릭 링크는 실제 파일 경로로 표시합니다. R2AI 실행 파일이 없으면 radare2가 로드한 플러그인 메타데이터의 경로를 확인하고 `(radare2 plugin)`으로 표시합니다. jq가 없을 때는 로드된 플러그인 이름과 표준 사용자·시스템 플러그인 경로를 확인합니다. 사용자 시작 스크립트에서만 수동 로드하는 플러그인은 이 검사에 포함하지 않습니다.

`list`는 점검 대상 이름만, `missing`은 누락 항목만, `versions`는 경로와 버전 첫 줄을 보여줍니다. 버전 조회에 실패하면 `Version unavailable`로 표시합니다. 플러그인·버전 조회는 각각 5초로 제한되며 AI 서버에 요청하지 않습니다. 검사에 필요한 기본 유틸리티는 Bash와 coreutils이며, jq가 있으면 플러그인의 정확한 메타데이터를 사용합니다.

종료 코드는 전체 설치 시 `0`, 누락 시 `1`, 잘못된 명령 사용 시 `2`입니다. `list`는 항상 `0`입니다. 기존 `lhlinux-check`(전체 환경 검사)와 `lhlinux-help`도 그대로 사용할 수 있습니다.

### AI CLI 연동

```bash
lhlinux ai check
lhlinux ai check --json
lhlinux ai providers
lhlinux reversing ask codex ./chall
lhlinux reversing ask claude ./chall -- "libc 버전 추정해줘"
lhlinux reversing ask ./chall --dry-run
lhlinux reversing ask local ./chall --model qwen2.5-coder:0.5b
lhlinux reversing ask r2ai ./chall
```

`ai check`는 PATH와 실행 권한을 확인합니다. 버전 조회는 `--version`을 최대 3초 실행하며, 실패하거나 버전을 파악할 수 없으면 설치 상태는 유지하고 `unknown`으로 표시합니다. 실행 파일/런타임 오류(126/127)는 `execution: unavailable`로 표시하고 자동 선택에서 제외합니다. 인증 성공 여부와 결제 상태는 검사하지 않습니다. Ollama의 설치 여부와 데몬 응답(`reachable`/`unreachable`)은 별도로 표시합니다. R2AI 플러그인만 있는 설치도 감지합니다.

`ai providers`는 provider 이름, 상태, 감지 경로, stdin 전달 커맨드를 보여줍니다. 두 명령 모두 `--json`을 지원합니다. JSON의 `installed`는 발견 여부, `available`은 실행 가능 후보 여부이며 인증이나 추론 성공을 보장하지 않습니다. R2AI 실행 파일만 있고 로드 가능한 radare2 플러그인이 없으면 `installed: true`, `available: false`이며 텍스트에는 `radare2 plugin required`를 표시합니다. 버전 확인 실패만으로는 설치를 누락으로 취급하지 않습니다. CLI 자체 출력은 기존처럼 색상 없이 출력하므로 `NO_COLOR`와 `--no-color`에서도 같은 형식입니다.

`ask`는 읽을 수 있는 일반 파일만 받으며 대상 파일을 실행하지 않습니다. 파일명·크기·SHA256과 `file`, `strings -n 6`, ELF인 경우 `readelf -h -S -d`, 주요 함수(main/_start) 위주의 `objdump -d` 결과를 Markdown으로 모읍니다. 주요 함수 심볼을 찾을 수 없으면 제한된 앞부분을 사용합니다. 도구가 없거나 10초 안에 끝나지 않으면 stderr에 경고하고 해당 섹션을 생략합니다. 해시 계산도 10초로 제한하며 분석 중 파일이 변경되면 전송을 중단합니다. 현재 저장소에는 `reversing scan`/`analyze`가 구현되어 있지 않으므로 재사용할 기존 결과는 없습니다.

프롬프트는 정적 동작·함수 역할·라이브러리의 설명과 수동 확인 항목을 요청합니다. 자동 취약점 탐색이나 공격 실행을 요청하는 기능은 포함하지 않습니다. 바이너리 문자열은 신뢰하지 않는 데이터로 구분합니다. `--` 뒤의 추가 질문은 맨 아래에 붙입니다. 이 지시문은 모델의 답변 정확도를 보장하지 않으므로 결과를 직접 검토하세요.

| 옵션 | 기본값 / 동작 |
| --- | --- |
| `--dry-run` | provider를 실행하거나 감지하지 않고 프롬프트만 stdout 출력 |
| `--max-bytes N` | 전체 UTF-8 프롬프트 최대 122880바이트(120KiB), 범위 1024~10485760 |
| `--strings-limit N` | strings 최대 300줄, 범위 1~1000000 |
| `--disasm-limit N` | 역어셈블리 최대 32768바이트, 범위 64~10485760 |
| `--timeout SECONDS` | provider 실행 최대 300초, 범위 1~86400 |
| `--model MODEL` | `local`의 필수 모델 인자로 그대로 전달; 다른 provider에 지정하면 오류 |
| `--no-color` | 색상 없는 출력 유지 |
| `--json` | `ai check` / `ai providers`의 JSON 출력 |

전체 제한에 맞춰 섹션마다 공간을 배분하고 잘린 곳에는 `[truncated]`를 표시합니다. 작은 전체 제한은 개별 섹션 제한보다 먼저 적용될 수 있습니다. 메타데이터조차 들어가지 않는 크기라면 오류로 종료합니다.

provider를 생략하면 codex → claude → local 순서로 선택하고 stderr에 한 줄 알립니다. Ollama는 응답하는 데몬이 있어야 자동 선택됩니다. Ollama CLI는 모델을 필수 인자로 받으므로 `--model`로 사용자가 직접 정합니다. `ollama list`에서 설치된 모델을 확인할 수 있습니다. lhlinux는 모델을 자동 선택하거나 다운로드하지 않습니다. `--dry-run`에는 모델이나 설치된 provider가 필요 없습니다.

각 어댑터는 프롬프트를 argv가 아닌 stdin으로 전달하고 provider stdout/stderr를 그대로 연결합니다. Codex는 읽기 전용 sandbox와 shell/unified-exec 비활성 설정을, Claude는 기본 도구와 MCP를 비활성화한 print 모드를 사용합니다. R2AI는 로드 가능한 radare2 플러그인의 `r2ai -i /dev/stdin`으로 읽으며, standalone REPL에 프롬프트를 입력하지 않습니다. 실행 파일만 있고 플러그인이 없다면 R2AI 전달은 오류로 종료합니다. R2AI 1.4.4는 일부 내부 오류에도 radare2 종료 코드 0을 반환할 수 있습니다. lhlinux는 그 upstream 코드를 변경하지 않습니다.

API 키를 위한 설정 필드는 없으며 인증 환경변수를 읽거나 기록하지 않습니다. 인증과 모델/과금 설정은 각 CLI가 관리합니다. 수집한 프롬프트는 권한을 제한한 임시 파일에 보관했다가 종료 시 제거합니다. 각 provider 자체의 로그/보존 정책은 그 CLI의 설정을 따릅니다. `--dry-run`으로 내용을 확인한 뒤 전송할 수 있습니다.

AI 점검 종료 코드는 사용 가능한 후보가 하나 이상이면 `0`, 없으면 `1`입니다. `ask`의 대상 파일 문제는 `1`, 잘못된 옵션·미설치 provider·필수 모델 누락은 `2`입니다. 실행한 provider의 종료 코드는 그대로 전파하며 시간 초과는 coreutils timeout의 `124`(강제 종료 시 `137`)입니다. 기본 도구는 Bash/coreutils이며, JSON과 컨텍스트 수집에는 Python 3가 필요합니다.

CLI별 설치 및 연동 문서:

- [Codex CLI](https://developers.openai.com/codex/cli/) · [stdin 기반 비대화형 실행](https://learn.chatgpt.com/docs/non-interactive-mode) · [설정 참조](https://learn.chatgpt.com/docs/config-file/config-reference)
- [Claude Code 설정](https://code.claude.com/docs/en/setup) · [CLI 옵션](https://code.claude.com/docs/en/cli-reference)
- [Ollama 설치](https://docs.ollama.com/linux)
- [R2AI 소스](https://github.com/radareorg/r2ai)

## 구성

| 항목 | 설정 |
| --- | --- |
| 기반 | Ubuntu Base 24.04.4 amd64 + 설치 시점의 Ubuntu 패키지 |
| WSL 데이터 | `<설치 경로>\lhlinux\ext4.vhdx` |
| 사용자 | `admin`, 비밀번호를 요구하는 sudo, docker 그룹 |
| 컨테이너 | Ubuntu의 docker.io, Docker Compose v2 |
| 분석 | binutils(strings/readelf/objdump), GDB, radare2 6.2.2 |
| 풀이 | Python 3, venv, Z3 CLI, python3-z3 |
| AI | R2AI 커밋 `9f9a3b87ae3318e63fe415ede1d2afe5d17688c0`, Ollama 0.33.3 |
| 기본 모델 | qwen2.5-coder:0.5b, 소형 코드 모델 |
| 서비스 | systemd, Docker, Ollama |
| 작업 폴더 | `~/lab/samples`, `~/lab/solvers`, `~/lab/results` |

Ollama는 `127.0.0.1:11434`에 바인딩합니다. 한 번에 모델 하나, 문맥 2048, 병렬 요청 하나로 설정했습니다. 작은 모델이므로 복잡한 코드 분석의 정확도에는 한계가 있습니다. R2AI 제공자 설정은 `~/.config/r2ai/rc`입니다.

직접 만든 샘플을 컴파일하고 확인하려면:

```bash
gcc -g -O0 ~/lab/samples/hello.c -o ~/lab/results/hello
~/lab/results/hello
readelf -h ~/lab/results/hello
gdb ~/lab/results/hello
r2 ~/lab/results/hello
```

radare2 내부에서 `r2ai -h`로 도움말을 확인할 수 있습니다. AI는 로컬 Ollama를 사용하도록 설정하며 API 키가 필요하지 않습니다. Solver 예제는 정수 방정식 `x+y=10`, `x-y=4`를 풉니다.

## 재설치 가능한 구성

설치가 중단된 이 프로젝트의 lhlinux를 이어서 구성하려면:

```powershell
./scripts/New-Lhlinux.ps1 -Resume
```

기존 이름이나 대상 폴더는 자동 삭제하지 않습니다. `-Resume`은 패키지/프로젝트 설정을 다시 적용하고 lhlinux를 재시작하므로 lhlinux 안의 작업을 먼저 저장하세요. Ubuntu 기본 배포판 지정은 바꾸지 않습니다.

예제 `~/lab/solvers/solver.py`와 `~/lab/samples/hello.c`는 없는 경우에만 설치합니다. 기존 파일이나 심볼릭 링크는 보존하므로 수정한 예제가 재개 과정에서 덮어써지지 않습니다. 최신 예제 원본은 저장소의 `examples/`에서 확인할 수 있습니다. Ubuntu 다운로드가 중단되었거나 캐시의 체크섬이 다르면 다시 다운로드하고 검증을 통과한 파일만 가져오기에 사용합니다.

초기 개발 버전의 luka 계정이 있는 경우, 모든 lhlinux 세션을 닫고 해당 배포판을 종료한 뒤 재개하세요. 계정과 홈 폴더를 admin으로 이전하며 기존 UID, 파일 및 Python 가상환경 패키지를 유지합니다. 이미 설정된 admin 비밀번호는 재개 과정에서 바꾸지 않습니다.

Ubuntu 이미지의 SHA256은 공식 HTTPS 체크섬 파일과 비교합니다. radare2 및 Ollama 바이너리는 고정 버전과 고정 SHA256을 사용합니다. R2AI 소스는 고정 커밋을 빌드합니다. Ubuntu 저장소 패키지는 보안 업데이트에 따라 달라지므로 바이트 단위로 동일한 빌드는 아닙니다. 실제 패키지 목록은 `/opt/lhlinux/packages.tsv`에 남깁니다.

```bash
lhlinux-check
systemctl status docker ollama --no-pager
```

## 백업과 이후 VM 버전

작업을 저장한 뒤 PowerShell에서 WSL 백업을 만들 수 있습니다:

```powershell
wsl --terminate lhlinux
wsl --export lhlinux D:\WSL\lhlinux-backup.tar
```

이 tar는 개인 데이터와 계정 설정을 포함하는 WSL 백업이며, 공개 배포용 파일이나 VM 부팅 이미지/설치 ISO는 아닙니다. VM 버전에서는 `bootstrap.sh`의 공통 패키지와 `install-tools.sh`를 재사용하되, 커널·부트로더·디스크·네트워크·사용자 인증을 별도로 구성해야 합니다. 호환성을 위해 `/etc/os-release`는 Ubuntu 정보를 유지하고, lhlinux 제품 정보는 `/etc/lhlinux-release`에 기록합니다.

## 라이선스와 참여

lhlinux가 작성한 스크립트, 예제 및 문서는 [MIT License](LICENSE)로 공개합니다. 외부 프로그램과 모델은 각각의 라이선스를 따릅니다. [외부 구성 요소 안내](THIRD_PARTY.md), [기여 방법](CONTRIBUTING.md), [실제 검증 결과](VALIDATION.md)를 참고하세요.

lhlinux는 독립적인 커뮤니티 프로젝트이며 Canonical의 공식 배포판이 아닙니다. GitHub에는 소스와 문서를 올리고, 개인 WSL 디스크·백업·비밀번호·API 키는 포함하지 않습니다.

## 공식 참고 자료

- [Microsoft: 사용자 지정 WSL 배포판 가져오기](https://learn.microsoft.com/en-us/windows/wsl/use-custom-distro)
- [Ubuntu Base 다운로드](https://cdimage.ubuntu.com/ubuntu-base/releases/24.04/release/)
- [radare2 릴리스](https://github.com/radareorg/radare2/releases/tag/6.2.2)
- [R2AI](https://github.com/radareorg/r2ai)
- [Ollama Linux 설치](https://docs.ollama.com/linux)
- [기본 모델](https://ollama.com/library/qwen2.5-coder:0.5b)
