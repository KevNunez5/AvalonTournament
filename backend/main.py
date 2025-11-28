import tornado.ioloop
import tornado.web
import tornado.websocket
import jsonpickle
import sys

import shortuuid
import regex as re

import subprocess

import avalon.avalon_rules as avalon_rules
from avalon.roles import unassigned, good, evil, merlin
from avalon.game_state import PublicGameState
from avalon.game_simulator import get_roles, assign_roles
from avalon.team import Team

from tornado.ioloop import IOLoop
from tornado.queues import Queue
from pathlib import Path
from datetime import datetime
import time


class GameController:
    
    def __init__(self, nplayers, nbots, url):
        self.q = Queue(maxsize=2)
        self.players = list()
        self.nplayers = nplayers
        self.nbots = nbots

        # ================================
        #   LOGGING POR PARTIDA
        # ================================
        game_id = url.rsplit("/", 1)[-1].strip("/")
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.log_path = logs_dir / f"avalon-log-{game_id}-{timestamp}.txt"

        # Header inicial
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(f"Avalon Game Log\n")
            f.write(f"Game ID: {game_id}\n")
            f.write(f"Created: {datetime.now().isoformat()}\n")
            f.write(f"Players={nplayers}, Bots={nbots}\n\n")

        subprocess.Popen([sys.executable, "bots.py", str(nbots), f"{url}"])
        
    def log_event(self, source: str, payload):
        """
        source: 'client_message', 'server_broadcast', 'system', etc.
        payload: dict o string
        """
        record = {
            "ts": time.time(),
            "source": source,
        }

        if isinstance(payload, dict):
            record.update(payload)
        else:
            record["message"] = str(payload)

        line = jsonpickle.encode(record)

        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    
    def add_player(self, channel):
        player_id = len(self.players)
        self.players.append(channel)

        self.log_event("system", {
            "event": "player_connected",
            "player_id": player_id,
            "remote": str(channel.request.remote_ip)
        })

        print("Number of players so far:", f"{len(self.players)}")
        channel.write_message({"message": f"Welcome player {player_id - 1}", "index": -1})

        if len(self.players) == self.nplayers + 1:
            self.q.put({"event": "AllPlayers"})


    def broadcast(self, msg, agent_index=-1):

        # Loguear mensaje antes de enviarlo
        self.log_event("server_broadcast", {
            "agent_index": agent_index,
            "payload": msg
        })

        for player in self.players:
            if isinstance(msg, dict):
                player.write_message(msg)
            else:
                player.write_message({
                    "message": msg,
                    "index": agent_index
                })

    
    def configure_player(self, index: int, public_state: PublicGameState, roles: list[str]):
        self.players[index + 1].write_message(jsonpickle.encode({
            "action": "RevealRoles",
            "msg": "Message?",
            "index": index,
            "game_state": public_state,
            "roles": roles
        }))

    def start_team_selection(self):
        print(self.public_state)
        if self.public_state.attempt == 5:
            self.broadcast("... 5 attempts ...")
            return
        self.st_state = "TEAM_SELECTION"
        self.players[0].write_message({"message": f"Asked Player {self.public_state.leader_index} to select a team"})
        self.players[self.public_state.leader_index + 1].write_message({"action": "SelectTeam", "team_size": self.public_state.team_size, "message": f"Please select a team with {self.public_state.team_size} members", "index": -1})

    def start_team_voting(self):
        self.st_state = "TEAM_VOTING"
        self.players[0].write_message({"message": f"Asked Players to vote for a team", "index": -1})
        for player in self.players:
            player.write_message({"action": "VoteTeam", "game_state": jsonpickle.dumps(self.public_state), "team": self.team, "message": "Please cast your vote"})

        # for player in self.players:
        #     player.write_message({"action": "VoteTeam", "team": self.team, "message": "Please cast your vote"})

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
                pnames = list([f"player{i}" for i in range(self.nplayers)])
                public_state = PublicGameState(pnames) # num_players)
                self.public_state = public_state

                #2. Assign roles
                self.roles = get_roles(public_state)
                print(self.roles)

                for i, role_assignment in assign_roles(public_state, self.roles):
                    print(i, role_assignment)
                    self.configure_player(i, public_state, role_assignment)

                public_state.round = 1
                self.round = 1
                public_state.team_size = avalon_rules.get_team_size(public_state.round, public_state.num_players)

                self.broadcast("Starting round " + str(self.round))
                for player_index in range(len(self.roles)):
                    self.players[player_index+1].write_message({"action": "StartRound", "game_state": jsonpickle.dumps(public_state)})

                # # Determine the team size for the current round.
                # #TODO: this assumes there are 5 players.
                # if self.round == 1 or self.round == 3:
                #     self.team_size = 2
                # else:
                #     self.team_size = 3

                # self.team_leader = 0
                # self.attempt = 1
                self.start_team_selection()
            elif self.st_state == "TEAM_SELECTION" and event["event"] == "TeamSelected":
                # normalizamos a enteros por si jsonpickle los manda como str
                self.team = [int(x) for x in event["team"]]

                # líder: usamos el index que viene del bot si está
                leader = int(event["index"]) if "index" in event else self.public_state.leader_index

                # actualizar public_state
                proposed_team = Team(
                    self.public_state.player_names,
                    [i in self.team for i in range(self.nplayers)]
                )
                self.public_state.proposed_team = proposed_team

                # 🔹 Ahora sí, broadcast bien formado
                self.broadcast({
                    "action": "TeamSelected",
                    "index": leader,
                    "team": self.team,
                    "message": f"Player {leader} proposes the following team [{', '.join(map(str, self.team))}]",
                })

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
                        # Usamos siempre el estado público
                        self.public_state.attempt += 1
                        self.public_state.leader_index = (self.public_state.leader_index + 1) % (len(self.players) - 1)
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
                        if self.round > avalon_rules.num_rounds:
                            self.broadcast("Game over!! ... but something went wrong")
                            self.st_state == "FINISHED"
                        else:
                            self.broadcast("Starting round " + str(self.round))

                            # Actualiza el tamaño de equipo en el estado público
                            self.public_state.team_size = avalon_rules.get_team_size(
                                self.round,
                                self.public_state.num_players
                            )

                            # Nuevo líder y se reinician intentos en el estado público
                            self.public_state.leader_index = (self.public_state.leader_index + 1) % (len(self.players) - 1)
                            self.public_state.attempt = 1

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
        print("\t", message_str)

        event = jsonpickle.decode(message_str)

        # Log entrada del cliente
        self.controller.log_event("client_message", {
            "remote_ip": self.request.remote_ip,
            "raw": message_str,
            "event": event
        })

        self.controller.q.put(event)


    def check_origin(self, origin):
        return True

