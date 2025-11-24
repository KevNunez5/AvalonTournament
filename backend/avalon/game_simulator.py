

import math
import random
import sys
from .agent import Agent

from typing import Generator

from . import avalon_rules, utils
from .game_state import PublicGameState
from . import roles as Roles
from .team import Team
# import utils



# Choose the total number of players in the game.
#       The number of players will be chosen as a random number between the minimum and the maximum given here.
#       If you want to play a game with a fixed number of players (e.g. 7 players) then just set both the minimum and the maximum equal to that number. 

min_num_players = 5     # should not be lower than 5.
max_mum_players = 10    # should not be higher than 10.
num_players = random.randint(min_num_players, max_mum_players)

player_names = ["Alice", "Bob", "Carol", "Dan", "Eve", "Frank", "Grace", "Heidi", "Ivan", "Judy"]

# The fraction of players that will be using a 'random' strategy.
# For example, if there are 8 players, and this number is set to 0.25, then there will be 8*0.25=2 random agents.
fraction_of_random_players = 0.5 # Can be any number between 0.0 and 1.0.

def run_simulation():

    # 1. Create the object storing the public state of the game.
    public_state = PublicGameState(player_names[:num_players])

    #2. Assign roles
    roles = assign_roles(public_state)
    #roles = [good, good, merlin, evil, evil]
    print(roles)
    
    #num_evil_players:int = public_state.role_to_num_players.get(evil)
    
    #3. Create the players.
    num_random_players = math.ceil(num_players * fraction_of_random_players)
    players:list[Agent] = []
    for i in range(num_players):
        players.append(Agent(i, public_state, press=False, is_random=(i<num_random_players)))

    #4. Reveal the roles to the appropriate players.
    reveal_roles(players, roles)



    # 5. Now, the game can start!
    for current_round in range(1,avalon_rules.num_rounds+1):

        public_state.round = current_round
        
        print("")
        print("Starting round " + str(current_round))


        # 5a. Let the players select a team.

            # Determine the team size for the current round.
        public_state.team_size = avalon_rules.get_team_size(current_round, num_players)


        for player in players:
            player.strategy.on_new_round(public_state)

        selected_team = team_voting_stage(players, public_state, roles)
        
        if selected_team.size == 0:
            print("The team vote was unsuccesful!")
            public_state.team_vote_failed = True
            break

        quest_result = quest(players, public_state, selected_team)

        if quest_result:
            public_state.num_quests_succeeded += 1
        else:
            public_state.num_quests_failed += 1

        print()
        print("Number of successful quests: " + str(public_state.num_quests_succeeded))
        print("Number of failed quests:     " + str(public_state.num_quests_failed))


        if public_state.get_winning_team() != Roles.unassigned:
            break
        
   
    if public_state.get_winning_team() == Roles.unassigned:
        print("Num quests succeeded: " + str(public_state.num_quests_succeeded))
        print("Num quests failed: " + str(public_state.num_quests_failed))
        print("Num quests required for victory: " + str(avalon_rules.num_quests_needed_for_victory))
        raise Exception("Something went wrong")
        # this situation should never happen, because there should be exactly 5 rounds

    # If the good team managed to successfully end 3 quests, then the evil team still has the chance to 
    # overturn the outcome by trying to expose Merlin.
    if public_state.get_winning_team() == Roles.good:
        
        print()
        exposed = expose_merlin(players, public_state, roles)

        if exposed:
            print("The evil team has successfully identified Merlin!")
        else:
            print("The evil team has failed to identify Merlin!")


    print("")
    print("The game has finished! " + public_state.get_winning_team() + " won")        
            

def get_roles(public_state:PublicGameState) -> list[str]:

    """Is called at the beginning of the game. Randomly assigns roles to players
        the given dictonary indicates for each role how many players need to get assigned that role.
    """

    roles = [Roles.unassigned] * public_state.num_players

    for role, num_players_with_role in public_state.role_to_num_players.items():
        

        num_assigned = 0
        while num_assigned < num_players_with_role:
            
            r:int = random.randint(0, public_state.num_players-1)
            
            if roles[r] == Roles.unassigned:
                roles[r] = role
                num_assigned += 1
    
    return roles



