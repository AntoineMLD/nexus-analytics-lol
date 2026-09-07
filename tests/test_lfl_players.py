"""Tests for pipeline/silver_transforms/lfl_players.py.

All GCS calls are mocked. Tests cover the 3 SoloqueueIds formats documented
in parse_euw_accounts, plus edge cases for each helper function.
"""

from unittest.mock import MagicMock, patch

from pipeline.silver_transforms.lfl_players import (
    _split_accounts,
    build_soloqueue_lookup,
    enrich_players,
    extract_players_from_rosters,
    filter_lfl_tournaments,
    parse_euw_accounts,
    run_transform,
    save_to_gcs,
    strip_wiki_markup,
)

LFL_LEAGUES = {"La Ligue Française", "La Ligue Française Division 2"}


# ─── strip_wiki_markup ────────────────────────────────────────────────────────


class TestStripWikiMarkup:
    def test_removes_triple_quotes(self):
        assert strip_wiki_markup("'''EUW:'''") == "EUW:"

    def test_removes_double_quotes(self):
        assert strip_wiki_markup("''italic''") == "italic"

    def test_replaces_br_with_newline(self):
        assert strip_wiki_markup("a<br>b") == "a\nb"

    def test_br_self_closing(self):
        assert strip_wiki_markup("a<br/>b") == "a\nb"

    def test_br_with_space(self):
        assert strip_wiki_markup("a<br />b") == "a\nb"

    def test_br_case_insensitive(self):
        assert strip_wiki_markup("a<BR>b") == "a\nb"

    def test_combined_markup(self):
        result = strip_wiki_markup("'''EUW:''' Name1<br>Name2")
        assert result == "EUW: Name1\nName2"

    def test_empty_string(self):
        assert strip_wiki_markup("") == ""


# ─── _split_accounts ─────────────────────────────────────────────────────────


class TestSplitAccounts:
    def test_single_account(self):
        assert _split_accounts("Caliste") == ["Caliste"]

    def test_comma_separated(self):
        assert _split_accounts("Caliste, Saken") == ["Caliste", "Saken"]

    def test_newline_separated(self):
        assert _split_accounts("Caliste\nSaken") == ["Caliste", "Saken"]

    def test_strips_server_suffix(self):
        assert _split_accounts("Achuu (EUW)") == ["Achuu"]

    def test_strips_whitespace(self):
        assert _split_accounts("  Caliste  ") == ["Caliste"]

    def test_filters_single_char(self):
        # Single-char entries are noise, not valid account names
        assert _split_accounts("a") == []

    def test_empty_entries_filtered(self):
        result = _split_accounts("Caliste,,Saken")
        assert result == ["Caliste", "Saken"]

    def test_riot_id_with_hash_preserved(self):
        assert _split_accounts("Caliste#EUW") == ["Caliste#EUW"]


# ─── parse_euw_accounts ───────────────────────────────────────────────────────


class TestParseEuwAccounts:
    def test_empty_string_returns_empty(self):
        assert parse_euw_accounts("") == []

    def test_none_returns_empty(self):
        assert parse_euw_accounts(None) == []

    # Format 1 : Riot IDs avec marqueurs région
    def test_format1_riot_ids_with_region_markers(self):
        text = "'''EUW:''' KC NEXT ADKING#EUW <br> I NEED SOLOQ#EUW <br> '''KR:''' KC Caliste#0001"
        result = parse_euw_accounts(text)
        assert "KC NEXT ADKING#EUW" in result
        assert "I NEED SOLOQ#EUW" in result
        assert "KC Caliste#0001" not in result  # KR, pas EUW

    # Format 2 : anciens summoner names avec marqueurs région
    def test_format2_old_summoner_names_with_markers(self):
        text = "'''EUW:''' AbbedaggÆ <br> Mein Königreich <br> '''KR:''' 아베다게"
        result = parse_euw_accounts(text)
        assert "AbbedaggÆ" in result
        assert "Mein Königreich" in result
        assert "아베다게" not in result  # KR

    # Format 3 : pas de marqueurs région (EUW implicite)
    def test_format3_no_region_markers_single(self):
        assert parse_euw_accounts("Acidy") == ["Acidy"]

    def test_format3_no_region_markers_with_suffix(self):
        assert parse_euw_accounts("Achuu (EUW)") == ["Achuu"]

    def test_format3_comma_separated(self):
        result = parse_euw_accounts("name1, name2")
        assert result == ["name1", "name2"]

    def test_other_region_only_returns_empty(self):
        # Marqueurs présents mais pas EUW → retourne vide
        text = "'''KR:''' KR Player <br> '''CN:''' CN Player"
        result = parse_euw_accounts(text)
        assert result == []

    def test_euw_only_no_other_region(self):
        text = "'''EUW:''' Caliste#EUW"
        result = parse_euw_accounts(text)
        assert "Caliste#EUW" in result

    def test_whitespace_only_returns_empty(self):
        assert parse_euw_accounts("   ") == []


