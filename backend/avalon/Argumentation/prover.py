


import re
from typing import Self, cast
import typing
from ..Argumentation.logic import AtLeast, Conjunction, Disjunction, Fact, Formula, Implication, Literal, ProverUtils


class Prover:

    def __init__(self, formulas:list[Formula], player_names:list[str]):
        
        self.player_names = player_names

        self.axioms = []
        
        self.proven_facts:set[Literal] = set() 
        self.disproven_facts:set[Literal] = set()

        # For each literal in the list of given formulas: add it to the set of proven facts, and add its negation to the set of disproven facts.
        # For all other formulas, add it to the list of axioms.
        for formula in formulas:
            
            if isinstance(formula, Literal):
                
                self.proven_facts.add(formula)
                
                negated_formula = ProverUtils.negate(formula)
                negated_formula = cast(Literal, negated_formula)
                self.disproven_facts.add(negated_formula)
            
            elif isinstance(formula, Formula):
                self.axioms.append(formula)

            else:
                raise Exception("The given formula " + str(formula) + " is not an object of type Formula, but rather a " + str(type(formula)))


    def prove(self, fact_to_prove:Literal):

        # 1. Create a root node representing the fact to prove.
        self.root = Node(None, fact_to_prove, self)

        # 2. starting building a tree structure.
        self.build_tree(self.root)

    def build_tree(self, parent_node:'Node'):

        children:list[Node] = []

        formula_to_prove = parent_node.formula

        # If the given formula is an implication, re-write it as a disjunction.
        if isinstance(formula_to_prove, Implication):       
            formula_to_prove = formula_to_prove.to_disjunction()
 

        if isinstance(formula_to_prove, Literal):

            # 1. Find all implications for which the conclusion contains the given literal.
            
            for axiom in self.axioms:

                implication = axiom.reshape(formula_to_prove)
                
                if implication != None:

                    parent_node.axioms_for_children.append(axiom)
                    parent_node.reshaped_axioms_for_children.append(implication)
                
            # 2. Next, for each of these, add a child to the parent node.
            for implication in parent_node.reshaped_axioms_for_children:
                
                if self.path_contains(parent_node, implication.premise):
                    # if the same premise is already contained in the path to the root we can't use this premise, because we would 
                    # get a circular proof. e.g. we would first be trying to prove p in order to prove p. This could result in infinite loops.
                    continue

                elif isinstance(implication.premise, Literal) and self.path_contains(parent_node, ProverUtils.negate(implication.premise)):
                    
                    # Now, check if the negation of the premise is contained in the path to the root.
                    
                    # the method self.path_contains() already checks if the given premise is a literal or not. 
                    # However, in this case we first negate the formula, which gives problems if the premise is of type AtLeast, for which we
                    # haven't implemented negation yet.

                    new_node = Node(parent_node, implication.premise, None, True)
                    children.append(new_node)  

                else:
                    new_node = Node(parent_node, implication.premise)
                    children.append(new_node)               
                    

        elif isinstance(formula_to_prove, Conjunction):
            
            for conjunct in formula_to_prove.conjuncts:

                if self.path_contains(parent_node, conjunct):
                    children.clear() 
                    #If the node doesn't have any children, then its truth status will never be updated, and therefore will always remain 'False'.
                    break

                elif self.path_contains(parent_node, ProverUtils.negate(conjunct)):
                    
                    new_node = Node(parent_node, conjunct, None, True)
                    children.append(new_node) 

                else:
                    new_node = Node(parent_node, conjunct)
                    children.append(new_node)               
                    
                #children.append(Node(parent_node, conjunct))
        
        elif isinstance(formula_to_prove, Disjunction):
            
            for disjunct in formula_to_prove.disjuncts:

                if self.path_contains(parent_node, disjunct):
                    continue

                elif self.path_contains(parent_node, ProverUtils.negate(disjunct)):
                    
                    new_node = Node(parent_node, disjunct, None, True)
                    children.append(new_node) 

                else:
                    new_node = Node(parent_node, disjunct)
                    children.append(new_node)               
                    

        elif isinstance(formula_to_prove, Implication):
                
            # This case should not happen, because above we called to_disjunction() to put it in a different form.
            raise Exception("One of the given formulas contained an implication as a subformula. This case is not implemented.")
        
        elif isinstance(formula_to_prove, AtLeast):
            
            for literal in formula_to_prove.arguments:

                if self.path_contains(parent_node, literal):
                    continue

                elif self.path_contains(parent_node, ProverUtils.negate(literal)):
                    
                    new_node = Node(parent_node, literal, None, True)
                    children.append(new_node) 

                else:
                    new_node = Node(parent_node, literal)
                    children.append(new_node)    
            
        else:
            raise Exception("unknown type: " + str(type(formula_to_prove)))
        


        parent_node.add_children(children)

        # Consistency check! Checking if the node does not contain the same formula more than once.
        # child_formulas = set()
        # for child in children:
        #     if child.formula in child_formulas:
        #         raise Exception("Multiple instances of the same child formula.")
        #     child_formulas.add(child.formula)

        #print("prover.py line 86 num children: " + str(len(children)) +  " " + str(children[0].formula))

        for child in children:  

            #if parent_node.proof_status != None:
                # Note: when we call child.set_proof_status() this will trigger the proof status of its ancestors to be updated as well.
                # Therefore, parent_node.proof_status may change.
                #break

            if child.formula in self.proven_facts:
                child.set_proof_status(True, set(), 1)
            
            elif child.assumed_true:
                conditions = set()
                conditions.add(child.formula)
                child.set_proof_status(True, conditions, 1)
            
            elif child.formula in self.disproven_facts:
                child.set_proof_status(False, set(), 1)
            
            else:
                self.build_tree(child)


    def path_contains(self, parent:'Node', child_formula:'Formula') -> bool:

        """ If the given formula is a literal, this method checks if the same literal is already appearing somewhere in the path 
                to the root."""
        
        if not isinstance(child_formula, Literal):
            return False 
        
       
        #negated_child_formula = ProverUtils.negate(child_formula)
        
        ancestor = parent
        
        while(ancestor != None):

            if isinstance(ancestor.formula, Literal):
                if ancestor.formula.__eq__(child_formula):
                    return True
                
                    #or ancestor.formula == negated_child_formula:

                    # We should adapt this. If we're trying to prove Y, it is actually okay to assume !Y, because !Y --> Y is equivalent to Y.
                    # In fact, this is not only allowed, it is even necessary, because otherwise we can't find non-constructive proofs.
                    # e.g.   suppose we have   X --> Y   and   !X --> Y. Clearly, from this it follows that Y must be true, but our current
                    #       algorithm can't find a proof. This can be solved by allowing the assumption of !Y when proving Y.

                    
            
            ancestor = ancestor.parent

        return False

    def get_formal_proof(self):
        
        formal_proof = []
        informal_proof = []
        self.build_proof(self.root, formal_proof, informal_proof)
        return formal_proof
    
    def get_informal_proof(self) -> str:
        
        formal_proof = []
        informal_proof = []
        self.build_proof(self.root, formal_proof, informal_proof)

        

        informal_proof_as_string = "\n\n"

        #informal_proof_as_string += "PROOF COMPLEXITY: " + str(self.root.proof_complexity) +" "

        for statement in informal_proof:

            # Make the first character upper case:
            statement = statement[0].upper() + statement[1:]

            # And the statement with a period:
            statement += ". "

            informal_proof_as_string += statement + "\n\n"

        for i in range(10):
            informal_proof_as_string = re.sub("it is not true that player " + str(i) +" is good", "player " + str(i) + " is evil", informal_proof_as_string)
            informal_proof_as_string = re.sub("then player " + str(i) +" is", "then player " + str(i) + " must be", informal_proof_as_string)

        for name in self.player_names:
            informal_proof_as_string = re.sub("it is not true that " + name  + " is good", name + " is evil", informal_proof_as_string)
            informal_proof_as_string = re.sub("then " + name + " is", "then " + name + " must be", informal_proof_as_string)
            informal_proof_as_string = re.sub("we conclude that " + name + " is", "we conclude that " + name + " must be", informal_proof_as_string)

        return informal_proof_as_string


    def build_proof(self, node:'Node', formal_proof:list[str], informal_proof:list[str]):

        if self.root.proof_status != True:
            print()
            print("GIVEN THE FOLLOWING AXIOMS:")
            for axiom in self.axioms:
                print(axiom)
            
            for fact in self.proven_facts:
                print(fact)

            print()
            print("WE DID NOT MANAGE TO FIND A PROOF OF: " + str(self.root.formula))
            print()



        if self.root.proof_status == None:

            return None

        elif self.root.proof_status != True:

            raise Exception("Proof failed.")


        

        # FOR DEBUGGING:
        path = str(node.id)
        n = node
        while n.parent != None:
            n = n.parent
            path += "-" + str(n.id)



        if isinstance(node.formula, Literal):
        
            statement = ""

            if len(node.children) == 0:
                
                #formal_proof.append(path + " - " + str(node.formula))
                formal_proof.append(str(node.formula))

                # if node.assumed_true:
                #     #statement = "We assume that " + node.formula.description
                #     pass
                # else:
                #     statement = "We know that " + node.formula.description

                #     if not statement in informal_proof:
                #         informal_proof.append(statement)

            else:

                

                found = False
                for i in range(len(node.children)):

                    child = node.children[i] # Each of these children corresponds to an implication.

                    if child.proof_status == True and child.used_in_proof:
                        found = True

                        self.build_proof(child, formal_proof, informal_proof)

                        # Update the formal proof.
                        #formal_proof.append(str(child.id) + "-" + path + " - " + str(node.reshaped_axioms_for_children[i]))
                        formal_proof.append(node.reshaped_axioms_for_children[i])
                        

                        break
                
                informal_proof.append(self.get_partial_proof(node))

                if found == False:
                    raise Exception("Something went wrong.")
                
        elif isinstance(node.formula, Disjunction):

            # First, all children for which their formula has been proven.
            true_children = [child for child in node.children if child.proof_status == True]

            if len(true_children) == 0:
                raise Exception("Something went wrong.")

            # Next, among those children, find the node with lowest proof complexity.
            chosen_child = min(true_children, key=lambda child: child.proof_complexity)

            ## Consistency check:
            chosen_children_2 = [child for child in node.children if child.used_in_proof]
            if len(chosen_children_2) != 1 or chosen_children_2[0] != chosen_child:
                raise Exception("Something went wrong!!")

            self.build_proof(chosen_child, formal_proof, informal_proof)


        elif isinstance(node.formula, Conjunction):

            
            for child in node.children:
                if child.proof_status != True:
                    raise Exception("Something went wrong.")
                
                self.build_proof(child, formal_proof, informal_proof)

                # if isinstance(child.formula, Literal):
                #     formal_proof.append(Implication(child.formula, node.formula))
                #     #TODO: I'm not sure if this is necessary

        elif isinstance(node.formula, AtLeast):       

            # First, find all children for which their formula has been proven.
            true_children = [child for child in node.children if child.proof_status == True] 

            if len(true_children) < node.formula.threshold:
                raise Exception("Something went wrong. num_found: " + str(len(true_children)) + " threshold: " + str(node.formula.threshold))
        
            # Next, sort them from lowest proof complexity to highest proof complexity.
            sorted_children  = sorted(true_children, key=lambda child: child.proof_complexity)

            # Consistency check.
            chosen_children = sorted_children[:node.formula.threshold]
            chosen_children_2 = [child for child in node.children if child.used_in_proof]
            if len(chosen_children_2) != len(chosen_children):
                raise Exception("Something went wrong!!")

            # In the proof, only consider the n children with lowest proof complexity.
            for i in range(node.formula.threshold):
                child = sorted_children[i]
                self.build_proof(child, formal_proof, informal_proof)


            # num_found = 0
            # for child in node.children:
            #     if child.proof_status == True:
            #         num_found += 1

            #         self.build_proof(child, formal_proof, informal_proof)



        else:
            raise Exception("unknown node type: " + str(type(node.formula)))
        

    def get_partial_proof(self, node:'Node') -> str:
        
        # The given formula of the given node should represent a literal. Furthermore, it must have children, which each represent an implication.

        if not isinstance(node.formula, Literal):
            raise Exception("The formula of the given node should be a literal. node.formula: " + str(node.formula))

        if len(node.children) == 0:
            raise Exception("The given node should have children")

        

        chosen_children = [child for child in node.children if child.used_in_proof]
        if len(chosen_children) != 1:
            raise Exception("Mulitple chosen children")
        
        chosen_child = chosen_children[0] # Note thatce chosen_children contains exactly one item, we are here just picking the unique item of the list.
        statement = ""



        # Collect all the literal nodes that are in the tree below the chosen_child, and such that there is no other literal node on the path between them.
        openlist = [chosen_child]
        literal_nodes = []
        while len(openlist) > 0:
            
            loop_node = openlist.pop()
            for ch in loop_node.children:

                if isinstance(ch.formula, Literal):
                    literal_nodes.append(ch)
                else:
                    openlist.append(ch)
                    
        # Now, separate the list of literal nodes into two lists: those that do and those that don't have children.
        nodes_with_children = [nod for nod in literal_nodes if nod.children != None and len(nod.children) > 0 and nod.used_in_proof]
        nodes_without_children = [nod for nod in literal_nodes if nod.children == None or len(nod.children) == 0 and nod.used_in_proof]

        if len(nodes_with_children) == 0:
            pass
        elif len(nodes_with_children) == 1:
            statement += "Using our previous conclusion that "
        else:
            statement += "Using our previous conclusions that "

        for i in range(len(nodes_with_children)):
            literal_node = nodes_with_children[i]

            if i!= 0:
                if i == len(nodes_with_children) - 1:
                    statement += ", and that "
                else:
                    statement += ", that "

            statement += self.get_literal_node_description(literal_node)
            
        
        not_assumed = [nod for nod in nodes_without_children if not nod.assumed_true]

        if len(nodes_with_children) > 0 and len(not_assumed) > 0:
            statement += ", plus the fact that "
        if len(nodes_with_children) == 0 and len(not_assumed) > 0:
            statement += "Given the fact that "

        for i in range(len(not_assumed)):
            literal_node = not_assumed[i]

            if i!= 0:
                if i == len(not_assumed) - 1:
                    statement += ", and that "
                else:
                    statement += ", that "
            
            statement += literal_node.formula.description

        index_of_chosen_child = node.children.index(chosen_child)
        axiom_used = node.axioms_for_children[index_of_chosen_child]

        include_axiom = True
        if isinstance(axiom_used, Implication):
            if isinstance(axiom_used.conclusion, Fact):
                if axiom_used.conclusion.predicate == "contains_evil_player":
                    include_axiom = False
                    # In this case, don't include the description of the axiom in the informal proof, because this axiom is 
                    # really just a definition of the predicate contains_evil_player

        if include_axiom:
            statement += ", plus the fact that " + axiom_used.description

        statement += ", we conclude that " + self.get_literal_node_description(node)

        return statement
    

    def get_literal_node_description(self, node):

        statement = ""

        proof_conditions = typing.cast(set, node.conditions)
        if len(proof_conditions) == 0:
        
            statement += node.formula.description
    
        else:
            statement = "if "
            
            num_conditions = len(proof_conditions)
            counter = 0
            for condition in proof_conditions:
                statement += condition.description
                counter += 1

                if counter < num_conditions:
                    statement += ", "

                if counter == num_conditions-1:
                    statement += "and "
                
            statement += " then " + node.formula.description

        return statement

