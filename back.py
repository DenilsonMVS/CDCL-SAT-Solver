


































import sys
import random
from dataclasses import dataclass
from collections import defaultdict
from typing import List, Set, Tuple, Optional, Iterator

# Neste codigo tentamos otimizar ao mudar 
# algumas estruturas como listas p numpy
import numpy as np


# frozen to be hashable
@dataclass(frozen=True)
class Literal:
    variable: int
    negation: bool

    def __repr__(self):
        if self.negation:
            return "¬" + str(self.variable)
        else:
            return str(self.variable)

    def neg(self) -> "Literal":
        """
        Return the negation of this literal.
        """
        return Literal(self.variable, not self.negation)


@dataclass
class Clause:
    literals: List[Literal]

    def __repr__(self):
        return "∨".join(map(str, self.literals))

    def __iter__(self) -> Iterator[Literal]:
        return iter(self.literals)

    def __len__(self):
        return len(self.literals)

    def __hash__(self):
        x = 0
        for lit in self.literals:
            x ^= hash(lit)
        return x


@dataclass
class Formula:
    clauses: List[Clause]
    __variables: Set[int]

    def __init__(self, clauses: List[Clause]):
        """
        Remove duplicate literals in clauses.
        """
        self.clauses = []
        self.__variables = set()
        for clause in clauses:
            self.clauses.append(Clause(list(set(clause))))
            for lit in clause:
                var = lit.variable
                self.__variables.add(var)

    def variables(self) -> Set[int]:
        """
        Return the set of variables contained in this formula.
        """
        return self.__variables

    def __repr__(self):
        return " ∧ ".join(f"({clause})" for clause in self.clauses)

    def __iter__(self) -> Iterator[Clause]:
        return iter(self.clauses)

    def __len__(self):
        return len(self.clauses)


@dataclass
class Assignment:
    value: bool
    antecedent: Optional[Clause]
    dl: int  # decision level


class Assignments(dict):
    """
    The assignments, also stores the current decision level.
    """

    def __init__(self):
        super().__init__()

        # the decision level
        self.dl = 0

    def value(self, literal: Literal) -> bool:
        """
        Return the value of the literal with respect the current assignments.
        """
        if literal.negation:
            return not self[literal.variable].value
        else:
            return self[literal.variable].value

    def assign(self, variable: int, value: bool, antecedent: Optional[Clause]):
        self[variable] = Assignment(value, antecedent, self.dl)

    def unassign(self, variable: int):
        self.pop(variable)

    def satisfy(self, formula: Formula) -> bool:
        """
        Check whether the assignments actually satisfies the formula.
        """
        for clause in formula:
            if True not in [self.value(lit) for lit in clause]:
                return False

        return True


