# ezcam 자동화 심층분석 (폴더 스캔 기반)

스캔 대상: `C:\ezcam\1.1_1.1`  (버전 1.1_1.1, 폴더 45개 / 파일 1031개)

## 1. 결론 요약

ezcam 은 **Genesis 2000 (Frontline) 계열의 PCB CAM 툴** 이며,
**외부 제어용 API/스크립트 엔진이 이미 내장**되어 있다.
따라서 UI 자동화(pywinauto 로 창·버튼 클릭 흉내)는 **불필요**하고,
아래 3가지 공식 경로 중 하나로 Job/Step 생성·데이터 Input 을 코드 제어할 수 있다.

| 경로 | 근거 파일 | 특징 |
|------|-----------|------|
| **Gateway API** | `bin\gateway.exe`, `resource\vbs\gateway.vbs`, `resource\vbs\demo.vbs`, `resource\vb6\gateway.bas`, `resource\vb.net\gateway.vb` | 외부 프로세스(VBScript/VB/VB.NET/Python)에서 ezcam 을 제어. **1순위 후보** |
| **csh 스크립트** | `bin\csh.exe`, `csh_syntax_checker.exe`, `csh_dbg_parser.exe`, `resource\scripts\ezcam_scr_start.csh` | ezcam 내부 명령어를 csh 스크립트로 실행 (Genesis COM 방식) |
| **Python API** | `resource\python\genCommands.py`, `genClasses.py`, `genFeatures.py`, `odb.py` | Genesis 스타일 Python 바인딩. ODB++ 처리 포함 |

서버 프로세스 `ezServer.exe` / `ezServerd.exe` 가 외부 명령 수신 채널로 보인다.

## 2. 세 가지 초기 질문에 대한 답

1. **루트 바로 아래 구성**
   - 실행파일: `ezcam.exe`(35MB), 버전별 `ezcam_191209.exe`, `ezcam_200506.exe`, `ezcam_v202112.EXE`(134MB), `ezServer.exe`, `ezServerd.exe`
   - 폴더: `bin`(GNU 유틸 + 엔진), `languages`(.po 번역), `lib`(compare.dll 등), `resource`

2. **resource 안 (docs 외)**
   - 자동화 관련: `scripts`, `python`, `vbs`, `vb6`, `vb.net`, `server`
   - 데이터/설정: `erf_map`, `imp`(imp_template.xls), `report`(xlsx 템플릿), `markers`, `fonts`, `fonts_ex`, `icons`, `ui`

3. **docs 언어 폴더**
   - `resource\docs\zh-tw` **번체 중국어만** 존재. en/ja/ko 없음.
   - 단, 핵심 문서가 HTML 이라 파싱/번역 용이. Genesis 2000 호환이라 영문 Genesis 레퍼런스도 상당수 호환.

## 3. 핵심 문서 (zh-tw\system, HTML)

| 파일 | 크기 | 내용 |
|------|------|------|
| `commands.html` | 124.9 KB | **전체 명령어 레퍼런스** (자동화의 핵심) |
| `config.html` | 60.8 KB | 설정 |
| `cli_args.html` | 14.2 KB | 명령줄 인자 |
| `gateway.html` | 8.7 KB | **Gateway(외부 제어) API** |
| `g2k_compatibility.html` | 15.4 KB | **Genesis 2000 호환성** (정체 확인) |
| `script_debugger.html` | 13.2 KB | 스크립트 디버거 |
| `bin_tools.html` | 19.3 KB | bin 유틸 설명 |
| `commands` 외 `input_output\input.html` | 12.6 KB | **데이터 Input** 문서 |
| `input_output\output.html` | 14.6 KB | 데이터 Output 문서 |

## 4. 자동화 전략 (제안)

목표 워크플로우: **Job/Step 입력 → DATA 폴더 파일 자동 Input → Gerber274X/Excellon View 정합**

1. **1단계 (완료)**: `job_input_ui.py` — Job/Step 입력창, DATA 파일 목록, 로그. (UI 껍데기)
2. **2단계 (다음)**: Gateway 또는 csh 스크립트로 실제 Input 연동
   - `demo.vbs` / `gateway.vbs` 를 분석해 명령 호출 패턴 파악
   - `commands.html` 에서 Job 생성, Step 생성, layer input, `INPUT` 관련 명령 추출
   - `input.html` 에서 Gerber274X / Excellon Parameters 옵션 확인
3. **3단계**: Gerber274X ↔ Excellon **View 정합 자동화**
   - 두 Format 의 unit / coordinate / number format / zeros-omitted 를 동일 기준으로 강제
   - View 크기 불일치 시 해당 layer 의 Parameters 를 스크립트로 재설정
   - (문제 지점) Excellon 이 Gerber 대비 크거나 작게 뜨는 것은 대개 unit(inch/mm) 또는
     number format(정수/소수 자릿수) 불일치 → 명령으로 통일하면 해결 가능

## 5. 다음 단계에 필요한 파일 (텍스트로 전달 요망)

자동화 코드를 실제로 붙이려면 아래 파일 내용이 필요하다. 모두 텍스트/HTML 이라 복사 가능.

1. `resource\vbs\demo.vbs`  ← **가장 중요** (동작하는 Gateway 예제)
2. `resource\vbs\gateway.vbs`
3. `resource\docs\zh-tw\system\gateway.html`
4. `resource\docs\zh-tw\system\commands.html` (핵심, 큼 — Job/Step/Input 부분 위주라도)
5. `resource\docs\zh-tw\system\cli_args.html`
6. `resource\docs\zh-tw\input_output\input.html`
7. `resource\python\genCommands.py`
8. `resource\scripts\ezcam_scr_start.csh`

## 6. 특수문자 경로 주의

작업 경로 `C:\----------Job Site\③---Job\` 의 `③`(원문자) 는
Gateway/csh 로 넘길 때 프로그램이 유니코드를 못 받으면 문제가 될 수 있다.
→ 2단계 연동 시 short path(8.3) 변환(`win32api.GetShortPathName`) 을 대비책으로 둔다.
