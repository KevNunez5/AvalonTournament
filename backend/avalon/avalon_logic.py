



    

import typing
from .Argumentation.logic import AtLeast, Fact, Formula, Implication, Literal, ProverUtils
from .Argumentation.prover import Prover
from . import avalon_rules
from .game_state import PublicGameState
from .quest_result import QuestResult
from .team import Team
from .team_proposal import TeamProposal



## 'FACTORY' METHODS to create Facts.


@staticmethod
def evil(player_name:str) -> Literal:
    #return Fact("evil", str(player_index), informal_description="player " + str(player_index) + " is evil")

    evil_fact = ProverUtils.negate(good(player_name), player_name + " is evil")
    evil_fact = typing.cast(Literal, evil_fact)
    return evil_fact


@staticmethod
def good(player_name:str) -> Fact:
    return Fact("good", player_name, description= player_name + " is good")

@staticmethod
def proposed_team(round:int, proposer:str, team:Team):
    return Fact("proposed_team", str(round), proposer, str(team), description="in round " + str(round) + " " + proposer + " proposed the team " + str(team))


@staticmethod
def quest_result(round_number:int, team:Team, num_no_votes:int) -> 'Fact':

    if num_no_votes == 0:
        description = "in round " + str(round_number) + " the quest with team " + str(team) + " succeeded"
    elif num_no_votes == 1:
        description = "in round " + str(round_number) + " the quest with team " + str(team) + " failed with 1 vote against" 
    else:
        description = "in round " + str(round_number) + " the quest with team " + str(team) + " failed with " + str(num_no_votes) + " votes against" 

    return Fact("quest_result", str(round_number), str(team), str(num_no_votes), description=description)

@staticmethod
def num_failed_quests(round_number:int, num_failures:int):

    description = "of the first " + str(round_number) + " quests, " + str(num_failures) + " quests have failed"
    return Fact("failed_quests", str(round_number), str(num_failures), description=description)

@staticmethod
def contains_evil_player(team:Team):
    return Fact("contains_evil_player", *team.get_player_names(),  description="The team " + str(team) + " contains at least one evil player.")





############# AXIOMS.


# Axiom 0:
# This axiom is not really an axiom. It's merely a definition of the literal 'contains_evil_player(team)'
# It says that if one of the team members is evil, then the predicate contains_evil_player(team) is true.
@staticmethod
def implies_contains_evil_player(team:Team):

    facts = [evil(name) for name in team.get_player_names()]
    premise = AtLeast(1, *facts) # Alternatively we could use a disjunction here.
    
    conclusion = contains_evil_player(team)

    return Implication(premise, conclusion)




# Axiom 1: evil(i) <--> !good(i). We don't need this axiom, because instead we will just never use the predicate 'evil' and instead always use !good




# The following two axioms are axioms 2 and 3:

@staticmethod
def num_good_players(num_good_players:int, player_names:list[str]):

    """There are at least m good players, or equivalently, there are at most n-m evil players."""

    #facts = [good(i) for i in range(0,num_players)]
    facts = [good(name) for name in player_names]

    num_evil_players = len(player_names) - num_good_players

    return AtLeast(num_good_players, *facts, description="there are " + str(num_good_players) + " good players and " + str(num_evil_players) + " evil players")

@staticmethod
def num_evil_players(num_good_players:int, player_names:list[str]):

    """There are at least m evil players, or equivalently, there are at most n-m good players."""

    #facts = [evil(i) for i in range(0,num_players)]
    facts = [evil(name) for name in player_names]

    num_evil_players = len(player_names) - num_good_players

    return AtLeast(num_evil_players, *facts, description = "there are " + str(num_good_players) + " good players and " + str(num_evil_players) + " evil players")


