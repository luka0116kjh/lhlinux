# 기여하기

버그 제보와 수정, 문서 개선을 환영합니다. 문제를 보고할 때 Windows/WSL 버전, lhlinux 설치 단계, 비밀정보를 제거한 오류 메시지를 포함해 주세요.

변경 사항은 작은 단위로 작성하고, 설치 스크립트에 영향을 준다면 테스트용 WSL 환경에서 확인해 주세요. 기존 Ubuntu를 변경하거나 사용자 데이터를 삭제하는 자동 동작은 추가하지 않습니다.

비밀번호, API 키, 개인 작업 파일, WSL 디스크와 개인 백업은 커밋하지 않습니다. 새 다운로드를 추가할 때 버전, 출처와 체크섬을 기록하고 외부 구성 요소 고지도 갱신해 주세요.

기본 검사:

```bash
bash -n scripts/lhlinux
bash -n scripts/lib/ai.sh
python3 -m unittest discover -s tests -v
lhlinux reversing check
lhlinux-check
bash scripts/smoke-test.sh
```

마지막 검사는 lhlinux의 기본 사용자 admin으로 실행합니다. Docker Hub 접근과 로컬 AI 추론을 수행합니다. PR에는 실제 실행한 검사와 실행하지 못한 검사를 구분해 적어 주세요.
