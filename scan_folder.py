#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ezcam 설치 폴더 구조 스캐너 (캡처 아님)

지정한 경로(기본: C:\\ezcam\\1.1_1.1)를 재귀적으로 스캔하여
사람이 읽는 트리(scan_report.txt)와 기계가 읽는 JSON(scan_report.json)을 만든다.

특히 아래 세 가지 질문에 답한다.
  1) 설치 폴더 바로 아래에 무엇이 있는지 (exe/dll/txt 등)
  2) resource\\ 안에 docs 외에 무엇이 있는지 (templates/scripts/plugins/postprocessors 등)
  3) resource\\docs 안에 언어 폴더(en/ja/ko/zh 등)가 있는지

사용법:
    python scan_folder.py
    python scan_folder.py --root "C:\\ezcam\\1.1_1.1" --max-depth 6
"""

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime

KNOWN_LANGS = {
    "en", "en-us", "ja", "jp", "ko", "kr",
    "zh", "zh-cn", "zh-tw", "cn", "de", "fr", "es",
}


def human_kb(size_bytes):
    return round(size_bytes / 1024, 1)


def scan_tree(root, max_depth):
    """os.walk 기반 재귀 스캔. (tree_lines, total_dirs, total_files, ext_counter) 반환."""
    tree_lines = []
    total_dirs = 0
    total_files = 0
    ext_counter = Counter()
    root_depth = root.rstrip(os.sep).count(os.sep)

    for dirpath, dirnames, filenames in os.walk(root):
        depth = dirpath.rstrip(os.sep).count(os.sep) - root_depth
        if depth > max_depth:
            dirnames[:] = []  # 더 깊이 내려가지 않음
            continue

        indent = "  " * depth
        folder_name = os.path.basename(dirpath) or dirpath
        tree_lines.append(f"{indent}[{folder_name}]/")
        total_dirs += 1

        for fname in sorted(filenames):
            fpath = os.path.join(dirpath, fname)
            try:
                size = os.path.getsize(fpath)
            except OSError:
                size = 0
            ext = os.path.splitext(fname)[1].lower() or "(none)"
            ext_counter[ext] += 1
            total_files += 1
            tree_lines.append(f"{indent}  - {fname}  ({human_kb(size)} KB)")

        dirnames.sort()

    return tree_lines, total_dirs, total_files, ext_counter


def list_children(path):
    """경로 바로 아래 항목을 [{name,type,sizeKB}] 리스트로 반환."""
    out = []
    if not os.path.isdir(path):
        return out
    try:
        entries = sorted(os.listdir(path))
    except OSError:
        return out
    for name in entries:
        full = os.path.join(path, name)
        is_dir = os.path.isdir(full)
        size_kb = None
        if not is_dir:
            try:
                size_kb = human_kb(os.path.getsize(full))
            except OSError:
                size_kb = None
        out.append({
            "name": name,
            "type": "dir" if is_dir else "file",
            "sizeKB": size_kb,
        })
    return out


def main():
    parser = argparse.ArgumentParser(description="ezcam 폴더 구조 스캐너")
    parser.add_argument("--root", default=r"C:\ezcam\1.1_1.1", help="스캔할 루트 경로")
    parser.add_argument("--max-depth", type=int, default=6, help="트리 최대 깊이")
    parser.add_argument("--out-dir", default=".", help="리포트 저장 폴더")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"[오류] 경로를 찾을 수 없습니다: {root}", file=sys.stderr)
        print("       --root 인자로 올바른 설치 경로를 지정하세요.", file=sys.stderr)
        sys.exit(1)

    out_dir = os.path.abspath(args.out_dir)
    txt_path = os.path.join(out_dir, "scan_report.txt")
    json_path = os.path.join(out_dir, "scan_report.json")

    print(f"스캔 시작: {root}")

    tree_lines, total_dirs, total_files, ext_counter = scan_tree(root, args.max_depth)

    # 질문 1/2/3 대상 수집
    top_level = list_children(root)
    resource_path = os.path.join(root, "resource")
    resource_children = list_children(resource_path)
    docs_path = os.path.join(resource_path, "docs")
    docs_children = list_children(docs_path)
    lang_folders = [
        c["name"] for c in docs_children
        if c["type"] == "dir" and c["name"].lower() in KNOWN_LANGS
    ]

    ext_summary = [
        {"ext": ext, "count": cnt}
        for ext, cnt in ext_counter.most_common()
    ]

    # ---- 텍스트 리포트 ----
    lines = []
    lines.append(f"SCAN ROOT : {root}")
    lines.append(f"SCAN TIME : {datetime.now():%Y-%m-%d %H:%M:%S}")
    lines.append("=" * 70)
    lines.extend(tree_lines)
    lines.append("")
    lines.append("=" * 70)
    lines.append("요약 (SUMMARY)")
    lines.append("=" * 70)
    lines.append(f"총 폴더 수 : {total_dirs}")
    lines.append(f"총 파일 수 : {total_files}")
    lines.append("")
    lines.append("[1] 루트 바로 아래:")
    for t in top_level:
        lines.append(f"    - {t['name']} ({t['type']})")
    lines.append("")
    lines.append("[2] resource\\ 바로 아래:")
    if resource_children:
        for r in resource_children:
            lines.append(f"    - {r['name']} ({r['type']})")
    else:
        lines.append("    (resource 폴더 없음 또는 접근 불가)")
    lines.append("")
    lines.append("[3] resource\\docs 안 언어 폴더:")
    if lang_folders:
        lines.append(f"    발견된 언어 폴더: {', '.join(lang_folders)}")
    else:
        lines.append("    (알려진 언어 폴더 없음)")
        lines.append("    docs 하위 항목:")
        for d in docs_children:
            lines.append(f"      - {d['name']} ({d['type']})")
    lines.append("")
    lines.append("확장자별 파일 개수:")
    for e in ext_summary:
        lines.append(f"    {e['ext']} : {e['count']}")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # ---- JSON 리포트 ----
    report = {
        "scanRoot": root,
        "scanTime": f"{datetime.now():%Y-%m-%d %H:%M:%S}",
        "totalDirs": total_dirs,
        "totalFiles": total_files,
        "topLevel": top_level,
        "resourceChildren": resource_children,
        "docsChildren": docs_children,
        "docsLangFolders": lang_folders,
        "extensionSummary": ext_summary,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print()
    print("완료!")
    print(f"  텍스트 리포트 : {txt_path}")
    print(f"  JSON 리포트   : {json_path}")
    print()
    print("이 두 파일을 보내주시면 됩니다.")


if __name__ == "__main__":
    main()
