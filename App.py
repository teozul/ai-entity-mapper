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
potentially_mapped_collection = all_leagues_db['potentially_mapped_players2']
unmapped_players_collection = all_leagues_db['unmapped_players']
master_players_collection = all_leagues_db['master_players']

load_dotenv()

# Create client for Ollama
ai_client = OpenAILikeClient(
    api_key="",  # Ollama doesn't require an API key
    model="gemma3:12b",  # Use any model you've pulled with Ollama
    system_prompt="You are a helpful assistant.",
    base_url="http://localhost:11434/v1",  # Default Ollama API endpoint
)


def invoke_ai(unmapped_player: dict, master_player: dict) -> dict:
    ai_prompt = f"Hello, based on these fields, is this the same person?\
        Anwer format ONLY in json valid format please: safety: 0-100%, reason: explanation.{{safety: int, reason: string}}\
        Criteria document1:firstName, name, matchName, birth date against the same fields with name external in document2\
        document1: {unmapped_player}\
        document2: {master_player}"

    response = ai_client.invoke(ai_prompt)
    content: list[TextBlock] = response.content
    srt_content: str = content[0].content
    content_replaced = srt_content.replace("```", "").replace("json", "")
    ai_response = json.loads(content_replaced)
    print(ai_response)
    return ai_response


def find_master_player_by_full_name(unmapped_player: dict) -> dict:
    regex = unmapped_player['externalFullName']
    return find_master_player_by_regex(unmapped_player, regex)


def find_master_player_by_first_and_last_name(unmapped_player: dict) -> dict:
    if "externalFirstName" not in unmapped_player or "externalLastName" not in unmapped_player:
        return None

    regex = unmapped_player['externalFirstName'] + " " + unmapped_player['externalLastName']
    return find_master_player_by_regex(unmapped_player, regex)


def find_master_player_by_match_name(unmapped_player: dict) -> dict:
    if "externalMatchName" not in unmapped_player:
        return None

    regex = unmapped_player['externalMatchName']
    return find_master_player_by_regex(unmapped_player, regex)


def find_master_player_by_regex(unmapped_player: dict, regex: str) -> dict:
    provider: str = unmapped_player["provider"]
    master_player_query = {
        "slug": {
            "$regex": regex,
            "$options": "i"
        },
        external_provider_to_field[provider]: {"$exists": False}
    }
    return master_players_collection.find_one(master_player_query)


unmapped_query = {"playerId": {"$exists": False}}  # , "externalFullName": "Nico O'Reilly"}
potentially_mapped_ids = [doc["_id"] for doc in potentially_mapped_collection.find({}, {"_id": 1})]

unmapped_players_find = list(unmapped_players_collection.find(unmapped_query))
total = len(unmapped_players_find)
for i, unmapped_player in enumerate(unmapped_players_find, 1):
    print(f"Progress: {i / total * 100:.1f}% ({i} of {total})")
    print(unmapped_player)
    if unmapped_player["_id"] in potentially_mapped_ids:
        print("already mapped, skipping")
        continue

    master_player = find_master_player_by_full_name(unmapped_player)
    choice = "full_name"
    if master_player is None:
        master_player = find_master_player_by_match_name(unmapped_player)
        choice = "match_name"

    if master_player is None:
        master_player = find_master_player_by_first_and_last_name(unmapped_player)
        choice = "first_and_last_name"

    if master_player is None:
        print("no match found")
        continue

    ai_response = invoke_ai(unmapped_player, master_player)
    potentially_mapped_collection.insert_one(
        {
            "_id": unmapped_player["_id"],
            "unmapped_player": unmapped_player,
            "master_player": master_player,
            "ai_response": ai_response,
            "choice": choice
        })
