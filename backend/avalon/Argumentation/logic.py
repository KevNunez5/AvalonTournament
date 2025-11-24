import abc
import typing
from .. import utils



class Formula:

    description = ""
    
    @abc.abstractmethod
    def reshape(self, literal) -> 'Implication|None': 
        """Returns a new, but equivalent, formula in the shape of an implication that has the given literal as its conclusion.
            Returns 'None' if that's impossible.
        """
        pass

    @abc.abstractmethod
    def __str__(self):
        return "NOT IMPLEMENTED"
    
    __repr__ = __str__

    def __eq__(self, other):
       return str(self) == str(other)
    
    def __hash__(self):
        return hash(str(self))
    

class Literal(Formula):
    
    def reshape(self, literal):
        if self.__eq__(literal):
            return Implication(ProverUtils.verum, literal, self.description)
        else:
            return None
        
    # def implies(self, literal) -> bool:
    #     return self.__eq__(literal)

class Fact(Literal):
    
    
    def __init__(self, predicate:str, *arguments:str, description:str=""):
        self.predicate = predicate
        self.arguments = arguments
        self.description = description

    def __str__(self):

        if len(self.arguments) == 0:
            return self.predicate
        else:
            return self.predicate + utils.get_string("(", " , ", ")", *self.arguments)

    __repr__ = __str__


   

class Negation(Literal):

    """ Note that this class only represents negations of facts. 
        It does not represnt the negation of a conjunction or a disjunction.
    """
    
    def __init__(self, negated:Fact, description:str=""):
        self.negated = negated

        if len(description) == 0:
            self.description = "it is not true that " + negated.description
        else:
            self.description = description
    
    def __str__(self):
        return "!" + str(self.negated)
    
    __repr__ = __str__

class Conjunction(Formula):

    

    def __init__(self, *conjuncts:Formula, description=""):
        self.conjuncts = conjuncts

        if len(description) == 0:
            conjunct_strings = [conjunct.description for conjunct in conjuncts]
            self.description = utils.get_string("", " and ", "", *conjunct_strings)
        else:
            self.description = description

    # def implies(self, literal):
        
    #     for conjunct in self.conjuncts:
    #         if conjunct.implies(literal):
    #             return True
        
    #     return False
    
    def reshape(self, literal):

        new_premise:list[Formula] = []
        
        # e.g   the formula is:   (a -> e) ^ c ^ (d -> e) ^ f  
        #       and we're tyring to prove 'e', 
        #       then this  becomes:     (a v d) -> e

        for conjunct in self.conjuncts:

            reshaped = conjunct.reshape(literal)
            if reshaped != None:
                new_premise.append(reshaped.premise)
        
        if len(new_premise) == 0:
            return None

        implication = Implication(ProverUtils.disjunct(*new_premise), literal, self.description)

        return implication

    def __str__(self):
        
        if len(self.conjuncts) == 0:
            return "TRUE"

        return utils.get_string("", " AND ", "", *self.conjuncts)

    __repr__ = __str__

class Disjunction(Formula):

    

    def __init__(self, *disjuncts:Formula, description=""):
        self.disjuncts = disjuncts

        if len(description) == 0:
            disjunct_strings = [disjunct.description for disjunct in disjuncts]
            self.description = utils.get_string("", " or ", "", *disjunct_strings)
        else:
            self.description = description

    # def implies(self, literal):
        
    #     for disjunct in self.disjuncts:
    #         if disjunct.implies(literal):
    #             return True
        
    #     return False
    
    def reshape(self, literal):

        # a V b V (c--> d) V (e-->d)  becomes:  !a ^ !b ^ (c V e) --> d

        premise_conjucts:list[Formula] = []
        premise_disjuncts:list[Formula] = []
        
        for disjunct in self.disjuncts:

            reshaped = disjunct.reshape(literal)

            if reshaped == None:
                premise_conjucts.append(ProverUtils.negate(disjunct))
            else:
                premise_disjuncts.append(reshaped.premise)
                
        if len(premise_disjuncts) == 0:
            return None 
        
        disjunction = ProverUtils.disjunct(*premise_disjuncts)
        premise_conjucts.append(disjunction)

        premise = ProverUtils.conjunct(*premise_conjucts)

        implication = Implication(premise, literal, self.description)

        return implication

    def __str__(self):

        if len(self.disjuncts) == 0:
            return "FALSE"

        return utils.get_string("", " OR ", "", *self.disjuncts)
    
    __repr__ = __str__



