from datapizza.clients.openai_like import OpenAILikeClient
from datapizza.tools import tool
from dotenv import load_dotenv

from Player import Player
from SportDB import SportDB

db = SportDB(api_key="Nwu6nZzWKP88q3DUsX4KEd5n2EsFr3Cxb4dHatdk")

load_dotenv()

# Create client for Ollama
ai_client = OpenAILikeClient(
    api_key="",  # Ollama doesn't require an API key
    model="gpt-oss:20b",  # Use any model you've pulled with Ollama
    system_prompt="You are a helpful assistant, it's better to say i cannot find a match instead of making a guess."
                  "Each document should contain a name and a birth date, try to match them and return the most likely match without any pressure."
                  "Sometimes it's ok to assume that the match name is shortened: eg fullName: Antony Pips -> matchName:A. Pips",
    base_url="http://localhost:11434/v1",  # Default Ollama API endpoint
)


# players = db.search_players("messi")["results"]
# for p in players:
#    print(p.name, p.club.name if p.club else None)
@tool
def search_players(regex_name: str) -> list[Player]:
    print(f"invoked search_players with {regex_name}")
    if regex_name == "messi":
        player_name = "messi"
    else:
        player_name = "dybala"
    return [
        Player.from_dict({"id": "2", "name": "player_name", "club": {"id": "1", "name": "barcelona"}})]


response = ai_client.invoke("Can you find the details of dybala?", tools=[search_players])

print(response)
for func_call in response.function_calls:
    result = func_call.tool(**func_call.arguments)
    print(f"Tool result: {result}")

print(response.text)
