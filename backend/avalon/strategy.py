import abc
import random
import re
import typing
from Argumentation.argument import Argument
from Argumentation.logic import AtLeast, Conjunction, Disjunction, Fact, Implication, ProverUtils
from Argumentation.prover import Prover
from avalon_logic import AvalonProver
import avalon_logic
import avalon_rules
from decision import Decision
from game_state import PublicGameState
from hypothesis import Hypothesis
from quest_result import QuestResult
from roles import *
from team import Team, TeamWithScore
from team_proposal import TeamProposal
import utils

class Strategy:

    def __init__(self, game_state:PublicGameState, my_index:int, roles:list[str], apply_special_axiom = True, press=True):
        self.game_state = game_state
        self.my_index = my_index
        self.my_name = game_state.player_names[my_index]
        self.generate_arguments = press

        print("" + self.my_name + " using press: " + str(self.generate_arguments))

        self.roles = roles
        self.my_role = roles[my_index]
        
        self.apply_special_axiom = apply_special_axiom

        # stores the utterances so far received from the other players in any discussion phase. Is cleared at the beginning of every new discussion phase.
        self.conversation = []

        # List to store the next things I'm planning to say in a discussion phase.
        self.my_next_utterances:list[str] = []

        self.facts_base = []
        self.argument_base:dict[str,Argument] = {}

    def get_name_and_role(self) -> str:
        
        string = self.my_name + " (" + self.my_role + ")"

        if self.my_role != merlin:
            string += "  "

        return string

    @abc.abstractmethod
    def on_new_round(self, game_state:PublicGameState) -> None:
        """Is called at the beginning of each new round, so that the player can do some preparations."""
        pass


    @abc.abstractmethod
    def discuss_before_team_proposal(self, conversation:list[str]) -> str:
        """ Is called during the discussion phase before the leader proposes a team. Allows the agent to say something during this discussion. """
        return self.discuss(conversation) # Just call a generic 'discuss' function.

    @abc.abstractmethod
    def propose_team(self, team_size:int) -> Team:
        pass

    
    @abc.abstractmethod
    def inform_proposed_team(self, game_state:PublicGameState):
        "Is called after the leader has proposed a team, to inform the players of the leader's choice"
        pass

    @abc.abstractmethod
    def discuss_proposed_team(self, conversation:list[str]) -> str:
        """ Is called during the discussion phase after the leader has proposed a team. Allows the agent to say something during this discussion. """
        return self.discuss(conversation) # Just call a generic 'discuss' function.

    @abc.abstractmethod
    def vote_team(self) -> bool:
        """Is called during the team-voting phase. 
            Returns True when the agent is in favor of the proposed team. Returns False when the agent is against the proposed team.
        """
        pass

    @abc.abstractmethod
    def vote_quest(self, Team) -> bool:
        """ Is called during the quest.
            Good agents always return True. Evil agents may return False, which will cause the quest to fail.
        """
        pass

    @abc.abstractmethod
    def guess_merlin(self) -> int:
        pass

    def receive_quest_result(self, team:Team, num_yes_votes:int, num_no_votes:int, success:bool) -> None:
        raise Exception("Not implemented!")

    def discuss(self, conversation:list[str]) -> str:
    
        # Extract any new utterances received from the other players.
        diff = len(conversation) - len(self.conversation)
        new_utterances = conversation[-diff:]

        #TODO: currently the agent does not listen to the things the other agents say.

        # update our conversation.
        self.conversation = conversation.copy()

        if self.generate_arguments and len(self.my_next_utterances) > 0:
            utterance = self.my_next_utterances.pop(0)
        else:
            utterance = ""

        return utterance


class RandomStrategy(Strategy):

    def on_new_round(self, game_state:PublicGameState) -> None:
        pass

    def propose_team(self, team_size:int) -> Team:

        num_selected_players = 0
        team = [False]*self.game_state.num_players

        while num_selected_players < team_size:
            r = random.randint(0, self.game_state.num_players-1)
            if team[r] == False:
                team[r] = True
                num_selected_players += 1

        return Team(self.game_state.player_names, team)

    def vote_team(self) -> bool:

        # If the team was proposed by me, then of course I should always vote True.
        if self.game_state.leader_index == self.my_index:
            return True

        return random.choice([True, False])

    def vote_quest(self, team:Team) -> bool:
        
        if self.my_role == evil:
            return random.choice([True, False])
        else:
            return True
        
    def receive_quest_result(self, team:Team, num_yes_votes:int, num_no_votes:int, success:bool) -> None:
        pass
        
    def guess_merlin(self) -> int:

        guessed_index = self.my_index

        while self.roles[guessed_index] == evil:
            guessed_index = random.randint(0, self.game_state.num_players-1)

        return guessed_index



