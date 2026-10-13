"""Independent check of the produced timetables, straight from the raw CSVs
(does not import anything from src/).

For each results/timetable_*.csv it checks:
  * every course has exactly one exam
  * no student has two exams in the same period
  * no room is used twice in the same period
  * rooms seat everyone enrolled
and recomputes the proximity penalty and room count.
"""
from collections import Counter
from itertools import combinations
from pathlib import Path

import pandas as pd

W_B2B, W_SAMEDAY, W_ROOM = 3, 1, 10
SESSIONS = ["09:00", "13:00", "16:00"]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]

enrol = pd.read_csv("data/schedule.csv")[["student_id", "course_id"]].drop_duplicates()
cap = pd.read_csv("data/classrooms.csv").set_index("classroom_id").capacity
students = enrol.groupby("course_id").student_id.apply(set).to_dict()


def period_index(label):  # "Week 1 Mon 09:00" -> 0
    _, week, day, t = label.split()
    return ((int(week) - 1) * 5 + DAYS.index(day)) * 3 + SESSIONS.index(t)


for f in sorted(Path("results").glob("timetable_*.csv")):
    tt = pd.read_csv(f)
    tt["p"] = tt.period.map(period_index)
    tt["room_list"] = tt.room_ids.astype(str).str.split(",").map(lambda xs: [int(x) for x in xs])
    problems = []

    if sorted(tt.course_id) != sorted(students):
        problems.append("course set mismatch")
    for p, g in tt.groupby("p"):
        c = Counter(s for cid in g.course_id for s in students[cid])
        if any(v > 1 for v in c.values()):
            problems.append(f"student clash in period {p}")
        rooms = [r for rl in g.room_list for r in rl]
        if len(rooms) != len(set(rooms)):
            problems.append(f"room clash in period {p}")
    for _, row in tt.iterrows():
        if cap[row.room_list].sum() < len(students[row.course_id]):
            problems.append(f"course {row.course_id} not fully seated")

    per = dict(zip(tt.course_id, tt.p))
    proximity = 0
    for a, b in combinations(per, 2):
        if per[a] // 3 == per[b] // 3:
            shared = len(students[a] & students[b])
            proximity += shared * (W_B2B if abs(per[a] - per[b]) == 1 else W_SAMEDAY)
    rooms_used = sum(len(r) for r in tt.room_list)
    print(f"{f.name}: {'FEASIBLE' if not problems else problems} | proximity {proximity} | "
          f"rooms {rooms_used} | total {proximity + W_ROOM * rooms_used}")