class Implication(Formula):

    def __init__(self, premise:Formula, conclusion:Formula, description:str=""):
        self.premise = premise
        self.conclusion = conclusion

        if len(description) == 0:
            self.description = "if " + premise.description + " then " + conclusion.description
        else:
            self.description = description

    # a --> b   equals equals !a V b.
    # so !(a --> b) equals !(!a V b) which equals a ^ !b


    # def implies(self, literal):
        
    #     if self.conclusion.implies(literal):
    #         return True
        
    #     elif self.premise.implies(ProverUtils.negate(literal)):
    #         return True
        
    #     else:
    #         return False
        
    def to_disjunction(self):
        return ProverUtils.disjunct(ProverUtils.negate(self.premise), self.conclusion, description=self.description)


    def reshape(self, literal):
        as_disjunction = self.to_disjunction()
        reshaped = as_disjunction.reshape(literal)
        return reshaped


    def __str__(self):

        string = str(self.premise)
        string += " ==> "

        string += str(self.conclusion)


        return string
    
    __repr__ = __str__

    # def __eq__(self, other):
    #    return str(self) == str(other)


class AtLeast(Formula):

    def __init__(self, threshold:int, *arguments:Literal, description=""):

        """ Note that this operator can only take literals as its arguments, in order to avoid ambiguities."""

        self.threshold = threshold
        self.arguments = tuple(arguments)

        if len(description) == 0:
            
            self.description = "at least " + str(threshold) + " of the following facts must be true: "

            add_comma = False
            for literal in arguments:

                if add_comma:
                    description += ", "
                add_comma = True

                self.description += literal.description
        
        else:
            self.description = description

            


    # Note that AtLeast(3, p,q,r,s,t) is equivalent to AtMost(5-3, !p, !q, !r, !s, !t)
    
    def reshape(self, literal):

        # AtLeast(2, p, q, r, s, t)    becomes:                   AtMost(2-1, q, r, s, t) --> p
        #                              which is equivalent to:    AtLeast(4-(2-1), !q, !r, !s, !t) --> p  (not that this AtLeast only has 4 arguments.)
        #                              or:                        AtLeast(5-2, !q, !r, !s, !t) --> p

        # In general:
        # AtLeast(m, p, q, r, ... )    becomes:    AtLeast(n-m, !q, !r, ...) --> p
        

        if literal in self.arguments:

            new_threshold = len(self.arguments) - self.threshold

            # Negate all arguments, and put them in a new list, except the literal to prove.
            new_arguments:list[Formula] = [ProverUtils.negate(arg) for arg in self.arguments if arg != literal]

            # Cast all arguments to class Literal.
            new_literals:list[Literal] = [typing.cast(Literal, arg) for arg in new_arguments]

            premise = AtLeast(new_threshold, *new_literals)
            
            return Implication(premise, literal, self.description)
        
        else:

            return None

    def __str__(self):
        return "AtLeast(" + str(self.threshold) + ", " + str(self.arguments) + ")" 

    __repr__ = __str__



