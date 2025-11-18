
from typing import Literal
from Argumentation.logic import Formula, Literal



class Argument:

    """Represents a set of formulas, together with a final conclusion that should follow logically from the combination of those formulas."""

    def __init__(self, formulas:set[Formula|str], conclusion:Literal):
        self.formulas = formulas.copy()
        self.conclusion = conclusion


