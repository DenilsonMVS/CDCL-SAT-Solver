
import sys


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

    clauses: list[set[int]] = []
    while num_clauses > 0:
        if lines[current_line][0] == "c":
            current_line += 1
            continue

        clauses.append([int(value) for value in " ".join(lines[current_line].split()).split(" ")[:-1]])
        current_line += 1
        num_clauses -= 1

    return clauses


def set_propagating_value(
    clauses: list[list[int]],
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
            variable_values[abs(value_to_set)] = 0
            decision_stack.pop()
            return False

    return True


def propagate(
    clauses: list[list[int]],
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
                    return False

        if value_to_set is None:
            break

        # adiciono a clausula olhando as clausulas que estão finalizadas que possuem o literal
        if not set_propagating_value(clauses, variable_values, decision_stack, value_to_set):
            return False
            
    return True

def decide(clauses: list[list[int]], variable_values: list[int], decision_stack: list[tuple[int, bool]]):
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

def get_biggest_variable(clauses: list[list[int]]):
    res = 0
    for clause in clauses:
        for var in clause:
            res = max(res, abs(var))
    return res

def solve(clauses: list[list[int]]):
    num_variables = get_biggest_variable(clauses)
    variable_values = [0 for _ in range(num_variables + 1)]

    decision_stack = []

    while True:
        if propagate(clauses, variable_values, decision_stack):
            if not decide(clauses, variable_values, decision_stack):
                return True
        else:
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
