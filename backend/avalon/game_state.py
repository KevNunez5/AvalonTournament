
import typing
from . import avalon_rules
from .roles import *
from .team import Team




class PublicGameState:

    """Represents all the information that is publically available to all players."""



    def __init__(self, player_names:list[str]):
       
        self.num_players = len(player_names)
        self.player_names = player_names.copy()
        
        self.role_to_num_players = avalon_rules.get_roles(self.num_players)

        self.num_good_players = typing.cast(int, self.role_to_num_players.get(good)) + 1 # add one for Merlin.
        self.num_evil_players = typing.cast(int, self.role_to_num_players.get(evil))

        self.round = 0

        self.team_size = -1 # the size of the team for the current round. The correct value for this variable should be set later.
        self.leader_index = 0
        self.attempt = 0

        self.num_quests_succeeded = 0
        self.num_quests_failed = 0

        # is set to True whenever in some round the players were not able to select a team.
        self.team_vote_failed = False

        self.winning_team = unassigned
        self.merlin_exposed = False

        self.proposed_team = Team(self.player_names)


    def get_leader_name(self):
        return self.player_names[self.leader_index]
    

    def get_winning_team(self):
        
        if  self.num_quests_succeeded >= avalon_rules.num_quests_needed_for_victory:
            self.winning_team = good
        
        elif self.num_quests_failed >= avalon_rules.num_quests_needed_for_victory:
            self.winning_team = evil

        elif self.team_vote_failed:
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