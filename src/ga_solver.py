import random
import time

import numpy as np
from deap import algorithms, base, creator, tools

from evaluate import W_B2B, W_ROOM, W_SAMEDAY, evaluate

BIG_M = 100_000

if not hasattr(creator, "FitnessMin"):
    creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
if not hasattr(creator, "Individual"):
    creator.create("Individual", list, fitness=creator.FitnessMin)


def decode(inst, ind):
    period = list(ind[: inst.n_exams])
    rooms = [[] for _ in range(inst.n_exams)]
    order = np.argsort(-inst.room_cap)  # largest rooms first
    by_period = {}
    for e, p in enumerate(period):
        by_period.setdefault(p, []).append(e)
    for exams in by_period.values():
        free = list(order)
        for e in sorted(exams, key=lambda e: -inst.size[e]):
            seats = 0
            while seats < inst.size[e] and free:
                r = free.pop(0)
                rooms[e].append(int(r))
                seats += inst.room_cap[r]
    return period, rooms


def fitness(inst, ind):
    """Vectorised version of evaluate.py's objective (same numbers, much faster).
    The final best individual is re-checked with evaluate.py in solve_ga."""
    period, rooms = decode(inst, ind)
    p = np.asarray(period)
    S = inst.sessions_per_day
    upper = np.triu(inst.conflict, k=1)
    same_period = p[:, None] == p[None, :]
    same_day = (p[:, None] // S) == (p[None, :] // S)
    b2b = same_day & (np.abs(p[:, None] - p[None, :]) == 1)
    proximity = (upper * (W_SAMEDAY * (same_day & ~same_period) + (W_B2B - W_SAMEDAY) * b2b)).sum()
    clashes = (upper * same_period).sum()
    shortfall = sum(max(0, inst.size[e] - inst.room_cap[rooms[e]].sum()) for e in range(inst.n_exams))
    rooms_used = sum(len(r) for r in rooms)
    return (float(proximity + W_ROOM * rooms_used + BIG_M * (clashes + shortfall)),)


def solve_ga(inst, pop_size=100, n_gen=300, cxpb=0.8, mutpb=0.3, indpb=0.05, seed=0):
    random.seed(seed)
    np.random.seed(seed)
    P = inst.n_periods
    assert P >= inst.n_exams, "need at least one period per exam"

    tb = base.Toolbox()
    tb.register("indices", random.sample, range(P), P)
    tb.register("individual", tools.initIterate, creator.Individual, tb.indices)
    tb.register("population", tools.initRepeat, list, tb.individual)
    tb.register("evaluate", fitness, inst)
    tb.register("mate", tools.cxOrdered)
    tb.register("mutate", tools.mutShuffleIndexes, indpb=indpb)
    tb.register("select", tools.selTournament, tournsize=3)

    pop = tb.population(n=pop_size)
    hof = tools.HallOfFame(1)
    stats = tools.Statistics(lambda ind: ind.fitness.values[0])
    stats.register("min", np.min)
    stats.register("avg", np.mean)

    start = time.perf_counter()
    pop, logbook = algorithms.eaSimple(pop, tb, cxpb=cxpb, mutpb=mutpb, ngen=n_gen,
                                       stats=stats, halloffame=hof, verbose=False)
    runtime = time.perf_counter() - start

    best = hof[0]
    period, rooms = decode(inst, best)
    assert evaluate(inst, period, rooms)["total"] == best.fitness.values[0]
    return {
        "method": "GA",
        "status": "HEURISTIC",
        "runtime_s": runtime,
        "objective": best.fitness.values[0],
        "period": period,
        "rooms": rooms,
        "history": logbook.select("min"),
        "seed": seed,
    }
