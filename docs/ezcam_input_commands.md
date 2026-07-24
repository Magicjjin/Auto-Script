# ezCAM Input 워크플로우 - 명령어 레퍼런스 (commands.html 대조본)

`resource\docs\zh-tw\system\commands.html` 에서 **Input 자동화에 관련된 명령만**
추려 파라미터를 정리한 것. ✅ = 문서에 상세 확인됨, ❌ = 이름만 있고 상세 없음.

## 명령 호출 형식 (csh 기준)

```csh
COM <command>, param=value, param=value      # 명령 실행. 반환값은 $COMANS 에 담김
AUX <command>, param=value                   # 보조 명령 (예: set_group)
INFO ...                                      # 질의
```

`open_entity` 등은 반환된 Group ID($COMANS)를 `AUX set_group, group=$COMANS`
로 넘겨 그 Entity 컨텍스트로 전환한다.

---

## 1. Entity 생성/열기 (✅ 검증됨)

### create_entity  (Engineering Toolkit)
새 Entity 생성.

| 파라미터 | 값 |
|---|---|
| job | 현재 열린 job 이름 (job 생성 시엔 관례상 비움) |
| is_fw | Yes=framework(form/flow), No=CAM entity |
| type | Job / step / symbol / stackup / wheel / matrix |
| fw_type | Form / flow  (**is_fw=yes 일 때만**) |
| Name | 유효한 entity 이름 |
| db | db 이름 (job 생성 시) |

> 주의: step 생성 시 `is_fw=no, type=step` 이면 되고 **fw_type 은 넣지 말 것**.

### open_job  (Engineering Toolkit)
joblist 에 있는 Job 열기.

| 파라미터 | 값 |
|---|---|
| job | joblist 내 존재하는 job |

### open_entity  (Engineering Toolkit)
Job 하위 Entity 열기. **반환값 = Group ID(양의 정수)**.

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| job | string | no | 존재하는 Job |
| type | options | no | step / matrix / attributes / wheel |
| name | string | no | Entity 이름 (필드표엔 "Command"로 적혀있으나 예제는 name=) |
| skip_gui | bool | yes | yes=화면 없이 내부 실체만 생성 (API 호출 시 유용) |
| top/left/width/height/stay_on_top | int/bool | yes | custom_appearance=yes 일 때 |

문서 예제 (그대로 따를 것):
```csh
COM open_entity, job=$JOB, type=step, name=$STEP
AUX set_group, group=$COMANS
```

---

## 2. Input 계열 (genCommands.py inputAuto() 로 확정)

`resource/python/genCommands.py` 의 `inputAuto()` 원본으로 파라미터 확정:
```python
# input_set_params 는 주석처리 = 불필요
STR = 'input_identify,path=%s,job=%s,script_path=%s,unify=yes,gbr_ext=yes,drl_ext=yes,gbr_units=auto,drl_units=auto,break_sr=no'
STR = 'input_auto,path=%s,job=%s,step=%s,report_path=%s,copy_to_job=%s'
```

| 명령 | 상태 | 설명 (문서에 있으면) |
|---|---|---|
| input_identify | ✅ | **확정**. param: `path`, `job`, `script_path`, `unify`, `gbr_ext`, `drl_ext`, `gbr_units`, `drl_units`, `break_sr` |
| input_auto | ✅ | **확정**. param: `path`, `job`, `step`, `report_path`, `copy_to_job` |
| input_set_params | ✅ | genCommands 에서 주석처리됨 = **input_identify+input_auto 만으로 충분** |
| input_manual_set | ❌ | 이름만. 수동 input 파일목록 지정 |
| input_manual | ✅ | 수동 input 실행. param: `script_path` (csh report 경로). 입력창 갱신 안 함 |
| input_manual_reset | ✅ | input_manual 파일목록 리셋 |
| input_copy | ✅ | 원본 입력 디렉토리를 job 디렉토리로 복사. param: `path`, `job`, `delete_source`(Yes/No) |
| input_cur_report | ✅ | 현재 료번 report 를 file 로 출력. param: `path` |
| input_extract_hdr | ✅ | 헤더 추출. param: `format`(Gerber/Pentax/Excellon/Excellon2), `file_path`, `out_path`, `separator` |
| input_dcodes_get / _add / _match / _reset | ✅/❌ | Gerber D-code 처리 |
| input_show_page / input_hide_page | ✅ | 입력 페이지 표시/숨김 |

