#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAM Job Input UI  (1단계 - UI 껍데기)

목표:
  - Job name, Step 을 입력하는 Windows 활성창 생성
  - "작업시작" 버튼 클릭 시 입력된 Job/Step 으로 DATA 폴더 경로를 구성하고
    그 안의 Input 대상 파일들을 목록으로 수집
  - 이후 CAM 프로그램(ezcam 등)에 실제로 Input 하는 부분은
    run_cam_input() 함수 안에 연동 코드를 채워 넣으면 된다 (지금은 자리만 비움).

특수문자 경로 대응:
  - 작업 폴더 경로에 ③, 공백, - 같은 문자가 있어도
    pathlib.Path 와 UTF-8 로 안전하게 처리한다.
  - 실제 CAM 프로그램에 경로를 넘길 때 그 프로그램이 유니코드를 못 받으면
    그때 short path(8.3) 변환 등을 추가로 고려한다. (TODO 참고)

실행:
    python job_input_ui.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# tkinter 는 UI 를 띄울 때만 필요하다. (Windows 표준 Python 에 기본 내장)
# 로직 함수만 import 해서 테스트할 수 있도록 여기서는 불러오지 않는다.

# ---------------------------------------------------------------------------
# 설정 (필요에 맞게 수정)
# ---------------------------------------------------------------------------

# 주 작업 폴더 기본 경로 (특수문자 포함 예시)
DEFAULT_BASE_DIR = r"C:\----------Job Site\③---Job"

# 기본 하위 폴더명
ORIGINAL_SUBDIR = "원본"   # 원본 보관 폴더
DATA_SUBDIR = "DATA"      # Input 대상 데이터 폴더

# Input 대상에서 제외할 확장자 (Input package 창의 Exclude 목록과 동일 취지)
EXCLUDE_EXTS = {
    ".tar", ".rar", ".zip", ".tgz", ".exe", ".gz",
    ".xls", ".jpg", ".doc", ".docx",
}

# Format 자동 판별 규칙 (확장자 -> Format 이름)
#   실제 규칙은 회사 데이터 명명 규칙에 맞게 확장하면 된다.
FORMAT_BY_EXT = {
    ".art": "Gerber274X",
    ".gbr": "Gerber274X",
    ".ger": "Gerber274X",
    ".drl": "Excellon",
    ".exc": "Excellon",
    ".txt": "Excellon",   # 드릴 파일이 .txt 인 경우가 있어 참고용
}


# ---------------------------------------------------------------------------
# 핵심 로직
# ---------------------------------------------------------------------------

def build_data_path(base_dir: str, job: str, step: str) -> Path:
    """base_dir / DATA 경로를 구성한다. (job/step 은 하위 구조가 있으면 확장)

    현재는 base_dir\\DATA 를 반환한다. 만약 Job/Step 마다 별도 하위폴더를
    쓴다면 아래 주석처럼 규칙을 바꾸면 된다.
    """
    base = Path(base_dir)
    data_path = base / DATA_SUBDIR
    # 예) Job/Step 별 하위폴더 구조라면:
    # data_path = base / DATA_SUBDIR / job / step
    return data_path


def guess_format(file_path: Path) -> str:
    """파일 확장자로 Format(Gerber274X / Excellon 등)을 추정한다."""
    return FORMAT_BY_EXT.get(file_path.suffix.lower(), "?")


def collect_input_files(data_path: Path):
    """DATA 폴더에서 Input 대상 파일 목록을 수집한다.

    반환: [{name, path, ext, format}] 리스트
    """
    files = []
    if not data_path.is_dir():
        return files
    for entry in sorted(data_path.iterdir()):
        if entry.is_dir():
            continue
        ext = entry.suffix.lower()
        if ext in EXCLUDE_EXTS:
            continue
        files.append({
            "name": entry.name,
            "path": str(entry),
            "ext": ext,
            "format": guess_format(entry),
        })
    return files


def run_cam_input(job: str, step: str, data_path: Path, files: list, logger):
    """실제 CAM 프로그램에 파일을 Input 하는 자리 (아직 미연동).

    여기에 제어 방식이 확정되면 코드를 채운다. 대표적으로 3가지 경로:
      1) CAM 프로그램의 스크립트/매크로/명령줄 API 호출
      2) pywinauto 로 Input package 창을 UI 자동화
      3) COM/OLE 인터페이스

    또한 아래 주의사항(Gerber274X vs Excellon View 정합)을 이 단계에서 처리한다:
      - 두 Format 은 Parameters 값이 다르지만 화면 View 는 1:1 로 일치해야 한다.
      - View 가 크거나 작으면 각 Layer 우클릭 > Parameters 에서 값(단위/좌표/
        number format 등)을 보정해야 한다.
      - 자동화 시에는 Excellon 의 단위/number format 을 Gerber274X 와
        일치하도록 강제 설정하는 로직을 넣는 것이 핵심.
    """
    logger("=" * 50)
    logger(f"[작업시작] Job={job}  Step={step}")
    logger(f"DATA 경로: {data_path}")
    logger(f"Input 대상 파일: {len(files)}개")
    for f in files:
        logger(f"  - {f['name']}  [{f['format']}]")

    # TODO: 실제 CAM 연동 코드
    #   예) subprocess 로 ezcam 매크로 실행, 또는 pywinauto 로 창 제어
    #   예) 특수문자 경로가 문제되면 short path 변환:
    #       import win32api; short = win32api.GetShortPathName(str(data_path))
    logger("")
    logger(">>> (안내) 실제 CAM Input 연동은 아직 연결되지 않았습니다.")
    logger(">>> 제어 방식이 확정되면 run_cam_input() 안을 채우면 됩니다.")
    logger("=" * 50)


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except ImportError:
    # tkinter 미설치 환경(예: 일부 리눅스)에서는 UI 를 못 띄우지만
    # 위의 로직 함수들은 그대로 import/테스트할 수 있다.
    tk = None


