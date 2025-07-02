import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

class Database:
    def __init__(self, db_name='university.db'):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_name)
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table (base for all user types)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                user_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Students table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                user_id TEXT PRIMARY KEY,
                student_id TEXT UNIQUE NOT NULL,
                enrollment_date DATE,
                graduation_date DATE,
                gpa REAL DEFAULT 0.0,
                year_level INTEGER DEFAULT 1,
                major TEXT,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Professors table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS professors (
                user_id TEXT PRIMARY KEY,
                employee_id TEXT UNIQUE NOT NULL,
                department TEXT NOT NULL,
                position TEXT DEFAULT 'Assistant Professor',
                hire_date DATE,
                office_location TEXT,
                phone TEXT,
                research_interests TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Admins table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                user_id TEXT PRIMARY KEY,
                admin_level INTEGER DEFAULT 1,
                permissions TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Departments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS departments (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                code TEXT UNIQUE NOT NULL,
                description TEXT,
                head_professor_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (head_professor_id) REFERENCES professors (user_id)
            )
        ''')
        
        # Courses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS courses (
                id TEXT PRIMARY KEY,
                course_code TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                credits INTEGER NOT NULL,
                department_id TEXT,
                prerequisites TEXT,
                max_students INTEGER DEFAULT 30,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (department_id) REFERENCES departments (id)
            )
        ''')
        
        # Course sections table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS course_sections (
                id TEXT PRIMARY KEY,
                course_id TEXT NOT NULL,
                professor_id TEXT NOT NULL,
                section_number TEXT NOT NULL,
                semester TEXT NOT NULL,
                year INTEGER NOT NULL,
                schedule TEXT,
                room TEXT,
                max_capacity INTEGER DEFAULT 30,
                current_enrollment INTEGER DEFAULT 0,
                status TEXT DEFAULT 'open',
                FOREIGN KEY (course_id) REFERENCES courses (id),
                FOREIGN KEY (professor_id) REFERENCES professors (user_id),
                UNIQUE(course_id, section_number, semester, year)
            )
        ''')
        
        # Enrollments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS enrollments (
                id TEXT PRIMARY KEY,
                student_id TEXT NOT NULL,
                section_id TEXT NOT NULL,
                enrollment_date DATE DEFAULT CURRENT_DATE,
                status TEXT DEFAULT 'enrolled',
                grade TEXT,
                grade_points REAL,
                FOREIGN KEY (student_id) REFERENCES students (user_id),
                FOREIGN KEY (section_id) REFERENCES course_sections (id),
                UNIQUE(student_id, section_id)
            )
        ''')
        
        # Assignments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assignments (
                id TEXT PRIMARY KEY,
                section_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                due_date DATETIME,
                max_points REAL DEFAULT 100.0,
                assignment_type TEXT DEFAULT 'homework',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (section_id) REFERENCES course_sections (id)
            )
        ''')
        
        # Submissions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                id TEXT PRIMARY KEY,
                assignment_id TEXT NOT NULL,
                student_id TEXT NOT NULL,
                submission_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                file_path TEXT,
                comments TEXT,
                score REAL,
                feedback TEXT,
                status TEXT DEFAULT 'submitted',
                FOREIGN KEY (assignment_id) REFERENCES assignments (id),
                FOREIGN KEY (student_id) REFERENCES students (user_id),
                UNIQUE(assignment_id, student_id)
            )
        ''')
        
        # Announcements table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS announcements (
                id TEXT PRIMARY KEY,
                section_id TEXT,
                author_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_urgent BOOLEAN DEFAULT 0,
                FOREIGN KEY (section_id) REFERENCES course_sections (id),
                FOREIGN KEY (author_id) REFERENCES users (id)
            )
        ''')
        
        # Attendance table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id TEXT PRIMARY KEY,
                student_id TEXT NOT NULL,
                section_id TEXT NOT NULL,
                date DATE NOT NULL,
                status TEXT DEFAULT 'present',
                notes TEXT,
                FOREIGN KEY (student_id) REFERENCES students (user_id),
                FOREIGN KEY (section_id) REFERENCES course_sections (id),
                UNIQUE(student_id, section_id, date)
            )
        ''')
        
        conn.commit()
        conn.close()

