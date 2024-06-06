import gradescope as gs

course_ids = gs.get_courses()
print(course_ids)
for id in course_ids:
    print(gs.get_course_assignments(id))