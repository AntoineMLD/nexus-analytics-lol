"""Configuration for the Leaguepedia Cargo API ingestion.

TABLE_CONFIGS maps each Cargo table name to the fields to fetch and the
page size to use. Adjust `limit` per table based on expected volume.
"""

API_LEAGUEPEDIA_URL = "https://lol.fandom.com/api.php"
MAX_PAGE_SIZE = 8000

TABLE_CONFIGS: dict[str, dict] = {
    "ScoreboardGames": {
        "fields": (
            "UniqueGame,Tournament,Team1,Team2,WinTeam,LossTeam,DateTime_UTC,"
            "Team1Score,Team2Score,Team1Kills,Team2Kills,Team1Gold,Team2Gold,"
            "Team1Barons,Team2Barons,Team1Towers,Team2Towers,Team1Dragons,"
            "Team2Dragons,Patch,GameId,OverviewPage"
        ),
        "limit": 500,
    },
    "ScoreboardPlayers": {
        "fields": (
            "UniqueGame,Tournament,Team,Player,Champion,Kills,Deaths,Assists,"
            "Gold,CS,Role,DateTime_UTC,GameId,IngameDuration"
        ),
        "limit": 500,
    },
    "PicksAndBansS7": {
        "fields": (
            "UniqueGame,Tournament,Phase,Team,Champion,PickOrBan,"
            "DateTime_UTC,OverviewPage,N_PickInPhase"
        ),
        "limit": 500,
    },
    "Tournaments": {
        "fields": "Name,OverviewPage,DateStart,Date,League,Region,Country,Prizepool",
        "limit": 500,
    },
    "Teams": {
        "fields": "Name,OverviewPage,Short,Location,Region,League,Image",
        "limit": 500,
    },
    "TournamentResults": {
        "fields": "Event,Team,Place,PrizeUSD,LastResult,LastTeam",
        "limit": 500,
    },
    "TournamentRosters": {
        "fields": "Tournament,OverviewPage,Team,Player,Role,IsStarter,Residency",
        "limit": 500,
    },
    "Teamnames": {
        "fields": "CurrentName,AllNames,OtherNames,Short,OverviewPage",
        "limit": 500,
    },
    "Players": {
        "fields": "ID,Player,Name,NativeName,Country,Nationality,Team,Roles,IsRetired,Region",
        "limit": 500,
    },
}
