

class Team:

    def __init__(self, as_list:list[bool] = []):
        self.as_list = as_list

        self.size = self.as_list.count(True)
        

    def contains_player(self, player_index:int) -> bool:
        return self.as_list[player_index]
    


class TeamWithScore(Team):

    def __init__(self, as_list:list[bool] = []):
        super().__init__(as_list)


    def set_score(self, score:int) -> None:
        self.score = score
    