class ProverUtils:

    @staticmethod
    def negate(formula, description="") -> 'Formula':
        
        if isinstance(formula, Fact):
            return Negation(formula, description)
        
        elif isinstance(formula, Negation):
            return formula.negated
        
        elif isinstance(formula, Conjunction):

            new_disjuncts = []
            for con in formula.conjuncts:
                new_disjuncts.append(ProverUtils.negate(con))

            return ProverUtils.disjunct(*new_disjuncts, description=description)
        
        elif isinstance(formula, Disjunction):
            
            new_conjuncts = []
            for disjunct in formula.disjuncts:
                new_conjuncts.append(ProverUtils.negate(disjunct))

            return ProverUtils.conjunct(*new_conjuncts, description=description)
        
        elif isinstance(formula, Implication):
            # a-> b   equals !a V b  so we should return a ^ !b
            return ProverUtils.conjunct(formula.premise, ProverUtils.negate(formula.conclusion), description=description)

        elif isinstance(formula, AtLeast):

            # ! AtLeast(m, p,q,r,s,t) is equivalent to  AtMost(m-1, p,q,r,s,t)
            # which is equivalent to AtLeast(n-(m-1), !p, !q, !r, !s, !t)
            #
            # e.g. "It is not true that at least 3 out of 10 players are good"
            # is equivalent to "At most 2 out of 10 players are good."
            # which, in turn, is equivalent to "At least 8 out of 10 players are evil."

            new_arguments = [ProverUtils.negate(arg) for arg in formula.arguments]
            new_arguments = typing.cast(list[Literal], new_arguments)

            new_threshold = len(formula.arguments) - (formula.threshold - 1)

            return AtLeast(new_threshold, *new_arguments, description=description)

            #raise Exception("Negation of operator AtLeast has not been implemented yet.")
        else:
            raise Exception("unhandled type: " + str(type(formula)))

    @staticmethod
    def conjunct(*formulas, description=""):

        """ Creates a conjunction of the given formulas. While this would typically return an object of class Conjunction,
            it may also return any other type of formula, if the given list of formulas contains only one element,
            or it may return 'falsum' if one of the given disjuncts is 'falsum'.
        """

        new_conjuncts = set()

        for formula in formulas:

            if formula == ProverUtils.falsum:
                return ProverUtils.falsum
            elif isinstance(formula, Literal):
                new_conjuncts.add(formula)
            elif isinstance(formula, Conjunction):
                new_conjuncts.update(formula.conjuncts)
            elif isinstance(formula, Disjunction):
                new_conjuncts.add(formula)
            elif isinstance(formula, Implication):
                # a ^ (b-->c)
                new_conjuncts.add(formula)
            elif isinstance(formula, AtLeast):
                new_conjuncts.add(formula)
                #raise Exception("Conjunction with formula of type AtLeast has not been implemented yet.")
            else:
                raise Exception("unhandled type: " + str(type(formula)))


        if len(new_conjuncts) == 1:
            return list(new_conjuncts)[0] 
        # This is to make sure that if we conjunct just one literal, the returned object will be of type Literal, rather than Conjunction.
        

        return Conjunction(*new_conjuncts, description=description)



    @staticmethod
    def disjunct(*formulas, description=""):

        """ Creates a disjunction of the given formulas. While this would typically return an object of class Disjunction,
            it may also return any other type of formula, if the given list of formulas contains only one element,
            or it may return 'verum' if one of the given disjuncts is 'verum'.
        """

        new_disjuncts = set()

        for formula in formulas:
            if formula == ProverUtils.verum:
                return ProverUtils.verum
            elif isinstance(formula, Literal):
                new_disjuncts.add(formula)
            elif isinstance(formula, Conjunction):
                new_disjuncts.add(formula)
            elif isinstance(formula, Disjunction):
                new_disjuncts.update(formula.disjuncts)
            elif isinstance(formula, Implication):
                # a V b V c V (d-->e)   equals a V b V c V (!d V e) which equals a V b V c V !d V e
                new_disjuncts.add(ProverUtils.negate(formula.premise))
                new_disjuncts.add(formula.conclusion)
            elif isinstance(formula, AtLeast):

                if formula.threshold == 1:
                    new_disjuncts.update(formula.arguments)
                else:
                    new_disjuncts.add(formula)

                #raise Exception("Disjunction with formula of type AtLeast has not been implemented yet.")
            else:
                raise Exception("unhandled type: " + str(type(formula)))
            
        if len(new_disjuncts) == 1:
            return list(new_disjuncts)[0] 
        # This is to make sure that if we disjunct just one literal, the returned object will be of type Literal, rather than Disjunction.


        return Disjunction(*new_disjuncts, description=description)


    verum = Conjunction()   # The empty conjunction. Is always true.
    falsum = Disjunction()  # The empty disjunction. Is always false.

    # @staticmethod
    # def get_informal_description(formula:Formula) -> str:
        
    #     if isinstance(formula, Fact):
    #         return formula.informal_description
        
    #     elif isinstance(formula, Negation):
    #         return "it is not true that " + ProverUtils.get_informal_description(formula.negated)
        
    #     elif isinstance(formula, Conjunction):

    #         conjunct_strings = [ProverUtils.get_informal_description(conjunct) for conjunct in formula.conjuncts]
    #         return utils.get_string("", " and ", "", *conjunct_strings)
    
    #     elif isinstance(formula, Disjunction):

    #         disjunct_strings = [ProverUtils.get_informal_description(disjunct) for disjunct in formula.disjuncts]
    #         return utils.get_string("", " or ", "", *disjunct_strings)
        
    #     elif isinstance(formula, Implication):

    #         return "if " + ProverUtils.get_informal_description(formula.premise) + " then " + ProverUtils.get_informal_description(formula.conclusion)
        
    #     elif isinstance(formula, AtLeast):

    #         description = "at least " + str(formula.threshold) + " of the following facts must be true: "

    #         first = True
    #         for literal in formula.arguments:

    #             if not first:
    #                 description += ", "
    #             first = False

    #             description += ProverUtils.get_informal_description(literal)

    #         return description
    #     else:

    #         raise Exception("Unknown formula type: " + str(type(formula)))

