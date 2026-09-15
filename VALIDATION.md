# lhlinux 설치 검증

## 실행 환경 고정과 출력 기록 (2026-09-11)

- 선택적 환경을 `~/.local/share/lhlinux/envs/nes-py-9.0.1`에 실제 설치했습니다. Python 3.13.15, nes-py 9.0.1, NumPy 2.5.3, Pillow 12.3.0 및 lock의 9개 패키지 버전·import·의존성 검사가 통과했습니다. 설치 도구 uv 0.12.13과 Python 패키지는 고정 버전으로 관리하며 lock에 패키지 파일 해시를 기록했습니다.
- 같은 setup을 다시 실행하면 `Ready (reused)`로 기존 환경을 재사용하며 다운로드·동기화를 생략함을 확인했습니다. `--check`도 통과했습니다. 관리되지 않은 환경과 심볼릭 링크를 보존하는 테스트 4개를 추가했습니다.
- `lhlinux run`은 실행당 별도 폴더에 stdout/stderr와 시간·종료 코드·중단 사유를 기록합니다. 출력 합산 한도, 짧은 미리보기, 0700/0600 권한, 인자 기록 기본 생략, literal argv, timeout 시 자식 종료, SIGTERM 결과 저장, 잘못된 Python 환경변수에서의 시작을 테스트했습니다.
- 최종 Linux unittest **57개 통과 (27.564초)**. PowerShell 설치 mock 5개, 실제 터미널 연동 검사, Bash 구문 검사, `git diff --check`도 통과했습니다. 마지막 테스트 로그는 Git 제외 파일 `logs/workflow-regression-tests.log`입니다.
- 새 CLI·도움말·run helper·전용 Python wrapper를 설치된 lhlinux에 반영했습니다. 이전 파일은 `/opt/lhlinux/workflow-backup-j40f4hzr`에 백업했습니다. 실제 `lhlinux run --json -- lhlinux-nes-python --version`은 종료 코드 0과 Python 3.13.15 출력을 기록했습니다.
- 잘못된 `PYTHONHOME`과 이전 `/tmp/nes-tools`가 지정된 `PYTHONPATH`에서도 실행기와 전용 Python의 조합이 정상 동작했습니다. 별도의 가짜 numpy 모듈을 둔 대조 검사에서도 전용 환경의 실제 numpy를 불러왔습니다. 시스템 Python은 3.12.3을 유지했고 기존 `~/lab/.venv`의 Z3 예제도 통과했습니다.
- 이 설치 검증은 ROM 실행이나 서버 제출을 수행하지 않습니다. 공개 PyPI 패키지와 문제 서버의 사용자 정의 코어·설정 동등성 및 기존 8.x 스크립트 호환성은 미검증입니다. 현재 Codex 세션의 모델·진행 파일·실행 프로세스는 변경하지 않았습니다. 실제 풀이 속도 개선을 측정한 결과가 아닙니다.

사용법과 로그 보관 조건은 [실행 환경 및 로그 안내](docs/execution-workflow.md)에 있습니다.

## 테스트 모드 1차 실측 (2026-09-11)

[상세 시험 보고서](docs/test-mode-report-2026-09-11.md): 기능 테스트 45개와 실제 WSL 연동은 통과했습니다. 그러나 `hello.c` 바이너리 요약은 compact/standard 각 2회 모두 수동 정확도 기준에 미달했습니다. compact 입력에서 `main`의 실제 출력 함수 호출이 잘리는 현상도 확인했습니다. 짧은 C 소스 직접 전달 대조 시험 1회는 정확히 응답했습니다. **테스트 모드를 유지하며, 현재 결과는 CTF 풀이 성능 개선의 근거로 사용하지 않습니다.**

## AI 입력 준비 최적화 — 테스트 모드 (2026-09-11)

현재 상태는 실험적 테스트 모드입니다. 아래 검증은 입력 준비·전달과 샘플 응답에 한정하며 실제 CTF 풀이 성능 검증은 남아 있습니다.

