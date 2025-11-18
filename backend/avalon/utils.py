
from game_state import PublicGameState
from roles import *
from team import Team


VERBOSITY_LEVEL = 0

def count_evil_players(team:Team, roles):
    
    num_evil_players_in_team = 0

    for i in range(len(roles)):
        if team.contains_player(i) and is_evil(roles[i]):
            #print("is evil team member: " + str(i))
            num_evil_players_in_team += 1

    return num_evil_players_in_team


def get_team_string(team:list[bool], names:list[str], roles:list[str]) -> str:

    team_string = "{"

    for i in range(len(team)):

        if team[i]:

            #team_string += " Player " + str(i)
            team_string += names[i]
            team_string += " ("
            team_string += roles[i]
            team_string += "), "

    # Remove the last comma.
    team_string = team_string[:-2]

    team_string += "}"
    return team_string

def get_string(start_symbol:str="", separation_symbol:str=",", end_symbol:str="", *components):

        string = start_symbol

        first =True
        for component in components:

            if not first:
                string += separation_symbol

            string += str(component)
            first = False

        string += end_symbol

        return string


def arg_max(list_of_numbers:list[float]) -> int:
    
    index_of_highest_val = 0
    for i in range(1, len(list_of_numbers)):
        if list_of_numbers[i] > list_of_numbers[index_of_highest_val]:
            index_of_highest_val = i

    return index_of_highest_val

def get_all_teams(game_state:PublicGameState, required_team_size:int) -> list[Team]:

    """ Returns a list of all possible teams of the given size."""


    # the list to return
    teams:list[Team] = []


    open_list:list[list[bool]] = []
    open_list.append([])

    while len(open_list) > 0:
        
        partial = open_list.pop()

        if len(partial) == game_state.num_players:
        
            teams.append(Team(game_state.player_names, partial))
       
        else:

            current_size = partial.count(True)

            # Count how many players still need to be added to the team.
            still_need_to_add = required_team_size - current_size

            # Count how many players we are still able to add to the team.
            capacity_left = game_state.num_players - len(partial)

            if still_need_to_add < capacity_left:
                copy1 = partial.copy()
                copy1.append(False)
                open_list.append(copy1)
            
            if still_need_to_add > 0:
                copy2 = partial.copy()
                copy2.append(True)
                open_list.append(copy2)

    return teams

def get_all_teams_including(game_state:PublicGameState, required_team_size:int, included_player:int) -> list[Team]:

    """ Returns a list of all possible teams of the given size that include the given player."""

    ## First get all teams *without* that player, with size 1 less than the required size.
    teams = get_all_teams_excluding(game_state, required_team_size-1, included_player)

    # Next, add that player to all teams.
    for team in teams:
        team.add_player(included_player)

    return teams



def get_all_teams_excluding(game_state:PublicGameState, required_team_size:int, excluded_player:int) -> list[Team]:

    """ Returns a list of all possible teams of the given size that exclude the given player."""

    # the list to return
    teams:list[Team] = []


    open_list:list[list[bool]] = []
    open_list.append([])

    while len(open_list) > 0:
        
        partial = open_list.pop()

        if len(partial) == game_state.num_players:
        
            teams.append(Team(game_state.player_names,partial))
        
        elif len(partial) == excluded_player:
            partial.append(False)  
            open_list.append(partial)
        
        else:

            current_size = partial.count(True)

            # Count how many players still need to be added to the team.
            still_need_to_add = required_team_size - current_size

            # Count how many players we are still able to add to the team.
            if(len(partial) > excluded_player):
                capacity_left = game_state.num_players - len(partial)
            else:
                capacity_left = (game_state.num_players - 1) - len(partial)


            if still_need_to_add < capacity_left:
                copy1 = partial.copy()
                copy1.append(False)
                open_list.append(copy1)
            
            if still_need_to_add > 0:
                copy2 = partial.copy()
                copy2.append(True)
                open_list.append(copy2)

    return teams


# teams = get_all_teams_excluding(num_players=5, required_team_size=3, excluded_player=2)
# for team in teams:
#     print(team)