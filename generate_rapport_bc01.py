#!/usr/bin/env python3
"""
Génère le rapport professionnel BC01 — version finale au format .docx.
Utilise uniquement la bibliothèque standard Python (zipfile + xml.sax).

Usage :
    python3 generate_rapport_bc01.py
    → produit docs/BC01_rapport_professionnel_nexus_analytics_final.docx
"""

import os
import zipfile
from xml.sax.saxutils import escape

OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__),
    "docs",
    "BC01_rapport_professionnel_nexus_analytics_final.docx",
)


# ---------------------------------------------------------------------------
# Helpers XML
# ---------------------------------------------------------------------------


def p(text: str, style: str = "Normal") -> str:
    return (
        f"<w:p>"
        f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>'
        f'<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r>'
        f"</w:p>"
    )


def p_runs(runs: list[tuple[str, bool]], style: str = "Normal") -> str:
    parts = [f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr>']
    for text, bold in runs:
        bld = "<w:b/><w:bCs/>" if bold else ""
        rpr = f"<w:rPr>{bld}</w:rPr>" if bld else ""
        parts.append(f'<w:r>{rpr}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>')
    parts.append("</w:p>")
    return "".join(parts)


def empty_p() -> str:
    return '<w:p><w:pPr><w:pStyle w:val="Normal"/></w:pPr></w:p>'


def page_break() -> str:
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'


def cell(text: str, bold: bool = False, shade: str = "") -> str:
    bld = "<w:b/><w:bCs/>" if bold else ""
    rpr = f"<w:rPr>{bld}</w:rPr>" if bld else ""
    shd = f'<w:shd w:val="clear" w:color="auto" w:fill="{shade}"/>' if shade else ""
    return (
        f"<w:tc>"
        f'<w:tcPr>{shd}<w:tcW w:w="0" w:type="auto"/></w:tcPr>'
        f'<w:p><w:r>{rpr}<w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'
        f"</w:tc>"
    )


def table(rows: list, header_shade: str = "D9E1F2") -> str:
    xml = [
        "<w:tbl>",
        "<w:tblPr>",
        '<w:tblStyle w:val="TableGrid"/>',
        '<w:tblW w:w="9200" w:type="dxa"/>',
        "<w:tblBorders>",
        '<w:top w:val="single" w:sz="4" w:space="0" w:color="999999"/>',
        '<w:left w:val="single" w:sz="4" w:space="0" w:color="999999"/>',
        '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="999999"/>',
        '<w:right w:val="single" w:sz="4" w:space="0" w:color="999999"/>',
        '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="BBBBBB"/>',
        '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="BBBBBB"/>',
        "</w:tblBorders>",
        "</w:tblPr>",
    ]
    for i, row in enumerate(rows):
        is_header = i == 0
        xml.append("<w:tr>")
        for c in row:
            xml.append(cell(str(c), bold=is_header, shade=header_shade if is_header else ""))
        xml.append("</w:tr>")
    xml.append("</w:tbl>")
    return "".join(xml)


# ---------------------------------------------------------------------------
# Document body
# ---------------------------------------------------------------------------


def build_body() -> str:
    parts: list[str] = []

    def add(*items: str) -> None:
        parts.extend(items)

    # ================================================================ PAGE DE GARDE
    add(empty_p(), empty_p(), empty_p())
    add(p("RNCP37638 — Expert en infrastructures de données massives", "Heading1"))
    add(p("Bloc de compétences BC01 — Piloter la conduite d'un projet data", "Heading2"))
    add(empty_p())
    add(p("Rapport professionnel individuel", "Heading2"))
    add(p("Infrastructure de données compétitives League of Legends", "Heading3"))
    add(empty_p())
    add(
        table(
            [
                ["Candidat", "Antoine MLD, Data Engineer consultant"],
                [
                    "Commanditaire",
                    "Marc Delacroix, Co-fondateur et Directeur général, Nexus Analytics",
                ],
                [
                    "Mission",
                    (
                        "Conception et déploiement d'une infrastructure de données pour l'automatisation de la production "
                        "des rapports d'analyse compétitive"
                    ),
                ],
                ["Date", "Mai 2026"],
                [
                    "Statut",
                    (
                        "Document produit dans le cadre de l'évaluation E2 du bloc BC01 — RNCP37638. "
                        "Commanditaire fictif, données de marché sourcées."
                    ),
                ],
            ]
        )
    )
    add(page_break())

    # ================================================================ SOMMAIRE
    add(p("Sommaire", "Heading1"))
    for item in [
        "1. Introduction : contexte, enjeux et reformulation du besoin",
        "   1.1 Contexte de la mission",
        "   1.2 Enjeux du projet",
        "   1.3 Reformulation du besoin initial",
        "2. Objectifs et périmètre fonctionnel du projet",
        "   2.1 Objectifs SMART",
        "   2.2 Périmètre fonctionnel inclus",
        "   2.3 Cartographie des données",
        "   2.4 Périmètre fonctionnel exclu (Won't Have — MoSCoW)",
        "3. Étude d'opportunités",
        "   3.1 Synthèse des entretiens métier",
        "   3.2 Benchmark des outils, plateformes et services disponibles",
        "4. Étude de faisabilité",
        "   4.1 Architecture technique retenue et justification des choix",
        "   4.2 Matrice des flux de données",
        "   4.3 Qualité des données",
        "   4.4 Conformité RGPD",
        "   4.5 Éco-responsabilité",
        "   4.6 Coûts, délais et moyens",
        "   4.7 Accessibilité des livrables",
        "5. Conclusions et recommandation de cadrage",
        "   5.1 Analyse RICE",
        "   5.2 Recommandation de cadrage",
        "   5.3 Conclusion",
        "",
        "Annexe 1 — Architecture technique et infrastructure GCP",
        "Annexe 2 — Modèle de données Gold (schéma en étoile)",
        "Annexe 3 — Plan de communication et rituels du projet",
        "Annexe 4 — Registre des traitements RGPD — synthèse",
    ]:
        add(p(item))
    add(page_break())

    # ================================================================ 1. INTRODUCTION
    add(p("1. Introduction", "Heading1"))

    add(p("1.1 Contexte de la mission", "Heading2"))
    add(
        p(
            "Je suis data engineer consultant, missionné par Nexus Analytics en mai 2026 pour concevoir et déployer une "
            "infrastructure de données adaptée à leurs besoins opérationnels. Nexus Analytics est un cabinet de conseil en "
            "performance compétitive spécialisé dans League of Legends, fondé il y a dix-huit mois par Marc Delacroix, ancien "
            "analyste performance dans une équipe de la Ligue Française de League of Legends (LFL). La structure accompagne "
            "quatre équipes clientes — deux équipes LFL, une équipe EMEA Masters, et une académie préparant des joueurs au "
            "circuit professionnel — en leur livrant des rapports hebdomadaires de préparation de matchs, d'analyse méta et "
            "de scouting d'adversaires."
        )
    )
    add(
        p(
            "League of Legends est un jeu vidéo compétitif édité par Riot Games, structuré en ligues professionnelles "
            "régionales dont la LEC (League of Legends EMEA Championship) représente l'échelon européen maximal et la "
            "LFL son équivalent français de deuxième division. Ces compétitions génèrent des données de match volumineuses — "
            "positions de joueurs, indicateurs économiques en jeu, compositions d'équipes — qui constituent la matière première "
            "du conseil en performance compétitive."
        )
    )

    add(p("1.2 Enjeux du projet", "Heading2"))
    add(
        p(
            "Le marché du conseil en analyse esport est en structuration rapide. Team Liquid, organisation esport "
            "professionnelle de 300 employés, a documenté publiquement avec SAP la problématique centrale de ce secteur : "
            "l'analyse de performance reposait sur du travail entièrement manuel, représentant 250 000 dollars d'économies "
            "annuelles une fois automatisée, sur la base de 1,6 terabyte de données historiques couvrant plus de dix millions "
            "de parties analysées. Source : SAP customer story officielle (sap.com, mise à jour mai 2025). Team Liquid est "
            "une grande organisation avec un partenariat SAP — son cas illustre le besoin mais ne représente pas la réalité "
            "de Nexus Analytics. Ce qui est pertinent pour ma mission, c'est la nature du problème : le déséquilibre entre "
            "le temps consacré à la collecte manuelle de données et le temps consacré à l'analyse à valeur ajoutée est un "
            "problème structurel qui se pose à toutes les échelles de l'écosystème."
        )
    )
    add(
        p(
            "Côté infrastructure de données, le marché s'est récemment consolidé autour d'un acteur unique. GRID, une "
            "startup berlinoise, est depuis décembre 2023 le distributeur officiel exclusif des données compétitives LoL en "
            "vertu d'un partenariat multi-années avec Riot Games couvrant la LEC, les ERLs et l'EMEA Masters. "
            "Source : SportVideo.org, 4 décembre 2023. En mai 2025, Bayes Esports — qui assurait précédemment ce rôle — "
            "a fait faillite, et GRID a racheté ses actifs en septembre 2025. Source : Yogonet International, "
            "24 septembre 2025. Ce service est commercial et orienté bookmakers, diffuseurs et grandes organisations, "
            "inaccessible pour une structure comme Nexus Analytics. L'accès non-commercial individuel à ces données "
            'officielles est mentionné par Riot comme "en cours de déploiement" sans date annoncée en mai 2026. '
            "Source : riotesportsdata.com."
        )
    )
    add(
        p(
            "C'est dans ce contexte — besoin documenté, données publiques disponibles mais sans infrastructure, solutions "
            "commerciales hors budget — que Nexus Analytics m'a confié cette mission."
        )
    )

    add(p("1.3 Reformulation du besoin initial", "Heading2"))
    add(
        p(
            "La demande initiale de Marc Delacroix, telle qu'il me l'a formulée lors de notre premier entretien le 12 mai 2026, "
            "était la suivante : réduire le temps que ses analystes passent à collecter et mettre en forme des données et leur "
            "permettre de se concentrer sur la production d'analyses. Cette formulation, bien que juste dans son intention, "
            "reste trop générale pour cadrer un projet data. Mon travail d'analyse de besoin a consisté à la préciser et à "
            "la compléter."
        )
    )
    add(
        p(
            "La reformulation que je soumets au commanditaire est la suivante : concevoir et déployer une infrastructure de "
            "données automatisée qui ingère hebdomadairement les données compétitives League of Legends disponibles "
            "publiquement (Oracle's Elixir, Leaguepedia API, Riot API), les normalise, les modélise dans un entrepôt "
            "analytique structuré, et les expose via une API interne permettant à l'analyste de produire ses rapports sans "
            "manipulation manuelle de fichiers, dans le cadre d'un usage interne non-commercial respectant les conditions "
            "d'utilisation de chaque source."
        )
    )
    add(page_break())

    # ================================================================ 2. OBJECTIFS ET PÉRIMÈTRE
    add(p("2. Objectifs et périmètre fonctionnel du projet", "Heading1"))

    add(p("2.1 Objectifs SMART", "Heading2"))
    add(
        p(
            "Quatre objectifs structurent ce projet, rédigés selon la méthode SMART (Spécifique, Mesurable, Acceptable, "
            "Réaliste, Temporellement défini). Ces objectifs ont été co-construits et validés lors des entretiens des "
            "12, 14 et 16 mai 2026 (voir Annexe 3 — Plan de communication, réunion de lancement S1)."
        )
    )
    add(
        table(
            [
                ["Objectif", "Formulation SMART"],
                [
                    "O1 — Automatisation de l'ingestion",
                    "Mettre en place un pipeline automatisé qui ingère les données Oracle's Elixir et Leaguepedia dans un délai "
                    "inférieur à deux heures suivant leur publication, sans intervention manuelle, avant le 30 septembre 2026. "
                    "Spécifique : pipeline Bronze GCS alimenté par Oracle's Elixir CSV + API Leaguepedia Cargo. "
                    "Mesurable : délai d'ingestion < 2h, zéro téléchargement manuel pendant 4 semaines consécutives. "
                    "Acceptable : validé par Yasmine Karim (entretien du 14 mai 2026). Réaliste : sources publiques accessibles. "
                    "Temporellement défini : 30 septembre 2026.",
                ],
                [
                    "O2 — Réduction du temps de collecte",
                    "Ramener le temps hebdomadaire de l'analyste consacré à la collecte et à la mise en forme des données "
                    "de deux jours (estimation Yasmine Karim, entretien du 14 mai 2026) à moins de trente minutes, avant le "
                    "31 octobre 2026. Mesurable : temps mesuré par l'analyste sur quatre semaines consécutives après mise "
                    "en production. Réaliste : la normalisation Silver et les modèles dbt éliminent les manipulations Excel.",
                ],
                [
                    "O3 — Traçabilité complète",
                    "Garantir que 100% des données utilisées dans les rapports sont traçables jusqu'à leur source et leur "
                    "date d'ingestion, avant le 30 septembre 2026. Spécifique : métadonnée source_uri et ingested_at sur "
                    "chaque objet GCS Bronze et chaque ligne des tables Gold BigQuery. Mesurable : audit aléatoire de "
                    "10 données dans un rapport — 100% doivent être retrouvables dans les logs d'ingestion.",
                ],
                [
                    "O4 — Disponibilité garantie",
                    "Garantir que les données de la semaine en cours sont disponibles dans BigQuery chaque lundi avant 8h00, "
                    "avec un taux de réussite d'au moins 95% sur trois mois glissants, avant le 30 novembre 2026. "
                    "Mesurable : timestamp de disponibilité des données dans BigQuery, taux de succès calculé sur "
                    "13 semaines glissantes. Acceptable : exprimé par Yasmine et Thomas Bourgeois (entretiens).",
                ],
            ]
        )
    )

    add(empty_p())
    add(p("2.2 Périmètre fonctionnel inclus", "Heading2"))
    add(
        p(
            "Le projet couvre les éléments suivants, issus de la synthèse des entretiens métier conduits entre le 12 et "
            "le 16 mai 2026 et confirmés par le commanditaire lors de la réunion de lancement. Les grilles d'entretien "
            "complètes constituent le livrable E1 associé à ce rapport."
        )
    )
    add(
        p(
            "L'ingestion automatisée depuis trois sources publiques : Oracle's Elixir (statistiques de matchs pro en CSV, "
            "couvrant la LFL et l'EMEA Masters depuis 2014), l'API Leaguepedia (historique de drafts, résultats, équipes, "
            "joueurs en tables Cargo MediaWiki, licence CC BY-SA 3.0), et l'API publique Riot Games (données de solo queue "
            "des joueurs LFL identifiés par leur PUUID, usage non commercial conforme à la politique Riot Developer Portal)."
        )
    )
    add(
        p(
            "La normalisation et le dédoublonnage de ces données dans une zone Silver, avec standardisation des noms "
            "d'équipes entre sources hétérogènes et traçabilité complète des transformations."
        )
    )
    add(
        p(
            "La modélisation dimensionnelle dans un entrepôt analytique BigQuery (zone Gold), structuré en schéma en "
            "étoile avec tables de dimensions et tables de faits, transformé et testé par dbt Core."
        )
    )
    add(
        p(
            "L'exposition des données via une API REST interne FastAPI (Nexus Data Platform) déployée sur Cloud Run, "
            "permettant à l'analyste d'interroger l'entrepôt sans écrire de SQL."
        )
    )
    add(
        p(
            "L'infrastructure as code Terraform garantissant la reproductibilité de l'environnement GCP, et le pipeline "
            "CI/CD GitHub Actions automatisant les vérifications à chaque modification du code."
        )
    )

    add(empty_p())
    add(p("2.3 Cartographie des données", "Heading2"))
    add(
        p(
            "La cartographie des données couvre quatre dimensions : la sémantique des objets métier (glossaire), les modèles "
            "de données, les flux de transformation, et les conditions d'accès et de mise à disposition."
        )
    )

    add(p("2.3.1 Sémantique — Glossaire métier", "Heading3"))
    add(
        p(
            "Un glossaire métier complet définit l'ensemble des termes du domaine en cinq périmètres : jeu League of "
            "Legends (champion, patch, méta, pick/ban, KDA, rôle, side, objectifs), compétition LFL (LFL, LEC, EMEA "
            "Masters, split, regular season, playoffs, OverviewPage, roster), sources de données (Oracle's Elixir, "
            "Leaguepedia, Cargo API, Riot API, GRID), identifiants techniques (GameId, MatchId, PUUID, Riot ID, "
            "SoloqueueIds), et architecture données (Bronze, Silver, Gold, NDJSON, schéma en étoile, SCD Type 1, "
            "dbt, partition, clustering, idempotence, quarantaine)."
        )
    )
    add(
        p(
            "Ce glossaire constitue la référence sémantique du projet : tout terme technique utilisé dans les modèles "
            "dbt, les endpoints API et les rapports livrés aux équipes clientes y est défini de façon univoque, "
            "éliminant toute ambiguïté entre les interlocuteurs (data engineer, analyste, commanditaire)."
        )
    )

    add(p("2.3.2 Modèles de données — Schéma en étoile Gold", "Heading3"))
    add(
        p(
            "L'entrepôt analytique BigQuery (zone Gold) est modélisé selon un schéma en étoile. Il comprend cinq "
            "tables de dimensions et trois tables de faits. Le détail complet des champs, clés et relations figure "
            "en Annexe 2 — Modèle de données Gold."
        )
    )
    add(
        table(
            [
                ["Objet", "Type", "Clé primaire", "Description"],
                [
                    "dim_player",
                    "Dimension",
                    "player_id",
                    "Joueurs LFL/EMEA avec Riot ID, équipe courante et historique",
                ],
                [
                    "dim_team",
                    "Dimension",
                    "team_id",
                    "Équipes avec historique de noms (dim_team_alias)",
                ],
                [
                    "dim_champion",
                    "Dimension",
                    "champion_name",
                    "Champions avec statistiques statiques (Data Dragon Riot)",
                ],
                ["dim_patch", "Dimension", "patch_version", "Patches avec dates de déploiement"],
                ["dim_time", "Dimension", "week_id", "Calendrier ISO aligné sur le calendrier LFL"],
                [
                    "fact_match",
                    "Fait",
                    "game_id",
                    "Une ligne par match — résultat, durée, kills, gold, objectifs",
                ],
                [
                    "fact_draft",
                    "Fait",
                    "game_id + action_idx",
                    "Une ligne par pick/ban — calcul pick/ban rates",
                ],
                [
                    "fact_meta_trend",
                    "Fait",
                    "champion + patch + tournament",
                    "Agrégation hebdomadaire winrates par champion/patch",
                ],
            ]
        )
    )

    add(empty_p())
    add(p("2.3.3 Flux de transformation — Architecture Medallion", "Heading3"))
    add(
        p(
            "L'architecture Medallion organise les données en trois zones de maturité croissante. "
            "Le détail technique complet de chaque zone figure en Annexe 1 — Architecture technique."
        )
    )
    add(
        table(
            [
                ["Zone", "Outil", "Format", "Contenu", "Fréquence"],
                [
                    "Bronze",
                    "GCS",
                    "JSON/NDJSON",
                    "Données brutes avec métadonnées d'ingestion (source, date, URI)",
                    "Hebdomadaire + quotidien",
                ],
                [
                    "Silver",
                    "Python + GCS",
                    "NDJSON",
                    "Données normalisées, typées, filtrées LFL",
                    "Hebdomadaire",
                ],
                [
                    "Gold",
                    "BigQuery + dbt",
                    "Tables BigQuery",
                    "Schéma en étoile, modèles analytiques testés",
                    "Hebdomadaire",
                ],
                [
                    "API",
                    "FastAPI + Cloud Run",
                    "JSON/HTTP",
                    "Endpoints analytiques sécurisés par clé API",
                    "À la demande",
                ],
            ]
        )
    )

    add(empty_p())
    add(p("2.3.4 Conditions d'accès et de mise à disposition", "Heading3"))
    add(
        p(
            "L'accès aux données est gouverné par le principe du moindre privilège. L'entrepôt Gold n'est accessible "
            "qu'au compte de service de l'API FastAPI, en lecture seule sur le dataset Gold uniquement. L'analyste "
            "(Yasmine Karim) accède aux données exclusivement via les endpoints API — sans accès direct à BigQuery ni "
            "aux fichiers GCS. Aucun tiers externe n'a accès aux données. Les conditions d'utilisation de chaque "
            "source (Oracle's Elixir, Leaguepedia CC BY-SA 3.0, Riot Developer Portal usage non-commercial) sont "
            "documentées dans le registre RGPD (Annexe 4)."
        )
    )

    add(empty_p())
    add(p("2.4 Périmètre fonctionnel exclu (Won't Have — MoSCoW)", "Heading2"))
    add(
        p(
            "Les éléments suivants ont été classés «Won't Have» dans la méthode MoSCoW appliquée lors de la "
            "priorisation des besoins. Cette classification traduit un choix délibéré de périmètre fondé sur les "
            "contraintes budgétaires, techniques et temporelles identifiées lors des entretiens — non un manque "
            "de valeur de ces fonctionnalités."
        )
    )
    add(
        p(
            "Les données live officielles des matchs LEC et LFL (positions, gold, objectifs en temps réel) sont "
            "distribuées exclusivement par GRID dans le cadre d'un service commercial inaccessible pour Nexus "
            "Analytics. Ces données sont hors périmètre Phase 1."
        )
    )
    add(
        p(
            "Les données de scrimmage (entraînements privés entre équipes) sont accessibles uniquement via le portail "
            "LDP officiel réservé aux organisations partenaires Riot. Elles sont hors périmètre."
        )
    )
    add(
        p(
            "La construction d'un dashboard de visualisation destiné aux équipes clientes constitue une Phase 2, "
            "non couverte par ce premier projet. Elle est identifiée comme fonctionnalité F7 dans l'analyse RICE "
            "(voir section 5.1) et sera cadrée à l'issue de la mise en production sur la base des retours d'usage."
        )
    )
    add(page_break())

    # ================================================================ 3. ÉTUDE D'OPPORTUNITÉS
    add(p("3. Étude d'opportunités", "Heading1"))

    add(p("3.1 Synthèse des entretiens métier", "Heading2"))
    add(
        p(
            "J'ai conduit trois entretiens semi-directifs entre le 12 et le 16 mai 2026. Les grilles d'entretien "
            "complètes constituent le livrable E1 associé à ce rapport. Je présente ici la synthèse analytique "
            "de ces entretiens, organisée par interlocuteur puis par convergences transversales."
        )
    )

    add(p("Marc Delacroix — Directeur général (entretien du 12 mai 2026)", "Heading3"))
    add(
        p(
            "Marc Delacroix a fondé Nexus Analytics après trois ans passés comme analyste performance dans une équipe "
            "LFL. Sa connaissance du terrain lui permet de formuler le problème avec précision : ses analystes passent "
            "plus de temps à manipuler des données qu'à produire de la valeur analytique. Il accompagne actuellement "
            "quatre équipes clientes — deux équipes LFL, une équipe EMEA Masters, et une académie — et leur livre "
            "des rapports hebdomadaires en PDF par email."
        )
    )
    add(
        p(
            "Le déclencheur du projet est un incident survenu en février 2026. Un rapport de préparation de match a "
            "été livré avec des données de méta issues de la semaine S-2 au lieu de la semaine S-1, en raison d'une "
            "confusion dans la gestion des fichiers de l'analyste. L'équipe a préparé son adversaire sur une méta "
            "périmée et a perdu le match. Le client a exprimé un mécontentement formel et Thomas Bourgeois a dû "
            "offrir un mois de prestation gratuit pour compenser. Marc Delacroix m'a explicitement identifié cet "
            "incident comme la révélation d'un problème structurel : le processus repose entièrement sur la "
            "vigilance individuelle de l'analyste, sans filet de sécurité automatisé."
        )
    )
    add(
        p(
            "Sa vision stratégique est pragmatique et chiffrée : doubler le nombre d'équipes clientes d'ici fin 2026 "
            "sans recruter. Il fixe un budget infrastructure de 300€ par mois maximum et exprime une méfiance "
            "explicite vis-à-vis des fournisseurs de données tiers, citant la faillite de Bayes Esports en "
            "mai 2025 comme exemple concret du risque de dépendance à un acteur externe. Cette contrainte oriente "
            "fortement l'architecture vers des sources publiques et une infrastructure auto-hébergée."
        )
    )

    add(p("Yasmine Karim — Analyste senior (entretien du 14 mai 2026)", "Heading3"))
    add(
        p(
            "Yasmine est l'utilisatrice finale principale du système. Sa description détaillée de sa semaine type "
            "m'a permis de cartographier précisément les étapes à automatiser. Chaque semaine, elle commence par "
            "télécharger manuellement le fichier CSV hebdomadaire d'Oracle's Elixir — quand il est disponible, "
            "ce qui arrive parfois le mardi ou mercredi au lieu du lundi. Elle ouvre ce fichier dans Excel, "
            "supprime les lignes vides, corrige les noms d'équipes qui varient selon les sources et les saisons "
            '(par exemple "Team BDS Academy", "BDS Academy" et "BDSA" désignent la même organisation), '
            "réalise des requêtes manuelles sur Leaguepedia pour récupérer les compositions de draft des matchs "
            "récents des adversaires, puis consolide tout dans des tableaux Excel."
        )
    )
    add(
        p(
            "Elle m'a décrit deux problèmes récurrents : l'absence de traçabilité (si elle retrouve un chiffre "
            "dans un rapport livré trois mois plus tôt, elle ne peut pas retrouver d'où il vient) et l'incohérence "
            "entre les sources (Oracle's Elixir et Leaguepedia utilisent des conventions de nommage différentes). "
            "Elle a également exprimé des besoins analytiques non satisfaits : analyser les tendances de draft "
            "au niveau régional, filtrer par patch, et calculer automatiquement les pick/ban rates et winrates "
            "par composition. Ces analyses constituent la valeur ajoutée différenciante de Nexus Analytics."
        )
    )

    add(p("Thomas Bourgeois — Chargé des relations clients (entretien du 16 mai 2026)", "Heading3"))
    add(
        p(
            "Thomas gère la relation avec les quatre équipes clientes. Il m'a indiqué que les équipes LFL ont des "
            "semaines de compétition le lundi et le mardi et attendent les rapports au plus tard le dimanche soir. "
            "Il a signalé un comportement client révélateur : une équipe fait ses propres analyses en parallèle, "
            "directement sur Leaguepedia, parce qu'elle ne fait pas entièrement confiance à la fraîcheur des "
            "données de Nexus Analytics. Ce comportement traduit un manque de confiance que Thomas attribue à "
            "l'absence de garantie sur l'horodatage des données. Une infrastructure avec métadonnées d'ingestion "
            "explicites permettrait à Nexus Analytics de garantir contractuellement la fraîcheur de ses données."
        )
    )
    add(
        p(
            "Il m'a aussi rapporté une demande émergente : une équipe a demandé si Nexus Analytics pourrait "
            "livrer une analyse flash en moins de deux heures quand l'adversaire change au dernier moment. "
            "Aujourd'hui impossible. Avec un entrepôt structuré et une API, cette analyse deviendrait faisable "
            "en moins d'une heure — valeur commerciale directe pour Nexus Analytics."
        )
    )

    add(p("Convergences transversales", "Heading3"))
    add(
        p(
            "Trois besoins convergent dans les trois entretiens, formulés différemment mais renvoyant au même "
            "problème structurel. La fiabilité de la donnée : Marc l'exprime en termes de risque client, "
            "Yasmine en termes de traçabilité, Thomas en termes de confiance client. La disponibilité en temps "
            "voulu : Marc veut des données disponibles avant les semaines de compétition, Yasmine veut ne plus "
            "travailler le week-end en urgence, Thomas veut garantir un délai de livraison contractuel. "
            "La capacité d'analyse à plus grande échelle : Marc veut onboarder de nouveaux clients sans recruter, "
            "Yasmine veut faire des analyses plus riches, Thomas veut proposer des analyses flash."
        )
    )

    add(p("3.2 Benchmark des outils, plateformes et services disponibles", "Heading2"))
    add(
        p(
            "Avant de proposer une architecture, j'ai analysé les outils, plateformes, APIs et services "
            "disponibles sur le marché pour répondre aux besoins de Nexus Analytics. Le benchmark couvre "
            "cinq catégories de solutions identifiées lors des entretiens et de la veille marché."
        )
    )
    add(
        table(
            [
                [
                    "Solution / Catégorie",
                    "Ce que ça couvre",
                    "Limites pour Nexus Analytics",
                    "Budget",
                    "Verdict",
                ],
                [
                    "Oracle's Elixir — site web et CSV (oracleselixir.com)",
                    "Statistiques de matchs pro mondiaux (LFL, LEC, EMEA Masters, LCK, LCS, LPL) depuis 2014. CSV téléchargeables librement. Géré par Tim Sevenhuysen, analyste indépendant.",
                    "Pas d'API. Téléchargement uniquement manuel. Publication non garantie le lundi. CSV bruts sans métadonnées. Noms d'équipes non standardisés. Risque de dépendance à un projet solo.",
                    "Gratuit",
                    "Source à intégrer dans le pipeline. Pas une solution complète.",
                ],
                [
                    "Leaguepedia — wiki collaboratif et API Cargo (lol.fandom.com)",
                    "Historique compétitif LoL complet : drafts, résultats, équipes, joueurs. API MediaWiki Cargo publique, gratuite. Licence CC BY-SA 3.0.",
                    "Pas de pipeline automatisé côté consommateur. API brute nécessitant une infrastructure client. Pas de statistiques post-match granulaires (K/D/A, gold).",
                    "Gratuit",
                    "Source complémentaire à intégrer dans le pipeline.",
                ],
                [
                    "GRID — plateforme de données esport (grid.gg)",
                    "Données officielles live et post-match LEC, LCS, EMEA Masters, ERLs. Partenaire exclusif Riot depuis déc. 2023. API unifiée multi-titres. Sources : sportsvideo.org (déc. 2023), yogonet.com (sept. 2025).",
                    "Service commercial exclusivement. Pas de tarif public. Orienté bookmakers et diffuseurs. Inaccessible pour une structure de 3 personnes. Accès non-commercial non encore disponible (riotesportsdata.com, mai 2026).",
                    "Non public / hors budget",
                    "Hors périmètre. Risque de dépendance illustré par la faillite de Bayes Esports (mai 2025).",
                ],
                [
                    "Mobalytics — plateforme analytics gaming (ESL FACEIT Group)",
                    "Analytics gaming pour joueurs individuels en solo queue. Coaching IA, recommandations de champions. Rachat par ESL FACEIT Group en mars 2025. Source : cbinsights.com.",
                    "Périmètre différent : orienté joueurs individuels, pas équipes professionnelles. Ne couvre pas les données LFL. Pas d'API d'export. Pas de modélisation pour la préparation de match compétitif.",
                    "Freemium (~10€/mois)",
                    "Hors périmètre. Besoin fondamentalement différent.",
                ],
                [
                    "Outils communautaires — sites et apps web (ProComps.gg, LolDraftAI, Draftedlol)",
                    "Aide au draft pour joueurs en ranked. Analyse de synergies, contre-picks, compositions.",
                    "Pas de données LFL pro. Pas d'API ni d'export. Pas d'infrastructure analytique. Conçus pour la consultation humaine, pas pour la production de rapports professionnels.",
                    "Gratuit / Freemium",
                    "Hors périmètre.",
                ],
                [
                    "Nexus Data Platform — solution sur mesure (ce projet)",
                    "Pipeline automatisé Oracle's Elixir + Leaguepedia + Riot API. Architecture Medallion sur GCP (GCS + BigQuery + dbt). API FastAPI interne. Données LFL et EMEA Masters. Traçabilité complète.",
                    "Pas de données live officielles (hors budget). Dépendance à Oracle's Elixir (projet solo). Volume de données modeste.",
                    "~8€/mois en régime de croisière",
                    "Seule solution répondant simultanément aux quatre critères : couverture LFL, automatisation, modélisation analytique, budget compatible.",
                ],
            ]
        )
    )
    add(empty_p())
    add(
        p(
            "Le benchmark confirme qu'aucune solution existante ne répond simultanément aux critères de couverture "
            "LFL, d'automatisation, de modélisation analytique et de budget contrôlé. Le gap identifié par Nexus "
            "Analytics est réel et documenté. Cette analyse comparative sert de fondation à la section 4.1 qui "
            "détaille les choix architecturaux retenus pour la Nexus Data Platform et leur justification "
            "au regard des alternatives identifiées ici."
        )
    )
    add(page_break())

    # ================================================================ 4. ÉTUDE DE FAISABILITÉ
    add(p("4. Étude de faisabilité", "Heading1"))

    add(p("4.1 Architecture technique retenue et justification des choix", "Heading2"))
    add(
        p(
            "L'architecture que je propose s'appuie sur le pattern Medallion, structuré en trois zones de données : "
            "Bronze pour les données brutes avec leurs métadonnées d'origine, Silver pour les données normalisées "
            "et dédoublonnées, Gold pour les données modélisées et prêtes à l'analyse. Ce pattern est devenu un "
            "standard de l'industrie car il offre une traçabilité complète de la transformation des données, une "
            "tolérance aux erreurs entre zones, et une flexibilité pour ajouter de nouvelles sources sans remettre "
            "en cause l'ensemble. Le schéma complet de l'architecture et l'infrastructure GCP associée figurent "
            "en Annexe 1."
        )
    )

    add(p_runs([("Zone Bronze — ", True), ("Google Cloud Storage", False)]))
    add(
        p(
            "Les données brutes de chaque source sont ingérées dans GCS avec leurs métadonnées d'ingestion : "
            "nom de la source, horodatage précis, version du schéma, URI de l'objet GCS. Ces métadonnées "
            "répondent directement au problème de traçabilité identifié lors des entretiens et à la cause racine "
            "de l'incident de février 2026. La stratégie de classes de stockage optimise les coûts : données "
            "courantes en Standard, données plus anciennes en Nearline (0,010$/Go/mois). "
            "Source : finout.io/blog/cloud-storage-pricing-comparison (mai 2026)."
        )
    )

    add(p_runs([("Zone Silver — ", True), ("Python + NDJSON sur GCS", False)]))
    add(
        p(
            "Les données Bronze sont transformées par des scripts Python. Les transformations comprennent la "
            "standardisation des noms d'équipes via une table de mapping (dim_team_alias), la résolution des "
            "doublons entre Oracle's Elixir et Leaguepedia, l'homogénéisation des formats de date en ISO 8601, "
            "et l'isolation des entrées corrompues dans une table de quarantaine. Le résultat est stocké en "
            "NDJSON (Newline Delimited JSON), format compatible natif avec BigQuery pour un chargement sans "
            "étape de conversion."
        )
    )

    add(p_runs([("Zone Gold — ", True), ("BigQuery + dbt Core", False)]))
    add(
        p(
            "Les données Silver sont chargées dans BigQuery et modélisées par dbt Core en schéma en étoile "
            "(détaillé en Annexe 2). dbt Core est open source et gratuit : il permet de versionner les modèles "
            "SQL dans Git, de les tester automatiquement à chaque exécution et de générer la documentation de "
            "l'entrepôt. Le partitionnement des tables de faits par date et le clustering par compétition et "
            "équipe réduisent le volume de données scannées par chaque requête de 60 à 90%. "
            "Source : leanopstech.com/blog/google-bigquery-pricing-2026."
        )
    )

    add(p_runs([("API Nexus Data Platform — ", True), ("FastAPI sur Cloud Run", False)]))
    add(
        p(
            "Une API REST développée avec FastAPI expose les indicateurs analytiques à Yasmine sans qu'elle ait "
            "besoin d'écrire du SQL. Les endpoints couvrent : pick/ban rates par champion sur les N derniers "
            "patches, winrates par composition sur une période donnée, historique de draft complet d'une équipe "
            "adverse, top 5 des compositions jouées par une équipe sur ses dix derniers matchs. "
            "L'API est déployée sur Cloud Run — serverless, gratuite pour un usage interne à faible fréquence "
            "(tier gratuit : 2 millions de requêtes par mois)."
        )
    )

    add(p_runs([("Infrastructure as Code et CI/CD", True)]))
    add(
        p(
            "L'ensemble de l'infrastructure GCP est décrit en Terraform et versionné dans Git : buckets GCS "
            "avec politiques de rétention et de tiering, dataset BigQuery Gold en europe-west1, service Cloud "
            "Run pour l'API, comptes de service IAM avec droits minimaux. Un pipeline GitHub Actions automatise "
            "les vérifications à chaque modification : lint Python avec ruff, tests dbt, build Docker API."
        )
    )

    add(p("4.2 Matrice des flux de données", "Heading2"))
    add(
        table(
            [
                [
                    "Flux",
                    "Source",
                    "Destination",
                    "Fréquence",
                    "Volume estimé *",
                    "Format",
                    "Déclencheur",
                ],
                [
                    "Ingestion Oracle's Elixir",
                    "oracleselixir.com",
                    "GCS Bronze",
                    "Hebdomad.",
                    "~5 Mo/CSV",
                    "CSV",
                    "Cloud Scheduler dim. 20h00",
                ],
                [
                    "Ingestion Leaguepedia API",
                    "lol.fandom.com Cargo",
                    "GCS Bronze",
                    "Quotid.",
                    "~1 Mo/jour",
                    "JSON",
                    "Cloud Scheduler quotidien 06h00",
                ],
                [
                    "Ingestion Riot API ranked",
                    "developer.riotgames.com",
                    "GCS Bronze",
                    "Quotid.",
                    "~500 Ko/jour",
                    "JSON",
                    "Cloud Scheduler quotidien 07h00",
                ],
                [
                    "Normalisation Silver",
                    "GCS Bronze",
                    "GCS Silver",
                    "Hebdomad.",
                    "~2 Mo/NDJSON",
                    "NDJSON",
                    "Après succès ingestion Oracle's Elixir",
                ],
                [
                    "Chargement Silver → Gold",
                    "GCS Silver",
                    "BigQuery raw",
                    "Hebdomad.",
                    "~1 Mo/semaine",
                    "BQ tables",
                    "Après normalisation Silver",
                ],
                [
                    "Transformation dbt",
                    "BigQuery raw",
                    "BigQuery Gold",
                    "Hebdomad.",
                    "~500 Ko nouvelles lignes",
                    "BQ views/tables",
                    "Après chargement Silver → Gold",
                ],
                [
                    "Requêtes analytiques",
                    "BigQuery Gold",
                    "API → Analyste",
                    "À la demande",
                    "< 1 Go scanné/req.",
                    "JSON/HTTP",
                    "Appel HTTP de l'analyste",
                ],
                [
                    "Alertes pipeline",
                    "GitHub Actions",
                    "Discord webhook",
                    "En cas d'erreur",
                    "Minimal",
                    "Texte",
                    "Échec de job ou données non disponibles avant 10h00 lundi",
                ],
            ]
        )
    )
    add(empty_p())
    add(
        p(
            "* Estimations basées sur les volumes réellement observés lors du développement et des premières "
            "ingestions (juin 2026) : 3 053 matchs LFL ingérés depuis Leaguepedia, CSV Oracle's Elixir 2026 "
            "mesurant 4,8 Mo en moyenne, API Riot retournant ~450 Ko pour 200 joueurs LFL. Ces volumes sont "
            "cohérents avec les projections au 30 septembre 2026."
        )
    )

    add(p("4.3 Qualité des données", "Heading2"))
    add(
        p(
            "La qualité des données est un enjeu central de ce projet, directement lié à l'incident de "
            "février 2026. Je structure la stratégie de qualité en quatre niveaux d'intervention."
        )
    )
    add(
        p(
            "Au niveau de l'ingestion Bronze, un contrôle de présence et d'intégrité vérifie que chaque "
            "fichier CSV Oracle's Elixir ingéré n'est pas vide, que son horodatage est cohérent avec la "
            "semaine courante (détection du bug qui a causé l'incident de février), et que le nombre de "
            "lignes est dans une plage statistiquement attendue — une alerte est déclenchée si le nombre "
            "de matchs LFL est inférieur à 30 sur une semaine standard de compétition."
        )
    )
    add(
        p(
            "Au niveau de la normalisation Silver, les scripts Python appliquent des règles de validation "
            "métier : format de date ISO 8601 obligatoire sur tous les champs temporels, noms d'équipes "
            "obligatoirement présents dans la table de mapping dim_team_alias (toute équipe non mappée génère "
            "une alerte et est isolée en quarantaine — règle validée avec Yasmine Karim lors de l'entretien "
            "du 14 mai 2026), Riot IDs validés par expression régulière correspondant au format "
            '"gamename#tagline". Les lignes ne passant pas la validation sont stockées dans une table de '
            "quarantaine Bronze distincte avec le motif de rejet explicite et l'horodatage."
        )
    )
    add(
        p(
            "Au niveau de la transformation Gold, dbt Core applique des tests automatiques : not_null sur "
            "toutes les clés, unique sur les identifiants de match et de draft, accepted_values sur les "
            "colonnes catégorielles, relationships pour l'intégrité référentielle. Des tests singuliers dbt "
            "vérifient des règles métier : le winrate d'un champion doit être compris entre 0 et 100%, "
            "un match doit avoir exactement 10 joueurs, une composition de draft valide comporte exactement "
            "5 picks par équipe."
        )
    )
    add(
        p(
            "Au niveau opérationnel, un rapport de qualité hebdomadaire automatique est envoyé sur le "
            "channel Discord de Nexus Analytics après chaque run complet du pipeline : nombre de matchs "
            "ingérés, lignes rejetées en quarantaine avec les motifs, tests dbt passés et échoués, "
            "timestamp exact de disponibilité des données dans BigQuery Gold."
        )
    )

    add(p("4.4 Conformité RGPD", "Heading2"))
    add(
        p(
            "Le Règlement Général sur la Protection des Données (RGPD, 2018) encadre le traitement des "
            "données à caractère personnel. J'ai conduit une analyse complète du périmètre et formalisé "
            "les résultats dans un registre des traitements détaillé (voir Annexe 4)."
        )
    )

    add(p_runs([("Analyse des données traitées", True)]))
    add(
        p(
            "Oracle's Elixir et Leaguepedia contiennent des statistiques de joueurs professionnels "
            "identifiés par leur Riot ID — un pseudonyme public choisi par le joueur et utilisé dans "
            "le cadre de son activité professionnelle publique. Le traitement de ces données relève "
            "de l'intérêt légitime au sens de l'article 6.1.f du RGPD. L'API Riot Games ranked "
            "retourne des données identifiées par PUUID, un identifiant unique pseudonymisé. "
            "Au sens du RGPD, les données pseudonymisées restent des données à caractère personnel "
            "car la réidentification reste possible. Dans ce projet, seul Riot Games dispose de la "
            "table de correspondance PUUID ↔ identité civile."
        )
    )

    add(p_runs([("Mesures de conformité mises en place", True)]))
    add(
        table(
            [
                ["Mesure", "Implémentation"],
                [
                    "Minimisation des données",
                    "Seules les statistiques strictement nécessaires à l'analyse compétitive sont ingérées. Aucune donnée civile (nom, email, adresse).",
                ],
                [
                    "Localisation UE",
                    "Toutes les ressources GCP provisionnées en région europe-west1 (Belgique). Formalisé dans le code Terraform — non modifiable sans changement explicite de configuration.",
                ],
                [
                    "Durée de conservation",
                    "Bronze : 90 jours puis Coldline (Terraform lifecycle). Silver : durée du projet (≤ 24 mois). Gold : 730 jours via expiration automatique BigQuery.",
                ],
                [
                    "Moindre privilège IAM",
                    "Compte nexus-ingestion : écriture GCS uniquement. Compte nexus-api : lecture seule BigQuery Gold uniquement. Aucun accès tiers externe.",
                ],
                [
                    "Traçabilité des traitements",
                    "Logs BigQuery INFORMATION_SCHEMA.JOBS : qui, quand, quelle table, quel volume scanné. Conservés 30 jours.",
                ],
                [
                    "Secrets",
                    ".env dans .gitignore. pydantic-settings pour la gestion — aucun os.getenv() dans le code métier.",
                ],
            ]
        )
    )

    add(empty_p())
    add(p_runs([("Fréquences d'exécution des traitements de conformité", True)]))
    add(
        table(
            [
                ["Traitement de conformité", "Type", "Fréquence", "Déclencheur"],
                [
                    "Vérification données collectées vs minimisation",
                    "Manuel",
                    "Hebdomadaire",
                    "Avant chaque ingestion Riot API",
                ],
                [
                    "Purge automatique Bronze → Coldline",
                    "Automatisé (Terraform lifecycle)",
                    "Continue (90 jours)",
                    "GCS lifecycle policy",
                ],
                [
                    "Expiration automatique tables BigQuery Gold",
                    "Automatisé (Terraform)",
                    "Continue (730 jours)",
                    "BigQuery table expiration",
                ],
                [
                    "Audit des accès IAM",
                    "Manuel",
                    "Trimestriel",
                    "Revue des comptes de service actifs",
                ],
                [
                    "Revue du registre des traitements",
                    "Manuel",
                    "Annuel ou si changement de traitement",
                    "Ajout d'une nouvelle source de données",
                ],
                [
                    "Traitement des demandes d'exercice des droits",
                    "Manuel (sur demande)",
                    "Sous 30 jours",
                    "Email du joueur concerné",
                ],
                [
                    "Vérification accès BigQuery (INFORMATION_SCHEMA.JOBS)",
                    "Manuel",
                    "Mensuel",
                    "Revue des requêtes sur données personnelles",
                ],
            ]
        )
    )

    add(empty_p())
    add(p_runs([("Absence de nécessité d'AIPD", True)]))
    add(
        p(
            "Ce projet ne nécessite pas d'Analyse d'Impact relative à la Protection des Données (AIPD) "
            "au sens de l'article 35 du RGPD car il ne traite pas de données sensibles au sens de l'article 9, "
            "il ne recourt pas à du profilage automatisé produisant des effets juridiques significatifs, "
            "et le traitement ne porte pas sur des données à grande échelle de personnes vulnérables."
        )
    )

    add(p("4.5 Éco-responsabilité", "Heading2"))
    add(
        p(
            "Le Référentiel Général d'Écoconception des Services Numériques (RGESN, version 2024) est le cadre "
            "de référence gouvernemental français pour réduire l'empreinte environnementale des services "
            "numériques. Il est co-piloté par la DINUM, le Ministère de la Transition Écologique, l'ADEME et "
            "l'Institut du Numérique Responsable, et découle de l'article 25 de la Loi REEN du 15 novembre 2021. "
            "Source : ecoresponsable.numerique.gouv.fr/publications/referentiel-general-ecoconception/. "
            "Le schéma d'architecture illustrant les choix d'écoconception figure en Annexe 1."
        )
    )
    add(
        p_runs(
            [
                ("Sobriété des ressources compute. ", True),
                (
                    "L'architecture est entièrement serverless : GCS, BigQuery, Cloud Run, GitHub Actions "
                    "n'allouent de ressources que lors des traitements effectifs. En dehors des plages d'ingestion "
                    "hebdomadaire et des appels API ponctuels, la consommation de ressources compute est nulle.",
                    False,
                ),
            ]
        )
    )
    add(
        p_runs(
            [
                ("Traitement batch plutôt que streaming. ", True),
                (
                    "Le choix délibéré de ne pas utiliser de pipeline de streaming continu (Kafka, Pub/Sub, Dataflow) "
                    "est une décision d'écoconception explicite. Les données de matchs pro LFL sont disponibles après "
                    "chaque journée de compétition — il n'existe pas de besoin temps réel chez Nexus Analytics.",
                    False,
                ),
            ]
        )
    )
    add(
        p_runs(
            [
                ("Réduction des volumes stockés et transférés. ", True),
                (
                    "Le format NDJSON est optimisé pour l'ingestion BigQuery native. Le partitionnement et le "
                    "clustering des tables BigQuery réduisent le volume de données scannées par chaque requête "
                    "de 60 à 90%. Source : leanopstech.com/blog/google-bigquery-pricing-2026.",
                    False,
                ),
            ]
        )
    )
    add(
        p_runs(
            [
                ("Localisation dans une région à faible intensité carbone. ", True),
                (
                    "La région GCP europe-west1 (Belgique) bénéficie d'un approvisionnement en énergie "
                    "renouvelable supérieur à 90% selon les données publiées par Google Cloud. "
                    "Source : cloud.google.com/sustainability/region-carbon.",
                    False,
                ),
            ]
        )
    )
    add(
        p_runs(
            [
                ("Usage exclusif de logiciels open source. ", True),
                (
                    "Python, dbt Core, FastAPI et Terraform sont tous open source. Cela évite la création "
                    "de nouveaux outils redondants et favorise la réutilisabilité du code.",
                    False,
                ),
            ]
        )
    )
    add(
        p_runs(
            [
                ("Indicateur de suivi. ", True),
                (
                    "Un tableau de bord interne basé sur une requête mensuelle INFORMATION_SCHEMA.JOBS expose "
                    "le volume total de données scannées et le nombre de jobs exécutés, permettant d'identifier "
                    "les requêtes non optimisées avant qu'elles génèrent une consommation énergétique inutile.",
                    False,
                ),
            ]
        )
    )

    add(p("4.6 Coûts, délais et moyens", "Heading2"))

    add(p_runs([("Coûts d'infrastructure mensuels en régime de croisière", True)]))
    add(
        table(
            [
                ["Poste", "Coût mensuel estimé", "Source tarifaire"],
                [
                    "GCS Bronze — 5 Go Standard",
                    "0,10€/mois",
                    "0,020$/Go/mois région EU. Source : finout.io (mai 2026)",
                ],
                [
                    "GCS Silver — 3 Go Nearline",
                    "0,03€/mois",
                    "0,010$/Go/mois Nearline. Même source.",
                ],
                [
                    "BigQuery Gold — stockage + requêtes",
                    "0€/mois (tier gratuit)",
                    "10 Go stockage + 1 TB requêtes gratuites/mois",
                ],
                [
                    "Cloud Run — API FastAPI interne",
                    "0€/mois (tier gratuit)",
                    "2 millions de requêtes gratuites/mois. Source : cloud.google.com/run/pricing",
                ],
                [
                    "GitHub Actions — CI/CD",
                    "0€/mois (tier gratuit)",
                    "2 000 minutes/mois gratuites. Source : github.com/pricing",
                ],
                [
                    "Inoreader Pro — veille technique",
                    "7€/mois (~7,50$/mois)",
                    "Plan Pro annuel 90$/an. Source : readless.app (mai 2026)",
                ],
                [
                    "Total mensuel en régime de croisière",
                    "~8€/mois",
                    "Très largement inférieur au plafond de 300€/mois fixé par le commanditaire. Marge de 292€/mois pour la montée en charge.",
                ],
            ]
        )
    )
    add(empty_p())
    add(
        p(
            "Note sur les tiers gratuits : les coûts de 0€ sur BigQuery, Cloud Run et GitHub Actions "
            "reposent sur les tiers gratuits permanents de GCP et GitHub. Ces tiers sont adaptés aux volumes "
            "du projet en Phase 1 (pipeline hebdomadaire, usage interne). En cas de doublement des clients "
            "et d'augmentation du volume de requêtes, le dépassement du tier BigQuery est possible mais "
            "resterait marginal (environ 5$/TB au-delà du tier gratuit). Le monitoring mensuel via "
            "INFORMATION_SCHEMA.JOBS permet d'anticiper ce risque."
        )
    )

    add(empty_p())
    add(p_runs([("Moyens humains", True)]))
    add(
        table(
            [
                ["Rôle", "Personne", "Disponibilité", "Périmètre de responsabilité"],
                [
                    "Data Engineer consultant",
                    "Antoine MLD",
                    "100% — durée projet",
                    "Architecture, développement, déploiement, documentation technique, formation de l'analyste à l'API",
                ],
                [
                    "Analyste senior — utilisatrice finale",
                    "Yasmine Karim",
                    "20% — phases de recette",
                    "Validation fonctionnelle des modèles dbt, recette de l'API FastAPI, feedback sur les endpoints analytiques",
                ],
                [
                    "Directeur général — commanditaire",
                    "Marc Delacroix",
                    "10% — comités de projet",
                    "Validation des jalons, arbitrages budgétaires, go/no-go mise en production",
                ],
            ]
        )
    )

    add(empty_p())
    add(p_runs([("Moyens techniques", True)]))
    add(
        table(
            [
                ["Composant", "Outil retenu", "Coût", "Justification du choix"],
                [
                    "Stockage brut (Bronze)",
                    "Google Cloud Storage Standard + Nearline",
                    "~0,13€/mois",
                    "Intégration native BigQuery, tiering automatique, lifecycle policies Terraform, région EU.",
                ],
                [
                    "Normalisation (Silver)",
                    "Python + NDJSON",
                    "0€ (open source)",
                    "Scripts Python lisibles et maintenables, format NDJSON compatible natif BigQuery, pas d'infrastructure Spark nécessaire.",
                ],
                [
                    "Entrepôt analytique (Gold)",
                    "BigQuery on-demand",
                    "0€ (tier gratuit)",
                    "Serverless, SQL standard, intégration native dbt, partitionnement et clustering pour l'optimisation des requêtes.",
                ],
                [
                    "Transformation et tests",
                    "dbt Core",
                    "0€ (open source)",
                    "Versionning des modèles SQL dans Git, tests automatiques, documentation auto-générée.",
                ],
                [
                    "Orchestration pipeline",
                    "GitHub Actions + Cloud Scheduler",
                    "0€ (tiers gratuits)",
                    "Orchestration légère suffisante pour un pipeline hebdomadaire. Évite la complexité d'Airflow pour ce volume.",
                ],
                [
                    "API interne",
                    "FastAPI sur Cloud Run",
                    "0€ (tier gratuit)",
                    "Framework Python moderne, OpenAPI auto-généré, déploiement serverless sans gestion de serveur.",
                ],
                [
                    "Infrastructure as Code",
                    "Terraform",
                    "0€ (open source)",
                    "Reproductibilité totale de l'environnement GCP, traçabilité des changements dans Git.",
                ],
                [
                    "Versionning et CI/CD",
                    "GitHub + GitHub Actions",
                    "0€ (plan gratuit)",
                    "Lint Python (ruff), tests dbt, build Docker automatisés à chaque modification.",
                ],
            ]
        )
    )

    add(empty_p())
    add(p("4.6.1 Planning prévisionnel et critères d'acceptation", "Heading3"))
    add(
        table(
            [
                ["Semaine(s)", "Jalons", "Contenu détaillé", "Critères d'acceptation"],
                [
                    "S1",
                    "Fondations infrastructure",
                    "Provisionnement Terraform : buckets GCS Bronze et Silver avec lifecycle policies, dataset BigQuery Gold en europe-west1, compte de service API.",
                    "terraform apply retourne exit 0. Tous les buckets GCS et le dataset BigQuery sont créés et vérifiables dans la console GCP.",
                ],
                [
                    "S2",
                    "Socle CI/CD",
                    "Configuration GitHub Actions : lint ruff, tests dbt, build Docker API. Mise en place du webhook Discord pour les alertes pipeline.",
                    "GitHub Actions workflow vert sur le main. Le webhook Discord reçoit un message test de confirmation.",
                ],
                [
                    "S3",
                    "Ingestion Bronze Oracle's Elixir + traçabilité",
                    "Script Python d'ingestion hebdomadaire avec horodatage, validation de présence et de cohérence temporelle, écriture GCS avec métadonnées.",
                    "CSV Oracle's Elixir du lundi est présent dans GCS Bronze avec source_uri et ingested_at. Alert Discord envoyée si absent à 10h00.",
                ],
                [
                    "S4",
                    "Ingestion Bronze Leaguepedia API",
                    "Script Python d'interrogation des 9 tables Cargo Leaguepedia. Pagination, rate limiting exponentiel, écriture GCS JSON.",
                    "9 tables présentes dans GCS Bronze, ScoreboardGames contient ≥ 3 000 lignes LFL, aucune table vide.",
                ],
                [
                    "S5–S6",
                    "Normalisation Silver",
                    "Standardisation des noms d'équipes via dim_team_alias, homogénéisation des formats de date, table de quarantaine.",
                    "0 ligne LFL 2024-2026 en quarantaine non justifiée. Toutes les équipes LFL actives mappées dans dim_team_alias.",
                ],
                [
                    "S7–S9",
                    "Modélisation Gold (dbt)",
                    "Création de tous les modèles dbt : stg, dim_champion, dim_patch, dim_team, dim_player, dim_time, fact_match, fact_draft, fact_meta_trend.",
                    "dbt test retourne 0 erreur. Toutes les dimensions et tables de faits disponibles dans BigQuery Gold.",
                ],
                [
                    "S10–S11",
                    "API FastAPI",
                    "Développement des endpoints analytiques. Authentification par clé API. Déploiement Cloud Run. Tests d'intégration.",
                    "curl /meta/champion-stats retourne 200 avec données LFL réelles. curl /health retourne 200 sur l'URL Cloud Run.",
                ],
                [
                    "S12",
                    "Recette fonctionnelle",
                    "Session de validation avec Yasmine Karim (demi-journée). Yasmine produit un rapport sans ouvrir Excel.",
                    "Yasmine signe le formulaire de recette avec la réponse « Oui » à la question 1 (rapport produit sans Excel). Go/no-go signé.",
                ],
                [
                    "S13",
                    "Corrections et optimisation",
                    "Corrections issues de la recette. Optimisation des requêtes BigQuery identifiées comme coûteuses (dry run).",
                    "0 requête BigQuery scannant > 1 Go par défaut. 0 bug bloquant ouvert issu de la recette S12.",
                ],
                [
                    "S14",
                    "Mise en production + documentation",
                    "Go-live. Formation de Yasmine à l'API (collection Postman). Runbook opérationnel. Premier rapport qualité Discord.",
                    "Pipeline hebdomadaire s'exécute sans erreur dimanche 20h00 → lundi 08h00. Rapport qualité Discord reçu. Yasmine formée.",
                ],
            ]
        )
    )

    add(empty_p())
    add(p("4.6.2 Rituels d'animation du projet", "Heading3"))
    add(
        p(
            "Le plan de communication complet et le processus de recueil des retours figurent en Annexe 3. "
            "Quatre rituels structurent la vie du projet sur les 14 semaines."
        )
    )
    add(
        table(
            [
                ["Rituel", "Fréquence", "Format", "Participants", "Durée"],
                [
                    "Point de statut hebdomadaire (asynchrone)",
                    "Chaque lundi matin",
                    "Message structuré Discord #nexus-updates : fait / prévu / blocages",
                    "Marc Delacroix",
                    "30 min d'écriture DE",
                ],
                [
                    "Point de jalon (synchrone)",
                    "Fin de chaque jalon majeur (S4, S6, S9, S12, S14)",
                    "Visioconférence : démo (10 min) + retours (15 min) + validation go/continue (5 min)",
                    "Marc (obligatoire) + Yasmine (S6/S9/S12) + Thomas (S12/S14)",
                    "45 min max",
                ],
                [
                    "Alerte blocage (asynchrone, à la demande)",
                    "Déclenchée si blocage non résolu en 24h",
                    "Message Discord #nexus-alerts : description, impact planning, action attendue",
                    "Marc Delacroix",
                    "—",
                ],
                [
                    "Rapport qualité automatique",
                    "Chaque dimanche soir après run pipeline",
                    "Message Discord auto-généré par run_pipeline.py : lignes, tests dbt, timestamp disponibilité",
                    "Marc Delacroix, Yasmine Karim",
                    "—",
                ],
            ]
        )
    )

    add(empty_p())
    add(p("4.6.3 Risques identifiés et mesures de mitigation", "Heading3"))
    add(
        table(
            [
                ["Risque", "Probabilité", "Impact", "Mesure de mitigation"],
                [
                    "Oracle's Elixir modifie la structure de ses CSV",
                    "Moyenne",
                    "Fort",
                    "Tests dbt not_null et accepted_values. Alerte Discord automatique. Table de quarantaine pour isoler les données affectées.",
                ],
                [
                    "Oracle's Elixir cesse d'être maintenu (projet solo)",
                    "Faible",
                    "Fort",
                    "Leaguepedia disponible comme source alternative pour les résultats. Veille Inoreader pour détecter toute annonce d'arrêt.",
                ],
                [
                    "Riot Games modifie les CGU de son API développeur",
                    "Faible",
                    "Fort",
                    "Architecture modulaire : la Riot API ranked est une source parmi trois. Le pipeline fonctionne sans elle.",
                ],
                [
                    "Oracle's Elixir non disponible le lundi matin",
                    "Moyenne",
                    "Moyen",
                    "Retry automatique toutes les 2h de 20h00 dimanche à 10h00 lundi. Alerte Discord si absent à 10h00.",
                ],
                [
                    "Dépassement du tier gratuit BigQuery",
                    "Faible à moyen terme",
                    "Faible",
                    "Monitoring mensuel INFORMATION_SCHEMA.JOBS. Partitionnement et clustering limitent structurellement le risque.",
                ],
                [
                    "Incohérence de nommage (nouvelle équipe LFL)",
                    "Certaine (chaque saison)",
                    "Moyen",
                    "Alerte automatique à l'ingestion Silver. Procédure de mise à jour dim_team_alias documentée dans le runbook.",
                ],
            ]
        )
    )

    add(p("4.7 Accessibilité des livrables", "Heading2"))
    add(
        p(
            "L'accessibilité des livrables a été anticipée dès la phase de conception, conformément aux "
            "référentiels RGAA 4.1 et aux recommandations Atalan AcceDe Web pour les documents et communications."
        )
    )
    add(
        table(
            [
                ["Livrable", "Type", "Public", "Mesures d'accessibilité appliquées"],
                [
                    "API REST FastAPI",
                    "Service JSON/HTTP",
                    "Yasmine (Postman), développeurs",
                    "Noms de champs snake_case explicites (player_name, win_rate_pct). Auth X-API-Key compatible tous clients HTTP.",
                ],
                [
                    "Swagger UI /docs",
                    "Interface web OpenAPI",
                    "Développeurs techniques",
                    "Swagger UI 4.x inclut ARIA sur les éléments interactifs. Yasmine utilisera Postman (plus accessible) comme client principal.",
                ],
                [
                    "Documentation Markdown",
                    "Fichiers texte GitHub",
                    "Équipe Nexus Analytics",
                    "Hiérarchie sémantique correcte (#/##/###). Tableaux avec en-têtes. Blocs de code délimités. Texte brut lisible par lecteurs d'écran.",
                ],
                [
                    "Notifications Discord",
                    "Messages texte webhook",
                    "Marc, Yasmine, Thomas",
                    "Messages en texte brut avec emoji textuels (✅/❌). Discord respecte WCAG 2.1 pour son interface web.",
                ],
            ]
        )
    )
    add(empty_p())
    add(
        p(
            "Plan d'amélioration Phase 2 : ajouter des descriptions textuelles aux schémas Mermaid (critère RGAA 1.1), "
            "vérifier la conformité WCAG 2.1 AA du Swagger UI avec axe-core, et vérifier les contrastes "
            "de couleurs du futur dashboard Looker Studio (critère RGAA 1.4 — contraste > 4.5:1)."
        )
    )
    add(page_break())

    # ================================================================ 5. CONCLUSIONS
    add(p("5. Conclusions et recommandation de cadrage", "Heading1"))

    add(p("5.1 Analyse RICE", "Heading2"))
    add(
        p(
            "La méthode RICE permet de prioriser les dix fonctionnalités identifiées lors des entretiens "
            "selon un score calculé comme suit : Score = (Reach × Impact × Confidence) / Effort. "
            "Le Reach exprime le nombre d'utilisateurs impactés par semaine (sur 3 utilisateurs au total). "
            "L'Impact est noté sur une échelle de 0,25 (minimal) à 3 (massif). La Confidence exprime le "
            "niveau de certitude en pourcentage. L'Effort est exprimé en semaines-personne à temps plein."
        )
    )
    add(
        table(
            [
                [
                    "Réf.",
                    "Fonctionnalité",
                    "Reach",
                    "Impact",
                    "Conf.",
                    "Effort",
                    "Score",
                    "Priorité",
                ],
                [
                    "F1",
                    "Ingestion automatisée Oracle's Elixir",
                    "3",
                    "3",
                    "80%",
                    "1 sem.",
                    "7,2",
                    "P1 — Absolu",
                ],
                [
                    "F6",
                    "Traçabilité des métadonnées d'ingestion",
                    "3",
                    "2",
                    "100%",
                    "1 sem.",
                    "6,0",
                    "P1 — Absolu",
                ],
                [
                    "F2",
                    "Ingestion automatisée API Leaguepedia",
                    "3",
                    "3",
                    "80%",
                    "1,5 sem.",
                    "4,8",
                    "P1",
                ],
                [
                    "F10",
                    "CI/CD GitHub Actions",
                    "2",
                    "2",
                    "100%",
                    "1 sem.",
                    "4,0",
                    "P1 — Socle technique",
                ],
                [
                    "F3",
                    "Normalisation Silver / dédoublonnage",
                    "3",
                    "3",
                    "80%",
                    "2 sem.",
                    "3,6",
                    "P1",
                ],
                [
                    "F9",
                    "Infrastructure as Code Terraform",
                    "2",
                    "2",
                    "100%",
                    "1,5 sem.",
                    "2,7",
                    "P1 — Socle technique",
                ],
                [
                    "F4",
                    "Modélisation dimensionnelle BigQuery (dbt)",
                    "3",
                    "3",
                    "80%",
                    "3 sem.",
                    "2,4",
                    "P1",
                ],
                [
                    "F5",
                    "API FastAPI interne (endpoints analytiques)",
                    "2",
                    "3",
                    "80%",
                    "2 sem.",
                    "2,4",
                    "P2",
                ],
                [
                    "F7",
                    "Dashboard de visualisation méta",
                    "2",
                    "2",
                    "50%",
                    "3 sem.",
                    "0,7",
                    "P3 — Phase 2",
                ],
                [
                    "F8",
                    "Alertes automatiques changement de méta",
                    "1",
                    "2",
                    "50%",
                    "2 sem.",
                    "0,5",
                    "P3 — Phase 2",
                ],
            ]
        )
    )
    add(empty_p())
    add(
        p(
            "F6 (traçabilité des métadonnées) obtient le deuxième score malgré sa simplicité technique "
            "apparente : Confidence à 100%, Impact 2 (direct sur l'incident de février et sur la confiance "
            "client), Effort minimal (1 semaine). La méthode RICE confirme ici l'intuition des entretiens : "
            "résoudre le problème de traçabilité est aussi prioritaire que l'ingestion automatisée elle-même."
        )
    )
    add(
        p(
            "F9 et F10 (Terraform et CI/CD) obtiennent des scores modestes en termes de Reach mais doivent "
            "être implémentés en premier dans la pratique, avant même les pipelines de données. L'analyse "
            "RICE ne capture pas les dépendances techniques — ces deux fonctionnalités constituent le socle "
            "sur lequel toutes les autres s'appuient. L'ordre d'implémentation doit donc être lu en "
            "combinaison avec la matrice de dépendances, pas seulement avec les scores RICE."
        )
    )
    add(
        p(
            "F7 et F8 (dashboard et alertes) obtiennent des scores inférieurs à 1 non pas parce qu'ils "
            "sont sans valeur commerciale — Thomas Bourgeois les a explicitement identifiés comme "
            "différenciants — mais parce que leur Confidence est à 50% (le format exact attendu par les "
            "clients n'a pas été validé en détail) et qu'ils sont dépendants de F1 à F5. "
            "Leur place en Phase 2 est cohérente avec cette analyse."
        )
    )

    add(p("5.2 Recommandation de cadrage", "Heading2"))
    add(
        p(
            "Au terme de cette analyse de besoin, de l'étude d'opportunités et de l'étude de faisabilité, "
            "je recommande de lancer le projet selon le périmètre, les conditions et les jalons suivants."
        )
    )
    add(
        p(
            "Le périmètre de la Phase 1 couvre les fonctionnalités F1, F2, F3, F4, F5, F6, F9 et F10, "
            "sur une durée de 14 semaines avec une mise en production avant le 30 septembre 2026 pour "
            "les objectifs O1, O3 et le début de la mesure O4. L'objectif O2 sera mesuré sur quatre "
            "semaines consécutives après mise en production, avec un bilan au 31 octobre 2026."
        )
    )
    add(
        p(
            "Ce périmètre répond intégralement aux besoins exprimés dans les trois entretiens : "
            "automatisation de l'ingestion (O1), traçabilité complète (O3), disponibilité garantie (O4), "
            "réduction du temps de collecte (O2), et capacité d'analyse à plus grande échelle (API FastAPI). "
            "Il respecte les contraintes budgétaires (8€/mois), légales (RGPD, Riot Developer Portal, "
            "CC BY-SA 3.0) et de résilience (pas de dépendance à un fournisseur commercial externe) "
            "exprimées par Marc Delacroix."
        )
    )
    add(
        p(
            "Trois conditions préalables doivent être réunies avant le lancement du développement : "
            "(1) création du projet GCP et activation du compte de facturation — Google Cloud propose "
            "300 dollars de crédits gratuits aux nouveaux comptes ; "
            "(2) enregistrement de l'application sur le Riot Developer Portal avec description précise "
            "de l'usage non commercial, interne, non-redistributif ; "
            "(3) disponibilité confirmée de Yasmine Karim pour une session de recette fonctionnelle "
            "d'une demi-journée en semaine 12 — sa validation est le critère go/no-go de la mise en "
            "production."
        )
    )
    add(
        p(
            "Les fonctionnalités F7 (dashboard de visualisation) et F8 (alertes automatiques) constituent "
            "la Phase 2, à cadrer à l'issue de la Phase 1 sur la base des retours d'usage de Yasmine et "
            "des besoins clients remontés par Thomas Bourgeois."
        )
    )

    add(p("5.3 Conclusion", "Heading2"))
    add(
        p(
            "Ce rapport a démontré que le besoin de Nexus Analytics est réel, documenté et fondé sur un "
            "problème structurel identifié avec précision lors des trois entretiens du 12 au 16 mai 2026. "
            "L'incident de février 2026 n'est pas un accident isolé — c'est la manifestation d'un processus "
            "de collecte de données entièrement dépendant de la vigilance individuelle d'une analyste, "
            "sans aucun filet de sécurité automatisé."
        )
    )
    add(
        p(
            "L'étude de marché a confirmé qu'aucune solution existante ne répond simultanément aux "
            "contraintes de Nexus Analytics : couverture des données LFL, automatisation complète, "
            "budget inférieur à 300€ par mois, et absence de dépendance à un fournisseur commercial "
            "tiers. La Nexus Data Platform, architecturée sur le pattern Medallion avec GCP, dbt Core "
            "et FastAPI, est la seule option qui répond intégralement à ces quatre critères à un coût "
            "de 8€ par mois en régime de croisière."
        )
    )
    add(
        p(
            "L'étude de faisabilité a démontré que ce projet est techniquement réalisable en 14 semaines, "
            "avec des outils open source éprouvés, sans dépassement de budget et dans le respect total "
            "des obligations légales (RGPD, conditions d'utilisation Riot Games, licence CC BY-SA 3.0 "
            "Leaguepedia). La cartographie des données, le modèle dimensionnel en étoile et l'architecture "
            "Medallion fournissent une base solide pour l'analyse compétitive et l'extension future "
            "du périmètre (Phase 2 : dashboard, alertes méta)."
        )
    )
    add(
        p(
            "À l'issue de cette mission d'analyse, je suis en mesure de confirmer que les quatre objectifs "
            "SMART (O1 à O4) sont atteignables dans les délais définis, sous réserve des trois conditions "
            "préalables identifiées. Je soumets cette étude au commanditaire Marc Delacroix pour "
            "validation et go/no-go de lancement du projet."
        )
    )
    add(empty_p())
    add(p("Antoine MLD — Data Engineer consultant — Mai 2026"))
    add(empty_p())
    add(p("Document produit dans le cadre de l'évaluation E2 du bloc BC01 — RNCP37638"))
    add(page_break())

    # ================================================================ ANNEXES
    add(p("Annexes", "Heading1"))

    # ---------------------------------------------------------------- Annexe 1 — Architecture
    add(p("Annexe 1 — Architecture technique et infrastructure GCP", "Heading2"))
    add(
        p(
            "Cette annexe détaille l'architecture technique de la Nexus Data Platform. Elle comprend "
            "la description du pattern Medallion, les services GCP utilisés et leurs rôles respectifs, "
            "et le pipeline CI/CD GitHub Actions."
        )
    )

    add(p("A1.1 Architecture Medallion — vue d'ensemble", "Heading3"))
    add(
        table(
            [
                ["Zone", "Technologie", "Format de stockage", "Rôle", "Politique de rétention"],
                [
                    "Bronze",
                    "Google Cloud Storage Standard",
                    "JSON / NDJSON",
                    "Stockage brut des données avec métadonnées d'ingestion : source_uri, ingested_at, schema_version. "
                    "Immuable après ingestion — aucune modification des données brutes.",
                    "90 jours Standard, puis bascule automatique en Coldline (Terraform lifecycle)",
                ],
                [
                    "Silver",
                    "Google Cloud Storage Nearline",
                    "NDJSON",
                    "Données normalisées, typées, filtrées (LFL uniquement). "
                    "Chargement direct dans BigQuery via bq load sans conversion.",
                    "Durée du projet (≤ 24 mois)",
                ],
                [
                    "Gold",
                    "BigQuery — dataset nexus_gold — région europe-west1",
                    "Tables BigQuery partitionnées",
                    "Schéma en étoile modélisé par dbt Core. Optimisé pour les requêtes analytiques via partitionnement "
                    "par date et clustering par tournament + team.",
                    "730 jours (expiration automatique configurée en Terraform)",
                ],
                [
                    "API",
                    "Cloud Run (Serverless) — europe-west1",
                    "JSON/HTTP sur HTTPS",
                    "API REST FastAPI exposant les endpoints analytiques. Authentification par clé API (header X-API-Key). "
                    "Consomme des ressources uniquement lors des appels effectifs.",
                    "Pas de données stockées à ce niveau",
                ],
            ]
        )
    )

    add(empty_p())
    add(p("A1.2 Infrastructure GCP — services et rôles", "Heading3"))
    add(
        table(
            [
                ["Service GCP", "Usage dans le projet", "Compte de service autorisé", "Coût"],
                [
                    "Cloud Storage (Standard)",
                    "Stockage Bronze — données brutes ingérées",
                    "nexus-ingestion (écriture)",
                    "~0,10€/mois",
                ],
                [
                    "Cloud Storage (Nearline)",
                    "Stockage Silver — données normalisées",
                    "nexus-ingestion (écriture), nexus-api (lecture)",
                    "~0,03€/mois",
                ],
                [
                    "BigQuery (dataset nexus_raw)",
                    "Tables intermédiaires chargées depuis Silver",
                    "nexus-ingestion (écriture)",
                    "0€ (tier gratuit)",
                ],
                [
                    "BigQuery (dataset nexus_gold)",
                    "Tables analytiques Gold — modèles dbt",
                    "nexus-api (lecture seule)",
                    "0€ (tier gratuit)",
                ],
                ["Cloud Run", "API FastAPI Nexus Data Platform", "nexus-api", "0€ (tier gratuit)"],
                [
                    "Cloud Scheduler",
                    "Déclenchement automatique des jobs d'ingestion",
                    "nexus-scheduler",
                    "0€ (tier gratuit)",
                ],
                [
                    "Secret Manager (optionnel Phase 2)",
                    "Stockage sécurisé des clés API",
                    "nexus-ingestion",
                    "< 0,10€/mois",
                ],
            ]
        )
    )

    add(empty_p())
    add(p("A1.3 Pipeline CI/CD GitHub Actions", "Heading3"))
    add(
        table(
            [
                ["Étape", "Déclencheur", "Actions exécutées", "Critère de succès"],
                [
                    "Lint",
                    "Push sur toute branche",
                    "ruff check + ruff format --check sur tout le code Python",
                    "0 erreur de lint, 0 problème de formatage",
                ],
                [
                    "Tests unitaires",
                    "Push sur toute branche",
                    "pytest tests/unit/ avec variables d'environnement dummy",
                    "100% des tests passent",
                ],
                [
                    "Tests dbt (mode CI)",
                    "Push sur branche main",
                    "dbt compile + dbt test avec connexion DuckDB locale (sans BigQuery)",
                    "0 test dbt échoué",
                ],
                [
                    "Build Docker API",
                    "Push sur branche main",
                    "docker build de l'image FastAPI + healthcheck basique",
                    "Image construite sans erreur",
                ],
                [
                    "Déploiement Cloud Run",
                    "Manuel (décision humaine)",
                    "gcloud run deploy — image construite à l'étape précédente",
                    "Service déployé et /health retourne 200",
                ],
            ]
        )
    )

    add(page_break())

    # ---------------------------------------------------------------- Annexe 2 — Modèle Gold
    add(p("Annexe 2 — Modèle de données Gold (schéma en étoile)", "Heading2"))
    add(
        p(
            "Cette annexe détaille le modèle dimensionnel de l'entrepôt analytique BigQuery (zone Gold), "
            "modélisé selon l'approche bottom-up (Kimball). Tous les modèles sont définis en SQL dans "
            "le répertoire dbt/models/ du projet."
        )
    )

    add(p("A2.1 Tables de dimensions", "Heading3"))
    add(
        table(
            [
                ["Table", "Clé primaire", "Principaux champs", "Type de changement (SCD)"],
                [
                    "dim_player",
                    "player_id (player_link Leaguepedia)",
                    "player_name, current_team, riot_id, role, nationality, total_games, total_wins, avg_kda",
                    "SCD Type 1 — stats recalculées à chaque run dbt",
                ],
                [
                    "dim_team",
                    "team_id (team_link Leaguepedia)",
                    "team_name, region, current_split, total_games, total_wins, win_rate",
                    "SCD Type 1 — avec table dim_team_alias pour les variantes de noms",
                ],
                [
                    "dim_champion",
                    "champion_name",
                    "champion_name, champion_class (Fighter/Mage/etc.), primary_role, release_patch",
                    "SCD Type 1 — données statiques (Data Dragon Riot Games)",
                ],
                [
                    "dim_patch",
                    "patch_version (ex: '14.5')",
                    "patch_version, release_date, end_date, patch_notes_url",
                    "Insert uniquement — les patches sont immuables une fois publiés",
                ],
                [
                    "dim_time",
                    "week_id (ISO — ex: '2026-W22')",
                    "week_id, year, week_number, split_name, tournament_phase (regular/playoffs)",
                    "Insert uniquement — calendrier ISO LFL",
                ],
            ]
        )
    )

    add(empty_p())
    add(p("A2.2 Tables de faits", "Heading3"))
    add(
        table(
            [
                ["Table", "Clé primaire", "Grain", "Clés étrangères", "Principaux indicateurs"],
                [
                    "fact_match",
                    "game_id (GameId Leaguepedia)",
                    "1 ligne par partie",
                    "team1_id, team2_id, win_team_id, patch_version, week_id",
                    "gamelength_seconds, team1_kills, team2_kills, team1_gold, team2_gold, team1_dragons, team2_dragons, team1_barons, team2_barons",
                ],
                [
                    "fact_draft",
                    "game_id + action_idx",
                    "1 ligne par action de draft (pick ou ban)",
                    "game_id → fact_match, champion_name → dim_champion",
                    "action_type (pick/ban), team_side (blue/red), pick_order, action_index",
                ],
                [
                    "fact_meta_trend",
                    "champion_name + patch_version + tournament",
                    "1 ligne par champion × patch × tournoi (agrégation hebdomadaire)",
                    "champion_name → dim_champion, patch_version → dim_patch",
                    "pick_count, ban_count, total_games, wins, pick_rate_pct, ban_rate_pct, win_rate_pct",
                ],
            ]
        )
    )

    add(empty_p())
    add(p("A2.3 Relations et intégrité référentielle", "Heading3"))
    add(
        p(
            "Les relations entre tables sont testées automatiquement à chaque run dbt via les tests "
            "relationships. Les relations principales sont :"
        )
    )
    add(
        table(
            [
                ["Table source", "Champ", "Table cible", "Test dbt appliqué"],
                [
                    "fact_match",
                    "team1_id / team2_id / win_team_id",
                    "dim_team.team_id",
                    "relationships (not_null + unique sur dim_team)",
                ],
                ["fact_match", "patch_version", "dim_patch.patch_version", "relationships"],
                ["fact_match", "week_id", "dim_time.week_id", "relationships"],
                ["fact_draft", "game_id", "fact_match.game_id", "relationships"],
                ["fact_draft", "champion_name", "dim_champion.champion_name", "relationships"],
                ["fact_meta_trend", "champion_name", "dim_champion.champion_name", "relationships"],
                ["fact_meta_trend", "patch_version", "dim_patch.patch_version", "relationships"],
            ]
        )
    )

    add(page_break())

    # ---------------------------------------------------------------- Annexe 3 — Plan de communication
    add(p("Annexe 3 — Plan de communication et rituels du projet", "Heading2"))
    add(
        p(
            "Cette annexe formalise la stratégie de communication du projet Nexus Analytics sur les "
            "14 semaines de développement. Elle couvre les parties prenantes, le plan de communication "
            "par étape, les rituels d'animation, les supports utilisés et le processus de recueil des retours."
        )
    )

    add(p("A3.1 Parties prenantes", "Heading3"))
    add(
        table(
            [
                ["Personne", "Rôle", "Intérêt dans le projet", "Canal principal"],
                [
                    "Marc Delacroix",
                    "Directeur général — commanditaire",
                    "Valider les jalons, arbitrages budgétaires, go/no-go mise en production",
                    "Email + Discord + visioconférence",
                ],
                [
                    "Yasmine Karim",
                    "Analyste senior — utilisatrice principale",
                    "Validation fonctionnelle, recette API, réduction de son temps de collecte",
                    "Discord + sessions synchrones",
                ],
                [
                    "Thomas Bourgeois",
                    "Chargé des relations clients",
                    "Retours clients non exprimés, besoins émergents des équipes LFL",
                    "Email",
                ],
                [
                    "Antoine MLD",
                    "Data Engineer consultant",
                    "Réalisation technique complète, documentation, formation",
                    "—",
                ],
            ]
        )
    )

    add(empty_p())
    add(p("A3.2 Plan de communication par étape", "Heading3"))
    add(
        table(
            [
                ["Étape du projet", "Communication prévue", "Destinataires", "Format", "Délai"],
                [
                    "Lancement (S1)",
                    "Réunion de lancement — présentation du plan de travail, jalons S1–S14",
                    "Marc, Yasmine, Thomas",
                    "Visioconférence + support PDF",
                    "Début S1",
                ],
                [
                    "Jalon Bronze (S4)",
                    "Rapport de statut : ingestion automatisée des 3 sources opérationnelle",
                    "Marc",
                    "Email + Discord",
                    "Fin S4",
                ],
                [
                    "Jalon Silver (S6)",
                    "Rapport de statut : données LFL normalisées disponibles en Silver",
                    "Marc, Yasmine",
                    "Discord",
                    "Fin S6",
                ],
                [
                    "Jalon Gold / dbt (S9)",
                    "Démo technique — schéma en étoile et tables Gold disponibles",
                    "Marc, Yasmine",
                    "Visioconférence + dbt docs",
                    "Fin S9",
                ],
                [
                    "Recette fonctionnelle (S12)",
                    "Session de validation : Yasmine produit un rapport sans Excel",
                    "Yasmine",
                    "Session synchrone (demi-journée)",
                    "S12",
                ],
                [
                    "Go/no-go mise en production (S13)",
                    "Compte-rendu de recette + arbitrage final",
                    "Marc",
                    "Email + réunion 30 min",
                    "S13",
                ],
                [
                    "Mise en production (S14)",
                    "Annonce go-live + formation Yasmine (collection Postman)",
                    "Marc, Yasmine, Thomas",
                    "Discord + session formation 1h",
                    "S14",
                ],
                [
                    "Suivi hebdomadaire (S1→S14)",
                    "Rapport qualité automatique pipeline",
                    "Marc, Yasmine",
                    "Discord automatique (run_pipeline.py)",
                    "Chaque dimanche soir",
                ],
                [
                    "Bilan final",
                    "Rapport de fin de projet + retour d'expérience",
                    "Marc, Thomas",
                    "Email + PDF",
                    "S14+1 semaine",
                ],
            ]
        )
    )

    add(empty_p())
    add(p("A3.3 Processus de recueil et traitement des retours", "Heading3"))
    add(
        p(
            "La session de recette fonctionnelle en S12 comprend un formulaire de 5 questions posées "
            "à Yasmine Karim :"
        )
    )
    add(
        table(
            [
                ["N°", "Question", "Type de réponse"],
                [
                    "1",
                    "Avez-vous réussi à produire un rapport de préparation de match complet à partir de l'API sans ouvrir Excel ?",
                    "Oui / Non / Partiellement",
                ],
                [
                    "2",
                    "Les données de pick/ban rates et winrates correspondent-ils à ce que vous attendiez ?",
                    "Oui / Non / Partiellement — préciser",
                ],
                [
                    "3",
                    "Y a-t-il des analyses que vous faisiez manuellement et que l'API ne couvre pas encore ?",
                    "Réponse ouverte",
                ],
                [
                    "4",
                    "La documentation Postman est-elle suffisamment claire pour utiliser l'API sans aide ?",
                    "Note de 1 à 5",
                ],
                [
                    "5",
                    "Recommanderiez-vous cet outil à un analyste qui rejoint l'équipe ?",
                    "Oui / Non — pourquoi",
                ],
            ]
        )
    )
    add(empty_p())
    add(
        table(
            [
                ["Type de retour", "Délai de traitement", "Résultat attendu"],
                [
                    "Bug bloquant (fonctionnalité cassée)",
                    "24h",
                    "Correctif livré et mis en production",
                ],
                [
                    "Fonctionnalité manquante Phase 1",
                    "1 semaine",
                    "Ajout au sprint en cours ou déprioritisation documentée",
                ],
                [
                    "Demande Phase 2",
                    "Après mise en production",
                    "Ajoutée au backlog Phase 2 (dashboard, alertes méta)",
                ],
            ]
        )
    )

    add(page_break())

    # ---------------------------------------------------------------- Annexe 4 — RGPD
    add(p("Annexe 4 — Registre des traitements RGPD — synthèse", "Heading2"))
    add(
        p(
            "Cette annexe synthétise le registre des traitements de données à caractère personnel établi "
            "conformément à l'article 30 du RGPD (UE 2016/679). Le registre complet est maintenu dans "
            "le fichier docs/RGPD_registre.md du dépôt Git du projet."
        )
    )

    add(p("A4.1 Traitements identifiés", "Heading3"))
    add(
        table(
            [
                ["Traitement", "Module", "Données traitées", "Base légale", "Personnes concernées"],
                [
                    "Collecte et stockage des PUUIDs via Riot API",
                    "ingestion/riot_api/ingest.py",
                    "PUUID (identifiant pseudonymisé), Riot ID (nom#tag), Match IDs",
                    "Art. 6.1.f — Intérêt légitime (analyse sportive professionnelle)",
                    "~200 joueurs LFL actifs 2019-2026",
                ],
                [
                    "Collecte des Riot IDs publics via scraping wiki Leaguepedia",
                    "ingestion/leaguepedia_wiki/ingest.py",
                    "Nom de joueur wiki, SoloqueueIds (nom de compte public)",
                    "Art. 6.1.f — Intérêt légitime (données publiques choisies par les joueurs)",
                    "~792 joueurs LFL historiques",
                ],
                [
                    "Stockage et exposition via API FastAPI",
                    "api/main.py + api/database.py",
                    "Riot ID, statistiques de performance (kills, KDA, winrate)",
                    "Art. 6.1.f — identique aux traitements précédents",
                    "Même périmètre",
                ],
            ]
        )
    )

    add(empty_p())
    add(p("A4.2 Durées de conservation et politiques techniques", "Heading3"))
    add(
        table(
            [
                ["Couche", "Durée", "Mécanisme", "Implémentation"],
                [
                    "Bronze GCS",
                    "90 jours Standard + conservation Coldline illimitée",
                    "Automatisé",
                    "Terraform : lifecycle_rule action=SetStorageClass, condition=age=90",
                ],
                [
                    "Silver GCS",
                    "Durée du projet (≤ 24 mois)",
                    "Manuel + suppression de fin de projet",
                    "gsutil rm ou suppression via Console GCP",
                ],
                [
                    "Gold BigQuery",
                    "730 jours (24 mois)",
                    "Automatisé",
                    "Terraform : table_expiration_ms = 730 * 24 * 60 * 60 * 1000",
                ],
            ]
        )
    )

    add(empty_p())
    add(p("A4.3 Droits des personnes concernées", "Heading3"))
    add(
        table(
            [
                ["Droit", "Article RGPD", "Procédure", "Délai"],
                [
                    "Droit d'accès",
                    "Art. 15",
                    "Demande par email — identification par player_link (nom wiki)",
                    "30 jours",
                ],
                [
                    "Droit de rectification",
                    "Art. 16",
                    "Correction manuelle dans les fichiers Silver et Gold, rechargement BigQuery",
                    "30 jours",
                ],
                [
                    "Droit à l'effacement",
                    "Art. 17",
                    "Suppression du PUUID dans Bronze + Silver + Gold via script dédié, relance dbt",
                    "30 jours",
                ],
                [
                    "Droit d'opposition",
                    "Art. 21",
                    "Exclusion du player_link de toutes les ingestions futures (liste de blocage)",
                    "30 jours",
                ],
                [
                    "Droit à la limitation",
                    "Art. 18",
                    "Anonymisation du PUUID (remplacement par hash non réversible SHA-256)",
                    "30 jours",
                ],
            ]
        )
    )

    add(empty_p())
    add(p("A4.4 Absence de nécessité d'AIPD", "Heading3"))
    add(
        p(
            "Ce projet ne nécessite pas d'Analyse d'Impact relative à la Protection des Données (AIPD) "
            "au sens de l'article 35 du RGPD. Les trois critères cumulatifs déclenchant l'obligation "
            "d'AIPD ne sont pas réunis : (1) absence de données sensibles au sens de l'article 9 "
            "(pas de données de santé, biométriques, politiques, etc.) ; (2) absence de profilage "
            "automatisé produisant des effets juridiques significatifs sur les personnes concernées ; "
            "(3) absence de traitement à grande échelle de personnes vulnérables. Les données traitées "
            "sont des statistiques de performance sportive de professionnels publics dans un volume limité "
            "(~200 joueurs actifs)."
        )
    )
    add(empty_p())
    add(p("Données NON collectées par ce projet :", "Normal"))
    add(
        p(
            "Noms civils (prénom, nom de famille) — adresses email ou postales — numéros de téléphone — "
            "données financières — données de santé — données de géolocalisation précise — "
            "données relatives aux mineurs — identités civiles associées aux PUUIDs."
        )
    )

    add(empty_p())
    add(p("——————————————————————————————————————————————————"))
    add(
        p(
            "Document produit dans le cadre de l'évaluation E2 du bloc BC01 — RNCP37638 — "
            "Antoine MLD, Data Engineer consultant — Mai 2026"
        )
    )

    return "".join(parts)


# ---------------------------------------------------------------------------
# OOXML / ZIP assembly
# ---------------------------------------------------------------------------

CONTENT_TYPES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml"
    ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml"
    ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
    Target="word/document.xml"/>
</Relationships>"""

DOCUMENT_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles"
    Target="styles.xml"/>
</Relationships>"""

STYLES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:pPr><w:spacing w:after="120"/></w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
      <w:sz w:val="22"/><w:szCs w:val="22"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr>
      <w:outlineLvl w:val="0"/>
      <w:spacing w:before="400" w:after="200"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
      <w:b/><w:bCs/>
      <w:color w:val="1F3864"/>
      <w:sz w:val="32"/><w:szCs w:val="32"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr>
      <w:outlineLvl w:val="1"/>
      <w:spacing w:before="320" w:after="160"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
      <w:b/><w:bCs/>
      <w:color w:val="2E75B6"/>
      <w:sz w:val="26"/><w:szCs w:val="26"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading3">
    <w:name w:val="heading 3"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr>
      <w:outlineLvl w:val="2"/>
      <w:spacing w:before="240" w:after="100"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
      <w:b/><w:bCs/>
      <w:color w:val="2E75B6"/>
      <w:sz w:val="24"/><w:szCs w:val="24"/>
    </w:rPr>
  </w:style>
  <w:style w:type="table" w:styleId="TableGrid">
    <w:name w:val="Table Grid"/>
    <w:tblPr>
      <w:tblBorders>
        <w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/>
        <w:left w:val="single" w:sz="4" w:space="0" w:color="auto"/>
        <w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/>
        <w:right w:val="single" w:sz="4" w:space="0" w:color="auto"/>
        <w:insideH w:val="single" w:sz="4" w:space="0" w:color="auto"/>
        <w:insideV w:val="single" w:sz="4" w:space="0" w:color="auto"/>
      </w:tblBorders>
    </w:tblPr>
    <w:tcPr>
      <w:tcMar>
        <w:top w:w="80" w:type="dxa"/>
        <w:left w:w="108" w:type="dxa"/>
        <w:bottom w:w="80" w:type="dxa"/>
        <w:right w:w="108" w:type="dxa"/>
      </w:tcMar>
    </w:tcPr>
    <w:rPr>
      <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
      <w:sz w:val="20"/><w:szCs w:val="20"/>
    </w:rPr>
  </w:style>
</w:styles>"""


def build_document_xml(body: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>" + body + "<w:sectPr>"
        '<w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1440" w:right="1134" w:bottom="1440" w:left="1701"'
        ' w:header="708" w:footer="708" w:gutter="0"/>'
        "</w:sectPr>"
        "</w:body>"
        "</w:document>"
    )


def generate_docx(output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    body = build_body()
    document_xml = build_document_xml(body)

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES_XML)
        zf.writestr("_rels/.rels", RELS_XML)
        zf.writestr("word/document.xml", document_xml)
        zf.writestr("word/styles.xml", STYLES_XML)
        zf.writestr("word/_rels/document.xml.rels", DOCUMENT_RELS_XML)

    size_kb = os.path.getsize(output_path) // 1024
    print(f"Fichier généré : {output_path} ({size_kb} Ko)")


if __name__ == "__main__":
    generate_docx(OUTPUT_PATH)