> **결론:** 실제 Input 을 수행하는 `input_auto` / `input_identify` / `input_set_params`
> 의 정확한 파라미터는 commands.html 에 상세가 없다.
> → **script_record 로 실제 명령을 캡처하는 것이 유일하게 확실한 방법** (아래 참고).

---

## 3. 저장/조회 유틸

| 명령 | 상태 | 설명 |
|---|---|---|
| **save_job** | (목록 존재) | **Input 후 반드시 호출**. 안 하면 close_job/unload 시 결과 소실 |
| close_job | ✅ | 메모리 job 닫기. 변경분은 저장 안 하면 소실 |
| info | ✅ | **gateway.vbs 로 확정**: `COM info, args=..., out_file=..., units=...` (아래 참고) |
| get_units | ✅ | 현재 단위 (Inch/mm) 반환 |
| get_version | ✅ | 버전 반환 |
| get_user_name | ✅ | 로그인 사용자명 반환 |
| ezcam_get_uid | ❌ | (gateway.uid 와 연관 추정) |
| get_work_layer / get_disp_layers / get_affect_layer | ✅ | 레이어 조회 |

---

## 4. 미해결 항목을 확정하는 방법: script_record

`commands.html` 목록에 **`script_record`** 와 **`script_run`** 이 있다.
현장에서 아래 순서로 하면 `input_auto` 등의 **실제 파라미터를 그대로 얻는다**:

1. ezCAM 에서 `script_record` 시작 (또는 UI: Script > Record)
2. Input package 창에서 평소처럼 **수동으로** Job/Step 만들고 DATA 를 Input
3. Gerber274X / Excellon 파라미터도 평소대로 조정
4. record 종료 → 생성된 `.csh` 스크립트를 열면
   `COM input_identify, ...` / `COM input_auto, ...` 의 **진짜 파라미터**가 다 찍혀 있다

이 캡처본을 확보하면 `ezgw.py` 및 `InputJob._input()` 의 파라미터를 확정할 수 있다.

---

## 4-1. gateway.vbs (Frank Yeh, 2015) 대조 결과

원본 `resource/vbs/gateway.vbs` 로 통신 계층을 확정함.

확정된 사실:
- **INFO 는 COM 명령이다**: `DO_INFO` 가 `COMS "info", Array("args="+args,
  "out_file="+unix_file, "units="+Units)` 를 호출 → `COM info,args=...,out_file=...,units=...`.
  ezgw 는 이 형식(args/out_file/units)을 따른다.
  (참고: `write_mode=replace` 도 유효한 파라미터다 — genCommands.py `featOut()` 이
   `info,out_file=...,write_mode=replace,args=...` 로 사용. 다만 ezgw 는 매번 새
   임시파일을 쓰므로 write_mode 없이도 무해하여 생략함.)
- **명령줄 형식**: `gateway.exe <UID> "COM <name>,<params>"` (params 는 콤마 연결, 공백 없음).
- **out_file 은 슬래시 경로**: `Replace(sTmpFile, "\", "/")`.
- **INFO 출력 파싱**: csh `set var = value` 및 `set var = ('v1' 'v2')`.
  단일따옴표 제거 후 dict 로. → ezgw `_parse_info` 와 동일.
- **UID 는 수동 지정**: `INITIALIZE "user@eastek.user.100", "C:\ezcam"`.
  gateway.vbs 는 세션 자동탐색을 하지 않는다. (ezgw 의 `WHO *` 자동탐색은 추정 —
  안 되면 `Gateway(uid="...")` 로 직접 지정)