class JobInputApp:
    def __init__(self, root):
        self.root = root
        root.title("CAM Job Input")
        root.geometry("640x520")
        root.minsize(560, 460)

        self.base_dir = tk.StringVar(value=DEFAULT_BASE_DIR)
        self.job = tk.StringVar()
        self.step = tk.StringVar()

        self._build_widgets()

    def _build_widgets(self):
        pad = {"padx": 8, "pady": 4}

        # --- 입력 영역 ---
        frm = ttk.LabelFrame(self.root, text="작업 정보 입력")
        frm.pack(fill="x", **pad)

        # 작업 폴더
        ttk.Label(frm, text="작업 폴더").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(frm, textvariable=self.base_dir).grid(row=0, column=1, sticky="ew", padx=6, pady=6)
        ttk.Button(frm, text="찾기…", command=self._pick_base_dir).grid(row=0, column=2, padx=6, pady=6)

        # Job name
        ttk.Label(frm, text="Job name").grid(row=1, column=0, sticky="w", padx=6, pady=6)
        job_entry = ttk.Entry(frm, textvariable=self.job)
        job_entry.grid(row=1, column=1, columnspan=2, sticky="ew", padx=6, pady=6)

        # Step
        ttk.Label(frm, text="Step").grid(row=2, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(frm, textvariable=self.step).grid(row=2, column=1, columnspan=2, sticky="ew", padx=6, pady=6)

        frm.columnconfigure(1, weight=1)

        # --- 버튼 영역 ---
        btnfrm = ttk.Frame(self.root)
        btnfrm.pack(fill="x", **pad)
        ttk.Button(btnfrm, text="DATA 파일 새로고침", command=self._refresh_files).pack(side="left", padx=6)
        start_btn = ttk.Button(btnfrm, text="작업시작", command=self._on_start)
        start_btn.pack(side="right", padx=6)

        # --- 파일 목록 ---
        listfrm = ttk.LabelFrame(self.root, text="DATA 폴더 Input 대상 파일")
        listfrm.pack(fill="both", expand=True, **pad)

        cols = ("name", "format", "ext")
        self.tree = ttk.Treeview(listfrm, columns=cols, show="headings", height=8)
        self.tree.heading("name", text="파일명")
        self.tree.heading("format", text="Format(추정)")
        self.tree.heading("ext", text="확장자")
        self.tree.column("name", width=320)
        self.tree.column("format", width=120, anchor="center")
        self.tree.column("ext", width=80, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        sb = ttk.Scrollbar(listfrm, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)

        # --- 로그 ---
        logfrm = ttk.LabelFrame(self.root, text="로그")
        logfrm.pack(fill="both", expand=True, **pad)
        self.log = tk.Text(logfrm, height=8, wrap="word", state="disabled")
        self.log.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        logsb = ttk.Scrollbar(logfrm, orient="vertical", command=self.log.yview)
        logsb.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=logsb.set)

    # --- 동작 ---
    def _pick_base_dir(self):
        chosen = filedialog.askdirectory(title="작업 폴더 선택")
        if chosen:
            self.base_dir.set(chosen)

    def _logln(self, text: str):
        self.log.configure(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self.log.insert("end", f"[{ts}] {text}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _refresh_files(self):
        data_path = build_data_path(self.base_dir.get(), self.job.get(), self.step.get())
        # 목록 비우기
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        if not data_path.is_dir():
            self._logln(f"[경고] DATA 폴더를 찾을 수 없음: {data_path}")
            return

        files = collect_input_files(data_path)
        for f in files:
            self.tree.insert("", "end", values=(f["name"], f["format"], f["ext"]))
        self._logln(f"DATA 스캔 완료: {data_path}  ({len(files)}개 파일)")
        return files

    def _on_start(self):
        job = self.job.get().strip()
        step = self.step.get().strip()
        if not job:
            messagebox.showwarning("입력 필요", "Job name 을 입력하세요.")
            return
        if not step:
            messagebox.showwarning("입력 필요", "Step 을 입력하세요.")
            return

        data_path = build_data_path(self.base_dir.get(), job, step)
        if not data_path.is_dir():
            messagebox.showerror("경로 오류", f"DATA 폴더가 없습니다:\n{data_path}")
            return

        files = collect_input_files(data_path)
        if not files:
            if not messagebox.askyesno("확인", "Input 대상 파일이 없습니다. 계속할까요?"):
                return

        # 목록 갱신
        self._refresh_files()

        # 실제 CAM Input (지금은 로그만)
        run_cam_input(job, step, data_path, files, self._logln)


def main():
    if tk is None:
        print("[오류] tkinter 를 사용할 수 없습니다. Windows 표준 Python 에서 실행하세요.", file=sys.stderr)
        sys.exit(1)
    root = tk.Tk()
    # Windows 에서 한글/특수문자 표시가 깨지지 않도록 기본 폰트 지정 시도
    try:
        import tkinter.font as tkfont
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family="Malgun Gothic", size=10)
    except Exception:
        pass
    JobInputApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