- Linux unittest 전체 45개 통과. 지정하지 않은 provider와 자동 선택의 후순위 후보를 실행하지 않는지, 잘못된 옵션·모델 누락·미설치 provider에서 컨텍스트 수집을 생략하는지 확인했습니다.
- local의 자동 compact 적용, standard 선택, provider 없는 compact 미리보기, 명시적 제한의 순서 독립성, 짧은 섹션에서 남는 공간의 재배분을 검증했습니다. 기존 stdin 전달·종료 코드·타임아웃·대상 미실행 테스트도 통과했습니다.
- Bash 구문 검사와 `git diff --check` 통과. CLI와 AI/context helper를 설치된 lhlinux에 반영했으며, 이전 파일은 `/opt/lhlinux/ai-backup-zfse5sa7`에 백업했습니다.
- 실제 제공 샘플 `/home/admin/lab/results/hello`의 dry-run 프롬프트는 standard **11721바이트**, compact **4096바이트**였습니다. 다른 파일은 크기와 내용에 따라 결과가 달라집니다.
- 설치된 Ollama `qwen2.5-coder:0.5b`에 compact로 같은 샘플의 동작 요약을 요청했습니다. 60초 제한 내 **30.923초**, 종료 코드 0으로 응답했고 `main`에서 `puts`로 `Hello from lhlinux`를 출력한다는 설명을 확인했습니다. 응답은 Git 제외 파일 `logs/ai-compact-smoke.txt`에 저장했습니다. 모델 로드 시간을 분리하거나 standard 추론 시간과 비교하지는 않았습니다.
- 커밋 `84a9cd7` 코드와 수정본을 임시 디렉터리에서 비교했습니다. 선택한 codex는 즉시 응답하고, 선택하지 않은 claude/ollama/r2ai의 버전·목록 조회마다 0.3초 대기하는 mock을 사용했습니다. 실제 AI·네트워크 요청 없이 각 3회 측정한 전달 준비 시간 중앙값은 **1.667초 → 0.820초**였습니다. WSL 실행 비용과 모델 추론을 제외한 인위적 지연 조건의 수치이며 실제 CTF 풀이 속도나 정확도를 측정한 결과는 아닙니다.

## 터미널 작업 흐름 개선 (2026-09-11)

- Linux Python unittest 전체 40개 통과. 새 workspace 테스트 6개에서 staged/unstaged/untracked 구분, 파일 본문 미포함, 출력 제한, 일반 폴더, 잘못된 경로, 특수문자 경로, 외부 diff/fsmonitor 미실행을 확인했습니다.
- PowerShell 설치 mock 5개, Bash 구문 검사, `git diff --check` 통과.
- `tests/test_terminal.ps1`을 PowerShell 7.6.5와 실제 lhlinux WSL에서 실행했습니다. 공백·한글·따옴표·빈 문자열·셸 특수문자 인자의 동일성, Windows/Linux 작업 경로, 종료 코드 37 전달을 확인했습니다. 호출자의 native-command 오류 승격 설정이 켜져 있어도 종료 코드를 보존합니다.
- 실제 lhlinux에 ripgrep 14.1.0을 설치하고 CLI, 도움말, workspace helper와 현재 저장소의 공통 context helper를 반영했습니다. 이전 설치 파일은 `/opt/lhlinux/cli-backup-pnnjdxom`에 백업했습니다.
- 설치된 `lhlinux workspace --json`의 JSON 파싱과 도구 경로·Git 상태, `rg --files scripts` 실행을 확인했습니다.
- 현재 `/mnt/c` 저장소에서 workspace 요약을 WSL 내부 Python으로 5회 실행한 중앙값은 **0.266초**, 당시 JSON 출력은 **1372바이트**였습니다. WSL 시작·PowerShell 호출 비용은 제외한 측정이며 이전 구현 대비 배속이나 CTF 풀이 속도를 측정한 수치가 아닙니다.
- 이번 변경의 새 설치/전체 `-Resume` 실행은 하지 않았습니다. 외부 AI 요청, 서비스 재시작, 사용자 작업 폴더 이동은 수행하지 않았습니다.

검증일: 2026-09-10

별도 WSL2 인스턴스 `lhlinux`를 설치하고 재부팅 후 검사했습니다. 이후 기본 계정을 `admin`으로 이전하고, 다시 시작한 상태에서 `scripts/smoke-test.sh` 전체를 admin으로 재실행했습니다. 종료 코드는 0입니다.