def cdcl_solve(formula: Formula) -> Optional[Assignments]:
    """
    Solve the CNF formula using the CDCL algorithm with VSIDS.
    """
    assignments = Assignments()
    lit2clauses, clause2lits = init_watches(formula)

    # Initialize VSIDS scores
    vsids_scores = defaultdict(int)
    decay_factor = 0.95  # Decay factor for VSIDS scores

    # Populate VSIDS scores initially
    for clause in formula:
        for literal in clause:
            vsids_scores[literal.variable] += 1

    # Unit propagation for unit clauses
    unit_clauses = [clause for clause in formula if len(clause) == 1]
    to_propagate = []
    for clause in unit_clauses:
        lit = clause.literals[0]
        var = lit.variable
        val = not lit.negation
        if var not in assignments:
            assignments.assign(var, val, clause)
            to_propagate.append(lit)

    reason, conflict_clause = unit_propagation(
        assignments, lit2clauses, clause2lits, to_propagate
    )
    if reason == "conflict":
        return None  # UNSAT due to conflict in unit propagation

    while not all_variables_assigned(formula, assignments):
        # Decision step: Pick a variable and assign it
        var, val = pick_branching_variable(formula, assignments, vsids_scores, decay_factor)
        if var is None:  # No variables left to assign
            break
        assignments.dl += 1
        assignments.assign(var, val, antecedent=None)
        to_propagate = [Literal(var, not val)]

        while True:
            # Propagate and check for conflicts
            reason, conflict_clause = unit_propagation(
                assignments, lit2clauses, clause2lits, to_propagate
            )
            if reason != "conflict":
                break  # No conflict, return to decision step

            # Analyze conflict and learn a new clause
            backtrack_level, learnt_clause = conflict_analysis(conflict_clause, assignments)
            if learnt_clause == conflict_clause:
                return None  # UNSAT
            if backtrack_level < 0:
                return None  # UNSAT

            # Add learnt clause and update VSIDS scores
            add_learnt_clause(
                formula, learnt_clause, assignments, lit2clauses, clause2lits
            )
            update_vsids(vsids_scores, learnt_clause)  # Update VSIDS scores
            backtrack(assignments, backtrack_level)
            assignments.dl = backtrack_level

            # Prepare for next propagation step
            unassigned_literals = [
                lit
                for lit in learnt_clause
                if lit.variable not in assignments
            ]
            if len(unassigned_literals) == 1:
                lit = unassigned_literals[0]
                var = lit.variable
                val = not lit.negation
                assignments.assign(var, val, antecedent=learnt_clause)
                to_propagate = [Literal(var, not val)]

    return assignments


def add_learnt_clause(formula, clause, assignments, lit2clauses, clause2lits):
    formula.clauses.append(clause)
    for lit in sorted(
        clause,
        key=lambda lit: -assignments[lit.variable].dl
        if lit.variable in assignments else float('-inf')
    ):
        if len(clause2lits[clause]) < 2:
            clause2lits[clause].append(lit)
            lit2clauses[lit].append(clause)
        else:
            break


def all_variables_assigned(formula: Formula, assignments: Assignments) -> bool:
    return len(formula.variables()) == len(assignments)


def pick_branching_variable(
    formula: Formula, assignments: Assignments, vsids_scores: defaultdict, decay_factor: float
) -> Tuple[int, bool]:
    """
    Pick the next branching variable using VSIDS heuristic.
    """
    # Decay scores periodically
    if assignments.dl % 100 == 0:  # Decay every 100 decision levels
        for var in vsids_scores:
            vsids_scores[var] *= decay_factor

    # Pick the unassigned variable with the highest score
    unassigned_vars = [var for var in formula.variables() if var not in assignments]
    if not unassigned_vars:
        return None, None

    var = max(unassigned_vars, key=lambda v: vsids_scores[v])
    val = random.choice([True, False])  # Random polarity
    return var, val


def update_vsids(vsids_scores: defaultdict, clause: Clause):
    """
    Update VSIDS scores for literals in a learned clause.
    """
    for literal in clause:
        vsids_scores[literal.variable] += 1


def backtrack(assignments: Assignments, b: int):
    to_remove = []
    for var, assignment in assignments.items():
        if assignment.dl > b:
            to_remove.append(var)

    for var in to_remove:
        assignments.unassign(var)


