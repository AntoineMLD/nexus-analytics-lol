# Évaluation accessibilité — Nexus Analytics

> Analyse des besoins et mesures d'accessibilité du projet.
> Répond aux critères C1 (avant-projet — accessibilité anticipée) et C3 (étude technique — accessibilité livrables)
> du référentiel RNCP BC01.
>
> Référentiels applicables :
> - RGAA 4.1 (Référentiel Général d'Amélioration de l'Accessibilité) — pour les interfaces web
> - Recommandations Atalan AcceDe Web — pour les documents et communications
> - Association Valentin Haüy — pour les documents bureautiques
>
> Dernière mise à jour : 2026-07-09

---

## 1. Périmètre du projet et identification des livrables

| Livrable | Type | Public | Interface humaine ? |
|----------|------|--------|-------------------|
| API REST FastAPI | Service JSON/HTTP | Développeurs, analyste (Yasmine) via Postman | Non (interface programmatique) |
| Swagger UI `/docs` | Interface web auto-générée | Développeurs techniques | Oui (web) |
| README.md + docs Markdown | Documentation technique | Développeurs, équipe Nexus Analytics | Non (Markdown → GitHub) |
| Notifications Discord | Messages texte | Marc Delacroix, Yasmine Karim, Thomas Bourgeois | Non (texte brut) |
| Rapport professionnel BC01 | Document PDF/DOCX | Jury RNCP | Non (document statique) |

---

## 2. Analyse des besoins d'accessibilité par livrable

### 2.1 API REST (format JSON)

**Nature** : interface programmatique, pas d'interface graphique. L'API produit du JSON qui sera consommé par Postman (Yasmine) ou par un futur dashboard.

**Accessibilité** :
- Les réponses JSON sont structurées avec des noms de champs en `snake_case` explicites (`player_name`, `win_rate_pct`, `total_games`) — lisibles par les outils de screen-reader via Postman.
- L'authentification repose sur un header HTTP `X-API-Key` — compatible avec tous les clients HTTP accessibles.
- **Aucune adaptation spécifique requise** pour cette interface : les formats JSON standard sont accessibles par défaut aux outils d'assistance.

### 2.2 Swagger UI (`/docs`)

**Nature** : interface web auto-générée par FastAPI basée sur OpenAPI 3.0. Rendue via le composant Swagger UI open source.

**Accessibilité** :
- Swagger UI 4.x inclut des attributs ARIA sur les éléments interactifs (boutons "Try it out", formulaires de paramètres).
- La navigation au clavier est partiellement supportée (tabulation entre les sections).
- **Limite connue** : Swagger UI n'est pas entièrement conforme RGAA/WCAG 2.1 AA (certains composants déroulants ne sont pas correctement labellisés pour les lecteurs d'écran).
- **Mesure compensatoire** : pour l'usage interne Nexus Analytics (Yasmine Karim), Postman sera le client principal de l'API — pas Swagger UI. Postman est accessible via raccourcis clavier.

### 2.3 Documentation Markdown (README, PROGRESS, MERISE, RUNBOOK)

**Nature** : fichiers texte au format Markdown, rendus sur GitHub.

**Accessibilité** :
- Le Markdown est un format texte brut lisible par les lecteurs d'écran sans rendu visuel.
- Les tableaux Markdown utilisent des en-têtes (`|------|`) lisibles par les outils d'assistance.
- Les blocs de code sont délimités par ``` (back-ticks triples) — accessibles en texte brut.
- Les titres utilisent la hiérarchie `#`, `##`, `###` — structure sémantique correcte.
- **Amélioration prévue** : ajouter des textes alternatifs aux schémas ASCII et Mermaid sous forme de description textuelle (déjà présent dans ARCHITECTURE.md via les tableaux "Matrice des flux").

### 2.4 Notifications Discord

**Nature** : messages texte envoyés via webhook.

**Accessibilité** :
- Discord est accessible via lecteur d'écran (NVDA, JAWS) — discord.com respecte les standards WCAG 2.1 pour son interface web.
- Les messages envoyés sont en texte brut avec emoji (`:white_check_mark:` / `:x:`) — lisibles car les emoji Discord ont des descriptions texte.
- **Limite** : les emoji peuvent être verbeux en lecteur d'écran. Si un membre de l'équipe utilise un lecteur d'écran, remplacer les emoji par du texte : `[OK]` / `[ERREUR]`.

---

## 3. Adaptation du poste de travail — équipe technique

**Contexte** : projet réalisé par un data engineer solo (Antoine MLD). Pas d'équipe technique avec des besoins d'adaptation identifiés.

**En cas d'élargissement de l'équipe** :

| Besoin potentiel | Adaptation recommandée |
|-----------------|----------------------|
| Développeur avec déficience visuelle | Configuration de VS Code / Cursor avec lecteur d'écran (NVDA + VS Code accessible) + raccourcis clavier documentés |
| Développeur avec trouble de l'attention | Découpage des PR en unités de < 200 lignes (déjà pratiqué) + revues de code structurées |
| Développeur daltonien | Les notifications Discord utilisent du texte (`✅ OK` / `❌ ERREUR`) et pas uniquement de la couleur |

---

## 4. Adaptation pour l'utilisatrice finale — Yasmine Karim (analyste senior)

**Profil** : analyste senior, usage principal via Postman et Excel. Pas de déficience identifiée.

**Mesures appliquées** :
- L'API expose des données en JSON avec des noms de champs lisibles — Yasmine n'a pas besoin d'écrire du SQL.
- La documentation Postman (prévu en S14) fournira des exemples de requêtes copiables-collables.
- Le Swagger UI permet d'explorer et tester l'API sans code.

**Mesures prévues** :
- Session de formation S14 (30 min) — Yasmine apprend à interroger l'API via Postman, incluant les raccourcis clavier Postman.

---

## 5. Plan d'amélioration accessibilité (Phase 2)

Pour un projet visant une mise en production avec des utilisateurs externes ou un dashboard web :

| Action | Priorité | Critère RGAA | Effort estimé |
|--------|----------|-------------|--------------|
| Ajouter des descriptions textuelles à tous les schémas Mermaid | P2 | 1.1 — Texte alternatif images | 1h |
| Vérifier la conformité WCAG 2.1 AA du Swagger UI avec axe-core | P3 | Multiple | 2h |
| Dashboard Looker Studio : vérifier les contrastes de couleurs (> 4.5:1) | P2 (Phase 2) | 1.4 — Contraste | 1h |
| Ajouter une option texte seul pour les notifications Discord (sans emoji) | P3 | Accessibilité des contenus | 30min |
