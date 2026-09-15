# 실행 환경과 로그 재사용

현재 기능은 테스트 단계입니다. 명령 실행·출력 수집과 Python 의존성 준비를 돕습니다. 문제 풀이 성공률이나 분석 결과의 정확도를 보장하는 기능은 아닙니다.

## 큰 출력을 파일에 보관하기

Linux에서:

```bash
lhlinux run -- python3 -m unittest discover -s tests -v
lhlinux run --timeout 60 --json -- python3 --version
```

PowerShell에서는:

```powershell
./scripts/Invoke-Lhlinux.ps1 -Command @('lhlinux', 'run', '--json', '--', 'python3', '--version')
```

매 실행마다 `~/lab/results/runs/<시각-고유값>/`에 `stdout.log`, `stderr.log`, `result.json`을 만듭니다. 기존 결과를 덮어쓰지 않습니다. 결과 폴더는 0700, 로그 파일은 0600 권한입니다. 실행 시간은 명령 시작부터 종료·정리까지의 벽시계 시간이며 모델 내부 추론 시간과 구분되는 수치는 아닙니다.

일반 출력은 경과 시간·종료 코드·로그 경로와 각 스트림 끝의 최대 2048 원시 바이트/30줄 미리보기입니다. JSON 모드는 메타데이터만 출력합니다. 전체 결과는 제한에 도달하기 전까지 파일에 보관하므로, 필요한 문자열은 저장된 파일을 대상으로 `rg`로 검색하고 해당 부분만 읽을 수 있습니다.

| 옵션 | 동작 |
| --- | --- |
| `--cwd 폴더` | 명령의 작업 폴더, 기본은 현재 폴더 |
| `--log-dir 폴더` | 결과를 모을 폴더 |
| `--timeout 초` | 기본 300초, 범위 1~86400 |
| `--max-output-bytes N` | stdout+stderr 합산 저장 한도, 기본 16MiB, 범위 1~1GiB |
| `--record-command` | 메타데이터에 인자 배열까지 기록 |
| `--json` | 메타데이터 JSON 출력 |

프로그램 종료 코드는 유지합니다. 시간 초과는 124, 출력 한도 초과는 125, 실행 실패는 126/127입니다. SIGINT/SIGTERM 중단도 결과를 남기고 130/143으로 종료합니다. `stop_reason`으로 실제 프로그램의 같은 번호 종료와 도구가 중단한 경우를 구분할 수 있습니다. 시간·출력 한도를 넘기면 실행 프로세스 그룹을 종료하므로 결과 파일은 부분 출력입니다. 백그라운드 작업 유지나 대화형 입력을 위한 실행기는 아니며 stdin은 닫힌 상태로 실행합니다.

실행 파일 이름과 작업 폴더는 기록합니다. 명령 인자 전체와 인증 환경변수는 기본 메타데이터에 기록하지 않습니다. 다만 프로그램 자체가 stdout/stderr에 출력한 비밀정보는 로그에 들어갈 수 있습니다. `--record-command`를 사용할 때는 인자에 비밀정보가 없는지 확인하세요. 로그 정리·보관 기간은 사용자가 관리합니다.

이 도구는 지정한 명령 한 번만 실행합니다. 동일 명령이라도 입력 파일·환경·상태가 바뀔 수 있으므로 결과를 자동 캐시하거나 실패한 명령을 자동 재시도하지 않습니다. 의미 있는 중간 결과를 재사용할지는 사용자가 결정합니다.

## 선택적 NES Python 환경

Ubuntu 기본 Python과 `~/lab/.venv`를 유지하면서 아래 환경을 별도로 구성합니다. 기본 배포판 설치 과정에는 포함하지 않습니다.

| 구성 | 고정값 |
| --- | --- |
| 플랫폼 | Linux x86-64 |
| Python | CPython 3.13.15 |
| 설치 도구 | uv 0.12.13 |
| 주요 패키지 | nes-py 9.0.1, NumPy 2.5.3, Pillow 12.3.0 |
| 전체 패키지 | requirements.lock의 9개 패키지, 버전과 파일 해시 고정 |
| 위치 | `~/.local/share/lhlinux/envs/nes-py-9.0.1` |

저장소 루트에서:

```bash
bash scripts/setup-nes-env.sh
bash scripts/setup-nes-env.sh --check
lhlinux-nes-python --version
lhlinux run -- lhlinux-nes-python -c 'from importlib.metadata import version; print(version("nes-py"))'
```

`lhlinux-nes-python`은 해당 환경의 Python을 실행하며 기존 `/tmp` 패키지가 우선 로드되지 않도록 `PYTHONPATH`와 `PYTHONHOME`을 제거합니다. 현재 작업 폴더의 자체 Python 모듈 로딩은 일반 Python 실행 규칙을 따릅니다. 설치된 CLI가 아직 없으면 저장소에서 `bash scripts/lhlinux-nes-python --version`으로 확인할 수 있습니다.

setup은 관리 표시가 있는 전용 환경만 수정하며, 기존의 관리되지 않은 폴더나 심볼릭 링크 환경은 보존하고 중단합니다. 최초 설치에 네트워크가 필요합니다. 같은 lock과 정상 환경이 있으면 재설치하지 않고 재사용합니다. 관리 환경의 패키지가 손상되면 고정 lock으로 다시 맞추며, 관리 표시 없는 사용자 환경은 자동 복구하지 않습니다. 동시에 두 setup이 실행되지 않도록 파일 잠금을 사용합니다.

`--check`는 Python·패키지 버전, 의존성 일관성, NumPy/Pillow 및 NESEnv import를 확인합니다. ROM을 열거나 게임을 실행하지 않습니다. 패키지는 [PyPI의 9.0.1](https://pypi.org/project/nes-py/9.0.1/)을 사용합니다. 해당 페이지는 Python 3.13 이상과 Gymnasium 인터페이스를 설명하므로 기존 8.x용 스크립트의 호환성은 별도 확인이 필요합니다.

문제 서버의 사용자 정의 빌드·코어·렌더링 설정과의 동등성은 버전 번호와 import 검사만으로 확인할 수 없습니다. 따라서 상태 출력의 `reference_core_equivalence`는 `unverified`로 남깁니다. 기존 Codex 세션의 모델 설정이나 실행 중인 Python 프로세스를 자동 전환하지 않으므로, 재개할 때 위의 전용 Python 명령을 명시적으로 사용해야 합니다.

Python 관리와 lock 방식은 [uv Python 관리](https://docs.astral.sh/uv/guides/install-python/) 및 [uv lock 문서](https://docs.astral.sh/uv/pip/compile/)를 따릅니다.
