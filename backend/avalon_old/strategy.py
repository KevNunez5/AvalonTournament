import abc
import random
from .game_state import PublicGameState
from .roles import *
from .utils import *

class Strategy:

    def __init__(self, game_state:PublicGameState, my_index:int, roles:list[str]):
        self.game_state = game_state
        self.my_index = my_index
        self.roles = roles
        self.my_role = roles[my_index]


    def get_name_and_role(self) -> str:
        return "Player " + str(self.my_index) + " (" + self.my_role + ")"

    @abc.abstractmethod
    def talk(self) -> str:
        """ Allows the agent to say something during a discussion phase. """
        pass

    @abc.abstractmethod
    def listen(self, sender_index, utterance) -> None:
        """ Is called during the discussion phase so that the agent can receive any message uttered by any of the other agents. """
        pass




    @abc.abstractmethod
    def propose_team(self, team_size:int) -> list[bool]:
        """ Return a list of booleans, with length equal to the number of players in the game.
            the list should contain 'True' for each team member, and 'False' for each player that is not in the team.
        """
        pass

    @abc.abstractmethod
    def vote_team(self, proposed_team:list[bool]) -> bool:
        """Is called during the team-voting phase. 
            Returns True when the agent is in favor of the proposed team. Returns False when the agent is against the proposed team.
        """
        pass

    @abc.abstractmethod
    def vote_quest(self) -> bool:
        """ Is called during the quest.
            Good agents always return True. Evil agents may return False, which will cause the quest to fail.
        """
        pass

    @abc.abstractmethod
    def guess_merlin(self) -> int:
        pass

    def receive_quest_result(self, team:list[bool], num_yes_votes:int, num_no_votes:int, success:bool) -> None:
        pass

class RandomStrategy(Strategy):

    def propose_team(self, team_size:int) -> list[bool]:

        num_selected_players = 0
        team = [False]*self.game_state.num_players

        while num_selected_players < team_size:
            r = random.randint(0, self.game_state.num_players-1)
            if team[r] == False:
                team[r] = True
                num_selected_players += 1

        return team

    def vote_team(self, proposed_team:list[bool]) -> bool:

        # If the team was proposed by me, then of course I should always vote True.
        if self.game_state.leader_index == self.my_index:
            return True

        return random.choice([True, False])

    def vote_quest(self, team:list[bool]) -> bool:
        
        if self.my_role == evil:
            return random.choice([True, False])
        else:
            return True
        
    def guess_merlin(self) -> int:

        guessed_index = self.my_index

        while self.roles[guessed_index] == evil:
            guessed_index = random.randint(0, self.game_state.num_players-1)

        return guessed_index