| 검사 | 결과 |
| --- | --- |
| 기본 사용자 / 호스트 이름 | `admin` / `lhlinux` |
| 계정 이전 | UID/GID 1000 유지, 홈 폴더 `/home/admin`, 기존 파일 유지 |
| 비밀번호 / sudo | 요청된 로컬 비밀번호 설정, sudo 인증 성공, 비밀번호 없는 실행 거부 확인 |
| 이전된 Python venv | Z3 풀이와 pip 실행 정상 |
| init | systemd |
| Docker 자동 시작, 클라이언트/서버 | 정상, 29.1.3 / 29.1.3 |
| Docker Compose | 2.40.3 |
| 컨테이너 실행 | 공식 hello-world 이미지 다운로드와 실행 성공 |
| Python | 3.12.3 |
| Z3 | 4.8.12, 시스템 Python과 venv에서 각각 x=7, y=3 확인 |
| C 샘플 | 컴파일/실행 성공, Hello from lhlinux 출력 |
| strings / readelf / objdump | 샘플 문자열, ELF64 헤더, main 역어셈블리 확인 |
| GDB | 15.1, main 중단점 도달 및 7+3=10 평가 확인 |
| radare2 | 6.2.2, 샘플의 dbg.main 확인 |
| R2AI | 플러그인 도움말 로딩 및 로컬 모델 응답 성공 |
| Ollama | 0.33.3, 자동 시작 및 모델 API 생성 응답 확인 |
| R2AI → Ollama 연결 | 2+2 질문에 4 응답 |

초기 실행 로그는 `logs/smoke-test.log`, 계정 변경 후 로그는 `logs/admin-smoke-test.log`, R2AI 응답은 lhlinux의 `~/lab/results/r2ai-smoke.txt`에 있습니다. 로그는 Git에서 제외됩니다. 검증은 이 설치 환경과 제공한 간단한 예제에 대한 것입니다. VM 부팅과 설치 ISO는 아직 제작/검증하지 않았습니다.

설치 중 스크립트 재개 위치 및 작업 폴더 소유권 오류를 수정하고 재개해 완성했습니다. 수정된 설치 스크립트를 별도의 두 번째 새 인스턴스에서 처음부터 다시 실행한 검증은 하지 않았습니다.

공개 준비 변경에 대해 PowerShell 구문 검사와 Bash 스크립트별 구문 검사를 통과했습니다. 설치 스크립트 및 공개 안내문에 로컬 비밀번호나 NOPASSWD 설정이 없는 것도 확인했습니다. 새 설치 시 대화형 비밀번호 설정을 포함한 전체 설치 경로는 별도 PC에서 아직 검증하지 않았습니다.

## 리버싱 CLI 검증

`scripts/lhlinux`를 `/usr/local/bin/lhlinux`에 설치하고 admin 사용자로 확인했습니다.

- `lhlinux reversing check`: Installed 7 / 7, Missing 0 / 7. 모든 실행 경로 표시 확인.
- `list`, `missing`, `versions`: 대상 7개 목록, 누락 0개 요약, 각 도구의 버전 출력 확인. R2AI 실행 파일의 버전은 1.4.4로 표시됨.
- `env PATH=/usr/bin:/bin /usr/local/bin/lhlinux reversing check`: R2AI 실행 파일이 PATH에 없는 상태에서 `/usr/lib/radare2/6.2.2/r2ai.so (radare2 plugin)`으로 탐지됨. 실제 설치 파일은 삭제하거나 옮기지 않음.
- 기존 `lhlinux-check`: 전체 환경 검사 통과.
- `python3 -m unittest discover -s tests -v`: 독립된 임시 PATH를 사용하는 9개 테스트 통과. 전체/일부 누락, 실행 권한 없음, r2 별칭, Python 없는 환경의 플러그인 검사, jq 없는 환경, 경로 없는 구형 메타데이터, 로드되지 않은 플러그인 파일, 심볼릭 링크, 잘못된 인자 등을 확인.

설치된 바이너리의 존재 여부를 점검하는 기능이며, 도구 전체 기능의 정상 동작이나 버전의 보안 상태까지 보증하는 검사는 아닙니다.

## AI CLI 연동 검증

2026-09-10, admin 사용자로 새 CLI와 helper를 설치한 뒤 검증했습니다.