def unit_propagation(
    assignments, lit2clauses, clause2lits, to_propagate: List[Literal]
) -> Tuple[str, Optional[Clause]]:
    while len(to_propagate) > 0:
        watching_lit = to_propagate.pop().neg()

        # use list(.) to copy it because size of
        # lit2clauses[watching_lit]might change during for-loop
        watching_clauses = list(lit2clauses[watching_lit])
        for watching_clause in watching_clauses:
            for lit in watching_clause:
                if lit in clause2lits[watching_clause]:
                    # lit is another watching literal of watching_clause
                    continue
                elif lit.variable in assignments and not assignments.value(lit):
                    # lit is a assigned False
                    continue
                else:
                    # lit is not another watching literal of watching_clause
                    # and is non-False literal, so we rewatch it. (case 1)
                    clause2lits[watching_clause].remove(watching_lit)
                    clause2lits[watching_clause].append(lit)
                    lit2clauses[watching_lit].remove(watching_clause)
                    lit2clauses[lit].append(watching_clause)
                    break
            else:
                # we cannot find another literal to rewatch (case 2,3,4)
                watching_lits = clause2lits[watching_clause]
                if len(watching_lits) == 1:
                    # watching_clause is unit clause, and the only literal
                    # is assigned False, thus indicates a conflict
                    return "conflict", watching_clause

                # the other watching literal
                other = (
                    watching_lits[0]
                    if watching_lits[1] == watching_lit
                    else watching_lits[1]
                )
                if other.variable not in assignments:
                    # the other watching literal is unassigned. (case 3)
                    assignments.assign(
                        other.variable, not other.negation, watching_clause
                    )
                    to_propagate.insert(0, other)
                elif assignments.value(other):
                    # the other watching literal is assigned True. (case 2)
                    continue
                else:
                    # the other watching literal is assigned False. (case 4)
                    return "conflict", watching_clause

    return "unresolved", None


def resolve(a: Clause, b: Clause, x: int) -> Clause:
    """
    The resolution operation
    """
    result = set(a.literals + b.literals) - {Literal(x, True), Literal(x, False)}
    result = list(result)
    return Clause(result)


def conflict_analysis(clause: Clause, assignments: Assignments) -> Tuple[int, Clause]:
    if assignments.dl == 0:
        return (-1, None)

    # literals with current decision level
    literals = [
        literal
        for literal in clause
        if literal.variable in assignments and
        assignments[literal.variable].dl == assignments.dl
    ]
    while len(literals) != 1:
        # implied literals
        literals = filter(
            lambda lit: (
                lit.variable in assignments and
                assignments[lit.variable].antecedent is not None
            ),
            literals
        )

        # select any literal that meets the criterion
        try:
            literal = next(literals)
        except StopIteration:
            break
        antecedent = assignments[literal.variable].antecedent
        clause = resolve(clause, antecedent, literal.variable)

        # literals with current decision level
        literals = [
            literal
            for literal in clause
            if literal.variable in assignments and
            assignments[literal.variable].dl == assignments.dl
        ]

    # out of the loop, clause is now the new learnt clause
    # compute the backtrack level b (second largest decision level)

    decision_levels = sorted(
        set(assignments[literal.variable].dl
            for literal in clause
            if literal.variable in assignments)
    )
    if len(decision_levels) <= 1:
        return 0, clause
    else:
        return decision_levels[-2], clause


def parse_dimacs_cnf(content: str) -> Formula:
    """
    parse the DIMACS cnf file format into corresponding Formula.
    """
    clauses = [Clause([])]
    for line in content.splitlines():
        tokens = line.split()
        if len(tokens) != 0 and tokens[0] not in ("p", "c"):
            for tok in tokens:
                lit = int(tok)
                if lit == 0:
                    clauses.append(Clause([]))
                else:
                    var = abs(lit)
                    neg = lit < 0
                    clauses[-1].literals.append(Literal(var, neg))

    if len(clauses[-1]) == 0:
        clauses.pop()

    return Formula(clauses)


def init_watches(formula: Formula):
    """
    Return lit2clauses and clause2lits
    """

    lit2clauses = defaultdict(list)
    clause2lits = defaultdict(list)

    for clause in formula:
        if len(clause.literals) > 0:
            if len(clause) == 1:
                lit2clauses[clause.literals[0]].append(clause)
                clause2lits[clause].append(clause.literals[0])
            else:
                lit2clauses[clause.literals[0]].append(clause)
                lit2clauses[clause.literals[1]].append(clause)
                clause2lits[clause].append(clause.literals[0])
                clause2lits[clause].append(clause.literals[1])

    return lit2clauses, clause2lits