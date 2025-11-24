from collections.abc import Generator
import random

from .agent import Agent

from .game_state import PublicGameState
from .roles import *
from .utils import *


num_players = 5



# def run_simulation():

#     # 1. Create the object storing the public state of the game.
#     public_state = PublicGameState(num_players)

#     #2. Assign roles
#     roles = assign_roles(public_state)
#     print(roles)
    
#     #num_evil_players:int = public_state.role_to_num_players.get(evil)
    
#     #3. Create the players.
#     players:list[Agent] = []
#     for i in range(num_players):
#         players.append(Agent(i, public_state))

#     #4. Reveal the roles to the appropriate players.
#     reveal_roles(players, roles)

#     for round in range(1,public_state.num_rounds+1):
        
#         print("")
#         print("Starting round " + str(round))

#         # Determine the team size for the current round.
#         #TODO: this assumes there are 5 players.
#         if round == 1 or round == 3:
#             team_size = 2
#         else:
#             team_size = 3
       
#         selected_team = team_voting_stage(players, team_size, public_state, roles)
        
#         if len(selected_team) == 0:
#             print("The team vote was unsuccesful!")
#             winning_team = evil
#             break

#         quest_result = quest(players, selected_team)

#         if quest_result:
#             public_state.num_quests_succeeded += 1
#         else:
#             public_state.num_quests_failed += 1

#         print("Number of successful quests: " + str(public_state.num_quests_succeeded))
#         print("Number of failed quests: " + str(public_state.num_quests_failed))


#         if public_state.get_winning_team() != unassigned:
#             break
        
   
#     if public_state.get_winning_team() == unassigned:
#         raise Exception("Something went wrong")
#         # this situation should never happen, because there should be exactly 5 rules, so t

#     # If the good team managed to successfully end 3 quests, then the evil team still has the chance to 
#     # overturn the outcome by trying to expose Merlin.
#     if public_state.get_winning_team() == good:
        
#         print()
#         exposed = expose_merlin(players, public_state, roles)

#         if exposed:
#             print("The evil team has successfully identified Merlin!")
#         else:
#             print("The evil team has failed to identify Merlin!")


#     print("")
#     print("The game has finished! " + public_state.get_winning_team() + " won")        
            

def get_roles(public_state:PublicGameState) -> list[str]:

    """Is called at the beginning of the game. Randomly assigns roles to players
        the given dictonary indicates for each role how many players need to get assigned that role.
    """

    roles = [unassigned] * num_players

    for role, num_players_with_role in public_state.role_to_num_players.items():
        

        num_assigned = 0
        while num_assigned < num_players_with_role:
            
            r:int = random.randint(0, num_players-1)
            
            if roles[r] == unassigned:
                roles[r] = role
                num_assigned += 1
    
    return roles



def assign_roles(roles:list[str]) -> Generator[(int, list[str])]:
    """Ensures that each player knows its own role.
        Furthermore, ensures that the evil players and Merlin know who are the evil players.
    """

    evil_players = [evil if role==evil else unknown for role in roles]

    for i in range(len(roles)):

        revealed_roles = []

        # For each type of role, determine which roles to reveal.
        if roles[i] == evil:
            
            revealed_roles = evil_players.copy()


        elif roles[i] == merlin:
           
            revealed_roles = roles.copy()
                   
        elif roles[i] == good:
            
            revealed_roles = [unknown] * len(roles)
            revealed_roles[i] = good
                    
        else:
            raise Exception("Unknown role: " + roles[i])

        yield i, revealed_roles
    

def team_voting_stage(players : list[Agent], team_size:int, game_state:PublicGameState, roles:list[str]) -> list[bool]:

    """ If a team was selected successfully, returns the list of player indices of the selected team members.
    Otherwise, returns an empty list.
    """



    for attempt in range(1, game_state.num_attempts_per_round+1):

            game_state.attempt = attempt

            print("")
            print("Trying to find a team. Attempt: " + str(attempt))

            votes = [False] * num_players


            # Set the leader for the current attempt.
            leader = players[game_state.leader_index]
           
           # for i in range(num_players):
                #players[i].game_state.set_leader(game_state.leader_index)

            # Discussion phase
            discuss(players, game_state.num_utterances_per_player)


            # when discussion is over, the leader should propose a team.
            proposed_team: list[bool] = leader.strategy.propose_team(team_size)
            print("Player " + str(game_state.leader_index) + " (" + roles[game_state.leader_index] + ") " + "Proposes the following team: " + utils.get_team_string(proposed_team, roles))

            # collect vote from each player.
            print("Voting for team:")
            num_votes_yes = 0
            for i in range(num_players):
                votes[i] = players[i].strategy.vote_team(proposed_team)
                if votes[i]:
                    num_votes_yes += 1
                print("  Player " + str(i) + " (" + roles[i] + ") " + str(votes[i]))

            #A team is accepted if and only if the majority voted in favor. A tie counts as a rejection.
            team_accepted = num_votes_yes > num_players / 2
            print("Team accepted: " + str(team_accepted))

            # make the votes available to each player
            for i in range(num_players):
                players[i].receive_team_votes(proposed_team, votes, team_accepted)

            game_state.leader_index = (game_state.leader_index + 1) % num_players

            if team_accepted:
                 return proposed_team
   
            
    return []


def discuss(players, num_utterances_per_player) -> None:

    for i in range(num_utterances_per_player):
        for j in range(num_players):
            speaker = players[j]
            utterance = speaker.strategy.talk()

            for k in range(num_players):
                if j==k:
                    continue
                listener = players[k]
                listener.strategy.listen(j, utterance)


def quest(players:list[Agent], selected_team:list[bool]) -> bool:

    num_votes_yes = 0
    num_votes_no = 0


    print("")
    print("Quest started!")

    # collect vote from each team member.
    for i in range(len(selected_team)):

        if(not selected_team[i]):
           continue
           
        vote = players[i].strategy.vote_quest(selected_team)
        if vote:
            num_votes_yes += 1
        else:
            num_votes_no += 1

    # The quest fails if and only if at least one player voted against.
    succes = num_votes_no == 0

    print("Votes in favor: " + str(num_votes_yes))
    print("Votes against: " + str(num_votes_no))
    if(succes):
        print("Quest successful!")
    else:
        print("Quest unsuccessful!")

    # make the result available to each player
    for i in range(num_players):
        players[i].strategy.receive_quest_result(selected_team, num_votes_yes, num_votes_no, succes)


    
    return succes


def expose_merlin(players:list[Agent], game_state:PublicGameState, roles:list[str]) -> bool:
    
    # Discussion phase
    discuss(players, game_state.num_utterances_per_player)

    # get the first evil player
    for i in range(num_players):
        if is_evil(roles[i]):
            assassin = players[i]
            break

    
    guessed_merlin_index = assassin.strategy.guess_merlin()

    print("Evil players: We think that player " + str(guessed_merlin_index) + " is Merlin.")

    game_state.merlin_exposed = (roles[guessed_merlin_index] == merlin)
    
    return game_state.merlin_exposed
 
    


if __name__ == "__main__":
    run_simulation()