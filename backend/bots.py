import asyncio
import websockets
import jsonpickle
from avalon.agent import Agent
from avalon.utils import get_team_string
import sys
import traceback

async def avalon_bot(loop: asyncio.AbstractEventLoop):
    uri = "ws://localhost:8888/ws"
    try:
        async with websockets.connect(
            uri,
            ping_interval=30,  # Send a Ping every 30 seconds
            ping_timeout=20    # Wait up to 20 seconds for a Pong
        ) as websocket:
            print("WebSocket connection established.")
            agent = None
            while True:
                message = await websocket.recv()
                print(f"Received message: {message}")
                message = jsonpickle.decode(message)

                if "action" not in message:
                    continue
                if message["action"] == "StartRound":
                    public_state = jsonpickle.decode(message["game_state"])
                    agent.strategy.on_new_round(public_state)
                elif  message["action"] == "RevealRoles":
                    index = message["index"]
                    public_state = message["game_state"]
                    roles = message["roles"]
                    agent = Agent(index, public_state)
                    agent.reveal_roles(roles)
                elif message["action"] == "SelectTeam":
                    team_size = message["team_size"]
                    print("-------------------------------")
                    print(f"Player {agent.my_index}: I am team leader and have to select a team")
                    proposed_team: list[bool] = agent.strategy.propose_team(team_size).as_list
                    team = [index for index in range(len(proposed_team)) if proposed_team[index]]
                    print("Team", proposed_team, team)
                    print("Player " + str(agent.my_index) + f" ({agent.roles}) " + "Proposes the following team: " + get_team_string(proposed_team, public_state.player_names, roles))
                    print(f"Player {agent.my_index} proposes the following team [{",".join([str(p) for p in team])}]")
                    print("-------------------------------")
                    await websocket.send(jsonpickle.encode({
                        "message": f"Player {agent.my_index} proposes the following team [{",".join([str(p) for p in team])}]",
                        "event": "TeamSelected",
                        "team": team,
                        "index": agent.my_index
                    }))

                elif message["action"] == "VoteTeam":
                    team = message["team"]
                    public_state = jsonpickle.decode(message["game_state"])
                    agent.strategy.inform_proposed_team(public_state)
                    my_vote = agent.strategy.vote_team()
                    print("Player " + str(agent.my_index) + f" ({agent.roles}) " + "decides to vote " + str(my_vote) + " on team")
                    await websocket.send(jsonpickle.encode({
                        "message": f"Player {agent.my_index} voted '{my_vote}' on team",
                        "event": "TeamVoted",
                        "index": agent.my_index,
                        "vote": my_vote
                    }))
                elif message["action"] == "VoteQuest":
                    team = message["team"]
                    # proposed_team = [False] * agent.game_state.num_players
                    # for player in team:
                    #     proposed_team[player] = True
                    my_vote = agent.strategy.vote_quest(public_state.proposed_team)
                    print("Player " + str(agent.my_index) + f" ({agent.roles}) " + "decides to vote " + str(my_vote) + " on quest")
                    await websocket.send(jsonpickle.encode({
                        "message": f"Player {agent.my_index} voted on quest",
                        "event": "QuestVoted",
                        "index": agent.my_index,
                        "vote": my_vote
                    }))
                elif message["action"] == "ExposeMerlin":
                    guessed_merlin_index = agent.strategy.guess_merlin()
                    await websocket.send(jsonpickle.encode({
                        "message": f"Evil players: We think that Player {guessed_merlin_index} is Merlin.",
                        "event": "MerlinExposed",
                        "index": agent.my_index,
                        "merlin_index": guessed_merlin_index
                    }))

    except websockets.exceptions.ConnectionClosedOK:
        print("WebSocket connection closed gracefully.")
        loop.stop()
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"WebSocket connection closed with error: {e}")
        loop.stop()
    except Exception as e:
        traceback.print_exception(e)
        print(f"An unexpected error occurred: {e}")
        loop.stop()

if __name__ == "__main__":
    if (len(sys.argv) != 2):
        raise("You forgot to specify the number of bots")
    nbots = int(sys.argv[1])
    # nbots = 5
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    for i in range(nbots):
        asyncio.ensure_future(avalon_bot(loop))
    loop.run_forever()