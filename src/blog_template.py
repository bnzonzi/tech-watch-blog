"""Shared HTML template helpers for AgentBnZo Tech Watch Blog (P0)."""

from __future__ import annotations

from html import escape
from typing import Optional

SITE_NAME = "AgentBnZo Tech Watch"
SITE_TAGLINE = "Veille technologique multi-agents — CrewAI · GLM · RAG"
SITE_URL = "https://bnzonzi.github.io/tech-watch-blog"
GITHUB_URL = "https://github.com/bnzonzi/tech-watch-blog"
THEME_STORAGE_KEY = "abz-theme"


def _prefix(depth: int = 0) -> str:
    return "../" * depth if depth else ""


def _css_href(depth: int = 0) -> str:
    return f"{_prefix(depth)}assets/css/blog.css"


def _home_href(depth: int = 0) -> str:
    return "../" * depth + "index.html" if depth else "index.html"


def _settings_href(depth: int = 0) -> str:
    return f"{_prefix(depth)}settings.html"


def render_theme_boot() -> str:
    """Blocking head script. Applies the stored theme before first paint."""
    key = THEME_STORAGE_KEY
    return f"""    <script>
    (function () {{
      try {{
        var theme = localStorage.getItem("{key}");
        if (theme !== "light" && theme !== "dark") theme = "dark";
        document.documentElement.setAttribute("data-theme", theme);
        document.documentElement.style.colorScheme = theme;
      }} catch (e) {{
        document.documentElement.setAttribute("data-theme", "dark");
      }}
    }})();
    </script>"""


def render_head(
    title: str,
    *,
    description: str = "",
    category: str = "",
    canonical: str = "",
    depth: int = 0,
    og_type: str = "website",
) -> str:
    safe_title = escape(title)
    full_title = f"{safe_title} · {SITE_NAME}" if title != SITE_NAME else SITE_NAME
    desc = escape((description or SITE_TAGLINE)[:160])
    canon = escape(canonical or SITE_URL)
    cat_meta = f'\n    <meta name="category" content="{escape(category)}">' if category else ""
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{full_title}</title>
    <meta name="description" content="{desc}">
    <meta name="author" content="AgentBnZo">
    <link rel="canonical" href="{canon}">
    <meta property="og:type" content="{escape(og_type)}">
    <meta property="og:title" content="{safe_title}">
    <meta property="og:description" content="{desc}">
    <meta property="og:url" content="{canon}">
    <meta property="og:site_name" content="{SITE_NAME}">
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{safe_title}">
    <meta name="twitter:description" content="{desc}">{cat_meta}
{render_theme_boot()}
    <link rel="stylesheet" href="{_css_href(depth)}">
</head>"""


def render_header(depth: int = 0, active: str = "") -> str:
    home = _home_href(depth)
    settings = _settings_href(depth)
    settings_current = ' aria-current="page"' if active == "settings" else ""
    return f"""<a class="skip-link" href="#main">Aller au contenu</a>
<header class="site-header">
  <div class="site-header-inner">
    <a class="brand" href="{home}">
      <span class="brand-mark" aria-hidden="true">ABZ</span>
      <span class="brand-text">
        <strong>{SITE_NAME}</strong>
        <span>{SITE_TAGLINE}</span>
      </span>
    </a>
    <nav class="nav" aria-label="Navigation principale">
      <a href="{home}">Accueil</a>
      <a href="{settings}"{settings_current}>Réglages</a>
      <a href="{GITHUB_URL}" rel="noopener" target="_blank">GitHub</a>
      <a href="{SITE_URL}/">Live</a>
    </nav>
  </div>
</header>"""


def render_footer() -> str:
    return f"""<footer class="site-footer">
  <div class="site-footer-inner">
    <div>© AgentBnZo · veille autonome (CrewAI feeders)</div>
    <div>
      <a href="{GITHUB_URL}" rel="noopener" target="_blank">Repo</a>
      · <a href="{SITE_URL}/">GitHub Pages</a>
    </div>
  </div>
