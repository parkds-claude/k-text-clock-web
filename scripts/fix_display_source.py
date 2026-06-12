#!/usr/bin/env python3
"""슬롯 파일(public/data/times/HH_MM.json)의 빈 display_source 보정.

quotes_public.json에서 text_ko로 원본을 역추적해
'— 작가, 「작품」' 형식으로 채운다. 매칭 실패 항목은 보고만 하고 건드리지 않는다.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TIMES_DIR = ROOT / "public" / "data" / "times"
QUOTES = ROOT / "data" / "quotes_public.json"


def make_display(src: dict) -> str:
    author = (src.get("author") or "").strip()
    title = (src.get("title") or "").strip()
    if author and title:
        return f"— {author}, 「{title}」"
    if author:
        return f"— {author}"
    if title:
        return f"— 「{title}」"
    return ""


def main() -> int:
    quotes = json.loads(QUOTES.read_text(encoding="utf-8"))
    # text_ko → source 매핑 (동일 문장 중복 시 첫 항목 사용)
    by_text = {}
    for q in quotes:
        t = (q.get("text_ko") or "").strip()
        if t and t not in by_text:
            by_text[t] = q.get("source") or {}

    fixed, unmatched = 0, []
    for f in sorted(TIMES_DIR.glob("*.json")):
        entries = json.loads(f.read_text(encoding="utf-8"))
        changed = False
        for e in entries:
            if (e.get("display_source") or "").strip():
                continue
            src = by_text.get((e.get("text_ko") or "").strip())
            ds = make_display(src) if src else ""
            if ds:
                e["display_source"] = ds
                fixed += 1
                changed = True
            else:
                unmatched.append((f.name, (e.get("text_ko") or "")[:30]))
        if changed:
            f.write_text(
                json.dumps(entries, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    print(f"보정 완료: {fixed}건")
    if unmatched:
        print(f"매칭 실패(미보정): {len(unmatched)}건")
        for name, txt in unmatched[:20]:
            print(f"  {name}: {txt}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