def assign_roles(public_state:PublicGameState, roles:list[str]) -> Generator[(int,list[str])]:
    """Ensures that each player knows its own role.
        Furthermore, ensures that the evil players and Merlin know who the evil players are.
    """

    for i in range(public_state.num_players):

        revealed_roles = []

        # For each type of role, determine which roles to reveal.
        if roles[i] == Roles.evil:
            
            revealed_roles = [Roles.evil if role==Roles.evil else Roles.good for role in roles]


        elif roles[i] == Roles.merlin:
           
            revealed_roles = roles.copy()
                   
        elif roles[i] == Roles.good:
            
            revealed_roles = [Roles.unknown] * public_state.num_players
            revealed_roles[i] = Roles.good
                    
        else:
            raise Exception("Unknown role: " + roles[i])

        yield i, revealed_roles

# def assign_roles(public_state:PublicGameState) -> list[str]:

#     """Is called at the beginning of the game. Randomly assigns roles to players.
#         The dictonary 'role_to_num_players' indicates for each role how many players need to get assigned that role.
#     """

#     roles = [unassigned] * num_players

#     for role, num_players_with_role in public_state.role_to_num_players.items():
        

#         num_assigned = 0
#         while num_assigned < num_players_with_role:
            
#             r:int = random.randint(0, num_players-1)
            
#             if roles[r] == unassigned:
#                 roles[r] = role
#                 num_assigned += 1
    
#     return roles



def reveal_roles(players:list[Agent], roles:list[str]):

    """Ensures that each player knows its own role.
        Furthermore, ensures that the evil players and Merlin know who the evil players are.
    """

    

    for i in range(len(players)):

        revealed_roles = []

        # For each type of role, determine which roles to reveal.
        if roles[i] == Roles.evil:
            
            revealed_roles = [Roles.evil if role==Roles.evil else Roles.good for role in roles]


        elif roles[i] == Roles.merlin:
           
            revealed_roles = Roles.copy()
                   
        elif roles[i] == Roles.good:
            
            revealed_roles = [Roles.unknown] * len(players)
            revealed_roles[i] = Roles.good
                    
        else:
            raise Exception("Unknown role: " + roles[i])


        players[i].reveal_roles(revealed_roles)

    

def team_voting_stage(players : list[Agent], game_state:PublicGameState, roles:list[str]) -> Team:

    """ If a team was selected successfully, returns the chosen team.
    Otherwise, returns an empty Team.
    """

    longest_name_length = max([len(name) for name in game_state.player_names])
    column_width = longest_name_length + len("(Merlin)") + 2

    for attempt in range(1, avalon_rules.num_attempts_per_round+1):

            game_state.attempt = attempt

            print("")
            print("Trying to find a team. Attempt: " + str(attempt))

            votes = [False] * num_players


            # Set the leader for the current attempt.
            leader = players[game_state.leader_index]

            #TODO: inform all players that a new attempt is starting, with the given leader.
           
            # Discussion phase
            discuss_before_team_proposal(players, game_state)

            # when discussion is over, the leader should propose a team.
            print()
            print("# LEADER PROPOSING A TEAM (round " + str(game_state.round) + ", attempt " + str(game_state.attempt) + "):")
            game_state.proposed_team = leader.strategy.propose_team(game_state.team_size)
            print(leader.my_name + " (" + roles[game_state.leader_index] + ") " + "Proposes the following team: " + utils.get_team_string(game_state.proposed_team.as_list, game_state.player_names, roles))

            #Inform all players of the proposed team.
            for i in range(num_players):
                players[i].strategy.inform_proposed_team(game_state)

            # Discussion phase
            discuss_before_team_vote(players, game_state)

            # collect vote from each player.
            print()
            print("# VOTING FOR TEAM (round " + str(game_state.round) + ", attempt " + str(game_state.attempt) + "):" )
            num_votes_yes = 0
            for i in range(num_players):
                votes[i] = players[i].strategy.vote_team()
                if votes[i]:
                    num_votes_yes += 1

                print(players[i].strategy.get_name_and_role().ljust(column_width) + ("yes" if votes[i] else "no"))


            #A team is accepted if and only if the majority voted in favor. A tie counts as a rejection.
            team_accepted = num_votes_yes > num_players / 2
            print("Team accepted: " + str(team_accepted))

            # make the votes available to each player
            #for i in range(num_players):
            #    players[i].receive_team_votes(game_state.proposed_team, votes, team_accepted)

            game_state.leader_index = (game_state.leader_index + 1) % num_players

            if team_accepted:
                 return game_state.proposed_team
   
            
    return Team(game_state.player_names)


