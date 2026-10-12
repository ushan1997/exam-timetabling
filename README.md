# exam-timetabling

---------------------------
Dataset
* schedule.csv   -> (student_id, course_id) enrolments. One exam per course.
* courses.csv    -> course names (for nicer output).
* classrooms.csv -> rooms and their seating capacity.
* timeslots.csv  -> only used to justify a Mon-Fri exam week. 44 of its 100 rows have
                    end_time <= start_time, so the raw slots are not usable as exam periods.
                    We use a clean grid instead: N days x 3 sessions (09:00, 13:00, 16:00).