# Charte & process pré-production — Blog AgentBnZo Tech Watch

> En vigueur 2026-07-30 · Owners: Golem (gate), Korben (voix), Composeur (process)

## Règle d'or

**Aucun article n'entre en `posts/` (production / GitHub Pages) s'il échoue la gate pré-production.**

Plus il y a d'articles, plus le risque de bugs d'affichage et d'incohérences augmente : la gate est obligatoire **avant** publication.

## Fichiers

| Fichier | Rôle |
|---------|------|
| `config/blog_charter.json` | Seuils & règles (CJK, titres, HTML) |
| `src/preprod_gate.py` | Validation + sanitization + quarantine |
| `drafts/quarantine/` | Articles bloqués (jamais poussés) |
| `enrich_chinese_articles.py` | Enrichissement FR sources chinoises |
| `auto_push_github.sh` | Repair + audit ; **bloque le push** si fail |

## Sources chinoises (`china_tech_ai` / CJK)

1. Fetch RSS OK → brouillon / quarantaine si texte chinois brut
2. **Obligatoire** : enrichissement FR (`enrich_chinese_articles.py` ou marqueurs `Analyse AgentBnZo` / `Résumé exécutif` / `enriched_fr=true`)
3. Gate re-valide → seulement alors `posts/`

Sans enrichissement FR : **blocage production** (message charter).

## Contrôles affichage

- Pas de balises block (`h1`–`h6`, `div`, …) imbriquées dans `<p>` (bug CERT/RSS)
- Contenu RSS sanitizé en paragraphes texte échappé
- Template P0 requis (`blog.css`, viewport, og:)
- Titre ≤ 120 chars (raccourci VU#/CVE trop longs)
- Contenu texte ≥ 120 chars

## Commandes

```bash
cd /media/raid10to/projets/blog
python3 src/preprod_gate.py --audit
python3 src/preprod_gate.py --repair   # répare HTML ou déplace en quarantine
bash auto_push_github.sh               # refuse push si hors charte
```

## Cron

`intelligent_blog_feeder.py` → gate à chaque `save_article`  
`auto_push_github.sh` → `--repair` + `--audit` avant push