- 전체 테스트 25개 통과: 기존 리버싱 테스트 9개 + AI 감지·컨텍스트·전달 테스트 16개. 외부 AI CLI는 mock 처리했습니다.
- provider 전체 미설치, 실행 권한 없음, 버전 실패/3초 초과, Ollama 데몬 실패, Codex 런타임 오류 시 다음 provider 선택을 확인했습니다.
- JSON 파싱, 색상 없는 출력, 추가 질문, 한글 UTF-8 바이트 제한과 `[truncated]`, SHA256, 잘못된 파일/옵션을 확인했습니다.
- 대상 파일 실행 없이 수집하고, 셸 특수문자가 포함된 파일명도 명령으로 해석하지 않음을 확인했습니다.
- Codex/Claude/Ollama/R2AI 어댑터의 stdin 전달을 mock으로 검증했습니다. provider의 stdout, stderr 및 종료 코드 37이 전파되고, 시간 초과 시 124로 종료되며 임시 프롬프트가 제거됨을 확인했습니다.
- 실제 WSL에서 help 3종, `ai check`, `ai providers --json`, 기존 `reversing check`를 실행했습니다. 기존 리버싱 도구는 7/7입니다.
- 실제 샘플 ELF에 `--dry-run --max-bytes 4096 --strings-limit 10 --disasm-limit 512`를 적용해 메타데이터와 섹션별 잘림 표시를 확인했습니다.
- 실제 Ollama `qwen2.5-coder:0.5b`에 샘플 컨텍스트를 stdin으로 전달했습니다. 종료 코드 0과 `The program prints "Hello from lhlinux".` 응답을 확인했습니다.

테스트 로그는 Git에서 제외된 `logs/ai-tests.log`, 실제 WSL 연동 로그는 `logs/ai-integration.log`입니다. 현재 Codex는 Windows npm shim 경로가 발견되지만 WSL에 node가 없어 `installed: true`, `version: unknown`, `execution: unavailable`로 표시됩니다. Claude는 미설치입니다. 실제 Codex/Claude 계정으로 요청하지 않았으며, R2AI의 새 stdin 어댑터도 실계정 요청 없이 mock으로 검증했습니다. 원격 인증·과금·실제 모델 응답은 검증 범위에 포함하지 않았습니다.

## 전체 코드 검토 및 리팩터링 검증

2026-09-10, 기준 커밋 `578dfb7`의 추적 파일 21개를 검토하고 설치 재개, 다운로드 캐시, AI 상태 판정 및 UTF-8 출력 제한을 수정했습니다.

| 수정 항목 | 검토에서 확인한 문제 | 변경 결과 |
| --- | --- | --- |
| 설치 재개 | 예제 두 개를 매번 복사하여 사용자 수정본을 덮어씀 | 공통 설치 helper로 분리하고 기존 파일·디렉터리·심볼릭 링크 보존 |
| Ubuntu 캐시 | 중단된 다운로드 파일을 재사용하면서 체크섬 오류가 반복됨 | 잘못된 캐시 재다운로드, `.part` 검증 후 최종 파일로 교체 |
| Ollama 감지 | 4096바이트를 넘는 모델 목록에서 파이프가 닫혀 정상 실행이 실패로 판정됨 | 보관할 출력만 제한하고 남은 출력은 소비하여 종료 코드 유지 |
| R2AI 상태 | 실행 파일만 있는 환경을 사용 가능으로 표시하지만 실제 어댑터는 플러그인이 필요함 | 플러그인 없을 때 `available: false`와 요구 사항 표시 |
| 컨텍스트 제한 | 잘못된 UTF-8의 대체 문자 변환 후 개별 출력이 바이트 제한을 초과함 | 변환 후 다시 제한 적용, 아주 작은 내부 예산도 준수 |

실행 결과:

- 기존 25개를 포함한 Python unittest 34개 통과. 새 테스트는 상태 판정, 출력 제한, 예제 보존 및 Bash 다운로드 helper의 실패·재시도 경로를 확인합니다.
- PowerShell 설치기 모의 검사 5개 통과: 신규 다운로드, 정상 캐시 재사용, 중단된 캐시 복구, 체크섬 불일치, 다운로드 실패.
- Bash 9개 파일 및 PowerShell 2개 파일 구문 검사 통과.
- 변경된 소스의 `reversing check`: 7/7 탐지. `ai check --json`: Ollama 응답 및 R2AI 플러그인 사용 가능 확인.
- 소스의 `lhlinux-check` 통과: Docker, Compose, 시스템/venv Z3, radare2, R2AI 도움말, 서비스 상태 및 모델 목록 확인.

전체 신규 설치, 실제 `-Resume`에 따른 계정 이전·패키지 재설치, `smoke-test.sh`의 컨테이너 실행 및 모델 추론은 이번 검토에서 다시 실행하지 않았습니다. 설치기 검증은 모의 검사이며 이 경로들의 실환경 검증을 대체하지 않습니다. 변경된 CLI를 시스템 경로에 설치하거나 GitHub에 푸시하지 않았습니다.
