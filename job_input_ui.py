# -*- coding: utf-8 -*-
"""
job_input_ui.py - Job / Step 생성 후 DATA 폴더를 ezCAM 으로 Input 하는 창

사용 순서
  1) ezCAM 을 실행하고 로그인해 둔다.
  2) 아래 JOB_SITE_LINK 정션을 한 번 만들어 둔다 (최초 1회, 관리자 권한 불필요):
         mklink /J C:\\ezjob "C:\\----------Job Site\\③---Job"
  3) python job_input_ui.py

정션을 쓰는 이유
  작업 폴더 경로에 선행 하이픈(----------), 공백, 특수문자(③)가 들어 있다.
  ezCAM 은 내부적으로 csh / awk / sed 같은 옛 유닉스 도구를 쓰는데
  - 하이픈으로 시작하는 경로를 명령 옵션으로 오해하고
  - CP949 2바이트 문자를 CP950 으로 잘못 해석한다.
  정션으로 순수 ASCII 별칭을 하나 만들어 ezCAM 에는 그 경로만 넘긴다.
  실제 파일은 그대로 있고 Total Commander 에서도 원래 경로를 계속 쓰면 된다.
"""

import os
import queue
import re
import threading
import tkinter as tk
from tkinter import ttk, filedialog

from ezgw import Gateway, EzcamError, to_cam_path

# ---------------------------------------------------------------------------
# 현장 설정
# ---------------------------------------------------------------------------

# 사람이 보는 실제 경로
JOB_SITE_REAL = r"C:\----------Job Site\③---Job"

# ezCAM 에 넘기는 ASCII 별칭 (mklink /J 로 만든 정션)
JOB_SITE_LINK = r"C:\ezjob"

DATA_SUBDIR = "DATA"
SOURCE_SUBDIR = "원본"

DATABASE = "ezcam"

# Input 리포트를 남길 곳
REPORT_DIR = r"C:\ezcam\tmp\input_report"

# 스케일 오판 경보 기준. Excellon 자동 판별이 틀리면 이 배수로 어긋난다.
SUSPECT_RATIOS = {
    25.4: "inch / mm 오판",
    10.0: "좌표 형식 오판 (2.4 ↔ 3.3 또는 2.4 ↔ 2.5)",
    100.0: "좌표 형식 2단계 오판",
}
RATIO_TOLERANCE = 0.02   # 2% 이내면 그 배수로 본다


# ---------------------------------------------------------------------------
# 작업 로직 (UI 와 분리)
# ---------------------------------------------------------------------------

VALID_NAME = re.compile(r"^[A-Za-z0-9._+-]+$")


def validate_name(kind, value):
    """ezCAM entity 이름 검사. 한글이나 공백이 들어가면 나중에 반드시 깨진다."""
    if not value:
        raise ValueError("%s 이름이 비어 있습니다." % kind)
    if not VALID_NAME.match(value):
        raise ValueError(
            "%s 이름에 쓸 수 없는 문자가 있습니다: %r\n"
            "영문, 숫자, . _ + - 만 쓰세요. 한글과 공백은 안 됩니다." % (kind, value)
        )


def resolve_data_dir():
    """ezCAM 에 넘길 DATA 폴더 경로. 정션이 있으면 그쪽을 쓴다."""
    linked = os.path.join(JOB_SITE_LINK, DATA_SUBDIR)
    if os.path.isdir(linked):
        return linked

    real = os.path.join(JOB_SITE_REAL, DATA_SUBDIR)
    if os.path.isdir(real):
        raise EzcamError(
            "DATA 폴더는 있지만 정션이 없습니다.\n"
            "명령 프롬프트에서 아래를 한 번 실행하세요:\n\n"
            '  mklink /J %s "%s"' % (JOB_SITE_LINK, JOB_SITE_REAL)
        )
    raise EzcamError("DATA 폴더를 찾을 수 없습니다: %s" % linked)


def normalize_to_link(path):
    """실제 경로(하이픈/③ 포함)로 들어오면 ASCII 별칭 경로로 바꾼다.

    '찾아보기' 로 정션 하위 폴더를 고르면 윈도우 대화상자가 정션을 풀어
    실제 경로(JOB_SITE_REAL)를 돌려주는 경우가 있다. ezCAM 에는 반드시
    별칭(JOB_SITE_LINK)만 넘겨야 하므로 여기서 되돌린다.
    """
    real = os.path.normcase(os.path.normpath(JOB_SITE_REAL))
    norm = os.path.normcase(os.path.normpath(path))
    if norm == real or norm.startswith(real + os.sep):
        return JOB_SITE_LINK + path[len(JOB_SITE_REAL):]
    return path


