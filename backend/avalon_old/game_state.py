
from .roles import *




class PublicGameState:

    """Represents all the information that is publically available to all players."""

    num_rounds = 5
    num_attempts_per_round = 5
    num_utterances_per_player = 10 # How many things each player can say during each discussion phase.
    
    num_quests_needed_for_victory = 3

    def __init__(self, num_players):
       
        self.num_players = num_players
        
        # TODO adapt this for the case that there are more than 5 players.
        self.num_evil_players = 2
        self.num_good_players = 3
        self.role_to_num_players:dict[str,int] = {merlin: 1,  good: 2, evil: self.num_evil_players}
       
        self.leader_index = 0
        self.attempt = 0

        self.num_quests_succeeded = 0
        self.num_quests_failed = 0



        self.winning_team = unassigned
        self.merlin_exposed = False


    def get_winning_team(self):
        


        if  self.num_quests_succeeded > self.num_rounds / 2:
            self.winning_team = good
        elif self.num_quests_failed > self.num_rounds / 2:
            self.winning_team = evil
        else:
            self.winning_team = unassigned

        if self.merlin_exposed:
            self.winning_team = evil

        return self.winning_team



# class FullGameState:

#     def __init__(self, public_state:PublicGameState, roles:list[str]):
#         self.public_state = public_state
#         self.roles = roles


# class IndividualGameState:

#     """Represents all the relevant information about the current game, as seen by one individual agent."""

#     def __init__(self, public_state:PublicGameState, my_index:int):

#         # The agent will know its role, and possibly the roles of the other players later.
       
#         self.my_index = my_index
#         self.num_players = public_state.num_players
#         self.num_evil_players = public_state.role_to_num_players.get(evil)
       
#         self.my_role = unknown
#         self.roles = [unknown]*public_state.num_players

#         self.num_quests_succeeded = 0
#         self.num_quests_failed = 0



#     def set_own_role(self, role):
#         self.my_role = role
#         self.roles[self.my_index] = self.my_role

#     def set_roles(self, roles:list[str]) -> None:
#         self.roles = roles


#     def set_leader(self, leader_index) -> None:
#         self.leader_index = leader_index