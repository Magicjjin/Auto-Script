# -*- coding: utf-8 -*-
"""
ezgw.py - ezCAM Gateway 통신 계층

실행 중인 ezCAM 세션에 gateway.exe 를 통해 COM 명령을 보내고
INFO 결과를 파이썬 자료구조로 되돌려 받는다.

전제:
  - ezCAM 이 이미 실행되어 로그인된 상태여야 한다.
    (무인 실행은  ezcam -b -u "아이디" -p "비밀번호"  로 띄운다)
  - gateway.exe 는 C:\\ezcam\\1.1_1.1\\bin\\gateway.exe 에 있다.

참고한 원본:
  resource/vbs/gateway.vbs      (Frank Yeh, 2015) - COM / DO_INFO 패턴
  resource/python/genClasses.py (Mike J. Hopkins, 2004) - INFO 출력 파싱
"""

import os
import re
import subprocess
import tempfile
import time

# ---------------------------------------------------------------------------
# 기본 설정
# ---------------------------------------------------------------------------

GATEWAY_EXE = r"C:\ezcam\1.1_1.1\bin\gateway.exe"

# ezCAM 이 임시 파일을 쓰고 파이썬이 읽는 공용 폴더.
# ezCAM 쪽은 항상 슬래시(/) 경로를 쓴다.
TMP_DIR = r"C:\ezcam\tmp"

# ezCAM 내부 도구가 유니코드를 모르므로 출력은 한글 Windows 기본 코드페이지로 읽는다.
CONSOLE_ENCODING = "cp949"

# COM 명령의 STATUS 반환값. 0 이 성공.
STATUS_OK = 0


class EzcamError(Exception):
    """gateway 호출 실패 또는 COM 명령 실패."""


def to_cam_path(path):
    """윈도우 경로를 ezCAM 이 받아들이는 슬래시 경로로 바꾼다.

    ezCAM 은 c:/ezcam/sys/scripts/ 처럼 항상 슬래시를 쓴다.
    """
    return str(path).replace("\\", "/")