def quest_involved_evil_player(round_number:int, team:Team, num_no_votes:int):

    """ Represents the axiom that if one or more players in a quest voted for failure, then at least that number of the team members must have been evil.
        This axiom only needs to be taken into account if there was at least one 'no' vote.
        However, note that this does *not* mean that it only applies to *failed* quests, because in some cases there are at least 2 'no' votes required for failure.
    """
    if num_no_votes == 0:
        raise Exception("num_no_votes should be greater than 0.")

    premise = quest_result(round_number, team, num_no_votes)

    evils = [evil(name) for name in team.get_player_names()]
        
    conclusion = AtLeast(num_no_votes, *evils)

    description = "only evil players can vote for a quest to fail"
    # description = "the quest in round " + str(round_number) + " with team " + str(team) + " failed with " + str(num_no_votes) + " against, so this team must contain at least " + str(num_no_votes) + " evil player"
    # if num_no_votes > 1:
    #     description += "s" # player --> players

    return Implication(premise, conclusion, description=description)

def success_after_two_failed_quests(quest:QuestResult) -> Implication:

    """
     If a quest succeeds after already two earlier quests have failed, then all team members that voted for success must have been good.
     Therefore, the number of evil team members must be exactly equal to the number of 'no' votes.
        (in general, *all* team members would be good, except in the case that there are 7 or more players and we are in the 4th round, in which 
         case there could be one evil player voting 'no', while the quest still succeeds)
    """

    if not quest.success:
        raise Exception("Error the given quest did not succeed.")

    
    # 1. Create the premise of this axiom.

        # 1a. Fact representing that in round n, two earlier quests have failed.
    nfq = num_failed_quests(quest.round,  avalon_rules.num_quests_needed_for_victory-1) 
    
        # 1b. Fact representing the current quest result.
    qr = quest_result(quest.round, quest.team, quest.num_votes_against) 
    
        # 1c. The premise is the conjunction of these two facts.
    premise = ProverUtils.conjunct(nfq , qr)


    # 2. Create the conclusion of this axiom.

    conjuncts = [good(name) for name in quest.team.get_player_names()]
    
    if quest.num_votes_against == 0:

        conclusion = ProverUtils.conjunct(*conjuncts)
    
    else:
        # Let m be the number of no-votes. 
        # Then there were at most m evil players 
        #   (actually, we know there were *exactly* m evil players, but we already have another axiom saying that there were *at least* m evil players)
        # That is, there were at least n-m good players.
        conclusion = AtLeast(quest.team.size - quest.num_votes_against, *conjuncts)


    description = "If the evil players only need one more failed quest to win the game, then the evil players no longer have any incentive to vote for a quest to succeed."
    return Implication(premise, conclusion, description=description)



## Axioms 9 and 10:

@staticmethod
def no_second_evil_player(round:int, leader_name:str, team:Team) -> Implication:
    
    """
        Represents the axiom that an evil player would never propose a team containing another evil player.
    
        proposed_team(R,X,{X,Y}) ==> good(X) OR good(Y)
        If, in round R, player X proposed the team {X,Y}, then at least one of the two players must be good.
    
        proposed_team(R,X,{X,Y,Z}) ==> good(X) OR  ( good(Y) AND good(Z))

    """

    if not team.contains_player(leader_name):
        raise Exception("Error: leader is not a member of the proposed team: " + str(team) + " Leader: " + leader_name)

    # Construct the premise
    premise = proposed_team(round, leader_name, team)

     # Construct the conclusion
    good_X = good(leader_name)
        
    all_other_team_members_are_good = [good(name) for name in team.get_player_names() if name != leader_name]

    if len(all_other_team_members_are_good) == 1:
        conclusion = ProverUtils.disjunct(good_X, all_other_team_members_are_good[0])
    elif len(all_other_team_members_are_good) > 1:
        conclusion = ProverUtils.disjunct(good_X, ProverUtils.conjunct(*all_other_team_members_are_good))

    implication = Implication(premise, conclusion, description="an evil player would never propose a team with another evil player")

    return implication


