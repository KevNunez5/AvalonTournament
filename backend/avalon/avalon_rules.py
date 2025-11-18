


import roles

# These arrays stores the team sizes for the respective rounds, depending on how many players there are.
five_players  = [-1,2,3,2,3,3]
six_players   = [-1,2,3,4,3,4]
seven_players = [-1,2,3,3,4,4]
eight_players = [-1,3,4,4,5,5]
nine_players  = [-1,3,4,4,5,5]
ten_players   = [-1,3,4,4,5,5]

team_sizes = [[],[],[],[],[], five_players,six_players,seven_players,eight_players,nine_players, ten_players]


num_rounds = 5
num_attempts_per_round = 5
num_quests_needed_for_victory = 3

def get_team_size(current_round:int, num_players:int) -> int:  
    return team_sizes[num_players][current_round]


def get_roles(num_players:int) -> dict[str,int]:

    if num_players == 5:
        return {roles.merlin: 1,  roles.good: 2, roles.evil: 2}
    elif num_players == 6:
        return {roles.merlin: 1,  roles.good: 3, roles.evil: 2}
    elif num_players == 7:
        return {roles.merlin: 1,  roles.good: 3, roles.evil: 3}
    elif num_players == 8:
        return {roles.merlin: 1,  roles.good: 4, roles.evil: 3}
    elif num_players == 9:
        return {roles.merlin: 1,  roles.good: 5, roles.evil: 3}
    elif num_players == 10:
        return {roles.merlin: 1,  roles.good: 5, roles.evil: 4}
    else:
        raise Exception("Number of players not supported: " + str(num_players))
    

def get_num_required_no_votes(current_round:int, num_players:int):
    
    """Returns the number of agents that need to vote for failure, in order for a quest to fail.<br>
        Specifically, returns 2 if it's the 4th round and there are 7 or more players. <br>
        Returns 1 in all other cases.
    """

    if current_round == 4 and num_players >= 7:
        return 2
    else:
        return 1
    


def quest_succeeded(current_round:int, num_players:int, num_no_votes:int):

    """
     In general, returns 'True' if there are exactly 0 no-votes, and returns 'False' if there is at least one no-vote. <br>
     Except in the 4th round, if there are 7 or more players. In that case the quest succeeds if there is at most 1 no-vote and
     fails if there is more than 1 no-vote.
    """

    return num_no_votes < get_num_required_no_votes(current_round, num_players)