class GoodStrategy(Strategy):

    """ A strategy for a player that is on the 'good' team. """

    def __init__(self, game_state:PublicGameState, my_index:int, roles:list[str], apply_special_axiom=True, press=True):
        super().__init__(game_state, my_index, roles, apply_special_axiom, press)

        # The following two arrays are used to keep track of which players are definitely 'evil' or definitely 'good'.
        self.is_certainly_evil = [False]*self.game_state.num_players
        self.is_certainly_good = [False]*self.game_state.num_players  

            # Initially, the agent only knows of itself that he is good, but does not know anything yet about the other players.
        self.is_certainly_good[my_index] = True

        # This array stores the results of all teams that have been proposed.
        self.team_proposals:list[TeamProposal] = []

        # This array stores the results of all previous quests.
        self.quest_results:list[QuestResult] = []
        

        self.generate_intial_role_hypotheses()


    def generate_intial_role_hypotheses(self):
    # GOOD
        """ A 'hypothesis' assigns a possible role to each player. 
            Initially, we are creating all possible hypotheses.
            Later, whenever we receive the results of a quest, we remove those hypotheses that are no longer possible.
        """
        
        self.hypotheses:list[Hypothesis] = []

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
                    self.hypotheses.append(Hypothesis(partial))
                   

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

        self.calculate_player_scores()


   
    def on_new_round(self, game_state:PublicGameState) -> None:
    # GOOD
        # First, determine which teams are feasible (i.e. discard those teams for which we are sure they contain an evil player.)
        feasible_teams = self.get_potential_teams_objectively(game_state.team_size, self.my_index)

        if len(feasible_teams) != 0:
            # Calculate a heuristic score for each team.
            self.teams_with_score = self.get_potential_teams_heuristically(feasible_teams)


        

    def get_potential_teams_objectively(self, team_size:int, included_player:int=-1, excluded_player:int=-1)-> list[Team]:
    # GOOD

        """ Returns all possible teams, except those for which we are absolutely certain that it contains an evil player."""
        
        # 1. Get all teams of the given size that include or exclude a given player.
        if included_player == -1 and excluded_player == -1:
            all_teams = utils.get_all_teams(self.game_state, team_size)
        
        elif included_player != -1 and excluded_player == -1:
            all_teams = utils.get_all_teams_including(self.game_state, team_size, included_player)
        
        elif included_player == -1 and excluded_player != -1:
            all_teams = utils.get_all_teams_excluding(self.game_state, team_size, excluded_player)
        else:
            raise Exception("This case is not implemented yet.")


        if len(all_teams) == 0:
            raise Exception("all_teams == 0")


        # 2. Filter out all teams for which we can be absolutely sure that they contain at least one evil player.
        all_teams_filtered = []
        for team in all_teams:
            num_plausible_hyps_all_good = sum(1 for hyp in self.hypotheses if hyp.plausible and team.count_evil_players(hyp.role_assignment) == 0)
            if num_plausible_hyps_all_good > 0:
                all_teams_filtered.append(team)

        #if len(all_teams_filtered) == 0:
            #raise Exception("all_teams_filtered == 0")
        # If this is a 'fake' strategy used by an Evil player, then it may happen that the list of feasible teams is empty.
        # This happens if we are already exposed as an Evil player.


        # 3. If I am Merlin, then check if any of the suggested teams only contains good players. 
        #  If that is the case, then we should only return such teams.
        if self.my_role == merlin:

            if len(all_teams_filtered) == 0:
                raise Exception("all_teams_filtered == 0")
            
            clean_team_suggestions = all_teams_filtered.copy()
            
            for suggested_team in all_teams_filtered:
                if suggested_team.count_evil_players(self.roles) > 0:
                    clean_team_suggestions.remove(suggested_team)
            
            all_teams_filtered = clean_team_suggestions

            if len(all_teams_filtered) == 0:
                raise Exception("all_teams_filtered == 0 (Merlin)")

        
        return all_teams_filtered


    def get_potential_teams_heuristically(self, feasible_teams:list[Team]) -> list[TeamWithScore]:
       
        """ Calculates a heuristic score for each given team and returns all teams in a list, sorted from best team to worst team."""

        if len(feasible_teams) == 0:
            raise Exception("No feasible teams given.")
        

        if utils.VERBOSITY_LEVEL > 0:
            print("Player " + str(self.my_index) + " get_potential_teams_heuristically() feasible teams:")

        # Calculate a heuristic score for each team.
        teams_with_score = []
        for team in feasible_teams:

            if not team.contains_player(self.my_name) and self.game_state.get_leader_name() == self.my_name:
                print(str(feasible_teams))
                raise Exception("Team does not contain myself")
            
            team_score = self.calculate_team_heurisitic(team)

            if utils.VERBOSITY_LEVEL > 0:
                team_score_string = str(team) + ": " + str(team_score) + " --- "    
                for i in range(self.game_state.num_players):
                    if team.contains_player(i):
                        team_score_string += " p" + str(i) + ": " + str(self.scores[i])
                print(team_score_string)

            team_with_score = TeamWithScore.from_team(team, team_score)
            teams_with_score.append(team_with_score)

        
        teams_with_score = sorted(teams_with_score, key=lambda team: team.score, reverse=True)
        
        return teams_with_score

    
    def propose_team(self, team_size:int) -> Team:
    # GOOD
        
        # The list teams_with_score is sorted from highest score to lowest score. 
        # So, the highest score can be obtained from the first element of this list.
        max_score = self.teams_with_score[0].score

        # Multiple teams can have the same score, so we get all teams with the highest score.
        teams_with_max_score = [team for team in self.teams_with_score if team.score == max_score and team.contains_player(self.my_name)]

        if len(teams_with_max_score) == 0:
            raise Exception("len(teams_with_max_score) == 0")

        # Finally, randomly pick one of the teams with the highest score.
        team = random.choice(teams_with_max_score)


        #It's important that good players, except Merlin, choose the team randomly, because in that way Merlin can choose a team that only
        # consists of good players, while Evil players might still believe that it was randomly chosen.
        
        if not team.contains_player(self.my_name):
            raise Exception("Team to propose does not contain myself")
        
        return team
    

    def inform_proposed_team(self, game_state:PublicGameState):
    # GOOD
    #  
        # Update the game state.
        # in a simulation this is not necessary, because the lhs is the same object as the rhs anyway. 
        # However, we do this to simulate the real-world case in which the agent and the game manager run on different machines
        self.game_state = game_state 

        team_proposal = TeamProposal(game_state.round, game_state.attempt, game_state.get_leader_name(), game_state.proposed_team)
        self.team_proposals.append(team_proposal)

    
        if utils.VERBOSITY_LEVEL > 0:
            print(self.get_name_and_role() + " inform_proposed_team() hypotheses:")
        

        # Under some circumstances, we can deduce the maximum number of evil players that can be in the team.

        if not game_state.proposed_team.contains_player(game_state.get_leader_name()):
            # If the proposer did not include himself in the proposed team, then he's not playing logically, so we can't deduce anything
            # about the number of evil players in the team.
            max_evil_players_in_team = game_state.num_evil_players

        elif self.game_state.round == 4 and self.game_state.num_players >= 7:
            max_evil_players_in_team = 2
            
        elif self.apply_special_axiom:
            max_evil_players_in_team = 1

        else:
            max_evil_players_in_team = game_state.num_evil_players
        

        # 1. Update our hypotheses, based on the team proposed by the leader.
        for hyp in self.hypotheses:
            
            if is_good(hyp.role_assignment[game_state.leader_index]):
                continue

            if game_state.proposed_team.count_evil_players(hyp.role_assignment) > max_evil_players_in_team:
                hyp.plausible = False


                if max_evil_players_in_team == 1:
                    hyp.reason_for_rejection = avalon_logic.no_second_evil_player(self.game_state.round, self.game_state.get_leader_name(), self.game_state.proposed_team)
                elif max_evil_players_in_team == 2:
                    hyp.reason_for_rejection = avalon_logic.no_third_evil_player(self.game_state.round, self.game_state.get_leader_name(), self.game_state.proposed_team)
                else:
                    raise Exception("evil players in team: " + str(game_state.proposed_team.count_evil_players(hyp.role_assignment)))

                hyp.reason_for_rejection_text = hyp.reason_for_rejection.description
                #hyp.reason_for_rejection_text = reason_for_rejection_text
                #TODO: I think we can remove this, because the axiom itself already contains a description.
            
            if utils.VERBOSITY_LEVEL > 0:
                s = str(hyp.role_assignment)
                if not hyp.plausible:
                    s += " X Rejected because: " + hyp.reason_for_rejection_text
                print(s)

        # 2. Check for which players we can determine whether they are definitely good or definitely bad.
        self.evaluate_players()


        # 3. Decide whether to vote in favor or against the proposed team.
        objective_decision = self.get_objective_team_vote_decision(self.game_state.proposed_team)

        if objective_decision == None:
            self.vote_decision = self.get_heuristic_team_vote_decision(self.game_state.proposed_team)
        else:
            self.vote_decision = objective_decision


        # 4. make sure that we will express our argument to the other players in the upcoming discussion.
        self.my_next_utterances.append(self.vote_decision.argument)

  
    def get_objective_team_vote_decision(self,proposed_team:Team) -> Decision|None:
    # GOOD

        ### 1. Check a few basic criteria that may lead to a quick decision.

        # 1a. If the team was proposed by me, then of course I should always vote True.
        if self.game_state.leader_index == self.my_index:
            
            vote_suggestions = [True]
            reason = "I'm voting 'yes', because this team was proposed by me."
            
            return Decision(vote_suggestions, reason) # type: ignore
            
        
        # 1b. In the first round, we have no information, so we may as well vote in favor.
        if self.game_state.num_quests_failed + self.game_state.num_quests_succeeded == 0:

            vote_suggestions = [True]
            reason = "I'm voting 'yes', because this is the first round."
            
            return Decision(vote_suggestions, reason) # type: ignore

        
        # 1c. If this is the last attempt, then I should vote True, otherwise we lose.
        # TODO: this can be improved if we take into account that we may know that the next player is evil.
        if self.game_state.attempt == avalon_rules.num_attempts_per_round:

            vote_suggestions = [True]
            reason = "I'm voting 'yes', because this is our last attempt, so otherwise we lose."
            
            return Decision(vote_suggestions, reason) # type: ignore

        
        ### 2. Check if we can be sure that the team contains any evil player.
        
   
        # 2a. Count how many plausible hypotheses we have left.
        num_plausible_hypotheses = sum(1 for hyp in self.hypotheses if hyp.plausible)

        # 2b. Count in how many of those plausible hypotheses the team only consists of good players.
        num_plausible_hyps_all_good = sum(1 for hyp in self.hypotheses if hyp.plausible and proposed_team.count_evil_players(hyp.role_assignment) == 0)

        # 2c. There are no plausible hypotheses according to which all team members are good, then we can be sure that the team contains an evil player.
        definitely_contains_evil_player = (num_plausible_hyps_all_good == 0)

        only_one_fail_left = (avalon_rules.num_quests_needed_for_victory - self.game_state.num_quests_failed == 1)
        #TODO: if we are Merlin and there is only one fail left, then we can use our 'superpower' to determine if the team has evil players.


        # 2d. if we know that there is an evil player then vote false
        if definitely_contains_evil_player:
                       
            vote_suggestions = [False]


            # Check if there is any agent in particular in the team that we know is evil.
            known_evil_players = [i for i in range(self.game_state.num_players) if proposed_team.contains_player(i) and self.is_certainly_evil[i]]

            # known_evil_players = []
            # for i in range(self.game_state.num_players):
            #     if proposed_team.contains_player(i) and self.is_certainly_evil[i]:
            #         known_evil_players.append(i)


            if len(known_evil_players) == 0:
                # This happens if we know there is an evil player in the team, but we don't know *who* is the evil player.

                if proposed_team.size > self.game_state.num_good_players - 1 and not proposed_team.contains_player(self.my_index):
                    reason = "Besides me there are only " + str(self.game_state.num_good_players - 1) + " other good players. Therefore, this team must contain at least one evil player. So I will vote 'no'."

                else:
                    reason = "I'm voting 'no', because this team definitely contains an evil player! "
                    
                    if self.generate_arguments:
                        arguments_against = []

                        # collect the hypotheses in which all proposed team members are good. (we know these are all rejected.)       
                        for hyp in self.hypotheses:
                            if proposed_team.count_evil_players(hyp.role_assignment) == 0:
                                
                                if hyp.reason_for_rejection == None:
                                    print("WARNING: reason for rejecting hypothesis is 'None'")
                                else:
                                    #print("strategy.py line 489: " + str(hyp) + " " + str(hyp.reason_for_rejection) + " " + hyp.reason_for_rejection_text)
                                    arguments_against.append(hyp.reason_for_rejection)

                        # We want to show that the team contains at least one evil player. (i.e.  AtLeast(1,Alice, Bob, Carol))
                        # However, since the prover can only prove literals, we need to add the following rule: 
                        # #   AtLeast(1,Alice, Bob, Carol) -> contains_evil_player(Alice, Bob, Carol)
                        arguments_against.append(avalon_logic.implies_contains_evil_player(proposed_team))
                        
                        prover = AvalonProver(self.game_state, self.my_name, arguments_against)
                        prover.prove(avalon_logic.contains_evil_player(proposed_team))
                        informal_proof = prover.get_informal_proof()

                        if informal_proof != None:
                            reason += "I can support this with the following arguments: " + str(informal_proof)

            elif len(known_evil_players) == 1:
                evil_player_index = known_evil_players[0]
                evil_player_name = self.game_state.player_names[evil_player_index]
                reason = "I'm voting 'no' because, as I mentioned before, player " +  evil_player_name +  " is definitely evil!"
            else:
                reason = "I'm voting 'no' because, as I mentioned before, players " 
                for j in known_evil_players:
                    evil_player_name = self.game_state.player_names[j]
                    reason +=  evil_player_name + ", "
                reason += "are definitely evil!"
            
            return Decision(vote_suggestions, reason) # type: ignore


        ### 2e. Check if we can be definitely sure that all team members are good.
       
        if num_plausible_hyps_all_good == num_plausible_hypotheses:

            vote_suggestions = [True]
            reason = "I'm voting 'yes', because I know that this team definitely only contains good players."
            
            return Decision(vote_suggestions, reason) # type: ignore


        # If there is only one hypothesis that considers all team members good, and that hypothesis has been rejected, then present that as 
        # the argument for rejecting the proposed team.

        if definitely_contains_evil_player and (proposed_team.size==self.game_state.num_good_players or (proposed_team.size==self.game_state.num_good_players-1 and not proposed_team.contains_player(self.my_index))):

            vote_suggestions = [False]
            reason = ""
            
            for hyp in self.hypotheses:

                if proposed_team.count_evil_players(hyp.role_assignment) == 0:
                    
                    # Consistency check
                    # TODO: remove debug code
                    if hyp.plausible:
                        raise Exception("This hypothesis is still considered plausible: " + str(hyp))

                    reason = "I reject this team for the following reason: " + hyp.reason_for_rejection_text
                    break

            # Consistency check
            # TODO: remove debug code
            if len(reason) == 0:
                print("proposed team: " + str(proposed_team))
                for hyp in self.hypotheses:
                    print("hypothesis: " + str(hyp.role_assignment)  + " number of evil players in proposed team: " + str(proposed_team.count_evil_players(hyp.role_assignment)))
                raise Exception("Something went wrong")
            

            return Decision(vote_suggestions, reason) # type: ignore
        
        

        return None


    def get_heuristic_team_vote_decision(self, proposed_team:Team) -> Decision:
    # GOOD
    #    
        # We have to add some checks that the other teams are realistic.
        # For example, if the proposed team contains fewer players than there are good players, then it doesn't 
        # make sense to only accept teams that include ourselves, because then for any team there would 
        # always be at least one good player rejecting it.

        if proposed_team.size < self.game_state.num_good_players:
            
            #feasible_teams = self.get_potential_teams_objectively(proposed_team.size, -1, self.my_index) #exclude myself.
                        
            #Improvement: get all feasible teams either with or without myself.
            # If the proposed team does not include myself, and we are looking for teams with fewer members than the number of good players,
            # then check if the best team without myself is as good as the proposed team.
            # If yes, then accept the proposed team. If not, then alternatively, proposed the best team among all feasible teams (including those that contain myself.)

            feasible_teams = self.get_potential_teams_objectively(proposed_team.size)

        
        elif proposed_team.size == self.game_state.num_good_players:
            feasible_teams = self.get_potential_teams_objectively(proposed_team.size) # get all possible teams (naturally the best possible team will include myself.)
        
        else:
            # According to the rules of the game this should never happen, for obvious reasons.
            raise Exception("proposed_team.size > self.game_state.num_good_players")
        

        if len(feasible_teams) == 0:
            raise Exception("Error: len(feasible_teams) == 0")

        # Calculate a heuristic score for each team.
        self.teams_with_score = self.get_potential_teams_heuristically(feasible_teams)
        
        score_of_proposed_team = self.calculate_team_heurisitic(proposed_team)

        best_team = self.teams_with_score[0]

        best_team_without_me = None
        for team in self.teams_with_score:
            if not team.contains_player(self.my_index):
                best_team_without_me = team
                break
            


        if proposed_team.size < self.game_state.num_good_players and not proposed_team.contains_player(self.my_index) and best_team_without_me != None:           
            reference_score = best_team_without_me.score
        else:
            reference_score = best_team.score

        #print("Player " + str(self.my_index) + " score of proposed team " + str(proposed_team) + ": " + str(score_of_proposed_team))

        if reference_score <= score_of_proposed_team:
            vote_suggestions = [True]
            argument = "I have no reason to vote against this team, so I will vote 'yes'."
            return Decision(vote_suggestions, argument) # type: ignore
        

        vote_suggestions = [False]
        argument = "" 

        for team in self.teams_with_score:

            # Loop over all teams that have a better score than the proposed team.
            if team.score < reference_score:
                break

            argument += "I think the the team " + str(team) + " would be better, because "
            

            first = True
            for i in range(self.game_state.num_players):

                name = self.game_state.player_names[i]
                
                if proposed_team.contains_player(i) and not team.contains_player(i):
                    

                    # collect all failed quests that involved player i
                    failed_quests = [str(quest.round) for quest in self.quest_results if not quest.success and quest.team.contains_player(i)]
                    
                    if len(failed_quests) > 0:

                        if not first:
                            argument += " and "
                            first = False

                        argument += name + " was a team member in the failed quests of round"
                        if len(failed_quests) > 1:
                            argument += "s "
                        else:
                            argument += " "
                        argument += utils.get_string("", " and ", "", *failed_quests) + " "

                if not proposed_team.contains_player(i) and team.contains_player(i):

                    # collect all successful quests that involved player i
                    successful_quests = [str(quest.round) for quest in self.quest_results if quest.success and quest.team.contains_player(i)]
                    
                    if len(successful_quests) > 0:
                        argument += name + " was a team member in the successful quests of round"
                        if len(successful_quests) > 1:
                            argument += "s "
                        else:
                            argument += " "
                        argument += utils.get_string("", " and ", "", *successful_quests) + " "

            argument += "."
        
       
        return Decision(vote_suggestions, argument) 


    def vote_team(self) -> bool:
    # GOOD
        return random.choice(self.vote_decision.choices)




    def vote_quest(self, team:Team) -> bool:
    # GOOD
        return True
    

    def receive_quest_result(self, team:Team, num_yes_votes:int, num_no_votes:int, success:bool) -> None:
    # GOOD

        quest_result = QuestResult(self.game_state.round, team, num_no_votes)
        self.quest_results.append(quest_result)

        # for i in range(self.game_state.num_players):
        #     if team.contains_player(i):
        #         if success:
        #             self.involved_in_successful_quests[i] += 1
        #         else:
        #             self.involved_in_failed_quests[i] += 1
        

        new_quest_result = avalon_logic.quest_result(self.game_state.round, team, num_no_votes)
        self.facts_base.append(new_quest_result)
        

        # after receiving the quest results, we update our hypotheses.
        # That is, we throw out those hypotheses that are inconsistent with the voting results, and keep the ones that are consistent with the results.

        if success:

            # calculate how many more quests we need to fail before losing the game.
            num_fails_needed = avalon_rules.num_quests_needed_for_victory - self.game_state.num_quests_failed

            # If the evil team only needed one more failed quest, then the evil players would have no reason to vote for success.
            # So, in that case, if the quest succeeded, we can conclude that all players that voted for success are good.
            # This means that any hypothesis that predicts the current team contains more evil players than the number of no-votes can be discarded.

            #  (in general *all* team members would have voted for succees, except in the case that there are 7 or more players
            #   and we are in the 4th round, because in that case a quest can still succeed with 1 no-vote)
            
            if num_fails_needed == 1:

                # loop over all hypotheses.
                for hyp in self.hypotheses:

                    if not hyp.plausible:
                        continue

                    # for the current hypotheses check if it predicts that any of the current team members is evil.
                    num_evil_players_in_team = team.count_evil_players(hyp.role_assignment)

                    # contains_evil = False
                    # for i in range(self.game_state.num_players):
                    #     if team.contains_player(i) and is_evil(hyp.role_assignment[i]):
                    #         contains_evil = True
                    #         break
                    
                    # only keep the current hypothesis if it predicts that all the current team members are good.
                    #if contains_evil:
                    if num_evil_players_in_team > num_no_votes:
                        hyp.plausible = False
                        hyp.reason_for_rejection_text = "In round " + str(self.game_state.round) +" the evil players only needed one more failed quest to win the game. Therefore, if any team member was evil, then he or she would have voted 'fail'. However, the quest succeeded, so all team members must have been good."


        if num_no_votes > 0:

            if team.contains_player(self.my_index):

                i_am_good = avalon_logic.good(self.my_name)
                premise = Conjunction(new_quest_result, i_am_good)

            else:
                # The premise of the argument is just the result of the quest.
                premise = new_quest_result

            # Create the conclusion of the argument: a disjuntion of 'evil' predicates. e.g.  evil(0) OR evil(1) OR evil(4)
            evils = [avalon_logic.evil(name) for name in team.get_player_names() if name != self.my_name]
            
            #facts = []
            # for i in range(self.game_state.num_players):
            #     if team.contains_player(i) and i != self.my_index:
            #         fact = avalon_logic.evil(i)
            #         facts.append(fact)
            
            # for name in self.game_state.player_names:
            #     if team.contains_player(name) and name != self.my_name:
            #         fact = avalon_logic.evil(name)
            #         facts.append(fact)

            if len(evils) == 1:
                conclusion = evils[0]
            
            elif len(evils) == num_no_votes:
                conclusion = ProverUtils.conjunct(*evils)
            
            else:
                conclusion = AtLeast(num_no_votes, *evils)
                #conclusion = Disjunction(*facts)

            # Create the argument itself
            implication = Implication(premise, conclusion)

            #self.argument_base.append(implication)

            # Determine which hypotheses can be rejected.
            for hyp in self.hypotheses:

                if not hyp.plausible:
                    continue

                # Count how many agents may vote 'no' according to this hypothesis.
                # That is, the number of agents in the team that are, according to the current hypothesis, evil.
                #num_evil_players_in_team = sum(1 for i in range(self.game_state.num_players) if team.contains_player(i) and is_evil(hyp.role_assignment[i]))
                num_evil_players_in_team = team.count_evil_players(hyp.role_assignment)

                # for i in range(self.game_state.num_players):
                #     if team.contains_player(i) and is_evil(hyp.role_assignment[i]):
                #         num_evil_players_in_team += 1

                # If there are more 'no'-votes than possible according to the hypothesis,
                # Then the hypothesis is false, so we have to reject it.
                if num_no_votes > num_evil_players_in_team:
                    hyp.plausible = False
                    hyp.reason_for_rejection = implication
                    #hyp.reason_for_rejection_text = "In round "+ str(self.game_state.round) + " The quest failed with " + str(num_no_votes) + " votes for 'no', while according to this hypothesis, the team would only have " + str(num_evil_players_in_team) + " evil team members."
                    hyp.reason_for_rejection_text = "In round "+ str(self.game_state.round) + " The team consisting of " + str(team) + " failed the quest with " + str(num_no_votes) + " votes for 'failure'. Therefore, at least " + str(num_no_votes) + " players of that team must be evil"
                    if team.contains_player(self.my_index):
                        hyp.reason_for_rejection_text += " and it's not me"
                    hyp.reason_for_rejection_text += "."

        self.evaluate_players()
        self.calculate_player_scores()           
                    #hyp.rejection_argument = "In round X there were " + str(num_no_votes) + " agents that voted for failure, while according to this hypothesis there were only " + str(max_num_no_votes) + " evil players in the team."
        
   


           
    def evaluate_players(self) -> None:

        """ Checks for which players we can determine whether they are definitely good or definitely bad."""
        
        num_plausible_hypotheses = sum(1 for hyp in self.hypotheses if hyp.plausible)

        # This can happen if it is a fake strategy employed by an evil player, and the evil player has been exposed as evil.
        # Indeed, in that case there is no plausible hypothesis in which this player is good.
        if num_plausible_hypotheses == 0: 
            return
        

        for i in range(self.game_state.num_players):
            
            # Count in how many plausible hypotheses player i is good.
            num_good = sum(1 for hyp in self.hypotheses if hyp.plausible and is_good(hyp.role_assignment[i]))
            
            self.is_certainly_evil[i] = (num_good == 0)
            self.is_certainly_good[i] = (num_good == num_plausible_hypotheses)

        
        for i in range(self.game_state.num_players):

            if not self.is_certainly_evil[i]:
                continue

            # A list to collect all arguments that indicate that this player could be evil.
            reasons_against = set()


            for hyp in self.hypotheses:

                if not hyp.plausible and is_good(hyp.role_assignment[i]):
                    #reasons_against.add(str(hyp.reason_for_rejection))
                    #reasons_against.add(hyp.reason_for_rejection_text)
                    reasons_against.add(hyp.reason_for_rejection)


            evil_fact = avalon_logic.evil(self.game_state.player_names[i])
            key = str(evil_fact)
            if self.generate_arguments and not key in self.argument_base:

                #formulas = list(reasons_against)
                
                string = self.game_state.player_names[i]  + " must be evil."

                formulas = avalon_logic.get_relevant_axioms(self.game_state, self.quest_results, self.team_proposals, self.apply_special_axiom)

                prover = AvalonProver(self.game_state, self.my_name, formulas)
                prover.prove(evil_fact)

                informal_proof = prover.get_informal_proof()
                
                if informal_proof != None:
                    informal_proof = re.sub("player " + str(self.my_index) + " is", "I am", informal_proof)
                    informal_proof = re.sub(self.my_name + " is", "I am", informal_proof)

                    argument = Argument(set(informal_proof), evil_fact)

                    self.argument_base[key] = argument

                    string += " I can support this with the following arguments: " + str(informal_proof)

                self.my_next_utterances.append(string)


    def calculate_player_scores(self):
    # GOOD
       
        """Calculate a *heuristic* score for each player indicating how likely he or she is good.<br>
           These scores will be stored inside the variable self.scores. <br>
        """
        
        self.scores = [0.0]*self.game_state.num_players

        num_plausible_hypotheses = sum(1 for hyp in self.hypotheses if hyp.plausible)

        # This can happen if it is a fake strategy employed by an evil player, and the evil player has been exposed as evil.
        # Indeed, in that case there is no plausible hypothesis in which this player is good.
        if num_plausible_hypotheses == 0: 
            return self.scores
            # if is_evil(self.my_role):
            #     return self.scores
            # else:

            #     print("ERROR: no plausible hypotheses for player " + str(self.my_index))
            #     for hyp in self.hypotheses:
            #         print(str(hyp.role_assignment) + ": " + hyp.rejection_argument)
                
            #     raise Exception("No plausible hypotheses.")

        for i in range(self.game_state.num_players):
            
            num_good = sum(1 for hyp in self.hypotheses if hyp.plausible and is_good(hyp.role_assignment[i]))

            self.scores[i] = num_good / num_plausible_hypotheses

            #The problem with the current system, is that even if a player was contained in a failed quest, this may not be reflected here,
            # if that quest could not rule out any particular hypothesis. In particular, if a failed quest contained 3 players,
            # then any good player who is not in that team would not reject any hypothesis.
            
            # Use the number of times that this player was a team member in a successful quest as a tie-breaker.
            if not self.is_certainly_good[i] and not self.is_certainly_evil[i]:
                num_present_in_successful_quest = sum(1 for quest_result in self.quest_results if quest_result.success and quest_result.team.contains_player(i))
                self.scores[i] += 0.01 * num_present_in_successful_quest
                     
                    
            



    def calculate_team_heurisitic(self, team:Team) -> float:
    # GOOD

        """ Uses a *heuristic* to determine how good this team is. 
            Returns 0 if at least one team member is definitely evil.
            Returns 1 if all team members are definitely good.
            Otherwise, returns the individual score of the player with the lowest score in the team.
        
        """
        
        # Since it's only  a heuristic, good players cannot assume that all other good players would use this same heuristic.


        # Count in how many of the plausible hypotheses the team consists of purely good players.
        num_plausible_hyps_all_good = sum(1 for hyp in self.hypotheses if hyp.plausible and team.count_evil_players(hyp.role_assignment) == 0)
        
        if num_plausible_hyps_all_good == 0:
            return 0.0
        
        # Count how many plausible hypotheses we have left.
        num_plausible_hypotheses = sum(1 for hyp in self.hypotheses if hyp.plausible)

        if num_plausible_hyps_all_good == num_plausible_hypotheses:
            return 1.0


        min_score = 10000
        for i in range(self.game_state.num_players):
            if team.contains_player(i):
                if self.scores[i] < min_score:
                    min_score = self.scores[i]

        return min_score


        # The calculation below is too crude
        # # Count how many plausible hypotheses we have left.
        # num_plausible_hypotheses = sum(1 for hyp in self.hypotheses if hyp.plausible)

        # # Count in how many of those plausible hypotheses the team consists of purely good players.
        # num_plausible_hyps_all_good = sum(1 for hyp in self.hypotheses if hyp.plausible and team.count_evil_players(hyp.role_assignment) == 0)

        # return num_plausible_hyps_all_good / num_plausible_hypotheses





