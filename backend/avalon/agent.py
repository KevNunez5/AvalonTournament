
import random
from .game_state import PublicGameState
from . import roles as Roles
from .strategy import EvilStrategy, GoodStrategy, RandomStrategy
from .team import Team

class Agent:

    def __init__(self, my_index:int, public_state:PublicGameState, press=True, is_random=False):
        self.my_index = my_index
        self.game_state = public_state
        self.my_name = public_state.player_names[my_index]
        self.generate_arguments = press
        self.is_random = is_random

        names_as_set = set(public_state.player_names)
        if len(names_as_set) != len(public_state.player_names):
            raise Exception("List of player names contains duplicate names: " + str(public_state.player_names) + " Please make sure that every player has a unique name.")

    def reveal_roles(self, roles:list[str]) -> None:
        """ Is called at the beginning of the game, if we are evil, after a role has been assigned to every agent."""
         
        self.roles = roles
        self.my_role = roles[self.my_index]

        # Choose a strategy.
        if self.is_random:

            self.strategy = RandomStrategy(self.game_state, self.my_index, self.roles, press=self.generate_arguments)

        elif self.my_role == Roles.evil:       

            # create a fake strategy in order to pretend to be a good player.
            fake_roles = [Roles.unknown]*self.game_state.num_players
            fake_roles[self.my_index] = Roles.good
            fake_strategy = GoodStrategy(self.game_state, self.my_index, fake_roles, press=self.generate_arguments)
        
            # Create our *real* strategy.
            self.strategy = EvilStrategy(self.game_state, self.my_index, self.roles, fake_strategy, press=self.generate_arguments)

        elif self.my_role == Roles.good:
            self.strategy = GoodStrategy(self.game_state, self.my_index, self.roles, press=self.generate_arguments)
        
        elif self.my_role == Roles.merlin:
            self.strategy = GoodStrategy(self.game_state, self.my_index, self.roles, press=self.generate_arguments)

        else:
            raise Exception("unknown role: " + self.my_role)
        


    # def receive_team_votes(self, proposed_team:Team, votes:list[bool], team_accepted:bool) -> None:
    #     pass
    #     #TODO implement this.


