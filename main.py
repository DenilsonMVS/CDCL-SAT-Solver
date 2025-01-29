
import sys
from dataclasses import dataclass
from typing import List, Set, Tuple, Optional, Iterator

def load_file(filename: str):
    lines = open(filename, "r").readlines()

    num_clauses = None

    current_line = 0
    while True:
        parts = " ".join(lines[current_line].split()).split(" ")
        current_line += 1

        if parts[0] == "p":
            num_clauses = int(parts[3])
            break

    clauses: set[Clause] = set()
    while num_clauses > 0:
        if lines[current_line][0] == "c":
            current_line += 1
            continue

        clauses.add(Clause(set([int(value) for value in " ".join(lines[current_line].split()).split(" ")[:-1]])))
        current_line += 1
        num_clauses -= 1

    return clauses


@dataclass
class Clause:
    literals: set[int]
    def __init__(self, literals: set[int]):
        self.literals = literals

    def __iter__(self) -> Iterator[int]:
        return iter(self.literals)
    
    def __len__(self):
        return len(self.literals)
    
    def __hash__(self):
        x = 0
        for lit in self.literals:
            x ^= hash(lit)
        return x

    def __contains__(self, item: int) -> bool:
        return item in self.literals


def join_clauses(a: Clause, b: Clause):
    joined = set()
    for v in a:
        if -v not in b:
            joined.add(v)
    for v in b:
        if -v not in a:
            joined.add(v)
    return Clause(joined)


def explain(
    clauses: set[Clause],
    variable_values: list[int],
    decision_stack: list[tuple[int, bool]],
    conflict_clause: Clause
):
    reverse_var_idx = {}
    for i in range(len(decision_stack)):
        reverse_var_idx[decision_stack[i][0]] = i

    while True:
        joined = False
        for i in range(len(decision_stack) - 1, -1, -1):
            var = decision_stack[i][0]
            if -var not in conflict_clause:
                continue

            for clause in clauses:
                
                if var not in clause:
                    continue

                ok = True
                for tmp in clause:
                    if tmp == var:
                        continue

                    if variable_values[abs(tmp)] == tmp or -tmp not in reverse_var_idx or reverse_var_idx[-tmp] > i:
                        ok = False
                        break

                if not ok:
                    continue

                conflict_clause = join_clauses(conflict_clause, clause)
                joined = True
                break
            
            if joined:
                break
        
        if not joined:
            return conflict_clause


def set_propagating_value(
    clauses: set[Clause],
    variable_values: list[int],
    decision_stack: list[tuple[int, bool]],
    value_to_set: int
):
    variable_values[abs(value_to_set)] = value_to_set
    decision_stack.append((value_to_set, False))

    for clause in clauses:
        solved = False
        free_variables = []
        
        for var in clause:
            value = variable_values[abs(var)]
            if var == value:
                solved = True
                break

            if value == 0:
                free_variables.append(var)
        
        if not solved and len(free_variables) == 0:
            return explain(clauses, variable_values, decision_stack, clause)

    return None


def propagate(
    clauses: set[Clause],
    variable_values: list[int],
    decision_stack: list[tuple[int, bool]]
):
    while True:
        value_to_set = None

        for clause in clauses:

            solved = False
            free_variables = []
            for var in clause:
                value = variable_values[abs(var)]
                if var == value:
                    solved = True
                    break

                if variable_values[abs(var)] == 0:
                    free_variables.append(var)

            if not solved:
                if len(free_variables) == 1:
                    value_to_set = free_variables[0]
                    break
                elif len(free_variables) == 0:
                    return []

        if value_to_set is None:
            break

        # adiciono a clausula olhando as clausulas que estão finalizadas que possuem o literal
        explanation = set_propagating_value(clauses, variable_values, decision_stack, value_to_set)
        if explanation is not None:
            return explanation

    return None

def decide(clauses: set[Clause], variable_values: list[int], decision_stack: list[tuple[int, bool]]):
    for clause in clauses:
        for var in clause:
            value = variable_values[abs(var)]
            if value == var:
                break

            if value == 0:
                variable_values[abs(var)] = var
                decision_stack.append((var, True))
                return True
    return False

def get_biggest_variable(clauses: set[Clause]):
    res = 0
    for clause in clauses:
        for var in clause:
            res = max(res, abs(var))
    return res

def solve(clauses: set[Clause]):
    num_variables = get_biggest_variable(clauses)
    variable_values = [0 for _ in range(num_variables + 1)]

    decision_stack = []

    while True:
        explanation = propagate(clauses, variable_values, decision_stack)
        if explanation is None:
            if not decide(clauses, variable_values, decision_stack):
                return True
        elif len(explanation) == 0:
            return False
        else:
            clauses.add(explanation)

            while len(decision_stack) > 0:
                value, from_decide = decision_stack.pop()
                variable_values[abs(value)] = 0

                if -value in explanation:
                    decision_stack.append((value, from_decide))
                    variable_values[abs(value)] = value
                    break
            
            while len(decision_stack) > 0:
                (value, from_decide) = decision_stack.pop()
                variable_values[abs(value)] = 0

                if from_decide:
                    decision_stack.append((-value, False))
                    variable_values[abs(value)] = -value
                    break
            
            if len(decision_stack) == 0:
                return False        



def main():
    clauses = load_file(sys.argv[1])
    print(solve(clauses))



if __name__ == "__main__":
    main()
