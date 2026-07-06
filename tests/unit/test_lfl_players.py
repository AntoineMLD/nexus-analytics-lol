"""Unit tests for pipeline/silver_transforms/lfl_players.py.

Covers:
- strip_wiki_markup : suppression des balises MediaWiki
- parse_euw_accounts : 3 formats de champs SoloqueueIds + cas limites
- filter_lfl_tournaments : filtrage par League
- extract_players_from_rosters : déduplication + filtrage OverviewPage
- build_soloqueue_lookup : construction du dictionnaire de comptes EUW
- enrich_players : association joueur ↔ comptes
- run_transform : scénario nominal + absence de tournois LFL (via mocks GCS)
"""

import json
from unittest.mock import MagicMock, patch

from pipeline.silver_transforms.lfl_players import (
    build_soloqueue_lookup,
    enrich_players,
    extract_players_from_rosters,
    filter_lfl_tournaments,
    parse_euw_accounts,
    run_transform,
    strip_wiki_markup,
)

PATCH_GCS = "pipeline.silver_transforms.lfl_players.gcs_client"
PATCH_SETTINGS = "pipeline.silver_transforms.lfl_players.settings"
PATCH_DISCORD = "pipeline.silver_transforms.lfl_players.send_discord_notification"


# ---------------------------------------------------------------------------
# strip_wiki_markup
# ---------------------------------------------------------------------------


class TestStripWikiMarkup:
    def test_removes_triple_apostrophes(self):
        assert strip_wiki_markup("'''EUW:'''") == "EUW:"

    def test_removes_double_apostrophes(self):
        assert strip_wiki_markup("''italic''") == "italic"

    def test_converts_br_to_newline(self):
        result = strip_wiki_markup("account1<br>account2")
        assert result == "account1\naccount2"

    def test_br_with_slash_variant(self):
        result = strip_wiki_markup("a<br/>b")
        assert result == "a\nb"

    def test_br_case_insensitive(self):
        result = strip_wiki_markup("a<BR>b")
        assert result == "a\nb"

    def test_empty_string_returns_empty(self):
        assert strip_wiki_markup("") == ""


# ---------------------------------------------------------------------------
# parse_euw_accounts
# ---------------------------------------------------------------------------


class TestParseEuwAccounts:
    def test_empty_string_returns_empty_list(self):
        assert parse_euw_accounts("") == []

    def test_none_equivalent_empty_string(self):
        assert parse_euw_accounts("") == []

    def test_format1_riot_id_with_euw_section(self):
        """Format 1 : marqueurs de région EUW: … KR: …"""
        text = "'''EUW:''' KC NEXT ADKING#EUW <br> I NEED SOLOQ#EUW <br> '''KR:''' KC Caliste#0001"
        result = parse_euw_accounts(text)
        assert result == ["KC NEXT ADKING#EUW", "I NEED SOLOQ#EUW"]

    def test_format2_old_summoner_names_with_region_markers(self):
        """Format 2 : anciens noms (sans #TAG) avec marqueurs de région."""
        text = "'''EUW:''' AbbedaggÆ <br> Mein Königreich <br> '''KR:''' 아베다게"
        result = parse_euw_accounts(text)
        assert result == ["AbbedaggÆ", "Mein Königreich"]

    def test_format3_no_region_markers_single_name(self):
        """Format 3 : pas de marqueur de région, nom unique."""
        result = parse_euw_accounts("Acidy")
        assert result == ["Acidy"]

    def test_format3_server_suffix_stripped(self):
        """Les suffixes '(EUW)' en fin de nom doivent être supprimés."""
        result = parse_euw_accounts("Achuu (EUW)")
        assert result == ["Achuu"]

    def test_format3_comma_separated_names(self):
        """Plusieurs noms séparés par des virgules."""
        result = parse_euw_accounts("name1, name2")
        assert result == ["name1", "name2"]

    def test_no_euw_section_with_other_region_returns_empty(self):
        """Si la section EUW est absente mais d'autres régions sont présentes."""
        text = "'''KR:''' someKRname"
        result = parse_euw_accounts(text)
        assert result == []

    def test_euw_only_section_no_other_region(self):
        """Section EUW seule, sans autre marqueur de région."""
        text = "'''EUW:''' Player1#EUW"
        result = parse_euw_accounts(text)
        assert result == ["Player1#EUW"]


