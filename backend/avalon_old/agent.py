
import random
from .game_state import PublicGameState
from .roles import *
from .strategy import EvilStrategy, GoodStrategy, RandomStrategy

class Agent:

    def __init__(self, my_index:int, public_state:PublicGameState):
        self.my_index = my_index
        self.game_state = public_state
        

    def reveal_roles(self, roles:list[str]) -> None:
        """ Is called at the beginning of the game, if we are evil, after a role has been assigned to every agent."""
         
        self.roles = roles
        self.my_role = roles[self.my_index]

        # Choose a strategy, based on our role.
        if self.my_role == evil:
            
            

            # create a fake strategy in order to pretend to be a good player.
            #fake_roles = [unknown]*self.game_state.num_players
            #fake_roles[self.my_index] = good
            #self.fake_strategy = GoodStrategy(self.game_state, self.my_index, fake_roles)
        
            # Create our *real* strategy.
            self.strategy = EvilStrategy(self.game_state, self.my_index, self.roles)

        elif self.my_role == good:
            self.strategy = GoodStrategy(self.game_state, self.my_index, self.roles)
        
        elif self.my_role == merlin:
            self.strategy = GoodStrategy(self.game_state, self.my_index, self.roles)

        else:
            raise Exception("unknown role: " + self.my_role)
        


    def receive_team_votes(self, proposed_team:list[bool], votes:list[bool], team_accepted:bool) -> None:
        pass
        #TODO implement this.


