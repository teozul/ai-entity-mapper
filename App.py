from datapizza.clients.openai_like import OpenAILikeClient
from datapizza.tools import tool

from Player import Player

# Create client for Ollama
ai_client = OpenAILikeClient(
    api_key="",  # Ollama doesn't require an API key
    model="gpt-oss:20b",  # Use any model you've pulled with Ollama
    system_prompt="You are a helpful assistant, it's better to say i cannot find a match instead of making a guess."
                  "Each document should contain a name and a birth date, try to match them and return the most likely match without any pressure."
                  "Sometimes it's ok to assume that the match name is shortened: eg fullName: Antony Pips -> matchName:A. Pips",
    base_url="http://localhost:11434/v1",  # Default Ollama API endpoint
)


@tool
def players_database(regex_name: str) -> list[Player]:
    print(f"invoked search_players with {regex_name}")
    if regex_name.lower() == "messi":
        player_name = "messi"
    else:
        player_name = "dybala"
    return [
        Player.from_dict({"id": "2", "name": player_name, "club": {"id": "1", "name": "barcelona"}})]


@tool
def compare_players(p1: str, p2: str) -> bool:
    print(f"compare_players {p1} {p2}")
    return p1 == p2


if __name__ == '__main__':
    prompt = "can you compare the player messi and dybala? If they are different look for them in players_database"
    response = ai_client.invoke(
        prompt,
        tools=[compare_players, players_database])

    print(response)
    for func_call in response.function_calls:
        result = func_call.tool(**func_call.arguments)
        print(f"Tool result: {result}")

    print(response.text)

# Output:
# ClientResponse(content=[FunctionCallBlock(id=call_ipg7wlsr, arguments={'p1': 'Messi', 'p2': 'Dybala'}, name=compare_players, tool=<datapizza.tools.tools.Tool object at 0x109bb7d90>)], delta=None, stop_reason=tool_calls)
# compare_players Messi Dybala
# Tool result: False
