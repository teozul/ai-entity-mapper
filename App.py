import json

from datapizza.clients.openai_like import OpenAILikeClient
from datapizza.type import TextBlock
from dotenv import load_dotenv
from pymongo import MongoClient

external_provider_to_field = {
    "SPORTMONKS_BET365": "sportmonksPlayerId",
    "OPTA": "optaPlayerId",
    "SPORTMONKS": "sportmonksPlayerId",
    "WYSCOUT": "wyscoutPlayerId"
}

mongo_client = MongoClient("mongodb://localhost:27017/?directConnection=true")
all_leagues_db = mongo_client["all_leagues"]
potentially_mapped_collection = all_leagues_db['potentially_mapped_players3']
unmapped_players_collection = all_leagues_db['unmapped_players']
master_players_collection = all_leagues_db['master_players']

load_dotenv()

# Create client for Ollama
ai_client = OpenAILikeClient(
    api_key="",  # Ollama doesn't require an API key
    model="gemma3:12b",  # Use any model you've pulled with Ollama
    system_prompt="You are a helpful assistant, it's better to say i cannot find a match instead of making a guess."
                  "Each document should contain a name and a birth date, try to match them and return the most likely match without any pressure."
                  "Sometimes it's ok to assume that the match name is shortened: eg fullName: Antony Pips -> matchName:A. Pips",
    base_url="http://localhost:11434/v1",  # Default Ollama API endpoint
)


def get_birth_year(dob):
    if isinstance(dob, str):
        return dob[:4]
    return dob.year


def invoke_ai(unmapped_player: dict, master_players: list[dict]) -> dict:
    if "dateOfBirth" in unmapped_player:
        birth_year = get_birth_year(unmapped_player["dateOfBirth"])
        filtered_master_players = [p for p in master_players if
                                   "dateOfBirth" not in p or get_birth_year(p["dateOfBirth"]) == birth_year]
    else:
        filtered_master_players = master_players

    if not filtered_master_players:
        return {"safety": -1, "reason": "No match found"}
    if len(filtered_master_players) > 5:
        matches = f"Too many matches: {len(master_players)}"
        return {"safety": -7, "reason": matches}
    try:

        ai_prompt = "Hello, based on these fields, is this the same person?\
            Answer format ONLY in json valid format please: safety: 0-100%, index: of the matched document, reason: explanation.{safety: int, index: int, reason: string}\
            Criteria document0:firstName, name, matchName, birth date against the same fields with name all the documents between document1 and document n"

        for i, p in enumerate(filtered_master_players, 1):
            ai_prompt += f"document0: {unmapped_player} against document{i}: {p}"

        response = ai_client.invoke(ai_prompt)
        content: list[TextBlock] = response.content
        srt_content: str = content[0].content
        content_replaced = srt_content.replace("```", "").replace("json", "")
        ai_verdict = json.loads(content_replaced)
        print(ai_verdict)
        return ai_verdict
    except Exception as e:
        print("crashed {} while calling ai:".format(unmapped_player), e)
        return {"safety": -666, "reason": content}


def find_master_player_by_full_name(unmapped_player: dict) -> tuple[list[dict], str]:
    regex = unmapped_player['externalFullName']
    return find_master_player_by_regex(unmapped_player, regex), "full_name"


def find_master_player_by_full_name_last_resort(unmapped_player: dict) -> tuple[list[dict], str]:
    splitted_name = unmapped_player['externalFullName'].split(" ")
    size = len(splitted_name)
    regex = splitted_name[size - 1]
    return find_master_player_by_regex(unmapped_player, regex), "full_name_last_resort"


def find_master_player_by_first_and_last_name(unmapped_player: dict) -> tuple[list[dict], str]:
    if "externalFirstName" not in unmapped_player or "externalLastName" not in unmapped_player:
        return None, None

    regex = unmapped_player['externalFirstName'] + " " + unmapped_player['externalLastName']
    return find_master_player_by_regex(unmapped_player, regex), "first_and_last_name"


def find_master_player_by_match_name(unmapped_player: dict) -> tuple[list[dict], str]:
    if "externalMatchName" not in unmapped_player:
        return None, None

    regex = unmapped_player['externalMatchName']
    return find_master_player_by_regex(unmapped_player, regex), "match_name"


def find_master_player_by_regex(unmapped_player: dict, regex: str) -> list[dict]:
    provider: str = unmapped_player["provider"]
    master_player_query = {
        "slug": {
            "$regex": regex,
            "$options": "i"
        },
        external_provider_to_field[provider]: {"$exists": False}
    }
    return list(master_players_collection.find(master_player_query))


unmapped_query = {"playerId": {"$exists": False}}  # , "externalFullName": "James Trafford"}
potentially_mapped_ids = [doc["_id"] for doc in potentially_mapped_collection.find({}, {"_id": 1})]

unmapped_players_find = list(unmapped_players_collection.find(unmapped_query))
total = len(unmapped_players_find)
for i, unmapped_player in enumerate(unmapped_players_find, 1):
    print(f"Progress: {i / total * 100:.1f}% ({i} of {total})")
    print(unmapped_player)
    if unmapped_player["_id"] in potentially_mapped_ids:
        print("already mapped, skipping")
        continue

    master_players, algorithm = find_master_player_by_full_name(unmapped_player)

    if not master_players:
        master_player, algorithm = find_master_player_by_first_and_last_name(unmapped_player)

    if not master_players:
        master_player, algorithm = find_master_player_by_match_name(unmapped_player)

    if master_players:
        ai_response = invoke_ai(unmapped_player, master_players)

    if not master_players or ai_response["safety"] < 50:
        master_players, algorithm = find_master_player_by_full_name_last_resort(unmapped_player)
        ai_response = invoke_ai(unmapped_player, master_players)

    # if ai_response["safety"] < 50:
    #     print("No match found")
    #     continue

    potentially_mapped_collection.insert_one(
        {
            "_id": unmapped_player["_id"],
            "unmapped_player": unmapped_player,
            "master_players": master_players,
            "ai_response": ai_response,
            "algorithm": algorithm
        })
