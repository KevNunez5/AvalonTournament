
from .roles import *
from .team import Team

def count_evil_players(team, roles):
    
    num_evil_players_in_team = 0

    for i in range(len(roles)):
        if team[i] and is_evil(roles[i]):
            #print("is evil team member: " + str(i))
            num_evil_players_in_team += 1

    return num_evil_players_in_team


def get_team_string(team:list[bool], roles:list[str]) -> str:

    team_string = "{"

    for i in range(len(team)):

        if team[i]:

            team_string += " Player " + str(i)
            team_string += "("
            team_string += roles[i]
            team_string += ") ,"

    # Remove the last comma.
    team_string = team_string[:-1]

    team_string += "}"
    return team_string


def arg_max(list_of_numbers:list[float]) -> int:
    
    index_of_highest_val = 0
    for i in range(1, len(list_of_numbers)):
        if list_of_numbers[i] > list_of_numbers[index_of_highest_val]:
            index_of_highest_val = i

    return index_of_highest_val


# def get_all_teams(num_players:int, required_team_size:int, included_player:int) -> list[Team]:

#     ini

#     open_list = []
#     open_list.append(Team([included_player]))

#     while len(open_list) > 0:
        
#         partial_team = open_list.pop()


#         if len(partial) < included_player:

#             if team_size < required_team_size

#         elif len(partial) == included_player:

#         else:


#         if team_size == required_team_size:


#         copy1 = partial.copy()
#         copy1.append(True)
#         open_list.append(copy1)

#         if len(partial) != included_player:
#             copy2 = partial.copy()
#             copy2.append(False)
#             open_list.append(copy2)