# ---------------------------------------------------------------------------
# filter_lfl_tournaments
# ---------------------------------------------------------------------------


class TestFilterLflTournaments:
    def test_returns_lfl_overview_pages(self):
        tournaments = [
            {"OverviewPage": "LFL/2026 Spring", "League": "La Ligue Française"},
            {"OverviewPage": "LFL2/2026 Spring", "League": "La Ligue Française Division 2"},
            {"OverviewPage": "LCS/2026", "League": "LCS"},
        ]
        result = filter_lfl_tournaments(tournaments)
        assert result == {"LFL/2026 Spring", "LFL2/2026 Spring"}

    def test_empty_list_returns_empty_set(self):
        assert filter_lfl_tournaments([]) == set()

    def test_no_lfl_tournament_returns_empty_set(self):
        tournaments = [{"OverviewPage": "LCS/2026", "League": "LCS"}]
        assert filter_lfl_tournaments(tournaments) == set()


# ---------------------------------------------------------------------------
# extract_players_from_rosters
# ---------------------------------------------------------------------------


class TestExtractPlayersFromRosters:
    LFL_PAGES = {"LFL/2026 Spring"}

    def test_extracts_players_from_matching_page(self):
        rosters = [
            {
                "OverviewPage": "LFL/2026 Spring",
                "RosterLinks": "Caliste;;Rekkles;;Cinkrof",
            }
        ]
        result = extract_players_from_rosters(rosters, self.LFL_PAGES)
        assert sorted(result) == ["Caliste", "Cinkrof", "Rekkles"]

    def test_ignores_non_lfl_pages(self):
        rosters = [
            {"OverviewPage": "LCS/2026", "RosterLinks": "SomePlayer"},
            {"OverviewPage": "LFL/2026 Spring", "RosterLinks": "Caliste"},
        ]
        result = extract_players_from_rosters(rosters, self.LFL_PAGES)
        assert result == ["Caliste"]

    def test_deduplicates_players_across_rosters(self):
        rosters = [
            {"OverviewPage": "LFL/2026 Spring", "RosterLinks": "Caliste;;Rekkles"},
            {"OverviewPage": "LFL/2026 Spring", "RosterLinks": "Caliste;;Cinkrof"},
        ]
        result = extract_players_from_rosters(rosters, self.LFL_PAGES)
        assert sorted(result) == ["Caliste", "Cinkrof", "Rekkles"]

    def test_handles_empty_roster_links(self):
        rosters = [{"OverviewPage": "LFL/2026 Spring", "RosterLinks": ""}]
        result = extract_players_from_rosters(rosters, self.LFL_PAGES)
        assert result == []


# ---------------------------------------------------------------------------
# build_soloqueue_lookup
# ---------------------------------------------------------------------------


class TestBuildSoloqueueLookup:
    def test_builds_mapping_from_overview_page(self):
        players_bronze = [
            {
                "OverviewPage": "Caliste",
                "SoloqueueIds": "'''EUW:''' KC NEXT ADKING#EUW <br> I NEED SOLOQ#EUW",
            }
        ]
        result = build_soloqueue_lookup(players_bronze)
        assert result == {"Caliste": ["KC NEXT ADKING#EUW", "I NEED SOLOQ#EUW"]}

    def test_skips_rows_without_overview_page(self):
        players_bronze = [{"OverviewPage": "", "SoloqueueIds": "SomeAccount"}]
        result = build_soloqueue_lookup(players_bronze)
        assert result == {}

    def test_player_with_no_euw_accounts(self):
        players_bronze = [{"OverviewPage": "KRplayer", "SoloqueueIds": "'''KR:''' KRname"}]
        result = build_soloqueue_lookup(players_bronze)
        assert result == {"KRplayer": []}


# ---------------------------------------------------------------------------
# enrich_players
# ---------------------------------------------------------------------------