class EvilStrategy(Strategy):

    def __init__(self,game_state:PublicGameState, my_index:int, roles:list[str]):
        super().__init__(game_state, my_index, roles)

        # Strategy that we will use to pretend that we are a good player.
        #self.fake_strategy = fake_strategy

    def propose_team(self, team_size:int) -> list[bool]:

    

        # Pick containing yourself and 1 or 2 good players.
             # I guess it doesn't make a lot of sense to include more than one evil player...

        team = [False]*self.game_state.num_players
        team[self.my_index] = True
        num_selected_players = 1

        while num_selected_players < team_size:
            r = random.randint(0, self.game_state.num_players-1)
            if team[r] == False and self.roles[r] != evil:
                team[r] = True
                num_selected_players += 1

        # TODO: implement something better?
            # IDEA: choose good players for which it is least obvious that they are good. This way it remains unclear that I am the evil one.
       
      

        #num_selected_evil_players = 0
        
        # while num_selected_evil_players == 0:
        #     team = [False]*self.game_state.num_players
        #     num_selected_players = 0

        #     while num_selected_players < team_size:
        #         r = random.randint(0, self.game_state.num_players-1)
        #         if team[r] == False:
        #             team[r] = True
        #             num_selected_players += 1

        #     num_selected_evil_players = utils.count_evil_players(team, self.game_state.roles)

        return team

    def vote_team(self, proposed_team:list[bool]) -> bool:

        # 1. If the team was proposed by me, then of course I should always vote True.
        if self.game_state.leader_index == self.my_index:
            print("  " + self.get_name_and_role() + " I'm voting 'yes', because this team was proposed by me")
            return True
        

        # 2. In the first round, always vote 'yes' otherwise I would expose myself as an Evil player
        if self.game_state.num_quests_failed + self.game_state.num_quests_succeeded == 0:
            print("  " + self.get_name_and_role()  + "  I'm voting 'yes', because this is the first round")
            return True
        



        # 3. If the team has 3 players and I am not in that team, then I should vote 'False'.
        # After all, if a team has 3 players and a good player is not included, then that good player would know that there is an evil player in the
        #  team.
        # Therefore, an evil player that is not in the team should do the same, otherwise it would be clear that he is evil.
        team_size = proposed_team.count(True)
        if team_size == self.game_state.num_good_players and not proposed_team[self.my_index]:
            print("  " + self.get_name_and_role()  + " I'm voting 'no', because I'm not in this team, which means that this team must contain an evil player!")
            return False



        # 3. Vote 'yes' if and only if the team contains at least one evil player.
             #TODO: implement a better strategy.

        # IDEA: always vote 'yes' unless:
        #   - you can construct an argument why a good player would vote 'no', 
        #   - you are already exposed as a bad player 
        #   - A 'yes' vote would lead to a third successful quest 
        #       -- On the other hand, the evil players would still have a chance to win if they can guess who Merlin is.

        # Count how many evil players are in the team (including myself).
        num_evil_players_in_team = count_evil_players(proposed_team, self.roles)
        
        if num_evil_players_in_team > 0:
            print("  " + self.get_name_and_role()  + " I'm voting 'yes', because this team contains an evil player.")
            return True
        else:
            print("  " + self.get_name_and_role()  + " I'm voting 'no', because this team does not contain any evil player.")
            return False

        


       
        
       

    def vote_quest(self, team:list[bool]) -> bool:
        


        # 1. If the evil team only needs one more failed quest to win, then we have no reason not to fail the quest.
        num_fails_needed = self.game_state.num_quests_needed_for_victory - self.game_state.num_quests_failed
        if num_fails_needed == 1:
            return False
        

        # 2. If the good team only needs one more succeeded quest to win, and this agent is the only evil player in the team, then it must 
        #     ensure the quest fails.

        #   Count how many successes the good team still needs.
        num_successes_needed = 3 - self.game_state.num_quests_succeeded

        #   Count how many evil players are in the team (including myself).
        num_evil_players_in_team = count_evil_players(team, self.roles)
        
        if num_successes_needed == 1 and num_evil_players_in_team == 1:
            return False
            # actually, it may be better to vote against, if you are very sure who Merlin is.
    
        # Note that if all team members are evil, then it is better if not all of them vote for a 'fail', otherwise the good players will know
        # exactly who are evil.

        # 3. Otherwise, just vote randomly.
        return random.choice([True, False])
    
    def guess_merlin(self) -> int:

        guessed_index = self.my_index

        while self.roles[guessed_index] == evil:
            guessed_index = random.randint(0, self.game_state.num_players-1)

        return guessed_index
        


