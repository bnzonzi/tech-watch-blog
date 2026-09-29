# AgentBnZo — Carnet de labo · Design Charter

**Version:** 1.0 · **Produit:** clone éditorial distinct de *Tech Watch* (GitHub Pages ABZ)  
**Statut:** référence UX/UI pour `packages/field-notes/`

---

## 1. Nom de marque

| Élément | Proposition |
|--------|-------------|
| **Nom principal** | **Carnet de labo** |
| **Signature** | AgentBnZo · notes de terrain pour alternants & curieux plateforme |
| **Slug / dossier** | `field-notes` (technique, anglais) |
| **Ton** | Première personne, pédagogique sans ton « formation certifiante », notes honnêtes d’expérimentation agentique |

*Alternative retenue en interne : « Field Notes » pour les assets et le repo ; l’interface reste en français.*

---

## 2. Personas

### Léa — Alternante IT en entreprise (22 ans)

- **Contexte :** alternance DSI / plateforme, découvre MLOps, agents, et outils GAFAM via Slack interne.
- **Objectifs :** comprendre *comment* on teste en vrai (pas un tuto académique), reprendre des commandes, éviter les pièges déjà vus.
- **Frictions :** jargon non expliqué, articles trop « veille RSS », dark mode fatigant en journée de bureau.
- **Besoins UX :** lecture longue confortable (clair par défaut), callouts « J’ai testé », blocs code copiables, badges de niveau (découverte / pratique).

### Malik — Curieux culture dev & plateforme (28 ans)

- **Contexte :** suit communautés type Google/OpenAI/Microsoft, lit en français mais vit dans l’écosystème outils.
- **Objectifs :** comprendre la posture AgentBnZo (flotte ML agentique), comparer avec ce qu’il voit sur X/Bluesky, partager un lien « propre ».
- **Frictions :** blogs clones type Korben, esthétique hacker ou corporate générique.
- **Besoins UX :** identité visuelle mémorable, playground / design system bookmarkable, mentions partenaires discrètes et éthiques.

---

## 3. Différenciation visuelle vs blog Tech Watch actuel

| Dimension | Tech Watch (ABZ) | Carnet de labo (Field Notes) |
|-----------|------------------|------------------------------|
| **Mode par défaut** | Sombre (`data-theme="dark"`) | **Clair** (papier chaud) |
| **Palette** | Navy `#0f1419`, bleu accent `#3d8bfd` | Encre `#1c1917`, papier `#faf6f0`, **violet labo** `#6d5efc`, **menthe** `#0d9488` |
| **Typographie** | System UI stack | **Fraunces** (titres) + **Source Sans 3** (corps) |
| **Atmosphère** | Veille nocturne, dashboard | Campus × product engineering, carnet de terrain |
| **Rayons** | 12px uniforme | 6px (UI) / 16px (cartes) — hiérarchie plus éditoriale |
| **Motif** | Dégradé vertical sombre | Grain léger + bandeau « lab stripe » |
| **Badges** | Bleu transparent | Pile sémantique (test, échec, interne, partenaire) |
| **Cible éditoriale** | Flux multi-agents, titres RSS | Récits « j’ai branché l’agent », échecs honnêtes |
| **Playground** | Absent | **Showroom** composants + toggles interactifs |

---

## 4. Tokens de design

### 4.1 Couleurs — thème clair (défaut)

| Token | Valeur | Usage |
|-------|--------|--------|
| `--fn-bg` | `#faf6f0` | Fond page |
| `--fn-surface` | `#ffffff` | Cartes, header |
| `--fn-surface-2` | `#f3ede4` | Zones secondaires |
| `--fn-text` | `#1c1917` | Texte principal |
| `--fn-muted` | `#57534e` | Méta, légendes |
| `--fn-border` | `#e7e0d4` | Contours |
| `--fn-accent` | `#6d5efc` | Liens, CTA, focus ring |
| `--fn-accent-2` | `#0d9488` | Succès, « chez nous » |
| `--fn-warm` | `#ea580c` | Énergie, « j’ai testé » |
| `--fn-danger` | `#be123c` | Échec honnête (texte sur fond clair) |
| `--fn-code-bg` | `#292524` | Blocs code (contraste élevé) |
| `--fn-on-accent` | `#ffffff` | Texte sur boutons accent |

### 4.2 Couche sombre (optionnelle)

| Token | Valeur |
|-------|--------|
| `--fn-bg` | `#141210` |
| `--fn-surface` | `#1f1c1a` |
| `--fn-text` | `#f5f0e8` |
| `--fn-accent` | `#8b7cff` |

Activée via `data-theme="dark"` sur `<html>` ; clé localStorage `fn-theme` : `light` | `dark` | `system`.

### 4.3 Typographie

| Token | Valeur |
|-------|--------|
| `--fn-font-display` | `"Fraunces", Georgia, serif` |
| `--fn-font-body` | `"Source Sans 3", system-ui, sans-serif` |
| `--fn-font-mono` | `"JetBrains Mono", ui-monospace, monospace` |

