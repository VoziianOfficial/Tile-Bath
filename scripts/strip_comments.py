#!/usr/bin/env python3
from __future__ import annotations

import pathlib


def strip_html_comments(text: str) -> str:
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        if text.startswith("<!--", i):
            end = text.find("-->", i + 4)
            if end == -1:
                # Unclosed comment; drop the rest.
                break
            i = end + 3
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


def strip_c_block_comments(text: str) -> str:
    # Used for CSS and JS block comments.
    out: list[str] = []
    i = 0
    n = len(text)
    in_single = False
    in_double = False
    while i < n:
        ch = text[i]
        if in_single:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if ch == "'":
                in_single = False
            i += 1
            continue
        if in_double:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if ch == '"':
                in_double = False
            i += 1
            continue

        if ch == "'":
            in_single = True
            out.append(ch)
            i += 1
            continue
        if ch == '"':
            in_double = True
            out.append(ch)
            i += 1
            continue

        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            end = text.find("*/", i + 2)
            if end == -1:
                break
            i = end + 2
            continue

        out.append(ch)
        i += 1
    return "".join(out)


def strip_js_comments(text: str) -> str:
    out: list[str] = []
    i = 0
    n = len(text)

    in_single = False
    in_double = False
    in_template = False
    template_brace_depth = 0
    in_regex = False

    def is_regex_start(prev_non_ws: str | None) -> bool:
        # Heuristic: after these tokens, a / is more likely to start a regex literal.
        if prev_non_ws is None:
            return True
        return prev_non_ws in ("(", "[", "{", ",", "=", ":", ";", "!", "?", "+", "-", "*", "%", "&", "|", "^", "~")

    prev_non_ws: str | None = None

    while i < n:
        ch = text[i]

        if in_single:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if ch == "'":
                in_single = False
            i += 1
            continue

        if in_double:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if ch == '"':
                in_double = False
            i += 1
            continue

        if in_template:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if ch == "`" and template_brace_depth == 0:
                in_template = False
                i += 1
                continue
            if ch == "$" and i + 1 < n and text[i + 1] == "{":
                template_brace_depth += 1
                out.append("{")
                i += 2
                continue
            if ch == "{" and template_brace_depth > 0:
                template_brace_depth += 1
            elif ch == "}" and template_brace_depth > 0:
                template_brace_depth -= 1
            i += 1
            continue

        if in_regex:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if ch == "/":
                in_regex = False
            i += 1
            continue

        if ch == "'":
            in_single = True
            out.append(ch)
            i += 1
            continue
        if ch == '"':
            in_double = True
            out.append(ch)
            i += 1
            continue
        if ch == "`":
            in_template = True
            template_brace_depth = 0
            out.append(ch)
            i += 1
            continue

        if ch == "/" and i + 1 < n:
            nxt = text[i + 1]
            if nxt == "/":
                # line comment: consume until newline, but keep the newline
                end = text.find("\n", i + 2)
                if end == -1:
                    break
                i = end
                continue
            if nxt == "*":
                end = text.find("*/", i + 2)
                if end == -1:
                    break
                i = end + 2
                continue

            # regex literal heuristic
            if is_regex_start(prev_non_ws):
                in_regex = True
                out.append(ch)
                i += 1
                continue

        out.append(ch)
        if not ch.isspace():
            prev_non_ws = ch
        i += 1

    return "".join(out)


def main() -> int:
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    git_files = (repo_root / ".git").exists()
    if not git_files:
        raise SystemExit("Expected a git repo (missing .git).")

    # Use git ls-files so we don't touch .git/ or untracked artifacts.
    import subprocess

    proc = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    paths = [p for p in proc.stdout.splitlines() if p]

    changed: list[str] = []
    for rel in paths:
        path = repo_root / rel
        suffix = path.suffix.lower()
        if suffix not in {".html", ".css", ".js", ".svg"}:
            continue
        try:
            original = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        updated = original
        if suffix == ".html":
            updated = strip_html_comments(updated)
        elif suffix == ".css":
            updated = strip_c_block_comments(updated)
        elif suffix == ".js":
            updated = strip_js_comments(updated)
        elif suffix == ".svg":
            # SVG comments are HTML-like.
            updated = strip_html_comments(updated)

        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed.append(rel)

    if changed:
        print("Updated files:")
        for rel in changed:
            print(f"- {rel}")
    else:
        print("No changes needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