class User:
    def __init__(self, first_name, last_name, email, username, password, user_type):
        self.id = str(uuid.uuid4())
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.username = username
        self.password_hash = generate_password_hash(password)
        self.user_type = user_type
        self.created_at = datetime.now()
        self.is_active = True
    
    def save(self):
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO users (id, first_name, last_name, email, username, password_hash, user_type, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (self.id, self.first_name, self.last_name, self.email, self.username, 
              self.password_hash, self.user_type, self.created_at, self.is_active))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def authenticate(username, password):
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, password_hash, user_type FROM users WHERE username = ? AND is_active = 1', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[1], password):
            return {'id': user[0], 'user_type': user[2]}
        return None
    
    @staticmethod
    def get_by_id(user_id):
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        return user

class Student(User):
    def __init__(self, first_name, last_name, email, username, password, major=None):
        super().__init__(first_name, last_name, email, username, password, 'student')
        self.student_id = self.generate_student_id()
        self.enrollment_date = datetime.now().date()
        self.gpa = 0.0
        self.year_level = 1
        self.major = major
        self.status = 'active'
    
    def generate_student_id(self):
        return f"STU{datetime.now().year}{str(uuid.uuid4())[:8].upper()}"
    
    def save(self):
        super().save()
        
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO students (user_id, student_id, enrollment_date, gpa, year_level, major, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (self.id, self.student_id, self.enrollment_date, self.gpa, self.year_level, self.major, self.status))
        
        conn.commit()
        conn.close()
    
    def enroll_in_section(self, section_id):
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if section exists and has capacity
        cursor.execute('''
            SELECT current_enrollment, max_capacity, status 
            FROM course_sections WHERE id = ?
        ''', (section_id,))
        section = cursor.fetchone()
        
        if not section:
            raise ValueError("Section not found")
        
        if section[2] != 'open':
            raise ValueError("Section is not open for enrollment")
        
        if section[0] >= section[1]:
            raise ValueError("Section is full")
        
        # Check if already enrolled
        cursor.execute('SELECT id FROM enrollments WHERE student_id = ? AND section_id = ?', 
                      (self.id, section_id))
        if cursor.fetchone():
            raise ValueError("Already enrolled in this section")
        
        # Enroll student
        enrollment_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO enrollments (id, student_id, section_id, enrollment_date, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (enrollment_id, self.id, section_id, datetime.now().date(), 'enrolled'))
        
        # Update section enrollment count
        cursor.execute('''
            UPDATE course_sections 
            SET current_enrollment = current_enrollment + 1 
            WHERE id = ?
        ''', (section_id,))
        
        conn.commit()
        conn.close()
    
    def get_enrolled_sections(self):
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT cs.*, c.title, c.course_code, c.credits,
                   u.first_name, u.last_name, e.grade, e.status
            FROM enrollments e
            JOIN course_sections cs ON e.section_id = cs.id
            JOIN courses c ON cs.course_id = c.id
            JOIN professors p ON cs.professor_id = p.user_id
            JOIN users u ON p.user_id = u.id
            WHERE e.student_id = ? AND e.status = 'enrolled'
        ''', (self.id,))
        
        sections = cursor.fetchall()
        conn.close()
        return sections

class Professor(User):
    def __init__(self, first_name, last_name, email, username, password, department, 
                 position="Assistant Professor", office_location=None, phone=None):
        super().__init__(first_name, last_name, email, username, password, 'professor')
        self.employee_id = self.generate_employee_id()
        self.department = department
        self.position = position
        self.hire_date = datetime.now().date()
        self.office_location = office_location
        self.phone = phone
        self.research_interests = ""
    
    def generate_employee_id(self):
        return f"EMP{datetime.now().year}{str(uuid.uuid4())[:8].upper()}"
    
    def save(self):
        super().save()
        
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO professors (user_id, employee_id, department, position, hire_date, 
                                  office_location, phone, research_interests)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (self.id, self.employee_id, self.department, self.position, self.hire_date,
              self.office_location, self.phone, self.research_interests))
        
        conn.commit()
        conn.close()
    
    def create_course_section(self, course_id, section_number, semester, year, 
                            schedule=None, room=None, max_capacity=30):
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        section_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO course_sections (id, course_id, professor_id, section_number, 
                                       semester, year, schedule, room, max_capacity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (section_id, course_id, self.id, section_number, semester, year, 
              schedule, room, max_capacity))
        
        conn.commit()
        conn.close()
        return section_id
    
    def get_teaching_sections(self):
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT cs.*, c.title, c.course_code, c.credits
            FROM course_sections cs
            JOIN courses c ON cs.course_id = c.id
            WHERE cs.professor_id = ?
        ''', (self.id,))
        
        sections = cursor.fetchall()
        conn.close()
        return sections
    
    def get_section_students(self, section_id):
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.first_name, u.last_name, u.email, s.student_id, 
                   e.enrollment_date, e.grade, e.status
            FROM enrollments e
            JOIN students s ON e.student_id = s.user_id
            JOIN users u ON s.user_id = u.id
            WHERE e.section_id = ?
        ''', (section_id,))
        
        students = cursor.fetchall()
        conn.close()
        return students

class Admin(User):
    def __init__(self, first_name, last_name, email, username, password, admin_level=1):
        super().__init__(first_name, last_name, email, username, password, 'admin')
        self.admin_level = admin_level
        self.permissions = "full" if admin_level >= 3 else "limited"
    
    def save(self):
        super().save()
        
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO admins (user_id, admin_level, permissions)
            VALUES (?, ?, ?)
        ''', (self.id, self.admin_level, self.permissions))
        
        conn.commit()
        conn.close()
    
    def create_course(self, course_code, title, description, credits, department_id, 
                     prerequisites=None, max_students=30):
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        course_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO courses (id, course_code, title, description, credits, 
                               department_id, prerequisites, max_students)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (course_id, course_code, title, description, credits, 
              department_id, prerequisites, max_students))
        
        conn.commit()
        conn.close()
        return course_id
    
    def create_department(self, name, code, description=None, head_professor_id=None):
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        dept_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO departments (id, name, code, description, head_professor_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (dept_id, name, code, description, head_professor_id))
        
        conn.commit()
        conn.close()
        return dept_id
    
    def get_all_users(self, user_type=None):
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        if user_type:
            cursor.execute('SELECT * FROM users WHERE user_type = ?', (user_type,))
        else:
            cursor.execute('SELECT * FROM users')
        
        users = cursor.fetchall()
        conn.close()
        return users
    
    def deactivate_user(self, user_id):
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('UPDATE users SET is_active = 0 WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()

class Course:
    @staticmethod
    def get_all_active():
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.*, d.name as department_name 
            FROM courses c
            LEFT JOIN departments d ON c.department_id = d.id
            WHERE c.is_active = 1
        ''')
        
        courses = cursor.fetchall()
        conn.close()
        return courses
    
    @staticmethod
    def get_available_sections(course_id, semester, year):
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT cs.*, u.first_name, u.last_name, p.department
            FROM course_sections cs
            JOIN professors p ON cs.professor_id = p.user_id
            JOIN users u ON p.user_id = u.id
            WHERE cs.course_id = ? AND cs.semester = ? AND cs.year = ? 
            AND cs.status = 'open' AND cs.current_enrollment < cs.max_capacity
        ''', (course_id, semester, year))
        
        sections = cursor.fetchall()
        conn.close()
        return sections

# Utility functions for the system
class Utils:
    @staticmethod
    def calculate_gpa(student_id):
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT grade_points, c.credits
            FROM enrollments e
            JOIN course_sections cs ON e.section_id = cs.id
            JOIN courses c ON cs.course_id = c.id
            WHERE e.student_id = ? AND e.grade_points IS NOT NULL
        ''', (student_id,))
        
        grades = cursor.fetchall()
        conn.close()
        
        if not grades:
            return 0.0
        
        total_points = sum(grade[0] * grade[1] for grade in grades)
        total_credits = sum(grade[1] for grade in grades)
        
        return round(total_points / total_credits, 2) if total_credits > 0 else 0.0
    
    @staticmethod
    def get_semester_schedule(user_id, semester, year):
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.course_code, c.title, cs.section_number, cs.schedule, cs.room
            FROM enrollments e
            JOIN course_sections cs ON e.section_id = cs.id
            JOIN courses c ON cs.course_id = c.id
            WHERE e.student_id = ? AND cs.semester = ? AND cs.year = ?
        ''', (user_id, semester, year))
        
        schedule = cursor.fetchall()
        conn.close()
        return schedule
