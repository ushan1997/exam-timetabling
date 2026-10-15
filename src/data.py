from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
import math

import numpy as np
import pandas as pd

SESSION_TIMES = ["09:00", "13:00", "16:00"]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]


@dataclass
class Instance:
    exam_ids: list            # course_id of each exam (index e = 0..n-1)
    exam_names: list
    size: np.ndarray          # students enrolled in each exam
    conflict: np.ndarray      # conflict[i, j] = students taking both exam i and exam j
    room_ids: list
    room_cap: np.ndarray #Array — capacity of each room.
    n_days: int #How many days the exam period spans.
    sessions_per_day: int = 3 #Default 3 (morning/afternoon/evening).
    students: dict = field(default_factory=dict)  # exam index -> set of student ids

    @property
    def n_exams(self):
        return len(self.exam_ids)

    @property
    def n_rooms(self):
        return len(self.room_ids)

    @property
    def n_periods(self):
        return self.n_days * self.sessions_per_day

    def period_label(self, p):
        d, s = divmod(p, self.sessions_per_day)
        return f"Week {d // 5 + 1} {WEEKDAYS[d % 5]} {SESSION_TIMES[s]}"

    def conflict_pairs(self):
        """(i, j, shared_students) for every pair of exams that share at least one student."""
        return [(i, j, int(self.conflict[i, j]))
                for i, j in combinations(range(self.n_exams), 2) if self.conflict[i, j] > 0]

# data_dir → folder with the CSVs (default "data").
# n_exams → optional cap; keeps only the first k courses (used for the scalability study, e.g. k = 6, 10, 14, 18, 22).
# n_days → optional override. If not given, auto-computed as ceil(0.45 × n_exams).
# sessions_per_day → default 3.
def load_instance(data_dir="data", n_exams=None, n_days=None, sessions_per_day=3):
    """Build an instance. n_exams keeps the first k courses (used for the scalability study);
    n_days defaults to ceil(0.45 * n_exams), i.e. 10 days (two exam weeks) for all 22 exams."""
    
    data_dir = Path(data_dir)
    # read the CSVs
    enrol = pd.read_csv(data_dir / "schedule.csv")[["student_id", "course_id"]].drop_duplicates()
    courses = pd.read_csv(data_dir / "courses.csv").set_index("course_id")
    rooms = pd.read_csv(data_dir / "classrooms.csv")

    # pick which exams to include
    exam_ids = sorted(enrol.course_id.unique())
    if n_exams is not None:
        exam_ids = exam_ids[:n_exams]
        enrol = enrol[enrol.course_id.isin(exam_ids)]
    idx = {c: e for e, c in enumerate(exam_ids)}

    #build student sets per exam
    students = {idx[c]: set(g.student_id) for c, g in enrol.groupby("course_id")}
    n = len(exam_ids)
    
    #compute exam sizes and conflicts
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
