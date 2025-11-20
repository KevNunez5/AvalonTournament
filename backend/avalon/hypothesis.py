from .Argumentation.argument import Argument
from .Argumentation.logic import Formula


class Hypothesis:

    def __init__(self, role_assignment:list[str]):
        self.role_assignment = role_assignment.copy()

        # Should be set to false as soon as we know that this hypothesis cannot be true.
        self.plausible = True
        
        # Once we know that this hypothesis cannot be true, we can use this variable to store the argument why this hypothesis should be rejected.
        self.reason_for_rejection:Formula|None = None

        self.reason_for_rejection_text = ""

    def __str__(self):
        return str(self.role_assignment)