| Niveau | Taille | Line-height | Poids |
|--------|--------|-------------|-------|
| Display | `clamp(2rem, 4vw, 2.75rem)` | 1.15 | 600 |
| H1 | `2rem` | 1.2 | 600 |
| H2 | `1.5rem` | 1.25 | 600 |
| H3 | `1.25rem` | 1.3 | 600 |
| Body | `1.0625rem` (17px) | 1.65 | 400 |
| Small | `0.875rem` | 1.5 | 400 |
| Label | `0.8125rem` | 1.4 | 600, uppercase tracking |

### 4.4 Espacement (échelle 4px)

`--fn-space-1` à `--fn-space-8` : 4, 8, 12, 16, 24, 32, 48, 64px.

### 4.5 Rayons

| Token | Valeur |
|-------|--------|
| `--fn-radius-sm` | `6px` |
| `--fn-radius-md` | `10px` |
| `--fn-radius-lg` | `16px` |
| `--fn-radius-pill` | `999px` |

### 4.6 Motion

| Token | Valeur | Note |
|-------|--------|------|
| `--fn-duration-fast` | `120ms` | Hover, toggle |
| `--fn-duration-normal` | `200ms` | Thème, panneaux |
| `--fn-ease` | `cubic-bezier(0.22, 1, 0.36, 1)` | Entrées douces |

**`prefers-reduced-motion: reduce`** : durées → `0.01ms`, pas d’animation sur grain / stripe ; `scroll-behavior: auto`.

---

## 5. Catalogue de composants

| Composant | Classe(s) | Rôle |
|-----------|-----------|------|
| **Skip link** | `.fn-skip` | Accessibilité clavier |
| **Header** | `.fn-header`, `.fn-brand`, `.fn-nav` | Nav sticky, marque « CL » |
| **Hero** | `.fn-hero`, `.fn-hero__stripe` | Accroche éditoriale + méta labo |
| **Article card** | `.fn-card`, `.fn-card__meta` | Liste d’articles |
| **Badge stack** | `.fn-badges`, `.fn-badge`, modificateurs `--test`, `--fail`, `--internal`, `--partner` | Taxonomie visuelle |
| **Callout J’ai testé** | `.fn-callout`, `.fn-callout--tested` | Récit d’expérience |
| **Callout Chez nous** | `.fn-callout--internal` | Contexte entreprise / flotte agents |
| **Callout Échec honnête** | `.fn-callout--fail` | Transparence sur échec |
| **Partenaire** | `.fn-partner`, `.fn-partner--inline` | Mention légale discrète |
| **Code** | `.fn-pre`, `.fn-code-inline` | Snippets monospace |
| **Playground panel** | `.fn-playground`, `.fn-playground__controls` | Zone interactive showroom |
| **Theme switch** | `.fn-theme-switch` | `role="switch"` |
| **Settings** | `.fn-settings`, `.fn-setting-row` | Page Réglages |
| **Persona preview** | `[data-persona="lea"]` / `malik` sur `body` | Ajuste accent secondaire (demo) |

---

## 6. Accessibilité

| Cible | Règle |
|-------|--------|
| Contraste texte | ≥ **4.5:1** corps ; ≥ **3:1** grands titres (vérifié clair + sombre) |
| Focus | Anneau `2px solid var(--fn-accent)` + offset 2px ; jamais `outline: none` sans substitut |
| Touch | Cibles interactives ≥ **44×44px** (switch, nav) |
| Sémantique | Landmarks `header`, `main`, `nav`, `footer` ; `aria-current` sur page active |
| Live regions | `aria-live="polite"` sur statut thème |
| Langue | `lang="fr"` sur documents |

---

## 7. Éthique partenaires / sponsors

1. **Pas de bannière pleine largeur** ni pop-in ; uniquement encart `.fn-partner` en bas d’article ou note de bas de page.
2. **Libellé explicite** : « Mention partenaire » / « Contenu en lien avec un outil utilisé en labo » — jamais « sponsor » déguisé en editorial.
3. **Style visuel** : bordure pointillée, fond neutre, pas de couleur marque partenaire dominante.
4. **Un seul encart** par article dans le mock ; empiler interdit dans le template.
5. **Lien** : `rel="sponsored noopener"` lorsque applicable.

---

## 8. Fichiers d’implémentation

| Fichier | Description |
|---------|-------------|
| `packages/field-notes/assets/css/field-notes.css` | Design system |
| `packages/field-notes/assets/js/field-notes-theme.js` | Thème + persona (playground) |
| `packages/field-notes/playground/index.html` | Showroom interactif |
| `packages/field-notes/index.html` | Landing minimale |
| `packages/field-notes/settings.html` | Mock Réglages |

---

## 9. Principes de rédaction (alignement UX)

- Titres en **question ou constat**, pas en slogan marketing.
- Les callouts portent la voix « je » ; le corps peut rester plus neutre.
- Les blocs code sont courts et commentés en français si besoin.
- Les badges ne remplacent pas le texte : ils orientent le scan.

---

*Document maintenu par l’équipe design AgentBnZo · prochaine étape : brancher `src/blog_template.py` clone sur ces tokens.*
