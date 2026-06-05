"""Configuration for the Leaguepedia Cargo API ingestion.

TABLE_CONFIGS maps each Cargo table name to the fields to fetch and the
page size to use. Field names are taken directly from Special:CargoTables.

Note: List-type fields must use the __full suffix to retrieve all values.
"""

API_LEAGUEPEDIA_URL = "https://lol.fandom.com/api.php"
MAX_PAGE_SIZE = 8000

TABLE_CONFIGS: dict[str, dict] = {
    "ScoreboardGames": {
        "tables": "ScoreboardGames=SG,Tournaments=T",
        "join_on": "SG.OverviewPage=T.OverviewPage",
        "fields": (
            "SG.OverviewPage,SG.Tournament,SG.Team1,SG.Team2,SG.WinTeam,SG.LossTeam,"
            "SG.DateTime_UTC,SG.Team1Score,SG.Team2Score,SG.Winner,"
            "SG.Gamelength,SG.Gamelength_Number,"
            "SG.Team1Dragons,SG.Team2Dragons,SG.Team1Barons,SG.Team2Barons,"
            "SG.Team1Towers,SG.Team2Towers,SG.Team1Gold,SG.Team2Gold,"
            "SG.Team1Kills,SG.Team2Kills,SG.Team1RiftHeralds,SG.Team2RiftHeralds,"
            "SG.Team1VoidGrubs,SG.Team2VoidGrubs,SG.Team1Inhibitors,SG.Team2Inhibitors,"
            "SG.Patch,SG.GameId,SG.MatchId,SG.N_GameInMatch"
        ),
        "where": "T.League='La Ligue Française' OR T.League='La Ligue Française Division 2'",
        "limit": 500,
    },
    "ScoreboardPlayers": {
        "tables": "ScoreboardPlayers=SP,Tournaments=T",
        "join_on": "SP.OverviewPage=T.OverviewPage",
        "fields": (
            "SP.OverviewPage,SP.Tournament,SP.Team,SP.TeamVs,SP.Link,SP.Name,SP.Champion,"
            "SP.Kills,SP.Deaths,SP.Assists,SP.Gold,SP.CS,SP.DamageToChampions,SP.VisionScore,"
            "SP.Role,SP.Side,SP.PlayerWin,SP.DateTime_UTC,SP.GameId,SP.MatchId"
        ),
        "where": "T.League='La Ligue Française' OR T.League='La Ligue Française Division 2'",
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
            "Name,OverviewPage,Short,Location,TeamLocation,Region," "Image,IsDisbanded,RenamedTo"
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
        "fields": ("Tournament,OverviewPage,Team,Short,Region," "RosterLinks,Roles,IsComplete"),
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
            "TeamLast,IsRetired,IsSubstitute"
        ),
        "limit": 500,
    },
}