class TestEnrichPlayers:
    def test_associates_accounts_to_players(self):
        lookup = {"Caliste": ["KC NEXT ADKING#EUW"]}
        result = enrich_players(["Caliste"], lookup)
        assert result == [{"player": "Caliste", "euw_accounts": ["KC NEXT ADKING#EUW"]}]

    def test_player_not_in_lookup_gets_empty_list(self):
        result = enrich_players(["UnknownPlayer"], {})
        assert result == [{"player": "UnknownPlayer", "euw_accounts": []}]

    def test_preserves_order(self):
        players = ["Alpha", "Beta", "Gamma"]
        result = enrich_players(players, {})
        assert [p["player"] for p in result] == ["Alpha", "Beta", "Gamma"]


# ---------------------------------------------------------------------------
# run_transform (integration via mocks GCS)
# ---------------------------------------------------------------------------


def _make_blob_mock(content: str) -> MagicMock:
    blob = MagicMock()
    blob.download_as_text.return_value = content
    return blob


def _make_gcs_ctx(blobs_content: list[str]) -> MagicMock:
    """Build a GCS context manager that returns blobs sequentially."""
    blobs = [_make_blob_mock(c) for c in blobs_content]
    bucket_mock = MagicMock()
    bucket_mock.blob.side_effect = blobs
    client_mock = MagicMock()
    client_mock.bucket.return_value = bucket_mock
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=client_mock)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


TOURNAMENT_ROW = json.dumps({"OverviewPage": "LFL/2026 Spring", "League": "La Ligue Française"})
ROSTER_ROW = json.dumps({"OverviewPage": "LFL/2026 Spring", "RosterLinks": "Caliste"})
PLAYER_ROW = json.dumps({"OverviewPage": "Caliste", "SoloqueueIds": "CalPlayer#EUW"})


def _make_ctx_with_downloads(download_contents: list[str]) -> tuple[MagicMock, list[MagicMock]]:
    """Build a GCS context manager that returns a new blob on each blob() call.

    Returns the context mock and the list of all blobs created, so tests can
    inspect any individual blob (e.g., the last one used for upload).

    run_transform opens gcs_client() four times (three load_bronze_table +
    one save_to_gcs), each time getting the same client mock.
    """
    all_blobs: list[MagicMock] = []
    download_iter = iter(download_contents)

    def make_blob(_path: str) -> MagicMock:
        b = MagicMock()
        try:
            b.download_as_text.return_value = next(download_iter)
        except StopIteration:
            pass
        all_blobs.append(b)
        return b

    client = MagicMock()
    client.bucket.return_value.blob.side_effect = make_blob

    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=client)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx, all_blobs


class TestRunTransform:
    def test_nominal_case_uploads_enriched_players(self):
        ctx, all_blobs = _make_ctx_with_downloads([TOURNAMENT_ROW, ROSTER_ROW, PLAYER_ROW])

        with (
            patch(PATCH_GCS, return_value=ctx),
            patch(PATCH_SETTINGS) as mock_settings,
            patch(PATCH_DISCORD),
        ):
            mock_settings.gcs_bucket_name = "test-bucket"
            run_transform(date="2026-06-04")

        # The 4th blob created (index 3) is the upload destination blob
        upload_blob = all_blobs[3]
        upload_blob.upload_from_string.assert_called_once()
        uploaded_content = upload_blob.upload_from_string.call_args[0][0]
        rows = [json.loads(line) for line in uploaded_content.splitlines()]
        assert len(rows) == 1
        assert rows[0]["player"] == "Caliste"
        assert rows[0]["euw_accounts"] == ["CalPlayer#EUW"]

    def test_no_lfl_tournaments_sends_discord_error(self):
        non_lfl_row = json.dumps({"OverviewPage": "LCS/2026", "League": "LCS"})
        ctx, _ = _make_ctx_with_downloads([non_lfl_row])

        with (
            patch(PATCH_GCS, return_value=ctx),
            patch(PATCH_SETTINGS) as mock_settings,
            patch(PATCH_DISCORD) as mock_discord,
        ):
            mock_settings.gcs_bucket_name = "test-bucket"
            run_transform(date="2026-06-04")

        mock_discord.assert_called_once()
        assert ":x:" in mock_discord.call_args[0][0]
