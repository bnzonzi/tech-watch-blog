#!/usr/bin/env python3
"""Restyle existing posts/*.html with the shared P0 template."""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

BLOG_DIR = Path(__file__).parent
POSTS_DIR = BLOG_DIR / "posts"
SRC_DIR = BLOG_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from blog_template import render_post_page


def parse_old_post(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")

    title_m = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.I | re.S)
    title = re.sub(r"<[^>]+>", "", title_m.group(1)).strip() if title_m else path.stem

    cat_m = re.search(r'name="category"\s+content="([^"]+)"', text, re.I)
    if not cat_m:
        cat_m = re.search(r'class="badge"[^>]*>([^<]+)', text, re.I)
    category = cat_m.group(1).strip() if cat_m else "general"

    src_m = re.search(r'Source:</strong>\s*<a href="([^"]+)"[^>]*>([^<]+)</a>', text, re.I)
    if not src_m:
        src_m = re.search(r'Source:\s*<a href="([^"]+)"[^>]*>([^<]+)</a>', text, re.I)
    source_url = src_m.group(1) if src_m else "#"
    source_feed = src_m.group(2) if src_m else "source"

    content_m = re.search(r'<div class="content">(.*?)</div>', text, re.I | re.S)
    content_html = content_m.group(1).strip() if content_m else f"<p>{title}</p>"

    gen_m = re.search(r"Généré(?: le)?[:\s]*([^<]+)", text, re.I)
    if gen_m:
        generated_at = gen_m.group(1).strip()
    else:
        generated_at = datetime.fromtimestamp(path.stat().st_mtime).strftime("%d/%m/%Y à %H:%M")

    # Already restyled?
    already = 'link rel="stylesheet" href="../assets/css/blog.css"' in text
    return {
        "title": title,
        "category": category,
        "source_url": source_url,
        "source_feed": source_feed,
        "content_html": content_html,
        "generated_at": generated_at,
        "already": already,
    }


def main():
    posts = sorted(POSTS_DIR.glob("*.html"))
    updated = 0
    skipped = 0
    for path in posts:
        if path.name == "index.html":
            continue
        data = parse_old_post(path)
        if data["already"] and "--force" not in sys.argv:
            skipped += 1
            continue
        html = render_post_page(
            title=data["title"],
            content_html=data["content_html"],
            source_url=data["source_url"],
            source_feed=data["source_feed"],
            category=data["category"],
            generated_at=data["generated_at"],
            description=re.sub(r"<[^>]+>", " ", data["content_html"]),
        )
        path.write_text(html, encoding="utf-8")
        updated += 1
    print(f"✅ Restylés: {updated} | déjà P0: {skipped} | total: {len(posts)}")


if __name__ == "__main__":
    main()
