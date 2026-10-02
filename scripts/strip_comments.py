#!/usr/bin/env python3
"""
strip_comments.py - Python utility to strip junk comments and notes from codebase.

Compatible with Python 3.10+.
Can be invoked standalone or delegates to bun scripts/strip-comments.ts if bun is installed.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Directive patterns to preserve
JS_DIRECTIVE_PATTERN = re.compile(
    r"^\s*//\s*(@ts-|eslint-|biome-ignore|istanbul|c8|prettier-ignore|vite-ignore|webpack\w+:)",
    re.IGNORECASE,
)
BLOCK_DIRECTIVE_PATTERN = re.compile(
    r"^\s*/\*\s*(@ts-|eslint-|biome-ignore|istanbul|c8|prettier-ignore|vite-ignore)",
    re.IGNORECASE,
)
PY_DIRECTIVE_PATTERN = re.compile(
    r"^\s*#\s*(noqa|type:\s*ignore|pragma:\s*no cover|fmt:\s*off|fmt:\s*on|pylint:|mypy:)",
    re.IGNORECASE,
)


def strip_html_comments(content: str) -> tuple[str, int]:
    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        count += 1
        return ""

    cleaned = re.sub(r"<!--[\s\S]*?-->", repl, content)
    return cleaned, count


def strip_css_comments(content: str) -> tuple[str, int]:
    count = 0
    out = []
    i = 0
    length = len(content)

    while i < length:
        ch = content[i]
        next_ch = content[i + 1] if i + 1 < length else ""

        if ch in ('"', "'"):
            quote = ch
            out.append(quote)
            i += 1
            while i < length:
                c = content[i]
                out.append(c)
                if c == "\\":
                    i += 1
                    if i < length:
                        out.append(content[i])
                elif c == quote:
                    i += 1
                    break
                i += 1
            continue

        if ch == "/" and next_ch == "*":
            end_pos = content.find("*/", i + 2)
            if end_pos == -1:
                end_pos = length
            else:
                end_pos += 2
            count += 1
            i = end_pos
            continue

        out.append(ch)
        i += 1

    return "".join(out), count


def strip_js_comments(content: str, keep_jsdoc: bool = False) -> tuple[str, int]:
    count = 0
    out = []
    i = 0
    length = len(content)
    stack: list[str | dict] = ["root"]

    def get_prev_non_ws() -> str:
        for idx in range(len(out) - 1, -1, -1):
            c = out[idx]
            if c not in (" ", "\t", "\r", "\n"):
                return c
        return ""

    while i < length:
        ch = content[i]
        next_ch = content[i + 1] if i + 1 < length else ""
        curr_ctx = stack[-1]

        if curr_ctx == "template":
            if ch == "\\":
                out.append(ch)
                i += 1
                if i < length:
                    out.append(content[i])
                    i += 1
                continue
            if ch == "`":
                out.append(ch)
                stack.pop()
                i += 1
                continue
            if ch == "$" and next_ch == "{":
                out.append("${")
                stack.append({"type": "interp", "braceDepth": 1})
                i += 2
                continue
            out.append(ch)
            i += 1
            continue

        if ch == "'":
            out.append(ch)
            i += 1
            while i < length:
                c = content[i]
                out.append(c)
                if c == "\\":
                    i += 1
                    if i < length:
                        out.append(content[i])
                elif c == "'":
                    i += 1
                    break
                i += 1
            continue

        if ch == '"':
            out.append(ch)
            i += 1
            while i < length:
                c = content[i]
                out.append(c)
                if c == "\\":
                    i += 1
                    if i < length:
                        out.append(content[i])
                elif c == '"':
                    i += 1
                    break
                i += 1
            continue

        if ch == "`":
            out.append(ch)
            stack.append("template")
            i += 1
            continue

        if isinstance(curr_ctx, dict) and curr_ctx.get("type") == "interp":
            if ch == "{":
                curr_ctx["braceDepth"] += 1
            elif ch == "}":
                curr_ctx["braceDepth"] -= 1
                if curr_ctx["braceDepth"] == 0:
                    out.append("}")
                    stack.pop()
                    i += 1
                    continue

        if ch == "/" and next_ch == "/":
            line_end = content.find("\n", i)
            if line_end == -1:
                line_end = length
            comment_text = content[i:line_end]

            if JS_DIRECTIVE_PATTERN.search(comment_text):
                out.append(comment_text)
            else:
                count += 1
            i = line_end
            continue

        if ch == "/" and next_ch == "*":
            end_pos = content.find("*/", i + 2)
            if end_pos == -1:
                end_pos = length
            else:
                end_pos += 2
            comment_text = content[i:end_pos]

            is_jsdoc = comment_text.startswith("/**") and not comment_text.startswith("/***")
            is_directive = bool(BLOCK_DIRECTIVE_PATTERN.search(comment_text))

            if is_directive or (keep_jsdoc and is_jsdoc):
                out.append(comment_text)
            else:
                count += 1
            i = end_pos
            continue

        if ch == "/":
            prev = get_prev_non_ws()
            is_regex_predecessor = bool(re.match(r"^[(=!+\-*%&|^~<?>:;,{}[\]?]", prev)) or prev == ""
            if is_regex_predecessor:
                out.append(ch)
                i += 1
                in_char_class = False
                while i < length:
                    c = content[i]
                    out.append(c)
                    if c == "\\":
                        i += 1
                        if i < length:
                            out.append(content[i])
                    elif c == "[":
                        in_char_class = True
                    elif c == "]":
                        in_char_class = False
                    elif c == "/" and not in_char_class:
                        i += 1
                        while i < length and re.match(r"[a-z]", content[i], re.IGNORECASE):
                            out.append(content[i])
                            i += 1
                        break
                    i += 1
                continue

        out.append(ch)
        i += 1

    return "".join(out), count


def strip_vue_comments(content: str, keep_jsdoc: bool = False) -> tuple[str, int]:
    total_count = 0
    block_regex = re.compile(
        r"(<script\b[^>]*>)([\s\S]*?)(<\/script>)|(<style\b[^>]*>)([\s\S]*?)(<\/style>)",
        re.IGNORECASE,
    )
    last_idx = 0
    result = []

    for match in block_regex.finditer(content):
        start, end = match.span()

        if start > last_idx:
            chunk = content[last_idx:start]
            html_code, c = strip_html_comments(chunk)
            total_count += c
            result.append(html_code)

        if match.group(1):
            open_tag, body, close_tag = match.group(1), match.group(2), match.group(3)
            js_code, c = strip_js_comments(body, keep_jsdoc)
            total_count += c
            result.append(open_tag + js_code + close_tag)
        elif match.group(4):
            open_tag, body, close_tag = match.group(4), match.group(5), match.group(6)
            css_code, c = strip_css_comments(body)
            total_count += c
            result.append(open_tag + css_code + close_tag)

        last_idx = end

    if last_idx < len(content):
        chunk = content[last_idx:]
        html_code, c = strip_html_comments(chunk)
        total_count += c
        result.append(html_code)

    return "".join(result), total_count


def clean_code_layout(code: str) -> tuple[str, int]:
    original_lines = code.split("\n")
    cleaned_lines = []
    prev_was_empty = False

    for line in original_lines:
        trimmed_right = line.rstrip()
        is_empty = len(trimmed_right.strip()) == 0

        if is_empty:
            if not prev_was_empty and cleaned_lines:
                cleaned_lines.append("")
                prev_was_empty = True
        else:
            cleaned_lines.append(trimmed_right)
            prev_was_empty = False

    while cleaned_lines and cleaned_lines[-1] == "":
        cleaned_lines.pop()
    cleaned_lines.append("")

    lines_removed = len(original_lines) - len(cleaned_lines)
    return "\n".join(cleaned_lines), lines_removed


def process_file(file_path: Path, dry_run: bool = False, keep_jsdoc: bool = False) -> tuple[int, int, int]:
    ext = file_path.suffix.lower()
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return 0, 0, 0

    count = 0
    if ext == ".vue":
        new_content, count = strip_vue_comments(content, keep_jsdoc)
    elif ext in (".ts", ".js", ".mjs", ".cjs"):
        new_content, count = strip_js_comments(content, keep_jsdoc)
    elif ext == ".css":
        new_content, count = strip_css_comments(content)
    elif ext == ".html":
        new_content, count = strip_html_comments(content)
    else:
        return 0, 0, 0

    if count == 0:
        return 0, 0, 0

    final_content, lines_removed = clean_code_layout(new_content)
    bytes_saved = len(content.encode("utf-8")) - len(final_content.encode("utf-8"))

    if not dry_run and final_content != content:
        file_path.write_text(final_content, encoding="utf-8")

    return count, lines_removed, bytes_saved


def main() -> int:
    parser = argparse.ArgumentParser(description="Strip junk comments and notes from codebase.")
    parser.add_argument("paths", nargs="*", default=[], help="Files or directories to process")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying files")
    parser.add_argument("--keep-jsdoc", action="store_true", help="Preserve JSDoc comments")
    parser.add_argument("--use-bun", action="store_true", help="Delegate directly to scripts/strip-comments.ts via bun")
    args = parser.parse_args()

    # If bun is available and scripts/strip-comments.ts exists, and not explicitly disabled, delegate
    ts_script = Path(__file__).parent / "strip-comments.ts"
    if shutil.which("bun") and ts_script.exists() and not args.use_bun:
        cmd = ["bun", str(ts_script)]
        if args.dry_run:
            cmd.append("--dry-run")
        if args.keep_jsdoc:
            cmd.append("--keep-jsdoc")
        cmd.extend(args.paths)
        return subprocess.run(cmd).returncode

    # Python standalone fallback
    target_dirs = [Path(p) for p in args.paths] if args.paths else [Path("frontend/pages"), Path("frontend/layouts"), Path("frontend/components"), Path("frontend/assets")]
    print(f"✨ Python StripComment running on {len(target_dirs)} targets...")
    total_comments, total_lines, total_bytes = 0, 0, 0

    for target in target_dirs:
        if target.is_file():
            c, l, b = process_file(target, args.dry_run, args.keep_jsdoc)
            total_comments += c
            total_lines += l
            total_bytes += b
        elif target.is_dir():
            for root, _, files in os.walk(target):
                for f in files:
                    fp = Path(root) / f
                    if fp.suffix.lower() in (".vue", ".ts", ".js", ".css", ".html"):
                        c, l, b = process_file(fp, args.dry_run, args.keep_jsdoc)
                        total_comments += c
                        total_lines += l
                        total_bytes += b

    print(f"✔ Hoàn thành: Đã xóa {total_comments} comments, rút gọn {total_lines} dòng ({total_bytes} bytes).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