class GoodStrategy(Strategy):

    def __init__(self, game_state:PublicGameState, my_index:int, roles:list[str]):
        super().__init__(game_state, my_index, roles)

        if self.my_role == merlin:
            self.hypotheses = []
            self.hypotheses.append(self.roles) 
            #print("Merlin's hypotheses: " + str(self.hypotheses[0]))

            #Actually, even if we are merlin, we could still generate hypotheses like the other good players,
            # so that we can pretend to be an 'ordinary' good player.

        else:
            self.generate_intial_role_hypotheses()




    def generate_intial_role_hypotheses(self):

        """ A 'hypothesis' assigns a possible role to each player. 
            Initially, we are creating all possible hypotheses.
            Later, whenever we receive the results of a quest, we remove those hypotheses that are no longer possible.
        """
        
        self.hypotheses = []

        max_evil = self.game_state.num_evil_players
        max_good = self.game_state.num_players - max_evil


        open_list = []
        open_list.append([])


        while len(open_list) > 0:
            partial = open_list.pop()

            num_evil = 0
            num_good = 0
            for i in range(len(partial)):
                if partial[i] == evil:
                    num_evil += 1
                else:
                    num_good += 1

            if len(partial) == self.game_state.num_players:

                if num_evil == self.game_state.num_evil_players:
                    self.hypotheses.append(partial)
                   

            elif len(partial) == self.my_index:
                
                partial.append(self.my_role)
                open_list.append(partial)

            else:

                if num_evil < max_evil:
                    copy1 = partial.copy()
                    copy1.append(evil)
                    open_list.append(copy1)

                if num_good < max_good:

                    copy2 = partial.copy()
                    copy2.append(good)
                    open_list.append(copy2)

        print()
        print("Player " + str(self.my_index) + " My hypotheses:")
        for hyp in self.hypotheses:
            print("*** " + str(hyp))
        print()


    def propose_team(self, team_size:int) -> list[bool]:
        
        #team_suggestions = self.get_team_suggestions(team_size)


        team = [False]*self.game_state.num_players
        
        # Make sure that I myself am in the team.
        team[self.my_index] = True
        num_selected_players = 1

        # Calculate a score for each player indicating how likely he or she is good, based on our current hypotheses.
        self.calculate_player_scores()
        

        # Now, add players based on their scores. Add the players that are most likely to be good.
        scores_copy = self.scores.copy()
        for i in range(team_size-1):
            
            # Get the player with the highest score.
            best = arg_max(scores_copy)

            # Consistency check.
            if scores_copy[best] == 0:
                print()
                print("Player " + str(self.my_index) + " My hypotheses:")
                for hyp in self.hypotheses:
                    print("*** " + str(hyp))
                raise Exception("Something went wrong: " + str(scores_copy))
            
            # Add it to the team.
            team[best] = True
            num_selected_players +=1

            # Now set its score to 0 so we won't add the same player again in the next iteration.
            scores_copy[best] = 0 
            


        # TODO: if I am merlin, and the evil players only need one more failed quest, then I should propose a team with only good players.

        return team

        #return random.choice(team_suggestions)



    # def get_team_suggestions(self, team_size:int)-> list[list[bool]]:
    #     pass



    def vote_team(self, proposed_team:list[bool]) -> bool:

        # If the team was proposed by me, then of course I should always vote True.
        if self.game_state.leader_index == self.my_index:
            print("  " + self.get_name_and_role()  + ": I'm voting 'yes', because this team is proposed by me")
            return True
        
        # In the first round, we have no information, so we may as well vote in favor.
        # After all, voting against might jeapordize losing the game.
        if self.game_state.num_quests_failed + self.game_state.num_quests_succeeded == 0:
            print("  " + self.get_name_and_role()  + ": I'm voting 'yes', because this is the first round")
            return True
        
        # If this is the last attempt, then I should vote True, otherwise we lose.
        if self.game_state.attempt == self.game_state.num_attempts_per_round:
            print("  " + self.get_name_and_role()  + ": I'm voting 'yes', because this is our last attempt, so otherwise we lose.") 
            return True
        


        
        # Check if the team contains any evil player.
            # Note: we can improve this, because for now we only test if there is a  player for which we know he is evil.
            # However, it can happen that we know the team must contain an evil player, even if we don't know which one it is.
            # SO: check that there is a hypothesis according to which all players are good. If not, then we know that at least one player must be evil.
        
        definitely_contains_evil_player = True
        for hyp in self.hypotheses:
            
            this_hyp_contains_evil_player = False
            for i in range(self.game_state.num_players):
                if proposed_team[i] and is_evil(hyp[i]):
                    this_hyp_contains_evil_player = True
                    break

            if not this_hyp_contains_evil_player:
                definitely_contains_evil_player = False
                break


        # if we know that there is an evil player (and I'm not merlin), than vote false
        if definitely_contains_evil_player and self.my_role != merlin:
            print("  " + self.get_name_and_role()  + ": I'm voting 'no', because this team definitely contains an evil player!")
            return False

        # if we know that there is an evil player and the evil players only need one more failed quest (even if I'm merlin), than vote false
        if definitely_contains_evil_player and self.game_state.num_quests_needed_for_victory - self.game_state.num_quests_failed == 1:
            print("  " + self.get_name_and_role()  + ": I'm voting 'no', because this team definitely contains an evil player!")
            return False


        # Calculate a score for each player indicating how likely he or she is good, based on our current hypotheses.
        self.calculate_player_scores()

        team_size = 0
        team_score = 0
        for i in range(self.game_state.num_players):
            
            if proposed_team[i]:
                team_size += 1
                
                if i == self.my_index:
                    team_score += 1.0
                else:
                    team_score += self.scores[i]

        # A score of 1.0 means we are sure the player is good. So if the team score equal the team size, 
        #  it means we are sure that every player in the team is good.
        if team_score == team_size:
            print("  " + self.get_name_and_role()  + ": I'm voting 'yes', because I know that this team definitely only contains good players.")
            return True

        # TODO: here we need to determine if there is any better team that can realistically be achieved.

        print("  " + self.get_name_and_role()  + ": I'm voting randomly...")
        return random.choice([True, False])

    def vote_quest(self, team:list[bool]) -> bool:
        return True
    

    def receive_quest_result(self, team:list[bool], num_yes_votes:int, num_no_votes:int, success:bool) -> None:
        
        retained_hypotheses = []

        num_fails_needed = 3 - self.game_state.num_quests_failed

        # If the evil team only needed one more failed quest, then they would have no reason to vote for success.
        # So, if the quest succeeded it means that all team members must have been good.
        if success and num_fails_needed == 1:
            for hyp in self.hypotheses:

                contains_evil = False
                for i in range(self.game_state.num_players):
                    if team[i] and is_evil(hyp[i]):
                        contains_evil = True
                        break
                
                if not contains_evil:
                    retained_hypotheses.append(hyp)

            self.hypotheses = retained_hypotheses

        if not success:
            
            for hyp in self.hypotheses:

                # Count how many agents may vote 'no' according to this hypothesis.
                # That is, the number of agents in the team that are, according to the current hypothesis, evil.
                max_num_no_votes = 0
                for i in range(self.game_state.num_players):

                    if team[i] and is_evil(hyp[i]):
                        max_num_no_votes += 1

                # If there are more 'no'-votes than possible according to the hypothesis,
                # Then the hypothesis is false, so we have to discard it.
                # Otherwise, we retain the hypothesis.
                if num_no_votes <= max_num_no_votes:
                    retained_hypotheses.append(hyp)
        
            self.hypotheses = retained_hypotheses
            # print("Player " + str(self.game_state.my_index) + ": Number of hypotheses left: " + str(len(self.hypotheses)))

        if(self.my_role != merlin):
            print()
            print("GoodStrategy.receive_quest_result()")
            print("Player " + str(self.my_index) + " My hypotheses:")
            for hyp in self.hypotheses:
                print("*** " + str(hyp))
            print()           



    def calculate_player_scores(self):
        
        # Calculate a score for each player indicating how likely he or she is good, based on our current hypotheses.
        self.scores = [0.0] * self.game_state.num_players

        for i in range(self.game_state.num_players):

            if i == self.my_index:
                continue # NOTE: an agent's own score is always 0.

            for hyp in self.hypotheses:
                if is_good(hyp[i]):
                    self.scores[i] += 1

            self.scores[i] = self.scores[i] / len(self.hypotheses)