def parse_limits(info_dict, prefix):
    """INFO 가 돌려준 gXXX_LIMITSxmin 같은 값들을 (xmin,ymin,xmax,ymax) 로."""
    try:
        return (
            float(info_dict["%sxmin" % prefix]),
            float(info_dict["%symin" % prefix]),
            float(info_dict["%sxmax" % prefix]),
            float(info_dict["%symax" % prefix]),
        )
    except (KeyError, ValueError):
        return None


def ratio_warning(profile_box, layer_box):
    """드릴 레이어가 프로파일 대비 배수로 어긋났는지 본다."""
    if not profile_box or not layer_box:
        return None

    p_width = profile_box[2] - profile_box[0]
    l_width = layer_box[2] - layer_box[0]
    if p_width <= 0 or l_width <= 0:
        return None

    ratio = l_width / p_width
    for suspect, reason in SUSPECT_RATIOS.items():
        for candidate in (suspect, 1.0 / suspect):
            if abs(ratio / candidate - 1.0) < RATIO_TOLERANCE:
                return "배율 %.4f 배 어긋남 - %s" % (ratio, reason)
    return None


class InputJob:
    """Job 생성 -> Step 생성 -> Data Input -> 스케일 검증."""

    def __init__(self, gateway, log):
        self.gw = gateway
        self.log = log

    def run(self, job, step, data_dir, gbr_units, drl_units, copy_to_job):
        cam_data = to_cam_path(data_dir)
        os.makedirs(REPORT_DIR, exist_ok=True)
        report = to_cam_path(os.path.join(REPORT_DIR, "%s_inp.txt" % job))

        self._ensure_job(job)
        self._ensure_step(job, step)
        self._input(job, step, cam_data, report, gbr_units, drl_units, copy_to_job)
        self._save(job)
        self._verify(job, step)

    # -- 단계별 ------------------------------------------------------------

    def _ensure_job(self, job):
        if self.gw.job_exists(job):
            self.log("Job 이 이미 있습니다. 그대로 엽니다: %s" % job)
        else:
            self.log("Job 생성: %s" % job)
            # genClasses.py Top.createJob() 와 동일한 형식:
            #   create_entity,job=,is_fw=no,type=job,name=<job>,db=<db>,fw_type=form
            # 새 Job 은 job= 을 비워 두고, fw_type=form 을 함께 준다.
            self.gw.com("create_entity", job="", is_fw="no", type="job",
                        name=job, db=DATABASE, fw_type="form")

        self.gw.com("open_job", job=job)
        self.log("Job 열림")

    def _ensure_step(self, job, step):
        if step in self.gw.step_list(job):
            self.log("Step 이 이미 있습니다: %s" % step)
        else:
            self.log("Step 생성: %s" % step)
            self.gw.com("create_entity", job=job, is_fw="no", type="step",
                        name=step, fw_type="form")

        # skip_gui=yes 는 화면을 띄우지 않고 내부 실체만 만든다.
        # 문서에 "ezCAM 을 API 로 호출할 때 유용하다" 고 명시된 옵션.
        self.gw.com("open_entity", job=job, type="step", name=step,
                    skip_gui="yes")
        self.log("Step 열림")

    def _input(self, job, step, cam_data, report, gbr_units, drl_units,
               copy_to_job):
        # genCommands.py inputAuto() 는 input_identify / input_auto 의 STATUS 를
        # 확인하지 않고 진행한다. input_identify 는 non-zero(예: 1000)를 정보성으로
        # 돌려줄 수 있으므로 여기서도 check=False 로 두고, 실제 성공 여부는 뒤의
        # 스케일검증(레이어가 실제로 올라왔는지)으로 판단한다.
        self.log("파일 식별 중: %s" % cam_data)
        st = self.gw.com(
            "input_identify",
            check=False,
            path=cam_data,
            job=job,
            script_path=report + "_id",
            unify="yes",
            gbr_ext="yes",
            drl_ext="yes",
            gbr_units=gbr_units,
            drl_units=drl_units,
            break_sr="no",
        )
        self.log("  input_identify STATUS=%d (0 이 아니어도 계속 진행)" % st)

        self.log("Input 실행 중 (Gerber=%s, Excellon=%s)" % (gbr_units, drl_units))
        st = self.gw.com(
            "input_auto",
            check=False,
            path=cam_data,
            job=job,
            step=step,
            report_path=report,
            copy_to_job="yes" if copy_to_job else "no",
        )
        self.log("  input_auto STATUS=%d" % st)
        self.log("Input 완료. 리포트: %s" % report)

    def _save(self, job):
        """Input 결과를 디스크에 저장한다.

        genCommands.py 의 save() 와 동일한 형식:
            save_job,job=<job>,override=no
        (override=yes 는 online 위반을 무시하고 저장). 이 호출이 없으면
        close_job/unload 시 Input 결과가 소실된다.
        """
        self.log("Job 저장 중: %s" % job)
        self.gw.com("save_job", job=job, override="no")
        self.log("Job 저장 완료")

    def _verify(self, job, step):
        """Excellon 이 Gerber 와 1:1 로 올라왔는지 크기로 확인한다.

        데이터 타입 이름은 genClasses.py 로 확정:
          - step 프로파일: -d PROF_LIMITS  -> gPROF_LIMITSxmin/ymin/xmax/ymax
          - layer 범위    : -d LIMITS       -> gLIMITSxmin/ymin/xmax/ymax
          - step 레이어목록: -d LAYERS_LIST  -> gLAYERS_LIST
        """
        self.log("-" * 50)
        self.log("스케일 검증")

        step_info = self.gw.info("-t step -e %s/%s -d PROF_LIMITS" % (job, step))
        profile_box = parse_limits(step_info, "gPROF_LIMITS")
        if not profile_box:
            self.log("  프로파일 크기를 읽지 못했습니다. 데이터 타입 이름을 확인하세요.")
            return

        p_width = profile_box[2] - profile_box[0]
        p_height = profile_box[3] - profile_box[1]
        self.log("  프로파일: %.4f x %.4f" % (p_width, p_height))

        layers = self.gw.info(
            "-t step -e %s/%s -d LAYERS_LIST" % (job, step)
        ).get("gLAYERS_LIST", [])

        problems = []
        for layer in layers:
            layer_info = self.gw.info(
                "-t layer -e %s/%s/%s -d LIMITS" % (job, step, layer)
            )
            box = parse_limits(layer_info, "gLIMITS")
            warning = ratio_warning(profile_box, box)
            if warning:
                problems.append("  [!] %s : %s" % (layer, warning))

        if problems:
            self.log("스케일이 맞지 않는 레이어가 있습니다:")
            for line in problems:
                self.log(line)
            self.log("")
            self.log("Excellon 단위를 auto 대신 inch 또는 mm 로 지정하고 다시 실행하세요.")
        else:
            self.log("  모든 레이어가 프로파일과 같은 축척입니다.")