@staticmethod
def no_third_evil_player(current_round:int, leader_name:str, team:Team) -> Implication:

    """In round 4, when there are 7 or more players, a quest needs 2 'no' votes in order to fail.
        Therefore, in that case an evil player would never propose a team with more than 1 other evil player.

        proposed_team(R,X,{X,Y,Z}) ==> good(X) OR  AtLeast(1, good(Y), good(Z))
        proposed_team(R,X,{X,Y,Z,V}) ==> good(X) OR  AtLeast(2, good(Y), good(Z), good(V))
        proposed_team(R,X,{X,Y,Z,V,W}) ==> good(X) OR  AtLeast(3, good(Y), good(Z), good(V), good(W))
    """

    if current_round != 4:
        raise Exception("This axiom only applies to round 4. Given round: " + str(current_round))

    if not team.contains_player(leader_name):
        raise Exception("Error: leader_index is not a member of the proposed team: " + str(team))
    
    # 1. Construct the premise
    premise = proposed_team(current_round, leader_name, team)

    # 2. Construct the conclusion
    
        # 2a. either the team leader is good...
    leader_is_good = good(leader_name)
    
        # 2b.  or at most 1 of the other team members is evil,
        #      which is equivalent to sayting that at least n-2 of the other team members are good (where n is the size of the team)
    other_team_members_are_good = [good(name) for name in team.get_player_names() if name != leader_name]
    at_least = AtLeast(team.size - 2, *other_team_members_are_good)
    
        # 2c.
    conclusion = ProverUtils.disjunct(leader_is_good, at_least)

    # 3. Combine the premise and the conclusion into an implication.
    return Implication(premise, conclusion, description="in round 4 an evil player would never propose a team with more than one other evil player")


@staticmethod
def get_relevant_axioms(game_state:PublicGameState, quest_results:list[QuestResult], team_proposals:list[TeamProposal], apply_special_axiom:bool) -> list[Formula]: 
    axioms = []

    ###
    axioms.append(num_good_players(game_state.num_good_players, game_state.player_names))

    ###
    axioms.append(num_evil_players(game_state.num_good_players, game_state.player_names))

    ### If in a quest n agents voted 'no', then at least n of the team members must be evil.
    quests_with_votes_against = [qr for qr in quest_results if qr.num_votes_against > 0]
    for quest in quests_with_votes_against:
        axioms.append(quest_involved_evil_player(quest.round, quest.team, quest.num_votes_against))
        axioms.append(quest_result(quest.round, quest.team, quest.num_votes_against))

    ### If a quest succeeds, after already two quests have failed, then all team members that voted for success must have been good.
    #   So, if n agents voted 'no', then at most n of the team members can be evil.
    #     (in general n would be 0, except in the 4th round when there are 7 or more players, in which case n can be 1.)
    failed_quests = [qr for qr in quest_results if not qr.success]
    if len(failed_quests) == avalon_rules.num_quests_needed_for_victory - 1:
        
        round_of_last_failed_quest = max(qr.round for qr in failed_quests)

        quests_after = [qr for qr in quest_results if qr.round > round_of_last_failed_quest]
            
        for quest in quests_after:
            
            # add the axiom itself.
            axioms.append(success_after_two_failed_quests(quest)) 
            
            # add the premises of the axiom.
            axioms.append(quest_result(quest.round, quest.team, quest.num_votes_against))
            axioms.append(num_failed_quests(quest.round, avalon_rules.num_quests_needed_for_victory - 1)) 


    ### An evil player would never propose a team with another evil player.
    for prop in team_proposals:

        premise = proposed_team(prop.round, prop.proposer_name, prop.team)

        if prop.round == 4 and game_state.num_players >= 7:
            axioms.append(no_third_evil_player(prop.round, prop.proposer_name, prop.team))
            axioms.append(premise)

        elif apply_special_axiom:
            axioms.append(no_second_evil_player(prop.round, prop.proposer_name, prop.team))
            axioms.append(premise)

    return axioms



class AvalonProver(Prover):
    
    def __init__(self, game_state:PublicGameState, my_name:str, formulas:list[Formula]):
        
        formulas_copy = formulas.copy()

        ngp = num_good_players(game_state.num_good_players, game_state.player_names)
        nep = num_evil_players(game_state.num_good_players, game_state.player_names)
        i_am_good = good(my_name)

        if not ngp in formulas:
            formulas_copy.append(ngp)

        if not nep in formulas:
            formulas_copy.append(nep)

        if not i_am_good in formulas:
            formulas_copy.append(i_am_good)

        super().__init__(formulas_copy, game_state.player_names) 
        