# ─── filter_lfl_tournaments ───────────────────────────────────────────────────


class TestFilterLflTournaments:
    def test_returns_lfl_pages(self):
        tournaments = [
            {"OverviewPage": "LFL/2025 Season/Spring", "League": "La Ligue Française"},
            {"OverviewPage": "LCS/2025", "League": "LCS"},
        ]
        result = filter_lfl_tournaments(tournaments)
        assert "LFL/2025 Season/Spring" in result
        assert "LCS/2025" not in result

    def test_includes_d2(self):
        tournaments = [
            {"OverviewPage": "LFLG/2025", "League": "La Ligue Française Division 2"},
        ]
        result = filter_lfl_tournaments(tournaments)
        assert "LFLG/2025" in result

    def test_empty_input_returns_empty_set(self):
        assert filter_lfl_tournaments([]) == set()

    def test_missing_league_field_excluded(self):
        tournaments = [{"OverviewPage": "LFL/2025", "League": None}]
        assert filter_lfl_tournaments(tournaments) == set()


# ─── extract_players_from_rosters ────────────────────────────────────────────


class TestExtractPlayersFromRosters:
    def test_extracts_players_from_lfl_rosters(self):
        rosters = [
            {"OverviewPage": "LFL/2025", "RosterLinks": "Caliste;;Saken;;Rekkles"},
        ]
        lfl_pages = {"LFL/2025"}
        result = extract_players_from_rosters(rosters, lfl_pages)
        assert "Caliste" in result
        assert "Saken" in result
        assert "Rekkles" in result

    def test_ignores_non_lfl_rosters(self):
        rosters = [
            {"OverviewPage": "LCS/2025", "RosterLinks": "Faker"},
        ]
        lfl_pages = {"LFL/2025"}
        result = extract_players_from_rosters(rosters, lfl_pages)
        assert "Faker" not in result

    def test_deduplicates_players(self):
        rosters = [
            {"OverviewPage": "LFL/2025 Spring", "RosterLinks": "Caliste;;Saken"},
            {"OverviewPage": "LFL/2025 Summer", "RosterLinks": "Caliste;;NewPlayer"},
        ]
        lfl_pages = {"LFL/2025 Spring", "LFL/2025 Summer"}
        result = extract_players_from_rosters(rosters, lfl_pages)
        assert result.count("Caliste") == 1

    def test_returns_sorted_list(self):
        rosters = [{"OverviewPage": "LFL/2025", "RosterLinks": "Zeka;;Aatrox;;Mia"}]
        lfl_pages = {"LFL/2025"}
        result = extract_players_from_rosters(rosters, lfl_pages)
        assert result == sorted(result)

    def test_handles_empty_roster_links(self):
        rosters = [{"OverviewPage": "LFL/2025", "RosterLinks": None}]
        lfl_pages = {"LFL/2025"}
        result = extract_players_from_rosters(rosters, lfl_pages)
        assert result == []

    def test_filters_empty_strings_from_delimiter(self):
        rosters = [{"OverviewPage": "LFL/2025", "RosterLinks": "Caliste;;  ;;Saken"}]
        lfl_pages = {"LFL/2025"}
        result = extract_players_from_rosters(rosters, lfl_pages)
        assert "" not in result
        assert "  " not in result


# ─── build_soloqueue_lookup ───────────────────────────────────────────────────


class TestBuildSoloqueueLookup:
    def test_builds_mapping(self):
        players_bronze = [
            {"OverviewPage": "Caliste", "SoloqueueIds": "Caliste#EUW"},
        ]
        result = build_soloqueue_lookup(players_bronze)
        assert result["Caliste"] == ["Caliste#EUW"]

    def test_empty_soloqueue_returns_empty_list(self):
        players_bronze = [{"OverviewPage": "Unknown", "SoloqueueIds": ""}]
        result = build_soloqueue_lookup(players_bronze)
        assert result["Unknown"] == []

    def test_none_soloqueue_handled(self):
        players_bronze = [{"OverviewPage": "Unknown", "SoloqueueIds": None}]
        result = build_soloqueue_lookup(players_bronze)
        assert result["Unknown"] == []

    def test_missing_overview_page_skipped(self):
        players_bronze = [{"OverviewPage": "", "SoloqueueIds": "Name#EUW"}]
        result = build_soloqueue_lookup(players_bronze)
        assert "" not in result

    def test_multiple_players(self):
        players_bronze = [
            {"OverviewPage": "Caliste", "SoloqueueIds": "Caliste#EUW"},
            {"OverviewPage": "Saken", "SoloqueueIds": "Saken#EUW"},
        ]
        result = build_soloqueue_lookup(players_bronze)
        assert len(result) == 2


