"""Exact method: Constraint Programming with OR-Tools CP-SAT (0-1 / ILP-style model).

Sets: exams E, periods P (= days D x sessions S), rooms R.  s_ij = students shared by exams i, j.

Decision variables
  x[e,p]    in {0,1}   exam e is held in period p
  z[e,d]    in {0,1}   exam e is held on day d          (z[e,d] = sum_s x[e, dS+s])
  y[e,r]    in {0,1}   room r is used for exam e
  sd[i,j]   in {0,1}   exams i, j are on the same day            (only for s_ij > 0)
  adj[i,j]  in {0,1}   exams i, j are in consecutive sessions    (only for s_ij > 0)

Constraints
  (C1) sum_p x[e,p] = 1                                  each exam scheduled exactly once
  (H1) x[i,p] + x[j,p] <= 1                for s_ij > 0  no student sits two exams at once
  (H2) x[i,p] + x[j,p] + y[i,r] + y[j,r] <= 3  for s_ij = 0  exams sharing a period don't share a room
  (H3) sum_r cap_r * y[e,r] >= size_e                    enough seats
  (L1) z[i,d] + z[j,d] - 1 <= sd[i,j]                    same day  -> sd = 1
  (L2) x[i,p] + x[j,p+1] - 1 <= adj[i,j]  (and i<->j)    back-to-back on the same day -> adj = 1

Objective (identical to evaluate.py)
  min  sum_{i<j} s_ij * (W_SAMEDAY * sd[i,j] + (W_B2B - W_SAMEDAY) * adj[i,j])  +  W_ROOM * sum y
"""
import time
from itertools import combinations

from ortools.sat.python import cp_model

from evaluate import W_B2B, W_ROOM, W_SAMEDAY


class SolutionTrace(cp_model.CpSolverSolutionCallback):
    def __init__(self):
        super().__init__()
        self.points = []

    def on_solution_callback(self):
        self.points.append((self.WallTime(), self.ObjectiveValue()))


def min_same_day_pairs(n, days, S):
    """Fewest same-day pairs (and back-to-back pairs) possible when every exam needs its own
    period: spread exams as evenly as possible over the days. A day with k exams in S sessions
    has k*(k-1)/2 same-day pairs and at least max(0, 2k - S - 1) back-to-back pairs."""
    base, extra = divmod(n, days)
    loads = [base + 1] * extra + [base] * (days - extra)
    return (sum(k * (k - 1) // 2 for k in loads),
            sum(max(0, 2 * k - S - 1) for k in loads))


def solve_cpsat(inst, time_limit=60, workers=8, seed=0, log=False):
    m = cp_model.CpModel()
    E, R = range(inst.n_exams), range(inst.n_rooms)
    D, S = inst.n_days, inst.sessions_per_day
    P = range(inst.n_periods)

    x = {(e, p): m.NewBoolVar(f"x[{e},{p}]") for e in E for p in P}
    z = {(e, d): m.NewBoolVar(f"z[{e},{d}]") for e in E for d in range(D)}
    y = {(e, r): m.NewBoolVar(f"y[{e},{r}]") for e in E for r in R}

    for e in E:
        m.AddExactlyOne(x[e, p] for p in P)                                         # C1
        for d in range(D):
            m.Add(z[e, d] == sum(x[e, d * S + s] for s in range(S)))
        m.Add(sum(int(inst.room_cap[r]) * y[e, r] for r in R) >= int(inst.size[e]))  # H3

    penalty, sd_vars, adj_vars = [], [], []
    for i, j in combinations(E, 2):
        s_ij = int(inst.conflict[i, j])
        if s_ij == 0:
            for p in P:                                                              # H2
                for r in R:
                    m.AddBoolOr([x[i, p].Not(), x[j, p].Not(), y[i, r].Not(), y[j, r].Not()])
            continue

        for p in P:                                                                  # H1
            m.AddBoolOr([x[i, p].Not(), x[j, p].Not()])

        sd = m.NewBoolVar(f"sd[{i},{j}]")
        adj = m.NewBoolVar(f"adj[{i},{j}]")
        for d in range(D):                                                           # L1
            m.AddBoolOr([z[i, d].Not(), z[j, d].Not(), sd])
            for s in range(S - 1):                                                   # L2
                p = d * S + s
                m.AddBoolOr([x[i, p].Not(), x[j, p + 1].Not(), adj])
                m.AddBoolOr([x[j, p].Not(), x[i, p + 1].Not(), adj])
        penalty += [W_SAMEDAY * s_ij * sd, (W_B2B - W_SAMEDAY) * s_ij * adj]
        sd_vars.append(sd)
        adj_vars.append(adj)

    # Symmetry breaking: days are interchangeable, so fix exam 0 on day 0.
    m.Add(z[0, 0] == 1)

    # Implied constraints (tighten the lower bound). When every pair of exams clashes,
    # n exams over D days force a minimum number of same-day and back-to-back pairs.
    if len(sd_vars) == inst.n_exams * (inst.n_exams - 1) // 2:
        min_sd, min_adj = min_same_day_pairs(inst.n_exams, D, S)
        m.Add(sum(sd_vars) >= min_sd)
        m.Add(sum(adj_vars) >= min_adj)

    m.Minimize(sum(penalty) + W_ROOM * sum(y.values()))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = workers
    solver.parameters.random_seed = seed
    solver.parameters.log_search_progress = log

    trace = SolutionTrace()  # records (time, objective) every time a better solution is found
    start = time.perf_counter()
    status = solver.Solve(m, trace)
    runtime = time.perf_counter() - start

    result = {
        "method": "CP-SAT",
        "status": solver.StatusName(status),
        "runtime_s": runtime,
        "objective": None,
        "best_bound": solver.BestObjectiveBound(),
        "gap_pct": None,
        "trace": trace.points,
        "period": None,
        "rooms": None,
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        obj = solver.ObjectiveValue()
        result["objective"] = obj
        result["gap_pct"] = 0.0 if obj == 0 else 100 * (obj - result["best_bound"]) / obj
        result["period"] = [next(p for p in P if solver.Value(x[e, p])) for e in E]
        result["rooms"] = [[r for r in R if solver.Value(y[e, r])] for e in E]
    return result
