
import sys
from dataclasses import dataclass
from typing import Optional, Iterator, Any
import itertools

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

    clauses: list[Clause] = []
    while num_clauses > 0:
        if lines[current_line][0] == "c":
            current_line += 1
            continue

        literals = [int(value) for value in " ".join(lines[current_line].split()).split(" ")[:-1]]
        clauses.append(Clause(set(literals), []))
        current_line += 1
        num_clauses -= 1

    return clauses


# Classe de uma clausula
# Responsável pela otimização de 2 watched literals
@dataclass
class Clause:
    set_literals: set[int]
    unset_literals: set[int]
    watched_literals: list[int]

    def __init__(self, literals: set[int], decision_stack: list[tuple[int, Optional[Any]]]):
        self.unset_literals = literals
        self.set_literals = set()
        self.watched_literals = []

        while len(self.watched_literals) < 2 and len(self.unset_literals) > 0:
            value = next(iter(self.unset_literals))
            self.watched_literals.append(value)
            self.unset_literals.remove(value)

        for lit, _ in decision_stack:
            self.set_literal(lit)
    
    def set_literal(self, literal: int):
        if -literal in self.watched_literals:
            self.watched_literals.remove(-literal)
            self.set_literals.add(-literal)
        elif literal in self.unset_literals:
            self.unset_literals.remove(literal)
            self.unset_literals.add(self.watched_literals.pop())
            self.watched_literals.append(literal)
        elif -literal in self.unset_literals:
            self.unset_literals.remove(-literal)
            self.set_literals.add(-literal)

        while len(self.watched_literals) < 2 and len(self.unset_literals) > 0:
            value = next(iter(self.unset_literals))
            self.watched_literals.append(value)
            self.unset_literals.remove(value)
    
    def unset_literal(self, literal: int):
        if -literal in self.set_literals:
            self.set_literals.remove(-literal)
            self.unset_literals.add(-literal)
        
        while len(self.watched_literals) < 2 and len(self.unset_literals) > 0:
            value = next(iter(self.unset_literals))
            self.watched_literals.append(value)
            self.unset_literals.remove(value)

    def __len__(self) -> int:
        return len(self.watched_literals) + len(self.unset_literals) + len(self.set_literals)

    def __iter__(self) -> Iterator[int]:
        return itertools.chain(iter(self.watched_literals), iter(self.unset_literals), iter(self.set_literals))

    def __contains__(self, item: int) -> bool:
        return item in self.watched_literals or item in self.unset_literals or item in self.set_literals


def join_clauses(a: Iterator[int], b: Iterator[int]):
    joined = set()
    for v in a:
        if -v not in b:
            joined.add(v)
    for v in b:
        if -v not in a:
            joined.add(v)
    return joined


# Equivalente à regra de explain lecionada em aulas
def explain(
    decision_stack: list[tuple[int, Optional[Clause]]],
    conflict_clause: set[int]
):
    for i in range(len(decision_stack) - 1, -1, -1):
        var, reason_clause = decision_stack[i]
        if -var not in conflict_clause or reason_clause is None:
            continue
        
        conflict_clause = join_clauses(conflict_clause, reason_clause)
    
    return Clause(conflict_clause, decision_stack)

# Função que define o valor de uma variável
# É chamada somente após a propagação
# Se houver um conflito, retorna a clausula de conflito
# Já passando pelo explain
def set_propagating_value(
    clauses: list[Clause],
    variable_values: list[int],
    decision_stack: list[tuple[int, bool]],
    value_to_set: int,
    reason: Clause,
    reverse_clauses: list[list[int]]
):
    variable_values[abs(value_to_set)] = value_to_set
    decision_stack.append((value_to_set, reason))
    for idx in reverse_clauses[abs(value_to_set)]:
        clause = clauses[idx].set_literal(value_to_set)

    for clause in clauses:
        solved = any([var == variable_values[abs(var)] for var in clause.watched_literals])
        if not solved and len(clause.watched_literals) == 0:
            return explain(decision_stack, set(iter(clause)))

    return None

# Rotina de propagação
def propagate(
    clauses: list[Clause],
    variable_values: list[int],
    decision_stack: list[tuple[int, Optional[Clause]]],
    reverse_clauses: list[list[int]]
):
    # Enquanto houver variáveis a serem propagadas
    while True:
        value_to_set = None
        reason_clause = None

        for clause in clauses:
            solved = any([var == variable_values[abs(var)] for var in clause.watched_literals])
            if not solved and len(clause.watched_literals) == 0:
                return explain(decision_stack, set(iter(clause)))

            if not solved:
                if len(clause.watched_literals) == 1:           # Encontramos uma clausula unitária
                    value_to_set = clause.watched_literals[0]
                    reason_clause = clause
                    break
                elif len(clause.watched_literals) == 0:         # Encontramos uma clausula sem solução
                    return []

        # Se não foi possível continuar a propagação, pare
        if value_to_set is None:
            break

        # Defino o valor da variável
        explanation = set_propagating_value(
            clauses,
            variable_values,
            decision_stack,
            value_to_set,
            reason_clause,
            reverse_clauses
        )

        # Se ouver conflito, logo um explicação
        if explanation is not None:
            return explanation

    return None