# ---------------------------------------------------------------------------
# 창
# ---------------------------------------------------------------------------

class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("ezCAM Data Input")
        self.resizable(False, False)

        self.messages = queue.Queue()
        self.worker = None

        self._build()
        self.after(100, self._drain)

    def _build(self):
        pad = {"padx": 8, "pady": 4}
        frame = ttk.Frame(self, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frame, text="Job name").grid(row=0, column=0, sticky="w", **pad)
        self.job_var = tk.StringVar()
        job_entry = ttk.Entry(frame, textvariable=self.job_var, width=42)
        job_entry.grid(row=0, column=1, columnspan=2, sticky="we", **pad)
        job_entry.focus()

        # ezCAM UID. demo.vbs 처럼 ezCAM > Actions > Copy UID to clipboard 로
        # 복사해 붙여넣는다. 비워 두면 ezgw 가 세션 자동탐색(WHO *)을 시도한다.
        ttk.Label(frame, text="ezCAM UID").grid(row=1, column=0, sticky="w", **pad)
        self.uid_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.uid_var, width=42).grid(
            row=1, column=1, columnspan=2, sticky="we", **pad)

        ttk.Label(frame, text="Step").grid(row=2, column=0, sticky="w", **pad)
        self.step_var = tk.StringVar(value="org")
        ttk.Entry(frame, textvariable=self.step_var, width=42).grid(
            row=2, column=1, columnspan=2, sticky="we", **pad)

        ttk.Label(frame, text="DATA 폴더").grid(row=3, column=0, sticky="w", **pad)
        self.data_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.data_var, width=34).grid(
            row=3, column=1, sticky="we", **pad)
        ttk.Button(frame, text="찾아보기", command=self._browse).grid(
            row=3, column=2, sticky="we", **pad)

        ttk.Separator(frame, orient="horizontal").grid(
            row=4, column=0, columnspan=3, sticky="we", pady=8)

        ttk.Label(frame, text="Gerber274x 단위").grid(row=5, column=0, sticky="w", **pad)
        self.gbr_var = tk.StringVar(value="auto")
        ttk.Combobox(frame, textvariable=self.gbr_var, width=10, state="readonly",
                     values=["auto", "inch", "mm"]).grid(row=5, column=1, sticky="w", **pad)

        ttk.Label(frame, text="Excellon 단위").grid(row=6, column=0, sticky="w", **pad)
        self.drl_var = tk.StringVar(value="auto")
        ttk.Combobox(frame, textvariable=self.drl_var, width=10, state="readonly",
                     values=["auto", "inch", "mm"]).grid(row=6, column=1, sticky="w", **pad)

        ttk.Label(
            frame,
            text="Excellon 이 Gerber 와 크기가 안 맞으면 auto 대신 단위를 직접 지정하세요.",
            foreground="#555555",
        ).grid(row=7, column=0, columnspan=3, sticky="w", padx=8)

        self.copy_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="원본 파일을 job 안에 복사해 보관",
                        variable=self.copy_var).grid(
            row=8, column=0, columnspan=3, sticky="w", **pad)

        self.start_btn = ttk.Button(frame, text="작업시작", command=self._start)
        self.start_btn.grid(row=9, column=0, columnspan=3, sticky="we", padx=8, pady=10)

        self.log_box = tk.Text(frame, width=72, height=18, wrap="word",
                               font=("Consolas", 9))
        self.log_box.grid(row=10, column=0, columnspan=3, sticky="nsew", padx=8)
        self.log_box.configure(state="disabled")

        # 시작할 때 DATA 폴더를 미리 채워 준다.
        try:
            self.data_var.set(resolve_data_dir())
        except EzcamError as exc:
            self.data_var.set("")
            self._log(str(exc))

    def _browse(self):
        start = self.data_var.get() or JOB_SITE_LINK
        chosen = filedialog.askdirectory(initialdir=start, title="DATA 폴더 선택")
        if chosen:
            self.data_var.set(normalize_to_link(os.path.normpath(chosen)))

    def _log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _drain(self):
        """작업 스레드가 보낸 메시지를 창에 옮긴다."""
        while True:
            try:
                kind, payload = self.messages.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                self._log(payload)
            elif kind == "done":
                self.start_btn.configure(state="normal", text="작업시작")
        self.after(100, self._drain)

    def _start(self):
        if self.worker and self.worker.is_alive():
            return

        job = self.job_var.get().strip()
        step = self.step_var.get().strip()
        uid = self.uid_var.get().strip()
        data_dir = normalize_to_link(self.data_var.get().strip())

        try:
            validate_name("Job", job)
            validate_name("Step", step)
            if not os.path.isdir(data_dir):
                raise ValueError("DATA 폴더가 없습니다: %s" % data_dir)
        except ValueError as exc:
            self._log("입력 확인 필요 - %s" % exc)
            return

        self.start_btn.configure(state="disabled", text="작업 중")
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

        self.worker = threading.Thread(
            target=self._run,
            args=(job, step, uid, data_dir, self.gbr_var.get(), self.drl_var.get(),
                  self.copy_var.get()),
            daemon=True,
        )
        self.worker.start()

    def _run(self, job, step, uid, data_dir, gbr_units, drl_units, copy_to_job):
        def log(text):
            self.messages.put(("log", text))

        try:
            log("ezCAM 세션 확인 중")
            # UID 를 입력했으면 그대로 쓰고, 비었으면 ezgw 가 자동탐색한다.
            gateway = Gateway(uid=uid) if uid else Gateway()
            log("연결: %s" % gateway.uid)
            log("-" * 50)

            InputJob(gateway, log).run(
                job, step, data_dir, gbr_units, drl_units, copy_to_job)

            log("-" * 50)
            log("끝났습니다.")
        except EzcamError as exc:
            log("")
            log("중단됨: %s" % exc)
        except Exception as exc:                      # noqa: BLE001
            log("")
            log("예상치 못한 오류: %r" % exc)
        finally:
            self.messages.put(("done", None))


if __name__ == "__main__":
    App().mainloop()
