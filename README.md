# exam-timetabling

---------------------------

# Exam Timetabling — Exact (CP-SAT) vs Heuristic (Genetic Algorithm)

**Module:** IT5082 Optimization Methods — Programming Assignment
**Members:** _<Member 1 name, ID>_ · _<Member 2 name, ID>_

**Problem.** Put each course's final exam into a time slot (period) and one or more rooms so that:

* no student has two exams at the same time (hard),
* every exam has enough seats in the rooms it is given (hard),
* a room is not used by two exams at the same time (hard),
* students' exams are spread out: same-day exams, and especially back-to-back exams, are penalised (soft),
* as few rooms as possible are opened, since each needs an invigilator (soft).

**Dataset.** [University Exam Scheduling (Kaggle, CC0)](https://www.kaggle.com/datasets/smrezwanulazad/exam-schedule):
`schedule.csv` (student–course enrolments), `courses.csv`, `classrooms.csv` (capacities), `timeslots.csv`,
`students.csv`, `instructors.csv`.

**Methods.** Exact: Constraint Programming with **OR-Tools CP-SAT**. Heuristic: **Genetic Algorithm** with **DEAP**.

## Data.py

Dataset
* schedule.csv   -> (student_id, course_id) enrolments. One exam per course.
* courses.csv    -> course names (for nicer output).
* classrooms.csv -> rooms and their seating capacity.
* timeslots.csv  -> only used to justify a Mon-Fri exam week. 44 of its 100 rows have
                    end_time <= start_time, so the raw slots are not usable as exam periods.
                    We use a clean grid instead: N days x 3 sessions (09:00, 13:00, 16:00).


Only `schedule.csv` (who takes which course) and `classrooms.csv` (room capacities) drive the model.
The existing `classroom_id`/`timeslot_id` columns in `schedule.csv` are the teaching timetable, not exams, so we ignore them.

## cpsat_solver.py

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

## evaludate.py

"""Shared objective + feasibility check, used by BOTH solvers so their results are comparable.

A solution is: period[e] (int) and rooms[e] (list of room indices) for every exam e.

Hard constraints (must be 0 for a feasible timetable)
  H1 student clash   : a student has two exams in the same period
  H2 room clash      : a room is used by two exams in the same period
  H3 capacity        : seats in the rooms given to an exam < students enrolled

Soft objective (minimise)
  proximity = sum over exam pairs (i, j) sharing s_ij students that sit on the same day:
                 W_B2B     * s_ij   if they are in consecutive sessions (back-to-back)
                 W_SAMEDAY * s_ij   otherwise (same day, with a gap)
  rooms_used = total rooms opened (each room needs an invigilator)
  total = proximity + W_ROOM * rooms_used
"""

## ga_solver.py

"""Heuristic method: Genetic Algorithm with DEAP.

Encoding : a permutation of the P period indices; exam e is placed in period ind[e].
           Every exam therefore gets its own period, so student clashes (H1) can never occur.
           This fits the data: every pair of courses shares students, so no two exams could
           share a period anyway.
Decoding : rooms are assigned greedily per period - largest free rooms first until the
           exam's students are seated. This uses the fewest rooms for that exam.
Fitness  : evaluate.py's total (proximity + W_ROOM * rooms), plus a big penalty for any
           hard-constraint violation (never triggered with this encoding, kept as a guard).
Operators: ordered crossover (cxOrdered), swap mutation (mutShuffleIndexes),
           tournament selection (k=3), elitism via HallOfFame.
"""