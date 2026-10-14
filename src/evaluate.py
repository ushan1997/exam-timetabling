from collections import defaultdict

W_B2B = 3
W_SAMEDAY = 1
W_ROOM = 10


def pair_penalty(inst, p_i, p_j):
    """Proximity weight (per shared student) for two exams placed in periods p_i and p_j."""
    S = inst.sessions_per_day
    if p_i // S != p_j // S:
        return 0
    return W_B2B if abs(p_i - p_j) == 1 else W_SAMEDAY


def evaluate(inst, period, rooms):
    # H1: student clashes, counted per student
    clashes = 0
    by_period = defaultdict(list)
    for e in range(inst.n_exams):
        by_period[period[e]].append(e)
    for exams in by_period.values():
        seen = defaultdict(int)
        for e in exams:
            for s in inst.students[e]:
                seen[s] += 1
        clashes += sum(c - 1 for c in seen.values() if c > 1)

    # H2: room used twice in the same period
    room_clashes = 0
    for exams in by_period.values():
        used = [r for e in exams for r in rooms[e]]
        room_clashes += len(used) - len(set(used))

    # H3: seat shortfall
    shortfall = sum(max(0, int(inst.size[e]) - int(sum(inst.room_cap[r] for r in rooms[e])))
                    for e in range(inst.n_exams))

    proximity = sum(s * pair_penalty(inst, period[i], period[j]) for i, j, s in inst.conflict_pairs())
    rooms_used = sum(len(rooms[e]) for e in range(inst.n_exams))
    return {
        "student_clashes": clashes,
        "room_clashes": room_clashes,
        "seat_shortfall": shortfall,
        "feasible": clashes == 0 and room_clashes == 0 and shortfall == 0,
        "proximity": proximity,
        "rooms_used": rooms_used,
        "total": proximity + W_ROOM * rooms_used,
    }


def timetable_table(inst, period, rooms):
    """Readable timetable as a list of dicts (one row per exam, ordered by period)."""
    rows = []
    for e in sorted(range(inst.n_exams), key=lambda e: period[e]):
        seats = int(sum(inst.room_cap[r] for r in rooms[e]))
        rows.append({
            "period": inst.period_label(period[e]),
            "course_id": inst.exam_ids[e],
            "course": inst.exam_names[e],
            "students": int(inst.size[e]),
            "rooms": len(rooms[e]),
            "seats": seats,
            "room_ids": ",".join(str(inst.room_ids[r]) for r in sorted(rooms[e])),
        })
    return rows
