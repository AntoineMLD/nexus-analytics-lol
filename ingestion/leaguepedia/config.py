"""Configuration for the Leaguepedia Cargo API ingestion.

TABLE_CONFIGS maps each Cargo table name to the fields to fetch and the
page size to use. Field names are taken directly from Special:CargoTables.

Note: List-type fields must use the __full suffix to retrieve all values.
"""

API_LEAGUEPEDIA_URL = "https://lol.fandom.com/api.php"
MAX_PAGE_SIZE = 8000

TABLE_CONFIGS: dict[str, dict] = {
    "ScoreboardGames": {
        "fields": (
            "OverviewPage,Tournament,Team1,Team2,WinTeam,LossTeam,"
            "DateTime_UTC,Team1Score,Team2Score,Winner,"
            "Gamelength,Gamelength_Number,"
            "Team1Dragons,Team2Dragons,Team1Barons,Team2Barons,"
            "Team1Towers,Team2Towers,Team1Gold,Team2Gold,"
            "Team1Kills,Team2Kills,Team1RiftHeralds,Team2RiftHeralds,"
            "Team1VoidGrubs,Team2VoidGrubs,Team1Inhibitors,Team2Inhibitors,"
            "Patch,GameId,MatchId,N_GameInMatch"
        ),
        # lfl_filter=True: uses OverviewPage IN (...) WHERE clause instead of a Cargo join.
        # The mwcleric join_on parameter is silently ignored by the MediaWiki API
        # (expects 'join on' with space, receives 'join_on' with underscore).
        "lfl_filter": True,
        # order_by ensures stable pagination with Cargo's auto_continue mechanism.
        "order_by": "DateTime_UTC",
        "limit": 500,
    },
    "ScoreboardPlayers": {
        "fields": (
            "OverviewPage,Tournament,Team,TeamVs,Link,Name,Champion,"
            "Kills,Deaths,Assists,Gold,CS,DamageToChampions,VisionScore,"
            "Role,Side,PlayerWin,DateTime_UTC,GameId,MatchId"
        ),
        # A LIKE pattern on OverviewPage avoids both problems:
        # - the IN(71) filter that triggers aggressive rate limiting, and
        # - the DateTime_UTC filter that misses LFL rows (regional leagues don't have
        #   DateTime_UTC populated, so a date WHERE excludes them entirely).
        # All LFL tournament OverviewPages start with 'LFL/', making this a reliable,
        # single-condition filter that is cheap for the Cargo query planner.
        "where": "OverviewPage LIKE 'LFL/%'",
        "order_by": "GameId",
        "limit": 500,
    },
    "PicksAndBansS7": {
        "fields": (
            "OverviewPage,Team1,Team2,Winner,Team1Score,Team2Score,"
            "Team1Ban1,Team1Ban2,Team1Ban3,Team1Ban4,Team1Ban5,"
            "Team1Pick1,Team1Pick2,Team1Pick3,Team1Pick4,Team1Pick5,"
            "Team2Ban1,Team2Ban2,Team2Ban3,Team2Ban4,Team2Ban5,"
            "Team2Pick1,Team2Pick2,Team2Pick3,Team2Pick4,Team2Pick5,"
            "GameId,MatchId,N_GameInMatch,N_GameInPage"
        ),
        "limit": 500,
    },
    "Tournaments": {
        "fields": "Name,OverviewPage,DateStart,Date,League,Region,Country,Prizepool",
        "limit": 500,
    },
    "Teams": {
        "fields": (
            "Name,OverviewPage,Short,Location,TeamLocation,Region,Image,IsDisbanded,RenamedTo"
        ),
        "limit": 500,
    },
    "TournamentResults": {
        "fields": (
            "Event,OverviewPage,Team,Date,Tier,Place,Place_Number,"
            "Qualified,Prize_USD,PrizeUnit,Phase,LastResult,LastTeam,LastOutcome"
        ),
        "limit": 500,
    },
    "TournamentRosters": {
        "fields": ("Tournament,OverviewPage,Team,Short,Region,RosterLinks,Roles,IsComplete"),
        "limit": 500,
    },
    "Teamnames": {
        "fields": "Link,Longname,Short,Medium,Inputs__full,TeamnameId",
        "limit": 500,
    },
    "Players": {
        "fields": (
            "ID,OverviewPage,Player,Name,NativeName,Country,"
            "Nationality__full,NationalityPrimary,Age,Birthdate,"
            "Team,Team2,CurrentTeams__full,Residency,Role,"
            "TeamLast,IsRetired,IsSubstitute,SoloqueueIds"
        ),
        "limit": 500,
    },
}