class EvilStrategy(Strategy):

    def __init__(self,game_state:PublicGameState, my_index:int, roles:list[str], fake_strategy:GoodStrategy, apply_special_axiom=True, press=True):
        super().__init__(game_state, my_index, roles, apply_special_axiom, press)

        # Strategy that we will use to pretend that we are a good player.
        self.fake_strategy = fake_strategy


     
    def propose_team(self, team_size:int) -> Team:
    #EVIL


        # 1. Get all teams that a good player might consider.
        possible_teams = self.fake_strategy.get_potential_teams_objectively(team_size, self.my_index)

        if len(possible_teams) == 0:
            
            # print("WARNING! len(possible_teams) == 0. My index: " + str(self.my_index))
            # for hyp in self.fake_strategy.hypotheses:
            #     print(str(hyp.role_assignment) + " " + hyp.reason_for_rejection_text)

            # This happens if I am already exposed as an evil player.
            # Pick a team consisting of myself plus one or two arbitrary good players. 
            team_as_list = [False] * self.game_state.num_players
            team_as_list[self.my_index] = True
            current_size = 1
            counter = 0
            while current_size < team_size:

                if counter >= len(self.roles):
                    print("ERROR: " + str(counter) + " " + str(self.roles))

                if is_good(self.roles[counter]):
                    team_as_list[counter] = True
                    current_size += 1
                counter += 1

            team = Team(self.game_state.player_names, team_as_list)
            possible_teams.append(team)

            

        # 2. Next, if applicable, remove those teams that include another evil player, besides myself.
        if self.apply_special_axiom and not (self.game_state.round == 4 and self.game_state.num_players >= 7):
            
            filtered = [team for team in possible_teams if team.count_evil_players(self.roles) == 1]

            if len(filtered) != 0:
                possible_teams = filtered

        sorted_teams = self.fake_strategy.get_potential_teams_heuristically(possible_teams)
        
        team_to_propose = sorted_teams[0]

        if not team_to_propose.contains_player(self.my_name):
            raise Exception("Team to propose does not contain myself")

        return team_to_propose


        # Pick a team containing yourself and 1 or 2 good players.
            

        # team = [False]*self.game_state.num_players
        # team[self.my_index] = True
        # num_selected_players = 1

        # while num_selected_players < team_size:
        #     r = random.randint(0, self.game_state.num_players-1)
        #     if team[r] == False and self.roles[r] != evil:
        #         team[r] = True
        #         num_selected_players += 1

        # TODO: implement something better?
            # IDEA: choose good players for which it is least obvious that they are good. This way it remains unclear that I am the evil one.
       
      




    def inform_proposed_team(self, game_state:PublicGameState):
    #EVIL

        if utils.VERBOSITY_LEVEL > 0:
            print("Player " + str(self.my_index) + " inform_proposed_team()")
        
        # Update the game state.
        # in a simulation this is not necessary, because the lhs is the same object as the rhs anyway. 
        # However, we do this to simulate the real-world case in which the agent and the game manager run on different machines
        self.game_state = game_state 

        team_proposal = TeamProposal(game_state.round, game_state.attempt, game_state.get_leader_name(), game_state.proposed_team)
        self.fake_strategy.team_proposals.append(team_proposal)

        if not game_state.proposed_team.contains_player(game_state.get_leader_name()):
            max_evil_players_in_team = 1000 # The team leader is playing illogically.

        elif self.game_state.round == 4 and self.game_state.num_players >= 7:
            max_evil_players_in_team = 2

        elif self.apply_special_axiom:
            max_evil_players_in_team = 1

        else:
            max_evil_players_in_team = 1000

        for hyp in self.fake_strategy.hypotheses:

            if is_good(hyp.role_assignment[game_state.leader_index]):
                continue

            if game_state.proposed_team.count_evil_players(hyp.role_assignment) > max_evil_players_in_team:
                hyp.plausible = False

                if max_evil_players_in_team == 1:
                    # we don't need to check whether the special axiom applies, because this is already done above.
                    hyp.reason_for_rejection = avalon_logic.no_second_evil_player(self.game_state.round, self.game_state.get_leader_name(), self.game_state.proposed_team)
                    hyp.reason_for_rejection_text = hyp.reason_for_rejection.description
                
                if max_evil_players_in_team == 2:
                    hyp.reason_for_rejection = avalon_logic.no_third_evil_player(self.game_state.round, self.game_state.get_leader_name(), self.game_state.proposed_team)
                    hyp.reason_for_rejection_text = hyp.reason_for_rejection.description

            
            if hyp.plausible and utils.VERBOSITY_LEVEL > 0:            
                print(self.get_name_and_role() + " " + str(hyp.role_assignment))
        
        self.fake_strategy.evaluate_players()

        objective_decision = self.fake_strategy.get_objective_team_vote_decision(self.game_state.proposed_team)
        
        if objective_decision == None:
            
            if game_state.proposed_team.count_evil_players(self.roles) > 0:
                self.vote_decision = Decision([True],"")
            else:
                self.vote_decision = Decision([False],"")


        else:
            self.vote_decision = objective_decision

        # If there is only one option for a good player, then do the same.
        # Otherwise, count how many evil players the team has, and vote 'yes' if and only if it has at least 1 evil player.
        if len(self.vote_decision.choices) > 1:
                    
            num_evil_players_in_team = utils.count_evil_players(self.game_state.proposed_team, self.roles)
            
            if num_evil_players_in_team > 0:
                self.vote_decision.choices = [True]
            else:
                self.vote_decision.choices = [False]

        
        # make sure that we will express our argument to the other players in the upcoming discussion.
        if len(self.vote_decision.argument) > 0:
            self.my_next_utterances.append(self.vote_decision.argument)


    

    def vote_team(self) -> bool:
    #EVIL

        # If this is the last attempt, then we would still vote 'yes' because we don't want to expose ourselves.
        # In principle, we could vote 'no' if it was the last attempt of the last round, but even then it doesn't really 
        #  make sense to vote 'no' because all the good players are going to vote 'yes' anyway, and since they are the majority
        # the good players will win this vote.

        # TODO: On the other hand, it could make sense to vote 'no' if it is *not* yet the last attempt, and the next leader will be an evil player too.
        # In that case we could avoid a team of only good players being elected, and since the next attempt will be accepted, the final team will 
        #  then contain an evil player.
        # However, this is risky, because if our 'no' vote is not sufficient and the team is accepted anyway, then we will expose ourselves.

        if self.game_state.round == avalon_rules.num_rounds:
            
            attemptsLeft = avalon_rules.num_attempts_per_round - self.game_state.attempt
            

            all_next_leaders_are_evil = True
            for i in range(attemptsLeft):
                
                next_leader = self.game_state.leader_index + 1 + i
                next_leader = next_leader % self.game_state.num_players
                
                if not is_evil(self.roles[next_leader]):
                    all_next_leaders_are_evil = False
                    break
            
            if all_next_leaders_are_evil:
                print(self.get_name_and_role() + " THINKING: This is the last round, there are only " + str(attemptsLeft) + " attempts left, and all next leaders are evil. Therefore I can safely vote 'no'. ")
                return False

        

        return random.choice(self.vote_decision.choices)





        






    def vote_team_OLD(self, proposed_team:Team) -> bool:
    #EVIL

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

        if proposed_team.size == self.game_state.num_good_players and not proposed_team.contains_player(self.my_index):
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
        num_evil_players_in_team = utils.count_evil_players(proposed_team, self.roles)
        
        if num_evil_players_in_team > 0:
            print("  " + self.get_name_and_role()  + " I'm voting 'yes', because this team contains an evil player.")
            return True
        else:
            print("  " + self.get_name_and_role()  + " I'm voting 'no', because this team does not contain any evil player.")
            return False

        


       
        
       

    def vote_quest(self, team:Team) -> bool:
    #EVIL

        
        #   Count how many no-votes are required to fail the quest..
        num_required_no_votes = 1
        if self.game_state.round == 4 and self.game_state.num_players >= 7:
            num_required_no_votes = 2

        #   Count how many evil players are in the team (including myself).
        num_evil_players_in_team = team.count_evil_players(self.roles)
        


        # 1. If there are not enough evil players in the team to make the quest fail, then there is no reason to vote for failure.
        if num_evil_players_in_team < num_required_no_votes:
            return True

        #   Count how many failed quests the evil players still need to win the game.
        num_fails_needed = avalon_rules.num_quests_needed_for_victory - self.game_state.num_quests_failed

        # 2. If the evil team only needs one more failed quest to win, then we have no reason not to fail the quest.
        if num_fails_needed == 1:
            return False
        
        
        #   Count how many successes the good team still needs.
        num_successes_needed = 3 - self.game_state.num_quests_succeeded


        # 3. If the good team only needs one more successful quest to win, and we are the only evil player in the team, then we must 
        #     ensure the quest fails.
        if num_successes_needed == 1 and num_evil_players_in_team == 1:
            return False
    

        if num_evil_players_in_team == num_required_no_votes:
            return False


        ## The following code can only be reached if num_evil_players_in_team > num_required_no_votes
        
        # Note that if there are more evil team members than required, then it is better if not all of them vote for a 'fail', 
        # because that would leak too much information to the good players.

        
        if self.apply_special_axiom:
            return random.choice([True, False])

        # the 'special' axiom says that an evil team leader would never include another evil player in the team.
        # However, alternatively, we can assume the unwritten rule that in that case only the team leader votes for 'failure' while the other 
        # evil team members vote for success.


        # If I am the team leader, vote for failure
        if self.game_state.get_leader_name() == self.my_name:
            return False
        
        # If I'm not the team leader, but the team leader is evil, and only one no-vote is needed, then vote for success
        if is_evil(self.game_state.get_leader_name()) and num_required_no_votes == 1:
                return True

        else:
            # This happens if we are not the team leader, but the team leader is evil, and there are two more evil players in the team
            # and we need 2 no-votes.
            return random.choice([True, False])
    

    def receive_quest_result(self, team:Team, num_yes_votes:int, num_no_votes:int, success:bool) -> None:
    #EVIL 
        self.fake_strategy.receive_quest_result(team, num_yes_votes, num_no_votes, success)
        self.my_next_utterances.extend(self.fake_strategy.my_next_utterances)
        self.fake_strategy.my_next_utterances.clear()

    def guess_merlin(self) -> int:
    #EVIL

        guessed_index = self.my_index

        while self.roles[guessed_index] == evil:
            guessed_index = random.randint(0, self.game_state.num_players-1)

        return guessed_index
        
