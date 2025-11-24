


import abc

from team import Team
import utils



class Formula:

    @abc.abstractmethod
    def implies(self, literal) -> bool:
        """Returns True iff the formula is equivalent to an implication that has the given literal as its conclusion."""
        pass
    
    @abc.abstractmethod
    def reshape(self, literal) -> Implication: # type: ignore
        """Returns a new, but equivalent, formula in the shape of an implication that has the given literal as its conclusion."""
        pass

    @abc.abstractmethod
    def __str__(self):
        return "NOT IMPLEMENTED"
    
    def __eq__(self, other):
       return str(self) == str(other)
    
    
    

class Literal(Formula):
    
    def reshape(self, literal):
        if self.__eq__(literal):
            return Implication(verum, literal)
        else:
            raise Exception("can't reshape this formlua")

class Fact(Literal):
    
    
    def __init__(self, predicate:str, *arguments:str):
        self.predicate = predicate
        self.arguments = arguments

    def implies(self, literal) -> bool:
        return self.__eq__(literal)
    


    def __str__(self):
        return self.predicate + utils.get_string("(", " , ", ")", *self.arguments)

    __repr__ = __str__

    ## 'FACTORY' METHODS
    
    @staticmethod
    def quest_result(round_number:int, team:Team, num_no_votes:int) -> 'Fact':
        return Fact("quest_result", str(round_number), str(team), str(num_no_votes))
    
    @staticmethod
    def evil(player_index:int) -> 'Fact':
        return Fact("evil", str(player_index))
    
    @staticmethod
    def good(player_index:int) -> 'Fact':
        return Fact("good", str(player_index))
    
    @staticmethod
    def proposed_team(round:int, proposer:int, team:Team):
        return Fact("proposed_team", str(round), str(proposer), str(team))

class Negation(Literal):
    
    def __init__(self, negated:Fact):
        self.negated = negated
    
    def __str__(self):
        return "!" + str(self.negated)
    
    __repr__ = __str__

class Conjunction(Formula):

    

    def __init__(self, *conjuncts:Formula):
        self.conjuncts = conjuncts

    def implies(self, literal):
        
        for conjunct in self.conjuncts:
            if conjunct.implies(literal):
                return True
        
        return False
    
    def reshape(self, literal):

        new_premise:list[Formula] = []
        
        for conjunct in self.conjuncts:
            if conjunct.implies(literal):
                reshaped = conjunct.reshape(literal)
                new_premise.append(reshaped.premise)
        
        implication = Implication(Disjunction(*new_premise), literal)

        return implication

    def __str__(self):
        return utils.get_string("", " AND ", "", *self.conjuncts)

    __repr__ = __str__

class Disjunction(Formula):

    

    def __init__(self, *disjuncts:Formula):
        self.disjuncts = disjuncts

    def implies(self, literal):
        
        for disjunct in self.disjuncts:
            if disjunct.implies(literal):
                return True
        
        return False
    
    def reshape(self, literal):

        # a V b V (c--> d) V (e-->d)  becomes:  !a ^ !b ^ (c V e) --> d

        premise_conjucts:list[Formula] = []
        premise_disjuncts:list[Formula] = []
        
        for disjunct in self.disjuncts:
            if disjunct.implies(literal):
            
                reshaped = disjunct.reshape(literal)
                premise_disjuncts.append(reshaped.premise)

            else:
                premise_conjucts.append(negate(disjunct))
        
        disjunction = Disjunction(*premise_disjuncts)
        premise_conjucts.append(disjunction)

        premise = Conjunction(*premise_conjucts)

        implication = Implication(premise, literal)

        return implication

    def __str__(self):
        return utils.get_string("", " OR ", "", *self.disjuncts)
    
    __repr__ = __str__



class Implication(Formula):

    def __init__(self, premise:Formula, conclusion:Formula):
        self.premise = premise
        self.conclusion = conclusion

    # a --> b   equals equals !a V b.
    # so !(a --> b) equals !(!a V b) which equals a ^ !b


    def implies(self, literal):
        
        if self.conclusion.implies(literal):
            return True
        
        elif self.premise.implies(literal.negate()):
            return True
        
        else:
            return False

    def reshape(self, literal):
        
        if self.conclusion.implies(literal):

            new_conjuncts = [self.premise]

            reshaped = self.conclusion.reshape(literal)
            if type(reshaped) == Implication.__class__:
                new_conjuncts.append(reshaped.premise)
           
            if len(new_conjuncts) == 1:
                return Implication(new_conjuncts[0], literal)
            else:
                return Implication(Conjunction(*new_conjuncts), literal)

            
        
        elif self.premise.implies(literal.negate()):
            # suppose the literal to prove is 'a'
            # (!a --> b)  equals a V b which becomes:  !b --> a 

            # ( (x--> !a) --> b)  becomes:  !b --> !(x--> !a)

            #TODO: finish this!

            reshaped = reshape(self.conclusion)
            new_conjuncts.append(reshaped.premise)

            return Implication(negate(self.conclusion), literal)
        
        else:
            return False

    def __str__(self):

        string = str(self.premise)
        string += " ==> "

        string += str(self.conclusion)


        return string
    
    __repr__ = __str__

    def __eq__(self, other):
       return str(self) == str(other)


class ProverUtils:

    def negate(formula:'Formula') -> Formula:
        
        if isinstance(formula, Fact):
            return Negation(formula)
        
        elif isinstance(formula, Negation):
            return formula.negated
        
        elif isinstance(formula, Conjunction):

            new_disjuncts = []
            for con in formula.conjuncts:
                new_disjuncts.append(negate(con))

            return disjunct(*new_disjuncts)
        
        elif isinstance(formula, Disjunction):
            
            new_conjuncts = []
            for disjunct in formula.disjuncts:
                new_conjuncts.append(negate(disjunct))

            return conjunct(*new_conjuncts)
        
        elif isinstance(formula, Implication):
            # a-> b   equals !a V b  so we should return a ^ !b
            return conjunct(formula.premise, negate(formula.conclusion))

        else:
            raise Exception("unhandled type: " + str(type(formula)))


    def conjunct(*formulas):

        new_conjuncts:list[Formula] = []

        for formula in formulas:

            if formula == falsum:
                return falsum
            elif isinstance(formula, Literal):
                new_conjuncts.append(formula)
            elif isinstance(formula, Conjunction):
                new_conjuncts.extend(formula.conjuncts)
            elif isinstance(formula, Disjunction):
                new_conjuncts.append(formula)
            elif isinstance(formula, Implication):
                # a ^ (b-->c)
                new_conjuncts.append(formula)
            else:
                raise Exception("unhandled type: " + str(type(formula)))

        return Conjunction(*new_conjuncts)




    def disjunct(*formulas):

        new_disjuncts:list[Formula] = []

        for formula in formulas:
            if formula == verum:
                return verum
            elif isinstance(formula, Literal):
                new_disjuncts.append(formula)
            elif isinstance(formula, Conjunction):
                new_disjuncts.append(formula)
            elif isinstance(formula, Disjunction):
                new_disjuncts.extend(formula.disjuncts)
            elif isinstance(formula, Implication):
                # a V b V c V (d-->e)   equals a V b V c V (!d V e) which equals a V b V c V !d V e
                new_disjuncts.append(negate(formula.premise))
                new_disjuncts.append(formula.conclusion)
            else:
                raise Exception("unhandled type: " + str(type(formula)))

        return Disjunction(*new_disjuncts)


    verum = Conjunction()   # The empty conjunction. Is always true.
    falsum = Disjunction()  # The empty disjunction. Is always false.