# ─── enrich_players ───────────────────────────────────────────────────────────


class TestEnrichPlayers:
    def test_combines_names_with_accounts(self):
        players = enrich_players(["Caliste"], {"Caliste": ["Caliste#EUW"]})
        assert players == [{"player": "Caliste", "euw_accounts": ["Caliste#EUW"]}]

    def test_keeps_players_without_accounts(self):
        players = enrich_players(["Unknown"], {})
        assert players == [{"player": "Unknown", "euw_accounts": []}]

    def test_preserves_order(self):
        names = ["Zeka", "Aatrox", "Mia"]
        result = enrich_players(names, {})
        assert [p["player"] for p in result] == names


# ─── save_to_gcs ─────────────────────────────────────────────────────────────


class TestSaveToGcs:
    def _make_gcs_mock(self):
        mock_blob = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_client = MagicMock()
        mock_client.bucket.return_value = mock_bucket
        return mock_client, mock_bucket, mock_blob

    def test_uploads_ndjson_to_correct_path(self):
        players = [{"player": "Caliste", "euw_accounts": []}]
        mock_client, mock_bucket, mock_blob = self._make_gcs_mock()

        with (
            patch("pipeline.silver_transforms.lfl_players.gcs_client") as mock_ctx,
            patch("pipeline.silver_transforms.lfl_players.send_discord_notification"),
        ):
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            save_to_gcs(players, "test-bucket", "2026-07-06")

        mock_bucket.blob.assert_called_once_with("silver/leaguepedia/lfl_players/2026-07-06.json")
        mock_blob.upload_from_string.assert_called_once()

    def test_does_not_upload_when_empty(self):
        with (
            patch("pipeline.silver_transforms.lfl_players.gcs_client") as mock_ctx,
            patch("pipeline.silver_transforms.lfl_players.send_discord_notification"),
        ):
            save_to_gcs([], "test-bucket", "2026-07-06")
        mock_ctx.assert_not_called()

    def test_sends_discord_on_success(self):
        players = [{"player": "Caliste", "euw_accounts": ["Caliste#EUW"]}]
        mock_client, _, _ = self._make_gcs_mock()

        with (
            patch("pipeline.silver_transforms.lfl_players.gcs_client") as mock_ctx,
            patch(
                "pipeline.silver_transforms.lfl_players.send_discord_notification"
            ) as mock_discord,
        ):
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            save_to_gcs(players, "test-bucket", "2026-07-06")

        mock_discord.assert_called_once()


# ─── run_transform (integration) ─────────────────────────────────────────────


class TestRunTransform:
    def test_full_pipeline(self):
        tournaments = [{"OverviewPage": "LFL/2025", "League": "La Ligue Française"}]
        rosters = [{"OverviewPage": "LFL/2025", "RosterLinks": "Caliste"}]
        players_bronze = [{"OverviewPage": "Caliste", "SoloqueueIds": "Caliste#EUW"}]

        load_calls = [tournaments, rosters, players_bronze]

        with (
            patch(
                "pipeline.silver_transforms.lfl_players.load_bronze_table",
                side_effect=load_calls,
            ),
            patch("pipeline.silver_transforms.lfl_players.save_to_gcs") as mock_save,
        ):
            run_transform("2026-07-06")

        saved = mock_save.call_args[0][0]
        assert len(saved) == 1
        assert saved[0]["player"] == "Caliste"
        assert saved[0]["euw_accounts"] == ["Caliste#EUW"]

    def test_aborts_when_no_lfl_tournaments(self):
        tournaments = [{"OverviewPage": "LCS/2025", "League": "LCS"}]
        rosters: list = []
        players_bronze: list = []

        with (
            patch(
                "pipeline.silver_transforms.lfl_players.load_bronze_table",
                side_effect=[tournaments, rosters, players_bronze],
            ),
            patch("pipeline.silver_transforms.lfl_players.save_to_gcs") as mock_save,
            patch("pipeline.silver_transforms.lfl_players.send_discord_notification"),
        ):
            run_transform("2026-07-06")

        mock_save.assert_not_called()
