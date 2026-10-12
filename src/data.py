import numpy as np
import pandas as pd

from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
import math

def load_instance(data_dir="data", n_exams=None, n_days=None, sessions_per_day=3):
    """Build an instance. n_exams keeps the first k courses (used for the scalability study);
    n_days defaults to ceil(0.45 * n_exams), i.e. 10 days (two exam weeks) for all 22 exams."""
    data_dir = Path(data_dir)
    enrol = pd.read_csv(data_dir / "schedule.csv")[["student_id", "course_id"]].drop_duplicates()
    courses = pd.read_csv(data_dir / "courses.csv").set_index("course_id")
    rooms = pd.read_csv(data_dir / "classrooms.csv")

    exam_ids = sorted(enrol.course_id.unique())
    if n_exams is not None:
        exam_ids = exam_ids[:n_exams]
        enrol = enrol[enrol.course_id.isin(exam_ids)]
    idx = {c: e for e, c in enumerate(exam_ids)}

    students = {idx[c]: set(g.student_id) for c, g in enrol.groupby("course_id")}
    n = len(exam_ids)
    size = np.array([len(students[e]) for e in range(n)])
    conflict = np.zeros((n, n), dtype=int)
    for i, j in combinations(range(n), 2):
        conflict[i, j] = conflict[j, i] = len(students[i] & students[j])

    if n_days is None:
        n_days = math.ceil(0.45 * n)

    return Instance(
        exam_ids=[int(c) for c in exam_ids],
        exam_names=[courses.loc[c, "course_name"] for c in exam_ids],
        size=size,
        conflict=conflict,
        room_ids=rooms.classroom_id.tolist(),
        room_cap=rooms.capacity.to_numpy(),
        n_days=n_days,
        sessions_per_day=sessions_per_day,
        students=students,
    )
