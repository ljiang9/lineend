"""lineend —— 检测与转换文本文件的行尾符。

设计：
- 以二进制方式读取全部内容，逐字节统计换行符：CRLF(\\r\\n)、LF(\\n)、
  孤立 CR(\\r)。不会被文本模式的 universal newlines 干扰。
- 二进制安全：含 NUL 字节的文件会被标记为“可能是二进制”，
  但仍能统计（不崩溃），转换操作会要求确认。

用法：
    lineend detect file.txt        检测行尾类型与数量
    lineend to-lf file.txt         原地转为 LF
    lineend to-crlf file.txt       原地转为 CRLF
    cat file | lineend detect --stdin
"""

import argparse
import json
import os
import shutil
import sys

VERSION = "0.1.0"


def count_endings(data: bytes) -> dict:
    """统计三种行尾的数量。返回 dict(crlf, lf, cr)。"""
    crlf = data.count(b"\r\n")
    total_lf = data.count(b"\n")
    total_cr = data.count(b"\r")
    lf = total_lf - crlf          # 孤立 LF
    cr = total_cr - crlf          # 孤立 CR
    return {"crlf": crlf, "lf": lf, "cr": cr}


def is_binary(data: bytes) -> bool:
    return b"\x00" in data


def describe(counts: dict) -> str:
    kinds = [k for k, v in counts.items() if v > 0]
    if not kinds:
        return "无换行符"
    if len(kinds) == 1:
        name = {"crlf": "CRLF（Windows）", "lf": "LF（Unix/macOS）",
                "cr": "CR（老式 Mac）"}[kinds[0]]
        return name
    return "混合行尾"


def cmd_detect(args) -> int:
    if args.stdin:
        data = sys.stdin.buffer.read()
        label = "<stdin>"
    else:
        if not os.path.isfile(args.file):
            print(f"error: 文件不存在：{args.file}", file=sys.stderr)
            return 2
        with open(args.file, "rb") as f:
            data = f.read()
        label = args.file

    counts = count_endings(data)
    binary = is_binary(data)
    total = sum(counts.values())

    if args.json:
        print(json.dumps({
            "file": label,
            "crlf": counts["crlf"],
            "lf": counts["lf"],
            "cr": counts["cr"],
            "total": total,
            "mixed": len([v for v in counts.values() if v > 0]) > 1,
            "binary": binary,
            "kind": describe(counts),
        }, ensure_ascii=False, indent=2))
        return 0

    print(f"===== 行尾检测：{label} =====")
    print(f"  CRLF（\\r\\n）：{counts['crlf']}")
    print(f"  LF  （\\n）  ：{counts['lf']}")
    print(f"  CR  （\\r）  ：{counts['cr']}")
    print(f"  结论：{describe(counts)}")
    if binary:
        print("  ⚠️  文件含有 NUL 字节，可能是二进制文件，统计仅供参考。")
    return 0


def cmd_convert(args) -> int:
    target = args.command  # to-lf / to-crlf
    path = args.file
    if not os.path.isfile(path):
        print(f"error: 文件不存在：{path}", file=sys.stderr)
        return 2
    with open(path, "rb") as f:
        data = f.read()

    if is_binary(data):
        print(f"error: {path} 含有 NUL 字节，看起来是二进制文件，拒绝转换。"
              "（文本工具不碰二进制文件）", file=sys.stderr)
        return 1

    counts = count_endings(data)
    target_name = "LF" if target == "to-lf" else "CRLF"

    # 归一化：先把 CRLF 和孤立 CR 都拆开，再按目标重组。
    normalized = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    new_data = normalized if target == "to-lf" else normalized.replace(b"\n", b"\r\n")

    changed = (new_data != data)
    if args.json:
        print(json.dumps({
            "file": path,
            "target": target_name,
            "before": counts,
            "changed": changed,
            "dry_run": args.dry_run,
        }, ensure_ascii=False, indent=2))
        return 0

    if not changed:
        print(f"{path}：已经是 {target_name}，无需转换。")
        return 0

    n = sum(counts.values())
    if args.dry_run:
        print(f"{path}：将转换 {n} 处行尾 → {target_name}（dry-run，未写入）。")
        return 0

    if args.backup:
        bak = path + ".bak"
        shutil.copy2(path, bak)
        print(f"已备份：{bak}")

    with open(path, "wb") as f:
        f.write(new_data)
    print(f"{path}：已转换为 {target_name}（{n} 处行尾）。")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lineend",
        description="检测与转换文本文件的行尾符（CRLF / LF / CR）。")
    p.add_argument("--version", action="version", version=f"lineend {VERSION}")
    sub = p.add_subparsers(dest="command", required=True)

    d = sub.add_parser("detect", help="检测行尾类型与数量")
    d.add_argument("file", nargs="?", help="要检测的文件")
    d.add_argument("--stdin", action="store_true", help="从标准输入读取")
    d.add_argument("--json", action="store_true", help="JSON 输出")

    for name, help_text in (("to-lf", "原地转换为 LF（Unix 风格）"),
                            ("to-crlf", "原地转换为 CRLF（Windows 风格）")):
        c = sub.add_parser(name, help=help_text)
        c.add_argument("file", help="要转换的文件")
        c.add_argument("--backup", action="store_true", help="转换前备份为 .bak")
        c.add_argument("--dry-run", action="store_true", help="只显示将要做的事，不写入")
        c.add_argument("--json", action="store_true", help="JSON 输出")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "detect":
        if not args.stdin and not args.file:
            print("error: 请指定文件，或使用 --stdin 从标准输入读取。",
                  file=sys.stderr)
            return 2
        return cmd_detect(args)
    return cmd_convert(args)


if __name__ == "__main__":
    sys.exit(main())
