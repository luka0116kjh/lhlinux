# 외부 구성 요소

이 저장소의 LICENSE는 lhlinux가 작성한 설치 스크립트, 예제 및 문서에 적용됩니다. 다운로드되는 Ubuntu, 개별 패키지, radare2, R2AI, Ollama, 모델의 라이선스를 바꾸지 않습니다.

이 저장소는 설치 방법과 설정 소스를 제공합니다. 설치 프로그램은 외부 구성 요소를 각 배포처에서 다운로드합니다. 설치된 Ubuntu 패키지의 고지문은 `/usr/share/doc/<패키지>/copyright`, 설치 버전 목록은 `/opt/lhlinux/packages.tsv`에서 확인할 수 있습니다.

관련 원문:

- [Ubuntu / Canonical 배포 및 상표 정책](https://canonical.com/legal/intellectual-property-policy)
- [radare2 6.2.2 소스 및 고지](https://github.com/radareorg/radare2/tree/6.2.2)
- [설치된 R2AI 커밋의 LICENSE](https://github.com/radareorg/r2ai/blob/9f9a3b87ae3318e63fe415ede1d2afe5d17688c0/LICENSE)
- [Ollama 0.33.3 소스 및 고지](https://github.com/ollama/ollama/tree/v0.33.3)
- [Qwen2.5-Coder 0.5B 모델 정보 및 라이선스](https://ollama.com/library/qwen2.5-coder:0.5b)

VM/ISO 또는 WSL 이미지 자체를 공개하는 릴리스는 별도 작업입니다. 그때 실제 포함 파일별 고지, 필요한 대응 소스 제공, 기반 배포판의 상표 처리와 모델·런타임의 재배포 조건을 해당 버전에 맞춰 확인합니다. 현재 개인 WSL 백업은 공개 릴리스 파일로 취급하지 않습니다.
