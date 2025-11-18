
from team import Team


class TeamProposal:

    def __init__(self, round:int, attempt:int, proposer_name:str, team:Team):
        self.round = round
        self.attempt = attempt
        self.proposer_name = proposer_name
        self.team = team