- **gateway.exe 경로**: gateway.vbs 기본값은 `CAMPath + "\1.1\bin\gateway.exe"` 지만,
  이 설치의 스캔 결과는 `C:\ezcam\1.1_1.1\bin\gateway.exe` (bin\gateway.exe 419KB 확인됨).
  → ezgw 는 `1.1_1.1` 로 설정. (만약 `C:\ezcam\1.1` 도 따로 있으면 확인 필요)
- **COM 은 fire-and-wait**: `CallProcessAndWait` 가 WMI 로 프로세스를 띄우고 종료만
  기다림. **stdout 의 상태값을 읽지 않음.** → ezgw `com()` 은 stdout 에서 상태를
  못 읽으면 성공으로 간주하도록 수정함. (gateway.exe 가 상태를 안 찍을 수 있으므로)

## 4-2. demo.vbs / genCommands.py 대조 결과

- **demo.vbs**: UID 는 ezCAM **Actions > Copy UID to clipboard** 로 얻어 `InputBox` 로
  입력받음. 자동탐색 아님. → UI 에 UID 입력칸 추가함(비우면 자동탐색 fallback).
  또한 `open_entity` 뒤 `set_group` 없이 바로 `DO_INFO` 하는 것을 보여줌 →
  info 질의에는 set_group 불필요 확인.
- **genCommands.py**:
  - `inputAuto()` → input_identify/input_auto 파라미터 확정 (위 2절).
  - `addStep()` → `create_entity,job=..,is_fw=no,type=step,name=..,fw_type=form`.
    **step 에도 fw_type=form 을 쓴다** (앞서 "제거" 권고는 철회).
  - `save()` → `save_job,job=..,override=no`. Input 후 저장에 사용.

## 4-3. genClasses.py (Mike J. Hopkins, 2004) 대조 결과 — 최종 확정

- **step 프로파일 데이터타입은 `PROF_LIMITS`** (PROFILE_LIMITS 아님):
  `getProfile()` 이 `gPROF_LIMITSxmin/ymin/xmax/ymax` 사용. → `_verify` 수정함.
- **layer 범위는 `LIMITS`** → `gLIMITSxmin...` (parseInfo 예제에 `set gLIMITSxmin` 명시). 유지.
- **step 레이어목록은 `LAYERS_LIST`** → `gLAYERS_LIST`. 유지.
- **Job 생성 형식 확정** — `Top.createJob()`:
  `create_entity,job=,is_fw=no,type=job,name=<name>,db=<db>,fw_type=form`.
  → `_ensure_job` 에 빠졌던 `fw_type=form` 추가함. `job=` 빈값도 이걸로 확정.
- **INFO 형식** — `info,out_file=..,write_mode=replace,args=..` (units 없이도 동작).
  ezgw 의 args/out_file/units 조합도 유효(gateway.vbs). 변경 불필요.
- **set_group** — `Step.COM` 이 그룹 있으면 `AUX set_group` 선행. 단 우리 흐름은
  INFO 를 명시 entity 경로로, input 을 명시 step= 로 하므로 set_group 불필요.
- **parseInfo** — ' = ' 분리 + 'set ' 제거 + `(...)` 워드리스트. ezgw `_parse_info` 와 동일.

## 5. job_input_ui.py 반영 상태 (전부 확정)

- [x] Input 완료 후 `save_job,job=..,override=no` 호출 추가 (`_save`)
- [x] UID 입력칸 추가 — 비우면 자동탐색, 채우면 그 UID 사용
- [x] `input_identify`/`input_auto` 파라미터 genCommands.py 로 확정 (수정 불필요)
- [x] step 의 `fw_type="form"` — genCommands.py 로 정당함 확인, 유지
- [x] `_verify` 프로파일 데이터타입 `PROFILE_LIMITS` → **`PROF_LIMITS`** 로 수정 (genClasses.py)
- [x] `_ensure_job` job 생성에 **`fw_type="form"` 추가** (genClasses.py Top.createJob)

→ 문서로 확정 가능한 항목은 모두 완료. 남은 것은 실기 스모크 테스트뿐.
