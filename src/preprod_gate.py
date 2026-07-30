#!/usr/bin/env python3
"""Pré-production gate — enforce blog charter BEFORE publishing to posts/.

Especially strict for Chinese sources (china_tech_ai / CJK): must be FR-enriched
before production. Prevents display bugs (nested headings in <p>, raw RSS dumps).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup, NavigableString, Tag

logger = logging.getLogger(__name__)

BLOG_ROOT = Path(__file__).resolve().parent.parent
CHARTER_PATH = BLOG_ROOT / "config" / "blog_charter.json"
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
BLOCK_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "div", "section", "article", "ul", "ol", "table", "pre", "blockquote"}


@dataclass
class GateResult:
    ok: bool
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    sanitized_title: str = ""
    sanitized_content_html: str = ""
    is_chinese: bool = False
    metadata_flags: Dict[str, Any] = field(default_factory=dict)

    def block(self, reason: str) -> "GateResult":
        self.ok = False
        self.reasons.append(reason)
        return self


def load_charter() -> Dict[str, Any]:
    if CHARTER_PATH.exists():
        return json.loads(CHARTER_PATH.read_text(encoding="utf-8"))
    return {
        "rules": {
            "min_content_chars": 120,
            "max_title_chars": 120,
            "chinese": {
                "category": "china_tech_ai",
                "cjk_char_threshold": 8,
                "require_french_enrichment_before_production": True,
                "enrichment_markers": ["Analyse AgentBnZo", "Résumé exécutif", "enriched_fr"],
            },
        },
        "quarantine_dir": "drafts/quarantine",
    }


def detect_chinese(title: str, content: str, category: str, charter: Dict[str, Any]) -> bool:
    rules = charter.get("rules", {}).get("chinese", {})
    if category == rules.get("category", "china_tech_ai"):
        return True
    threshold = int(rules.get("cjk_char_threshold", 8))
    return len(CJK_RE.findall(f"{title}\n{content}")) >= threshold


def has_french_enrichment(text: str, article: Dict[str, Any], charter: Dict[str, Any]) -> bool:
    if article.get("enriched_fr") is True or article.get("preprod_enriched") is True:
        return True
    markers = charter.get("rules", {}).get("chinese", {}).get("enrichment_markers", [])
    blob = text or ""
    return any(m in blob for m in markers)


def sanitize_title(title: str, charter: Dict[str, Any]) -> str:
    title = re.sub(r"\s+", " ", (title or "").strip())
    title = BeautifulSoup(title, "html.parser").get_text(" ", strip=True)
    max_len = int(charter.get("rules", {}).get("max_title_chars", 120))
    title_cfg = charter.get("rules", {}).get("title", {})
    if title_cfg.get("shorten_vuln_ids"):
        # VU#123: Very long English dump → keep id + short rest
        m = re.match(r"^(VU#\d+|CVE-\d{4}-\d+)\s*[:\-–]?\s*(.*)$", title, re.I)
        if m and len(title) > max_len:
            rest = m.group(2).strip()
            keep = max_len - len(m.group(1)) - 3
            title = f"{m.group(1)}: {rest[:keep].rstrip()}…" if keep > 20 else m.group(1)
    if len(title) > max_len:
        title = title[: max_len - 1].rstrip() + "…"
    return title or "Sans titre"


def sanitize_content_html(raw: str, max_chars: int = 1200) -> str:
    """Convert raw RSS/HTML dump into safe paragraph HTML (no nested block tags in <p>)."""
    raw = (raw or "").strip()
    if not raw:
        return "<p><em>Résumé indisponible.</em></p>"

    # If looks like plain text
    if "<" not in raw:
        text = re.sub(r"\s+", " ", raw)[:max_chars]
        return f"<p>{escape(text)}{'…' if len(raw) > max_chars else ''}</p>"

    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style", "iframe", "object", "embed"]):
        tag.decompose()

    # Unwrap illegal nesting: move block children out of <p>
    for p in list(soup.find_all("p")):
        blocks = [c for c in list(p.children) if isinstance(c, Tag) and c.name in BLOCK_TAGS]
        if not blocks:
            continue
        for block in blocks:
            p.insert_before(block.extract())
        leftover = p.get_text(" ", strip=True)
        if leftover:
            new_p = soup.new_tag("p")
            new_p.string = leftover
            p.insert_before(new_p)
        p.decompose()

    parts: List[str] = []
    seen: set[str] = set()
    for el in soup.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        # Skip containers that still wrap other blocks
        if el.find(list(BLOCK_TAGS)):
            continue
        text = el.get_text(" ", strip=True)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        if el.name.startswith("h"):
            parts.append(f"<p><strong>{escape(text)}</strong></p>")
        else:
            parts.append(f"<p>{escape(text)}</p>")

    if not parts:
        text = soup.get_text(" ", strip=True)
        text = re.sub(r"\s+", " ", text)[:max_chars]
        parts = [f"<p>{escape(text)}{'…' if len(text) >= max_chars else ''}</p>"]

    # Drop short heading-only paras that are prefixes of a longer sibling (anti-doublon Overview)
    cleaned: List[str] = []
    plain_parts = [BeautifulSoup(p, "html.parser").get_text(" ", strip=True) for p in parts]
    for i, (part, plain) in enumerate(zip(parts, plain_parts)):
        if len(plain) < 40:
            if any(
                plain.lower() in other.lower() and other != plain
                for j, other in enumerate(plain_parts)
                if j != i
            ):
                continue
        # Drop near-duplicates / substrings (RSS flatten artifacts)
        if any(
            plain.lower() != other.lower()
            and plain.lower() in other.lower()
            and len(plain) > 60
            for j, other in enumerate(plain_parts)
            if j != i
        ):
            continue
        cleaned.append(part)
    parts = cleaned or parts

    # Cap total length of text
    out: List[str] = []
    total = 0
    for part in parts:
        t = BeautifulSoup(part, "html.parser").get_text()
        if total >= max_chars:
            break
        if total + len(t) > max_chars:
            remain = max_chars - total
            trimmed = escape(t[:remain].rstrip() + "…")
            out.append(f"<p>{trimmed}</p>")
            break
        out.append(part)
        total += len(t)

    return "\n".join(out) if out else "<p><em>Résumé indisponible.</em></p>"


def validate_article_dict(article: Dict[str, Any], charter: Optional[Dict[str, Any]] = None) -> GateResult:
    charter = charter or load_charter()
    rules = charter.get("rules", {})
    title = article.get("title") or ""
    content = article.get("content") or article.get("description") or ""
    category = article.get("category") or "general"

    result = GateResult(ok=True)
    result.is_chinese = detect_chinese(title, content, category, charter)
    result.sanitized_title = sanitize_title(title, charter)
    max_snippet = int(rules.get("max_content_snippet_chars", 1200))
    result.sanitized_content_html = sanitize_content_html(content, max_snippet)

    plain = BeautifulSoup(result.sanitized_content_html, "html.parser").get_text(" ", strip=True)
    min_chars = int(rules.get("min_content_chars", 120))
    if len(plain) < min_chars:
        result.block(f"Contenu trop court ({len(plain)} < {min_chars}) — hors charte")

    if result.is_chinese and rules.get("chinese", {}).get("require_french_enrichment_before_production", True):
        if not has_french_enrichment(f"{title}\n{content}\n{plain}", article, charter):
            msg = rules.get("chinese", {}).get(
                "block_message",
                "Source chinoise: enrichissement FR obligatoire avant production",
            )
            result.block(msg)
            result.metadata_flags["requires_chinese_enrichment"] = True

    # Raw nested HTML dump indicator (before sanitize) — warn only if we still see blocks
    if re.search(r"<p[^>]*>\s*<h[1-6]", content, re.I):
        result.warnings.append("RSS HTML imbriqué détecté — sanitizé pour production")

    result.metadata_flags.update(
        {
            "preprod_gate": True,
            "is_chinese": result.is_chinese,
            "charter_version": charter.get("version"),
        }
    )
    return result


def validate_post_html(html: str, charter: Optional[Dict[str, Any]] = None) -> GateResult:
    charter = charter or load_charter()
    rules = charter.get("rules", {})
    result = GateResult(ok=True)
    soup = BeautifulSoup(html, "html.parser")

    if rules.get("require_template_css") and not soup.select_one('link[href*="blog.css"]'):
        result.block("Template P0 manquant (assets/css/blog.css)")
    if rules.get("require_viewport_meta") and not soup.select_one('meta[name="viewport"]'):
        result.block("meta viewport manquant")

    # Nested block in <p>
    for p in soup.find_all("p"):
        for child in p.find_all(True):
            if isinstance(child, Tag) and child.name in BLOCK_TAGS:
                result.block(f"HTML invalide: <{child.name}> imbriqué dans <p> (bug affichage)")
                break
        if not result.ok:
            break

    title_el = soup.find("h1")
    title = title_el.get_text(" ", strip=True) if title_el else ""
    content_el = soup.select_one(".content")
    content = content_el.get_text(" ", strip=True) if content_el else ""
    cat_el = soup.select_one('meta[name="category"]')
    category = cat_el.get("content", "general") if cat_el else "general"

    result.is_chinese = detect_chinese(title, content, category, charter)
    result.sanitized_title = title
    if result.is_chinese and rules.get("chinese", {}).get("require_french_enrichment_before_production", True):
        if not has_french_enrichment(html, {"category": category}, charter):
            result.block(
                rules.get("chinese", {}).get(
                    "block_message",
                    "Article chinois non enrichi FR — hors production",
                )
            )

    min_chars = int(rules.get("min_content_chars", 120))
    if len(content) < min_chars:
        result.block(f"Contenu trop court ({len(content)} < {min_chars})")

    return result


def quarantine_path(charter: Optional[Dict[str, Any]] = None) -> Path:
    charter = charter or load_charter()
    rel = charter.get("quarantine_dir", "drafts/quarantine")
    path = BLOG_ROOT / rel
    path.mkdir(parents=True, exist_ok=True)
    return path


def audit_posts_dir(posts_dir: Optional[Path] = None) -> Dict[str, Any]:
    posts_dir = posts_dir or (BLOG_ROOT / "posts")
    charter = load_charter()
    report = {"ok": [], "fail": [], "chinese_blocked": 0, "html_bugs": 0}
    for path in sorted(posts_dir.glob("*.html")):
        if path.name == "index.html":
            continue
        html = path.read_text(encoding="utf-8", errors="replace")
        res = validate_post_html(html, charter)
        entry = {"file": path.name, "reasons": res.reasons, "warnings": res.warnings}
        if res.ok:
            report["ok"].append(entry)
        else:
            report["fail"].append(entry)
            if any("chinois" in r.lower() or "chinese" in r.lower() or "CJK" in r or "enrich" in r.lower() for r in res.reasons):
                report["chinese_blocked"] += 1
            if any("imbriqué" in r or "HTML" in r for r in res.reasons):
                report["html_bugs"] += 1
    return report


def repair_post_file(path: Path, charter: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
    """Repair display bugs in an existing post; quarantine if Chinese unenriched."""
    from blog_template import render_post_page

    charter = charter or load_charter()
    html = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.find("h1")
    title = title_el.get_text(" ", strip=True) if title_el else path.stem
    cat_el = soup.select_one('meta[name="category"]')
    category = cat_el.get("content", "general") if cat_el else "general"
    content_el = soup.select_one(".content")
    raw_content = content_el.decode_contents() if content_el else ""
    src_a = soup.select_one(".article-meta a") or soup.select_one('a[href^="http"]')
    source_url = src_a.get("href", "#") if src_a else "#"
    source_feed = src_a.get_text(strip=True) if src_a else "source"
    gen_m = re.search(r"Généré[:\s]*([^<\n]+)", html)
    generated_at = gen_m.group(1).strip() if gen_m else ""

    article = {
        "title": title,
        "content": raw_content,
        "category": category,
        "link": source_url,
        "source_feed": source_feed,
        "enriched_fr": "Analyse AgentBnZo" in html or "enriched_fr" in html,
    }
    gate = validate_article_dict(article, charter)

    if not gate.ok and gate.metadata_flags.get("requires_chinese_enrichment"):
        qdir = quarantine_path(charter)
        dest = qdir / path.name
        dest.write_text(html, encoding="utf-8")
        path.unlink(missing_ok=True)
        return False, f"quarantine→{dest.relative_to(BLOG_ROOT)}: {'; '.join(gate.reasons)}"

    new_html = render_post_page(
        title=gate.sanitized_title,
        content_html=gate.sanitized_content_html,
        source_url=source_url,
        source_feed=source_feed,
        category=category,
        generated_at=generated_at or "n/a",
        description=BeautifulSoup(gate.sanitized_content_html, "html.parser").get_text(" ", strip=True),
    )
    # Re-validate after repair
    post_gate = validate_post_html(new_html, charter)
    if not post_gate.ok:
        qdir = quarantine_path(charter)
        dest = qdir / path.name
        dest.write_text(new_html, encoding="utf-8")
        path.unlink(missing_ok=True)
        return False, f"quarantine→{dest.relative_to(BLOG_ROOT)}: {'; '.join(post_gate.reasons)}"

    path.write_text(new_html, encoding="utf-8")
    return True, "repaired"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    import argparse

    parser = argparse.ArgumentParser(description="Blog pre-production gate")
    parser.add_argument("--audit", action="store_true", help="Audit posts/")
    parser.add_argument("--repair", action="store_true", help="Repair/quarantine posts/")
    args = parser.parse_args()

    if args.repair:
        ok_n = fail_n = 0
        for path in sorted((BLOG_ROOT / "posts").glob("*.html")):
            if path.name == "index.html":
                continue
            ok, msg = repair_post_file(path)
            print(f"{'✅' if ok else '🚫'} {path.name}: {msg}")
            ok_n += int(ok)
            fail_n += int(not ok)
        print(f"Done repaired={ok_n} quarantined/failed={fail_n}")
        return

    report = audit_posts_dir()
    print(json.dumps({
        "ok": len(report["ok"]),
        "fail": len(report["fail"]),
        "chinese_blocked": report["chinese_blocked"],
        "html_bugs": report["html_bugs"],
        "failures": report["fail"][:20],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