class GamesHandler(tornado.web.RequestHandler):
    urls = []
    def set_default_headers(self):
        # Origen
        self.set_header("Access-Control-Allow-Origin", "*")
        # Qué headers acepta en las peticiones
        self.set_header("Access-Control-Allow-Headers", "Content-Type")
        # Qué métodos acepta
        self.set_header("Access-Control-Allow-Methods", "POST, OPTIONS")

    def options(self):
        self.set_status(204)
        self.finish()

    async def get(self):
        self.write(jsonpickle.dumps(self.urls))

    async def post(self):
        if self.request.body:
            body = jsonpickle.decode(self.request.body)
        else:
            body = {}

        gameid = shortuuid.uuid()
        url = f"/ws/{gameid}"
        print(url)
        self.urls.append(url)
        # 👇 lee del body, con default 5/5
        nplayers = int(body.get("nplayers", 1))
        nbots    = int(body.get("nbots", 4))
        
        print("Creating a game instance with:", nplayers, "players and", nbots, "bots")

        controller = GameController(nplayers, nbots, url)
        IOLoop.current().spawn_callback(controller.game_loop)

        self.application.add_handlers(
            r".*",
            [
                (re.escape(url), GameWSHandler, dict(controller=controller)),
            ]
        )

        self.set_header("Content-Type", "application/json")
        self.write(jsonpickle.dumps({"location": url}))



if __name__ == "__main__":
    app = tornado.web.Application([(r"/games", GamesHandler)])
    app.listen(8888, "0.0.0.0")
    tornado.ioloop.IOLoop.current().start()