class Node:
    
    num_generated = 0

    def __init__(self, parent:Self|None, formula:Formula, prover=None, assumed_true=False): 
        
        self.parent = parent
        self.formula = formula

        Node.num_generated += 1
        self.id = Node.num_generated

        # When set to true, it means we will assume that the formula is true, even though it is not an axiom and it hasn't been proved.
        # This allows us to assume !p whenever we are trying to prove p. This means that we are actually proving !p-->p but that is equivalent to just p.
        self.assumed_true = assumed_true

        if parent == None and prover == None:
            raise Exception("prover should be given.")
        elif parent != None and prover == None:
            self.prover = parent.prover
        elif parent == None and prover != None:
            self.prover = prover
        else:
            raise Exception("Prover should only be given to the root node.")

        if parent == None:
            self.depth = 0
        else:
            self.depth = parent.depth + 1

            #print("creating node at depth: " + str(self.depth) + " formula: " + str(formula) + " parent formula: " + str(parent.formula))

        self.proof_status:bool|None = None
        self.conditions:set[Formula]|None = None
        self.proof_complexity:int = 1
        self.used_in_proof:bool = False # even if the formula is proven TRUE, we still may not actually use it in the proof.
        
        self.children = []

        # These two are only used if the formula is a Literal.
        self.axioms_for_children:list[Formula] = []
        self.reshaped_axioms_for_children = []



        # If the given formula is an implication, then it means we should prove its premise, 
        #   So, if the premise is a conjunction, we have to prove all conjuncts, so the node is an 'and' node
        #   while if the premise is a disjunction we only need to prove one of its disjuncts, so the node is an 'or' node.
        # If the given formula is a literal (e.g. x), it means we need to prove that literal, which means the children of this node will
        #     all contain implications that have that literal as their consequnce (e.g.   a ^ b --> x   or    c V d --> x)
        #      since we only need to prove one of these implications, the current node is an 'or' node.

        if isinstance(formula, Literal): #  e.g. just x
            self.threshold = 1 # It's children will represent implications with the given literal as their conclusion.
        elif isinstance(formula, Conjunction):
            self.threshold = "all"
        elif isinstance(formula, Disjunction):
            self.threshold = 1    
        elif isinstance(formula, Implication):
            
            # I think this never happens.

            if isinstance(formula.premise, Literal): # e.g. x -> y
                self.threshold = 1 # in this case it doesn't matter whether this node is an 'and' node or an 'or' node.
            elif isinstance(formula.premise, Disjunction): # e.g. x V y -> z
                self.threshold = 1
            elif isinstance(formula.premise, Conjunction):  # e.g. x ^ y -> z
                self.threshold = "all"
            elif isinstance(formula.premise, Implication):
                raise Exception("This case is not implemented.")
            elif isinstance(formula.premise, AtLeast):
                self.threshold = formula.premise.threshold
            else:
                raise Exception("unknown type: " + str(type(formula.premise)))
        
        elif isinstance(formula, AtLeast):
            
            self.threshold = formula.threshold
        
        else:
            raise Exception("unknown type: " + str(type(formula)))
        
        
    def add_children(self, children:list[Self]):  
        self.children = children.copy()

    def set_proof_status(self, new_status:bool, conditions:set[Formula], proof_complexity:int):
        self.proof_status = new_status
        self.conditions = conditions.copy()
        self.proof_complexity = proof_complexity

        # The code below is problematic, for example in the following case:
        #  We're trying to prove 'c' and we have the following axioms:  
        #       !a --> b         b --> a        a ^ b --> c
        # 
        # We can assume !a which leads to !a --> a, which is equivalent to a.
        #   However, the code below would store 'b' as a proven fact, which is not correct.


        # if self.proof_status == True and isinstance(self.formula, Literal):
        #         self.prover.proven_facts.add(self.formula)
        #         self.prover.disproven_facts.add(ProverUtils.negate(self.formula))

        if self.parent != None:
            self.parent.check_status()

    def check_status(self):

        update_parent = False

        # First, determine the 'threshold'.
        if self.threshold == "all":
            threshold = len(self.children)
        else:
            threshold = self.threshold
        threshold = typing.cast(int, threshold)
        
        
        


        # Next, determine the children for which their formula has been proven True, and the children for which it remains unproven.
        true_children = [child for child in self.children if child.proof_status == True] 
        undetermined_children = [child for child in self.children if child.proof_status == None] 


        if len(true_children) >= threshold:
            new_status = True
        elif len(true_children) + len(undetermined_children) < threshold:
            new_status = False
        else:
            new_status = None

        #if len(true_children) < threshold:
            # raise Exception("Something went wrong. num_found: " + str(len(true_children)) + " threshold: " + str(node.formula.threshold))
        
        if new_status == True:
        
            # Next, get the children with lowest proof complexity.
            sorted_children  = sorted(true_children, key=lambda child: child.proof_complexity)
            selected_children = sorted_children[:threshold]

            # Reset the 'used_in_proof' variable to FALSE for all children (I'm not sure if this is really necessary, but just to be sure.)
            # Then in the next loop we will set it to TRUE for all children that are used in the proof.
            for child in self.children:
                child.used_in_proof = False              


            conditions = set()
            proof_complexity = 1
            for child in selected_children:

                child.used_in_proof = True
                
                child_conditions = typing.cast(set, child.conditions)
                conditions.update(child_conditions)

                proof_complexity += child.proof_complexity
            
            ## If we have proven:     !p ^ q --> p   then that is equivalent to q --> p
            if isinstance(self.formula, Literal):
                negated = ProverUtils.negate(self.formula)
                if negated in conditions:
                    conditions.remove(negated)

            # if num_proved >= threshold:
            #     new_status = True
            # elif num_proved + num_undetermined < threshold:
            #     new_status = False
            # else:
            #     new_status = None

            #if new_status != self.proof_status:
                
            self.proof_status = new_status
            self.conditions = conditions
            self.proof_complexity = proof_complexity
        
        if self.parent != None:
            self.parent.check_status()
        

    def __repr__(self):
        return str(self.depth) +  ". " + self.formula.__repr__()


# Suppose we have: (a V b) ^ (c V d) --> e.
# Then the algorithm above will build the following tree:
#  * e
#  |
#  -- * (a V b) ^ (c V d) --> e
#     |
#     -- * (a V b)
#     |   |
#     |   -- * a
#     |   |
#     |   -- * b
#     |
#     -- * (c V d)
#     |   |
#     |   -- * c
#     |   |
#     |   -- * d


