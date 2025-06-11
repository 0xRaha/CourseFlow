from datetime import time
from typing import List, Dict

class User:
    def __init__(self, user_id: str, firstname: str, lastname: str, email: str, password: str):
        self.user_id = user_id
        self.firstname = firstname
        self.lastname = lastname
        self.email = email
        self.password = password


class Student(User):
    def __init__(self, user_id: str, firstname: str, lastname: str, email: str, password: str, major: str, max_credits: int = 20, credits_taken: int = 0, enrolled_courses: List[str] = None,  completed_courses: List[str] = None):
        super().__init__(user_id, firstname, lastname, email, password)
        self.major = major
        self.max_credits = max_credits
        self.credits_taken = credits_taken

        self.enrolled_courses = enrolled_courses or []
        self.completed_courses = completed_courses or []


class Professor(User):
    def __init__(self, user_id: str, firstname: str, lastname: str, email: str, password: str, department: str, teaching_courses: List[str] = None):
        super().__init__(user_id, firstname, lastname, email, password)
        self.department = department
        self.teaching_courses = teaching_courses or []


class Course:
    def __init__(self, course_id: str, title: str, description: str, credits: int, capacity: int, professor_id: str = None, schedule: Dict[str, List[str]] = None, prerequisites: List[str] = None, current_students: List[str] = None):
        self.course_id = course_id
        self.title = title
        self.describtion = description
        self.credits = credits
        self.capacity = capacity
        self.professor_id = professor_id
        self.schedule = schedule or {}
        self.prerequisites = prerequisites or []
        self.current_students = current_students or []

    def has_time_conflict_with(self, other_course: "Course") -> bool:
        for day, times in self.schedule.items():
            if day in other_course.schedule:
                for t1, t2 in zip(times, other_course.schedule[day]):
                    if not (t2 <= t1 or t1 >= t2):
                        return True
            return False
        

class Department:
    def __init__(self, department_id: str, name: str):
        self.department_id = department_id
        self.name = name
        self.courses: List[Course] = []
        self.professors: List[Professor] = []
    
    def add_course(self, course: Course):
        if course not in self.courses:
            self.courses.append(course)
    
    def add_professor(self, professor: Professor):
        if professor not in self.professors:
            self.professors.append(professor)
            professor.department = self.name