# Função responsável pela decisão
# Utiliza VSIDS para decidir
def decide(
    clauses: list[Clause],
    variable_values: list[int],
    decision_stack: list[tuple[int, Optional[Clause]]],
    reverse_clauses: list[list[int]],
    score: list[float]
):
    selected_var = None
    for i in range(1, len(score)):
        if variable_values[i] == 0 and (selected_var is None or score[i] > score[selected_var]):
            selected_var = i

    if selected_var is None:
        return False
    
    for idx in reverse_clauses[selected_var]:
        clauses[idx].set_literal(selected_var)
    variable_values[selected_var] = selected_var
    decision_stack.append((selected_var, None))
    return True

def get_biggest_variable(clauses: list[Clause]):
    res = 0
    for clause in clauses:
        for var in clause:
            res = max(res, abs(var))
    return res

def setup_vsids(clauses: list[Clause], num_variables: int):
    score = [0 for _ in range(num_variables + 1)]
    for clause in clauses:
        for var in clause:
            score[abs(var)] += 1
    return score

def generate_reverse_clauses(clauses: list[Clause], num_variables: int):
    reverse_clauses = [[] for _ in range(num_variables + 1)]
    for i in range(len(clauses)):
        for var in clauses[i]:
            reverse_clauses[abs(var)].append(i)
    return reverse_clauses

def vsids_decay(score: list[float], num_variables: int):
    decay = 0.95
    for i in range(num_variables + 1):
        score[i] *= decay

def solve(clauses: list[Clause]):
    num_variables = get_biggest_variable(clauses)

    # Guarda os valores das variáveis
    # Se 0, indefinida
    # Se -i, negativa
    # Se i, positiva
    variable_values = [0 for _ in range(num_variables + 1)]
    
    # Guarda em que clausulas uma variável é presente
    reverse_clauses = generate_reverse_clauses(clauses, num_variables)

    # Score para a heurístice de VSIDS
    score = setup_vsids(clauses, num_variables)

    # Stack com os valores das variáveis
    # Cada elemento é uma dupla. O primeiro elemento é o valor da variável.
    # O segundo elemento pode ser None, ou uma Clausula
    # Se for None, a variável assumiu o valor por conta de uma decisão
    # Caso contrário, o valor foi assumido por propagação
    # É guardada a cláusula que causou a propagação
    # Para a operação de explain
    decision_stack = []

    iteration = 1
    while True:

        if iteration % 10000 == 0:
            vsids_decay(score, num_variables)

        # Tentamos propagar, e verificamos se há conflito
        explanation = propagate(clauses, variable_values, decision_stack, reverse_clauses)
        if explanation is None:
            # Se não houver conflito, decidimos
            if not decide(clauses, variable_values, decision_stack, reverse_clauses, score):
                # Se decidimos tudo que tinha para ser decidido, SAT!!! :)
                return decision_stack
        elif len(explanation) == 0: # Se a explicação for uma clausula vazia, UNSAT :(
            return None
        else:
            # Adicionamos a explicação nas outras clausulas
            # Também precismaos atualizar o reverse_clauses e score
            clauses.append(explanation)
            for var in explanation:
                reverse_clauses[abs(var)].append(len(clauses) - 1)
                score[abs(var)] += 1

            # Realiza backtrack
            while len(decision_stack) > 0:
                value, reason = decision_stack.pop()
                variable_values[abs(value)] = 0

                if -value in explanation:
                    decision_stack.append((value, reason))
                    variable_values[abs(value)] = value
                    break

                for clause in clauses:
                    clause.unset_literal(value)
            
            # Realiza backtrack (acredito ser desnecessário)
            while len(decision_stack) > 0:
                value, reason = decision_stack.pop()
                variable_values[abs(value)] = 0
                for clause in clauses:
                    clause.unset_literal(value)

                if reason is None:
                    decision_stack.append((-value, {}))
                    variable_values[abs(value)] = -value
                    for idx in reverse_clauses[abs(value)]:
                        clauses[idx].set_literal(-value)
                    break

            # Se a stack de decisão ficar vazia, UNSAT :(
            if len(decision_stack) == 0:
                return None

        iteration += 1


def main():
    clauses = load_file(sys.argv[1])
    result = solve(clauses)
    if result is None:
        print("UNSATISFIABLE")
    else:
        print("SATISFIABLE")
        for value, _ in result:
            print(value, end=" ")
        print()



if __name__ == "__main__":
    main()
