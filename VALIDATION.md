# lhlinux 설치 검증

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
