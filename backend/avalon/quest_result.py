from .team import Team


class QuestResult:

    def __init__(self, round:int, team:Team, num_votes_against:int):
        self.round = round
        self.team = team
        self.num_votes_against = num_votes_against

        self.success = (num_votes_against == 0)