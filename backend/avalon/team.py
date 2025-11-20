

from . import roles as Roles


class Team:

    def __init__(self, all_player_names:list[str], as_list:list[bool] = []):
        
        """ Takes as input a list containing the names of *all* players in the game (including those that are not in the team) and a list of booleans, with length equal as the list of players names.
            the list should contain 'True' for each team member, and 'False' for each player that is not in the team.
        """

        self.as_list = as_list.copy()
        self.size = self.as_list.count(True)
        self.all_player_names = all_player_names.copy()
        

    def contains_player(self, player:int|str) -> bool:

        if isinstance(player, int):
            player_index = player
        else:
            player_index = self.all_player_names.index(player)
            
        return self.as_list[player_index]
            
    
    def add_player(self, player_index:int) -> None:
        self.as_list[player_index] = True
        self.size = self.as_list.count(True)

    def count_evil_players(self, player_roles:list[str]):

        """ return the number of evil players in this team, according to the given role assignment."""
        
        count = 0
        for player_index in range(len(player_roles)):
            
            if self.as_list[player_index] and Roles.is_evil(player_roles[player_index]):
                count+=1
        
        return count
    
    def get_player_indices(self) -> list[int]:

        """ Returns a list of integers representing the indices of the players in this team."""

        all_players = []
        for i in range(len(self.as_list)):
            if self.as_list[i]:
                all_players.append(i)

        return all_players
    
    def get_player_names(self) -> list[str]:

        """ Returns the list of names of the players in this team."""

        num_players = len(self.all_player_names)
        return [self.all_player_names[i] for i in range(num_players) if self.as_list[i]]

        # all_players = []
        # for i in range(len(self.as_list)):
        #     if self.as_list[i]:
        #         all_players.append(self.all_player_names[i])

        # return all_players    


    def __str__(self):

        team_string = "{"
        first = True

        for i in range(len(self.as_list)):
            if self.contains_player(i):
                if not first:
                    team_string += ","
                team_string += str(self.all_player_names[i])
                first = False
        team_string += "}"

        return team_string
    
    __repr__ = __str__
    
    def __eq__(self, other):
       
       if other == None:
           return False

       return self.as_list == other.as_list


class TeamWithScore(Team):

    def __init__(self, all_player_names:list[str], as_list:list[bool] = []):
        super().__init__(all_player_names, as_list)


    def set_score(self, score:float) -> None:
        self.score = score
    

    @staticmethod
    def from_team(team:Team, score:float):
        team_with_score = TeamWithScore(team.all_player_names, team.as_list)
        team_with_score.set_score(score)
        return team_with_score