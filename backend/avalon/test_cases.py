





from Argumentation.logic import AtLeast, Conjunction, Fact, Implication, Negation, ProverUtils
from Argumentation.prover import Prover


def prove_test_case_1():

    a = Fact("a")
    b = Fact("b")
    c = Fact("c")
    d = Fact("d")

    a_imp_b = Implication(a,b)
    b_imp_c = Implication(b,c)
    

    formulas = [a, a_imp_b, b_imp_c]
    prover = Prover(formulas)
    prover.prove(c)

    proof = prover.get_formal_proof()
    print("PROOF:")
    print(str(proof))


def get_test_case_2():

    alice_studies = Fact("studies", "Alice", informal_description="Alice has studied")
    bob_studies = Fact("studies", "Bob", informal_description="Bob has studied")
    alice_passes = Fact("passes", "Alice", informal_description="Alice has passed the exam")
    bob_passes = Fact("passes", "Bob", informal_description="Bob has passed the exam")

    average_is_high = Fact("high_average_mark", informal_description="the average mark is high")
    average_not_high = Negation(average_is_high)

    a_imp = Implication(alice_studies,alice_passes)
    b_imp = Implication(bob_studies,bob_passes)
    will_be_high = Implication(Conjunction(alice_passes, bob_passes) , average_is_high)

    bob_did_not_study = Negation(bob_studies)

    

    axioms = [a_imp, b_imp, will_be_high, average_not_high, alice_studies]

    return [axioms, bob_did_not_study]


def get_test_case_3():

    good_1 = Fact("good", "1", informal_description="Player 1 is good")
    good_2 = Fact("good", "2", informal_description="Player 2 is good")
    good_3 = Fact("good", "3", informal_description="Player 3 is good")
    good_4 = Fact("good", "4", informal_description="Player 3 is good")
    good_5 = Fact("good", "5", informal_description="Player 5 is good")

    evil_1 = Negation(good_1)
    evil_2 = Negation(good_2)
    evil_3 = Negation(good_3)
    evil_4 = Negation(good_4)
    evil_5 = Negation(good_5)

    two_evil_players = AtLeast(2, evil_1, evil_2, evil_3, evil_4, evil_5)


    # Knowing that players, 1,2, and 3 are good, and that there are at least two evil players, prove that player 4 is evil.

    axioms = [good_1, good_2, good_3, two_evil_players]

    return [axioms, evil_4]

def get_test_case_4():

    a = Fact("a", informal_description="a")
    b = Fact("b", informal_description="b")
    c = Fact("c", informal_description="c")

    a_and_b = Conjunction(a,b)
    not_a_and_b = ProverUtils.negate(a_and_b)

    implies_1 = Implication(a_and_b, c)
    implies_2 = Implication(not_a_and_b, c)

    axioms = [implies_1, implies_2]

    return [axioms, c]




if __name__ == "__main__":
    

    [formulas, fact_to_prove] = get_test_case_4()

    print("We know the following:")
    for formula in formulas:
        print(str(formula))
    
    print()
    print("From this we will prove: " + str(fact_to_prove))
    print()

    prover = Prover(formulas)
    prover.prove(fact_to_prove)

    formal_proof = prover.get_formal_proof()
    print("FORMAL PROOF:")
    print(str(formal_proof))
    print()
    
    informal_proof = prover.get_informal_proof()
    print("INFORMAL PROOF:")
    print(str(informal_proof))