</footer>"""


def render_post_page(
    *,
    title: str,
    content_html: str,
    source_url: str,
    source_feed: str,
    category: str,
    generated_at: str,
    description: Optional[str] = None,
) -> str:
    plain = (description or content_html)
    # strip rough tags for meta description
    import re
    plain = re.sub(r"<[^>]+>", " ", plain)
    plain = re.sub(r"\s+", " ", plain).strip()
    desc = plain[:155] + ("…" if len(plain) > 155 else "")

    head = render_head(
        title,
        description=desc,
        category=category,
        canonical=f"{SITE_URL}/posts/",
        depth=1,
        og_type="article",
    )
    header = render_header(depth=1)
    footer = render_footer()
    safe_title = escape(title)
    safe_cat = escape(category or "general")
    safe_feed = escape(source_feed or "source")
    safe_url = escape(source_url or "#")
    safe_gen = escape(generated_at)

    return f"""{head}
<body>
{header}
<main id="main" class="container">
  <article class="article-card">
    <span class="badge">{safe_cat}</span>
    <h1>{safe_title}</h1>
    <div class="article-meta">
      <span>Source: <a href="{safe_url}" rel="noopener" target="_blank">{safe_feed}</a></span>
      <span>Généré: {safe_gen}</span>
    </div>
    <div class="content">
      {content_html}
    </div>
    <div class="article-footer">
      <p>Article agrégé par les feeders AgentBnZo. Contexte stack: CrewAI · GLM-5.2 · ChromaDB · GitHub Pages.</p>
      <p><a href="../index.html">← Retour à l'index</a></p>
    </div>
  </article>
</main>
{footer}
</body>
</html>
"""


def render_settings_page() -> str:
    head = render_head(
        "Réglages",
        description="Préférences d'affichage du blog AgentBnZo Tech Watch.",
        canonical=f"{SITE_URL}/settings.html",
        depth=0,
    )
    header = render_header(depth=0, active="settings")
    footer = render_footer()
    return f"""{head}
<body>
{header}
<main id="main" class="container">
  <section class="settings-card" aria-labelledby="settings-title">
    <h1 id="settings-title">Réglages</h1>
    <p class="settings-lead">Préférences d'affichage enregistrées dans ce navigateur.</p>
    <div class="setting-row">
      <div class="setting-copy">
        <h2 id="dark-mode-label">Mode sombre</h2>
        <p>Fond sombre pour la lecture. Désactivé, le blog passe au thème clair.</p>
      </div>
      <button type="button" class="theme-switch" id="dark-mode-toggle" role="switch" aria-checked="true" aria-labelledby="dark-mode-label">
        <span class="switch-thumb"></span>
      </button>
    </div>
    <p id="theme-status" class="theme-status" aria-live="polite"></p>
  </section>
</main>
{footer}
<script src="assets/js/theme.js"></script>
</body>
</html>
"""


def render_index_page(
    *,
    articles_html: str,
    pagination_html: str,
    total_articles: int,
    today_articles: int,
    page: int,
    total_pages: int,
    page_articles_count: int,
    updated_at: str,
) -> str:
    title = SITE_NAME if page == 1 else f"{SITE_NAME} — Page {page}"
    head = render_head(
        title,
        description=SITE_TAGLINE,
        canonical=SITE_URL if page == 1 else f"{SITE_URL}/index_page_{page}.html",
        depth=0,
    )
    header = render_header(depth=0)
    footer = render_footer()
    return f"""{head}
<body>
{header}
<main id="main" class="container">
  <section class="hero">
    <h1>Blog AgentBnZo</h1>
    <p class="subtitle">{SITE_TAGLINE}</p>
    <div class="stats" role="group" aria-label="Statistiques">
      <div class="stat"><strong>{total_articles}</strong><span>Articles</span></div>
      <div class="stat"><strong>{today_articles}</strong><span>Aujourd'hui</span></div>
      <div class="stat"><strong>Auto</strong><span>Feeders</span></div>
      <div class="stat"><strong>P0</strong><span>Design</span></div>
    </div>
  </section>
  <section class="posts" aria-label="Articles">
    {articles_html}
  </section>
  {pagination_html}
  <p class="last-update">Mise à jour: {escape(updated_at)} · Page {page}/{total_pages} · {page_articles_count} articles</p>
</main>
{footer}
</body>
</html>
"""