class Gateway:
    """ezCAM 한 세션에 대한 원격 조종 핸들."""

    def __init__(self, uid=None, gateway_exe=GATEWAY_EXE, tmp_dir=TMP_DIR,
                 timeout=300):
        if not os.path.isfile(gateway_exe):
            raise EzcamError("gateway.exe 를 찾을 수 없습니다: %s" % gateway_exe)

        self.gateway_exe = gateway_exe
        self.tmp_dir = tmp_dir
        self.timeout = timeout
        self.uid = uid or self.pick_session(gateway_exe, timeout)

        os.makedirs(self.tmp_dir, exist_ok=True)

    # -- 저수준 -------------------------------------------------------------

    @staticmethod
    def _exec(args, timeout):
        """gateway.exe 를 한 번 호출하고 표준출력을 문자열로 돌려준다."""
        try:
            done = subprocess.run(
                args,
                capture_output=True,
                timeout=timeout,
                # 리스트로 넘기면 공백이 든 인자를 윈도우가 알아서 인용해 준다.
                shell=False,
            )
        except subprocess.TimeoutExpired:
            raise EzcamError("gateway 응답 시간 초과: %s" % " ".join(args))

        out = done.stdout.decode(CONSOLE_ENCODING, errors="replace").strip()
        err = done.stderr.decode(CONSOLE_ENCODING, errors="replace").strip()
        if done.returncode != 0 and not out:
            raise EzcamError("gateway 실행 실패 (%d): %s" % (done.returncode, err))
        return out

    # -- 세션 ---------------------------------------------------------------

    @classmethod
    def list_sessions(cls, gateway_exe=GATEWAY_EXE, timeout=30):
        """실행 중인 ezCAM 세션의 UID 목록.

        UID 형식:  사용자@호스트.사용자.PID
        예:        g@BELLA-PC.Bella.A000EC.7832
        """
        out = cls._exec([gateway_exe, "WHO *"], timeout)
        return [line.strip() for line in out.splitlines() if line.strip()]

    @classmethod
    def pick_session(cls, gateway_exe=GATEWAY_EXE, timeout=30):
        """세션이 정확히 하나면 그것을 쓴다. 없거나 여럿이면 사람이 골라야 한다."""
        sessions = cls.list_sessions(gateway_exe, timeout)
        if not sessions:
            raise EzcamError(
                "실행 중인 ezCAM 세션이 없습니다. ezCAM 을 먼저 실행하고 로그인하세요."
            )
        if len(sessions) > 1:
            raise EzcamError(
                "ezCAM 세션이 %d 개입니다. UID 를 직접 지정하세요:\n  %s"
                % (len(sessions), "\n  ".join(sessions))
            )
        return sessions[0]

    # -- COM ----------------------------------------------------------------

    def com(self, name, /, check=True, **params):
        """COM 명령 하나를 보낸다.

        사용 예:
            gw.com("open_job", job="l26p06014t88-tr3-m07")
            gw.com("open_entity", job=j, type="step", name="pcs", skip_gui="yes")

        반환값은 STATUS 정수. 0 이 성공.
        check=True 면 0 이 아닐 때 예외를 던진다.

        name 은 위치 전용 인자다. COM 명령 중에는 entity 의 "name" 필드를
        키워드로 받아야 하는 것들이 있는데 (create_entity, open_entity 등),
        name 이 일반 키워드 인자면 그 값과 충돌해
        "got multiple values for argument 'name'" 이 난다.
        """
        parts = [name]
        for key, value in params.items():
            parts.append("%s=%s" % (key, value))
        command = "COM " + ",".join(parts)

        raw = self._exec([self.gateway_exe, self.uid, command], self.timeout)

        match = re.search(r"-?\d+", raw)
        status = int(match.group()) if match else -1

        if check and status != STATUS_OK:
            raise EzcamError("COM 실패 (STATUS=%d): %s" % (status, command))
        return status

    def comans(self):
        """직전 COM 명령의 응답값(COMANS)."""
        return self._exec([self.gateway_exe, self.uid, "COMANS"], self.timeout)

    def com_get(self, name, /, **params):
        """값을 돌려주는 COM 명령용. 실행 후 COMANS 를 바로 반환한다.

        예: gw.com_get("get_units")        -> "Inch"
            gw.com_get("get_select_count") -> "137"
        """
        self.com(name, **params)
        return self.comans()

    # -- INFO ---------------------------------------------------------------

    def info(self, args, units="inch"):
        """INFO 명령 결과를 dict 로 돌려준다.

        ezCAM 은 결과를 csh 문법의 파일로 쓴다:
            set gSTEPS_LIST = ('org' 'net' 'pcb' 'wpnl')
            set gEXISTS = yes
        이것을 파싱해 {'gSTEPS_LIST': ['org','net','pcb','wpnl'], 'gEXISTS': 'yes'}
        형태로 만든다.

        args 예:
            "-t root -d JOBS_LIST"
            "-t job -e 품번 -d EXISTS"
            "-t job -e 품번 -d STEPS_LIST"
            "-t step -e 품번/pcs -d PROFILE_LIMITS"
            "-t layer -e 품번/pcs/drl -d LIMITS"

        entity type: root / job / step / layer / matrix / check
        """
        fd, tmp_path = tempfile.mkstemp(prefix="info_", suffix=".tmp",
                                        dir=self.tmp_dir)
        os.close(fd)

        try:
            self.com(
                "info",
                args=args,
                out_file=to_cam_path(tmp_path),
                write_mode="replace",
                units=units,
            )
            # ezCAM 이 파일을 다 쓸 때까지 아주 잠깐 기다린다.
            for _ in range(20):
                if os.path.getsize(tmp_path) > 0:
                    break
                time.sleep(0.05)

            with open(tmp_path, "r", encoding=CONSOLE_ENCODING,
                      errors="replace") as handle:
                return self._parse_info(handle.read())
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    @staticmethod
    def _parse_info(text):
        """csh 의 set 문을 파이썬 dict 로."""
        result = {}
        pattern = re.compile(r"^\s*set\s+(\w+)\s*=\s*(.+?)\s*$")

        for line in text.splitlines():
            match = pattern.match(line)
            if not match:
                continue
            key, value = match.group(1), match.group(2)

            if value.startswith("(") and value.endswith(")"):
                inner = value[1:-1]
                items = re.findall(r"'([^']*)'|(\S+)", inner)
                result[key] = [a or b for a, b in items]
            else:
                result[key] = value.strip("'\"")
        return result

    # -- 자주 쓰는 조회 ------------------------------------------------------

    def job_exists(self, job):
        return self.info("-t job -e %s -d EXISTS" % job).get("gEXISTS") == "yes"

    def job_list(self):
        return self.info("-t root -d JOBS_LIST").get("gJOBS_LIST", [])

    def step_list(self, job):
        return self.info("-t job -e %s -d STEPS_LIST" % job).get("gSTEPS_LIST", [])
