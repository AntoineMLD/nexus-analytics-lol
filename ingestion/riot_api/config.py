RIOT_API_BASE = "https://europe.api.riotgames.com"

# Queue ID for Ranked Solo/Duo in League of Legends
RANKED_SOLO_QUEUE = 420

# Maximum match IDs returned per player (Riot API cap is 100)
MATCH_IDS_PER_PLAYER = 100

# Delay between consecutive API calls in seconds.
# Personal key limits: 20 req/s and 100 req/2min.
# 1.5s gives ~40 req/min — safely within both limits.
SLEEP_BETWEEN_CALLS = 1.5
