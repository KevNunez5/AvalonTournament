import tornado.ioloop
import tornado.web
import tornado.websocket
import jsonpickle

import subprocess

from avalon_old.roles import unassigned, good, evil, merlin
from avalon.game_state import PublicGameState
from avalon_old.game_simulator import get_roles, assign_roles

from tornado.ioloop import IOLoop
from tornado.queues import Queue

class GameController:
    def __init__(self, nplayers, nbots):
        self.q = Queue(maxsize=2)
        self.players = list()
        self.nplayers = nplayers
        self.nbots = nbots
        subprocess.Popen(["python3", "bots.py", str(nbots)])

    
    def add_player(self, channel):
        player_id = len(self.players)
        self.players.append(channel)
        print("Number of players so far:", f"{len(self.players)}")
        channel.write_message({"message": f"Welcome player {player_id - 1}", "index": -1})
        if len(self.players) == self.nplayers + 1:
            self.q.put({"event": "AllPlayers"})

    def broadcast(self, msg, agent_index = -1):
        for player in self.players:
            player.write_message({"message": msg, "index": agent_index})
    
    def configure_player(self, index: int, public_state: PublicGameState, roles: list[str]):
        self.players[index + 1].write_message(jsonpickle.encode({
            "action": "RevealRoles",
            "msg": "Message?",
            "index": index,
            "game_state": public_state,
            "roles": roles
        }))

    def start_team_selection(self):
        if self.attempt == 5:
            self.broadcast("... 5 attempts ...")
            return
        self.st_state = "TEAM_SELECTION"
        self.players[0].write_message({"message": f"Asked Player {self.team_leader} to select a team"})
        self.players[self.team_leader + 1].write_message({"action": "SelectTeam", "team_size": self.team_size, "message": f"Please select a team with {self.team_size} members", "index": -1})

    def start_team_voting(self):
        self.st_state = "TEAM_VOTING"
        self.players[0].write_message({"message": f"Asked Players to vote for a team", "index": -1})
        for player in self.players:
            player.write_message({"action": "VoteTeam", "team": self.team, "message": "Please cast your vote"})

    def start_quest(self):
        self.st_state = "ON_QUEST"
        self.quest_result = True
        self.number_of_votes = 0
        self.players[0].write_message({"message": f"Team asked to vote on quest"})
        for player_index in self.team:
            self.players[player_index+1].write_message({"action": "VoteQuest", "team": self.team, "message": "Please cast your vote on quest"})

    def start_expose_merlin(self):
        self.st_state = "GUESSING_ON_MERLIN"
        for player_index, role in enumerate(self.roles):
            if role == evil:
                self.players[player_index+1].write_message({"action": "ExposeMerlin", "message": "Please guess who Merlin is"})
                break

    async def game_loop(self):
        print("From GameSimulator")
        self.st_state = "INITIAL"
        async for event in self.q:
            print(event)
            if self.st_state == "INITIAL" and event["event"] == "AllPlayers":
                self.broadcast("Welcome to Avalon!")
                # 1. Create the object storing the public state of the game.
                public_state = PublicGameState(5) # num_players)
                self.public_state = public_state

                #2. Assign roles
                self.roles = get_roles(public_state)
                print(self.roles)

                for i, role_assignment in assign_roles(self.roles):
                    print(i, role_assignment)
                    self.configure_player(i, public_state, role_assignment)

                self.round = 1
                self.broadcast("Starting round " + str(self.round))

                # Determine the team size for the current round.
                #TODO: this assumes there are 5 players.
                if self.round == 1 or self.round == 3:
                    self.team_size = 2
                else:
                    self.team_size = 3

                self.team_leader = 0
                self.attempt = 1
                self.start_team_selection()
            elif self.st_state == "TEAM_SELECTION" and event["event"] == "TeamSelected":
                self.team = event["team"]
                print("... Broadcasting selected team")
                self.broadcast(event["message"])
                self.votes = [None] * (len(self.players) - 1)
                self.start_team_voting()
            elif self.st_state == "TEAM_VOTING" and event["event"] == "TeamVoted":
                self.broadcast(event["message"], event["index"])
                index = event["index"]
                self.votes[index] = event["vote"]
                number_of_votes = sum([0 if v is None else 1 for v in self.votes])
                number_of_votes_yes = sum([1 if v else 0 for v in self.votes])
                if number_of_votes == len(self.players) - 1:
                    if number_of_votes_yes > number_of_votes / 2:
                        print("--- Team accepted")
                        self.broadcast("Team accepted!")
                        self.start_quest()
                    else:
                        self.attempt += 1
                        self.team_leader = (self.team_leader + 1) % (len(self.players) - 1)
                        self.start_team_selection()
            elif self.st_state == "ON_QUEST" and event["event"] == "QuestVoted":
                self.broadcast(event["message"])
                self.number_of_votes += 1
                self.quest_result = self.quest_result and event["vote"]
                if self.number_of_votes == len(self.team):
                    self.broadcast(f"Quest result {self.quest_result}")
                    if self.quest_result:
                        self.public_state.num_quests_succeeded += 1
                    else:
                        self.public_state.num_quests_failed += 1

                    print("Number of successful quests: " + str(self.public_state.num_quests_succeeded))
                    print("Number of failed quests: " + str(self.public_state.num_quests_failed))

                    if self.public_state.get_winning_team() == unassigned:
                        self.round += 1
                        if self.round > self.public_state.num_rounds:
                            self.broadcast("Game over!! ... but something went wrong")
                            self.st_state == "FINISHED"
                        else:
                            self.broadcast("Starting round " + str(self.round))

                            # Determine the team size for the current round.
                            #TODO: this assumes there are 5 players.
                            if self.round == 1 or self.round == 3:
                                self.team_size = 2
                            else:
                                self.team_size = 3

                            self.team_leader = (self.team_leader + 1) % (len(self.players) - 1)
                            self.attempt = 1
                            self.start_team_selection()
                    elif self.public_state.get_winning_team() == good:
                        self.broadcast("Goods are winning ... Let 'assasin' try to identify Merlin")
                        self.start_expose_merlin()
                    else:
                        self.broadcast("Game over!! Evil team wins")
                        self.st_state == "FINISHED"

            elif self.st_state == "GUESSING_ON_MERLIN" and event["event"] == "MerlinExposed":
                self.broadcast(event["message"])
                if self.roles[event["merlin_index"]] == merlin:
                    self.broadcast("Game over!! Evil team wins")
                else:
                    self.broadcast("Game over!! Good team wins")
                self.st_state == "FINISHED"                

class GameWSHandler(tornado.websocket.WebSocketHandler):
    def initialize(self, controller: GameController):
        self.controller = controller

    def open(self):
        self.controller.add_player(self)

    async def on_message(self, message_str: str):
        print(f"Message received from {self.request.remote_ip}: processing...")
        print("\t",message_str)
        # self.write_message({"message": message_str})
        self.controller.q.put(jsonpickle.decode(message_str))

    def check_origin(self, origin):
        return True

class GamesHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
    def options(self):
        self.set_status(204)
        self.finish()

    async def post(self):
        body = jsonpickle.decode(self.request.body)
        print("Creating a game instance", body)
        controller = GameController(5,4)
        IOLoop.current().spawn_callback(controller.game_loop)
        self.application.add_handlers(
            r".*",  # match any host
            [
                (
                    r"/ws",
                    GameWSHandler,
                    dict(controller=controller)
                ),
            ]
        )
        print("Done ..")
        self.write(f"Done ...")

if __name__ == "__main__":
    app = tornado.web.Application([(r"/games", GamesHandler)])
    app.listen(8888, "0.0.0.0")
    tornado.ioloop.IOLoop.current().start()