def discuss_before_team_proposal(players:list[Agent], game_state) -> None:
    print()
    print("# DISCUSSION PHASE (round " + str(game_state.round) + ", attempt " + str(game_state.attempt) + ")")

    conversation = []

    # the index of the player who is next to talk.
    speaker_index = 0

    # counts how many consecutive players have been silent. Once all players are silent, the discussion ends.
    count_silences = 0


    longest_name_length = max([len(name) for name in game_state.player_names])
    column_width = longest_name_length + len("(Merlin)") + 2

    
    while(True):
    
        speaker = players[speaker_index]
        utterance = speaker.strategy.discuss_before_team_proposal(conversation)
        
        if len(utterance) == 0:
            count_silences += 1
        else:
            count_silences = 0
            print()
            print(speaker.strategy.get_name_and_role().ljust(column_width) + utterance)
            
        conversation.append(utterance)
        
        if count_silences == num_players:
            break

        speaker_index += 1
        speaker_index = speaker_index % num_players

def discuss_before_team_vote(players:list[Agent], game_state) -> None:

    print()
    print("# DISCUSSION PHASE (round " + str(game_state.round) + ", attempt " + str(game_state.attempt) + ")")

    conversation = []

    # the index of the player who is next to talk.
    speaker_index = 0

    # counts how many consecutive players have been silent. Once all players are silent, the discussion ends.
    count_silences = 0

    longest_name_length = max([len(name) for name in game_state.player_names])
    column_width = longest_name_length + len("(Merlin)") + 2
    
    while(True):
    
        speaker = players[speaker_index]
        utterance = speaker.strategy.discuss_proposed_team(conversation)
        
        if len(utterance) == 0:
            count_silences += 1
        else:
            count_silences = 0
            print(speaker.strategy.get_name_and_role().ljust(column_width) + utterance)
            
        conversation.append(utterance)
        
        if count_silences == num_players:
            break

        speaker_index += 1
        speaker_index = speaker_index % num_players




def quest(players:list[Agent], game_state:PublicGameState, selected_team:Team) -> bool:

    num_votes_yes = 0
    num_votes_no = 0


    print("")
    print("# QUEST STARTED! ")

    # 1. collect vote from each team member.
    for i in range(len(players)):

        if(not selected_team.contains_player(i)):
           continue
           
        vote = players[i].strategy.vote_quest(selected_team)
        if vote:
            num_votes_yes += 1
        else:
            num_votes_no += 1

    # 2. Determine whether the quest has failed or succeeded.
    succes = avalon_rules.quest_succeeded(game_state.round, game_state.num_players, num_votes_no)

    print("Votes in favor: " + str(num_votes_yes))
    print("Votes against:  " + str(num_votes_no))
    if(succes):
        print("Quest successful!")
    else:
        print("Quest unsuccessful!")

    # 3. Communicate the result to each player
    for i in range(num_players):
        players[i].strategy.receive_quest_result(selected_team, num_votes_yes, num_votes_no, succes)


    
    return succes


def expose_merlin(players:list[Agent], game_state:PublicGameState, roles:list[str]) -> bool:
    
    # Discussion phase
    discuss_before_merlin_vote()

    # get the first evil player
    for i in range(num_players):
        if Roles.is_evil(roles[i]):
            assassin = players[i]
            break

    
    guessed_merlin_index = assassin.strategy.guess_merlin()

    print("Evil players: We think that player " + str(guessed_merlin_index) + " is Merlin.")

    game_state.merlin_exposed = (roles[guessed_merlin_index] == Roles.merlin)
    
    return game_state.merlin_exposed
 

def discuss_before_merlin_vote():
    pass


if __name__ == "__main__":

    if len(sys.argv) >= 3 and sys.argv[1] == "-v":
        utils.VERBOSITY_LEVEL = int(sys.argv[2])
    

    run_simulation()