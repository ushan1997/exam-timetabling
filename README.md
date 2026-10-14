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


Dataset
* schedule.csv   -> (student_id, course_id) enrolments. One exam per course.
* courses.csv    -> course names (for nicer output).
* classrooms.csv -> rooms and their seating capacity.
* timeslots.csv  -> only used to justify a Mon-Fri exam week. 44 of its 100 rows have
                    end_time <= start_time, so the raw slots are not usable as exam periods.
                    We use a clean grid instead: N days x 3 sessions (09:00, 13:00, 16:00).


Only `schedule.csv` (who takes which course) and `classrooms.csv` (room capacities) drive the model.
The existing `classroom_id`/`timeslot_id` columns in `schedule.csv` are the teaching timetable, not exams, so we ignore them.