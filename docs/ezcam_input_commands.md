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

## 2. Input 계열 (핵심 — 대부분 ❌ 상세 미확인)

| 명령 | 상태 | 설명 (문서에 있으면) |
|---|---|---|
| input_identify | ❌ | 이름만. 파일 식별. **파라미터 미확인** |
| input_auto | ❌ | 이름만. 자동 Input 실행. **파라미터 미확인** |
| input_set_params | ❌ | 이름만. Input 파라미터 설정. **미확인** |
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
| info | ❌ | 이름만. 질의 명령. **파라미터/반환형식 미확인** |
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

## 5. 현재 job_input_ui.py 대비 반영할 수정

- [ ] step 의 `create_entity` 에서 `fw_type="form"` 제거
- [ ] `open_entity` 후 `AUX set_group` 컨텍스트 전환 (ezgw 가 자동 처리하지 않는다면)
- [ ] Input 완료 후 `save_job` 호출 추가
- [ ] `input_auto`/`input_identify`/`input_set_params`/`info` 파라미터는
      script_record 캡처로 확정
