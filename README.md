# ezcam 폴더 구조 스캐너

`C:\ezcam\1.1_1.1` 같은 설치 폴더의 구조를 **캡처(스크린샷)가 아니라 스캔**으로 읽어서
텍스트/JSON 리포트 파일로 뽑아내는 스크립트입니다. 그 파일만 보내면 됩니다.

## 무엇에 답하나

1. **설치 폴더 바로 아래에 무엇이 있는지** — exe / dll / txt 등
2. **`resource\` 안에 `docs` 외에 무엇이 있는지** — templates / scripts / plugins / postprocessors 등
3. **`resource\docs` 안에 언어 폴더가 있는지** — en / ja / ko / zh 등 자동 탐지

## 실행 방법 (둘 중 하나)

### A. PowerShell (설치 불필요, 권장)

Windows에서 PowerShell을 열고:

```powershell
powershell -ExecutionPolicy Bypass -File .\scan_folder.ps1
```

경로가 다르면:

```powershell
powershell -ExecutionPolicy Bypass -File .\scan_folder.ps1 -Root "C:\ezcam\1.1_1.1" -MaxDepth 6
```

### B. Python (Python 3 설치되어 있을 때)

```bat
python scan_folder.py
```

경로가 다르면:

```bat
python scan_folder.py --root "C:\ezcam\1.1_1.1" --max-depth 6
```

## 결과물

같은 폴더에 두 파일이 생성됩니다.

| 파일 | 용도 |
|------|------|
| `scan_report.txt` | 사람이 읽는 폴더 트리 + 요약 |
| `scan_report.json` | 프로그램이 읽는 구조화 데이터 |

이 **두 파일을 보내주시면** 자동화 전략을 잡을 수 있습니다.

## 참고

- 접근 권한이 없는 파일/폴더는 조용히 건너뜁니다 (스캔이 중단되지 않음).
- `--max-depth` 로 트리 깊이를 조절할 수 있습니다 (기본 6단계).
- 파일 **내용**은 읽지 않고, 이름·크기·확장자만 수집합니다.
