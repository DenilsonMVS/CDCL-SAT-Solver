
import sys


def load_file(filename: str):
    lines = open(filename, "r").readlines()

    num_variables = None    
    num_clauses = None

    current_line = 0
    while True:
        parts = lines[current_line].split(" ")
        current_line += 1

        if parts[0] == "p":
            num_variables = int(parts[2])
            num_clauses = int(parts[3])
            break

    clauses: list[set[int]] = []
    for _ in range(num_clauses):
        clauses.append([int(value) for value in lines[current_line].split(" ")[:-1]])
        current_line += 1

    return clauses, num_variables



def set_variable(clauses: list[list[int]], num_variables, variable: int):

    new_clauses = []
    for clause_idx in range(len(clauses)):
        clause = clauses[clause_idx]
        if variable in clause:
            continue

        new_clause = [var for var in clause if var != -variable]
        if len(new_clause) == 0:
            return None

        new_clauses.append(new_clause)
    
    return recursion_step(new_clauses, num_variables)

def recursion_step(clauses: list[list[int]], num_variables: int):
    if len(clauses) == 0:
        return []
    
    pure_verification = [[False, False] for _ in range(num_variables + 1)]

    for clause in clauses:
        if len(clause) == 1:
            return set_variable(clauses, num_variables, clause[0])
        for variable in clause:
            if variable < 0:
                pure_verification[-variable][0] = True
            else:
                pure_verification[variable][1] = True
    
    for var in range(len(pure_verification)):
        has_neg, has_pos = pure_verification[var]
        if has_neg and not has_pos:
            return set_variable(clauses, num_variables, -var)
        elif not has_neg and has_pos:
            return set_variable(clauses, num_variables, var)
    
    result = set_variable(clauses, num_variables, clauses[0][0])
    if result is None:
        result = set_variable(clauses, num_variables, -clauses[0][0])
        
        if result is None:
            return None
        else:
            result.append(-clauses[0][0])
            return result
    
    else:

        result.append(clauses[0][0])
        return result


def main():
    clauses, num_variables = load_file(sys.argv[1])
    print(recursion_step(clauses, num_variables))



if __name__ == "__main__":
    main()
