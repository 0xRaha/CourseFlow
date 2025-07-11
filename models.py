import sqlite3
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import json

class Database:
    def __init__(self, db_name='university.db'):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn
    
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
                max_credits INTEGER DEFAULT 20,
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
                average_rating REAL DEFAULT 0.0,
                total_ratings INTEGER DEFAULT 0,
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
                schedule TEXT NOT NULL,
                room TEXT,
                max_capacity INTEGER DEFAULT 30,
                current_enrollment INTEGER DEFAULT 0,
                status TEXT DEFAULT 'open',
                grades_submitted BOOLEAN DEFAULT 0,
                semester_ended BOOLEAN DEFAULT 0,
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
                can_disenroll BOOLEAN DEFAULT 1,
                FOREIGN KEY (student_id) REFERENCES students (user_id),
                FOREIGN KEY (section_id) REFERENCES course_sections (id),
                UNIQUE(student_id, section_id)
            )
        ''')
        
        # Course ratings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS course_ratings (
                id TEXT PRIMARY KEY,
                student_id TEXT NOT NULL,
                course_id TEXT NOT NULL,
                rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                review TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students (user_id),
                FOREIGN KEY (course_id) REFERENCES courses (id),
                UNIQUE(student_id, course_id)
            )
        ''')
        
        # Academic calendar table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS academic_calendar (
                id TEXT PRIMARY KEY,
                semester TEXT NOT NULL,
                year INTEGER NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                enrollment_start DATE,
                enrollment_end DATE,
                is_current BOOLEAN DEFAULT 0,
                UNIQUE(semester, year)
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
        self.password_hash = generate_password_hash(password) if password else None
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
        
        if user and check_password_hash(user['password_hash'], password):
            return {'id': user['id'], 'user_type': user['user_type']}
        return None
    
    @staticmethod
    def get_by_id(user_id):
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        return dict(user) if user else None
    
    @staticmethod
    def get_all_users(user_type=None):
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        if user_type:
            cursor.execute('SELECT * FROM users WHERE user_type = ? AND is_active = 1', (user_type,))
        else:
            cursor.execute('SELECT * FROM users WHERE is_active = 1')
        
        users = cursor.fetchall()
        conn.close()
        
        return [dict(user) for user in users]

class Student(User):
    def __init__(self, first_name, last_name, email, username, password, major=None):
        super().__init__(first_name, last_name, email, username, password, 'student')
        self.student_id = self.generate_student_id()
        self.enrollment_date = datetime.now().date()
        self.gpa = 0.0
        self.year_level = 1
        self.major = major
        self.status = 'active'
        self.max_credits = 20  # Default for first year
    
    def generate_student_id(self):
        return f"STU{datetime.now().year}{str(uuid.uuid4())[:8].upper()}"
    
    def save(self):
        super().save()
        
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO students (user_id, student_id, enrollment_date, gpa, year_level, major, status, max_credits)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (self.id, self.student_id, self.enrollment_date, self.gpa, self.year_level, self.major, self.status, self.max_credits))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_by_user_id(user_id):
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.*, s.student_id, s.gpa, s.year_level, s.major, s.status
            FROM users u
            JOIN students s ON u.id = s.user_id
            WHERE u.id = ?
        ''', (user_id,))
        
        student = cursor.fetchone()
        conn.close()
        
        return dict(student) if student else None
    
    def calculate_max_credits(self):
        """Calculate max credits based on year level and GPA"""
        if self.year_level == 1:
            return 20
        elif self.gpa == 0.0:
            return 14
        elif self.gpa >= 3.0:
            return 24
        else:
            return 20
    
    def get_current_credits(self, semester, year):
        """Get total credits for current semester"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT SUM(c.credits)
            FROM enrollments e
            JOIN course_sections cs ON e.section_id = cs.id
            JOIN courses c ON cs.course_id = c.id
            WHERE e.student_id = ? AND cs.semester = ? AND cs.year = ? AND e.status = 'enrolled'
        ''', (self.id, semester, year))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result[0] else 0
    
    def check_prerequisites(self, course_id):
        """Check if student has completed prerequisites for a course"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get course prerequisites
        cursor.execute('SELECT prerequisites FROM courses WHERE id = ?', (course_id,))
        prereq_result = cursor.fetchone()
        
        if not prereq_result or not prereq_result['prerequisites']:
            conn.close()
            return True
        
        prerequisites = json.loads(prereq_result['prerequisites']) if prereq_result['prerequisites'] else []
        
        # Check if student has completed all prerequisites with passing grade
        for prereq_code in prerequisites:
            cursor.execute('''
                SELECT e.grade_points
                FROM enrollments e
                JOIN course_sections cs ON e.section_id = cs.id
                JOIN courses c ON cs.course_id = c.id
                WHERE e.student_id = ? AND c.course_code = ? AND e.grade_points >= 2.0
            ''', (self.id, prereq_code))
            
            if not cursor.fetchone():
                conn.close()
                return False
        
        conn.close()
        return True
    
    def check_time_conflict(self, new_section_id):
        """Check if there's a time conflict with existing enrolled courses"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get new section schedule
        cursor.execute('''
            SELECT schedule, semester, year FROM course_sections WHERE id = ?
        ''', (new_section_id,))
        new_section = cursor.fetchone()
        
        if not new_section:
            conn.close()
            return True  # No conflict if section doesn't exist
        
        # Get student's current enrollments for the same semester
        cursor.execute('''
            SELECT cs.schedule
            FROM enrollments e
            JOIN course_sections cs ON e.section_id = cs.id
            WHERE e.student_id = ? AND cs.semester = ? AND cs.year = ? AND e.status = 'enrolled'
        ''', (self.id, new_section['semester'], new_section['year']))
        
        current_schedules = cursor.fetchall()
        conn.close()
        
        # Parse schedule format (e.g., "MWF 10:00-11:00")
        new_schedule = new_section['schedule']
        
        for current in current_schedules:
            if self._has_time_overlap(new_schedule, current['schedule']):
                return True
        
        return False
    
    def _has_time_overlap(self, schedule1, schedule2):
        """Check if two schedules overlap"""
        # Simple implementation - you can make this more sophisticated
        # Format: "MWF 10:00-11:00"
        try:
            days1, time1 = schedule1.split(' ')
            days2, time2 = schedule2.split(' ')
            
            # Check if there are common days
            common_days = any(day in days2 for day in days1)
            
            if common_days:
                # Parse times
                start1, end1 = time1.split('-')
                start2, end2 = time2.split('-')
                
                # Convert to comparable format
                start1_h, start1_m = map(int, start1.split(':'))
                end1_h, end1_m = map(int, end1.split(':'))
                start2_h, start2_m = map(int, start2.split(':'))
                end2_h, end2_m = map(int, end2.split(':'))
                
                # Check overlap
                start1_total = start1_h * 60 + start1_m
                end1_total = end1_h * 60 + end1_m
                start2_total = start2_h * 60 + start2_m
                end2_total = end2_h * 60 + end2_m
                
                return not (end1_total <= start2_total or end2_total <= start1_total)
        except:
            # If parsing fails, assume no conflict
            return False
        
        return False
    
    def enroll_in_section(self, section_id):
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get section and course info
        cursor.execute('''
            SELECT cs.current_enrollment, cs.max_capacity, cs.status, cs.semester, cs.year, c.credits, c.id
            FROM course_sections cs
            JOIN courses c ON cs.course_id = c.id
            WHERE cs.id = ?
        ''', (section_id,))
        section = cursor.fetchone()
        
        if not section:
            raise ValueError("Section not found")
        
        if section['status'] != 'open':
            raise ValueError("Section is not open for enrollment")
        
        if section['current_enrollment'] >= section['max_capacity']:
            raise ValueError("Section is full")
        
        # Check if already enrolled
        cursor.execute('SELECT id FROM enrollments WHERE student_id = ? AND section_id = ?', 
                      (self.id, section_id))
        if cursor.fetchone():
            raise ValueError("Already enrolled in this section")
        
        # Check prerequisites
        if not self.check_prerequisites(section[6]):
            raise ValueError("Prerequisites not met")
        
        # Check time conflicts
        if self.check_time_conflict(section_id):
            raise ValueError("Time conflict with another enrolled course")
        
        # Check credit limit
        current_credits = self.get_current_credits(section['semester'], section['year'])
        max_credits = self.calculate_max_credits()
        
        if current_credits + section['credits'] > max_credits:
            raise ValueError(f"Enrollment would exceed max credits ({max_credits})")
        
        # Enroll student
        enrollment_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO enrollments (id, student_id, section_id, enrollment_date, status, can_disenroll)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (enrollment_id, self.id, section_id, datetime.now().date(), 'enrolled', True))
        
        # Update section enrollment count
        cursor.execute('''
            UPDATE course_sections 
            SET current_enrollment = current_enrollment + 1 
            WHERE id = ?
        ''', (section_id,))
        
        conn.commit()
        conn.close()
    
    def disenroll_from_section(self, section_id):
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if can disenroll (no grades submitted)
        cursor.execute('''
            SELECT can_disenroll FROM enrollments 
            WHERE student_id = ? AND section_id = ? AND status = 'enrolled'
        ''', (self.id, section_id))
        
        enrollment = cursor.fetchone()
        if not enrollment:
            raise ValueError("Not enrolled in this section")
        
        if not enrollment['can_disenroll']:
            raise ValueError("Cannot disenroll - grades have been submitted")
        
        # Remove enrollment
        cursor.execute('''
            DELETE FROM enrollments WHERE student_id = ? AND section_id = ?
        ''', (self.id, section_id))
        
        # Update section enrollment count
        cursor.execute('''
            UPDATE course_sections 
            SET current_enrollment = current_enrollment - 1 
            WHERE id = ?
        ''', (section_id,))
        
        conn.commit()
        conn.close()
    
    def get_class_schedule(self, semester, year):
        """Get student's class schedule for a semester"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.course_code, c.title, c.credits, cs.section_number, 
                   cs.schedule, cs.room, u.first_name, u.last_name, e.grade
            FROM enrollments e
            JOIN course_sections cs ON e.section_id = cs.id
            JOIN courses c ON cs.course_id = c.id
            JOIN professors p ON cs.professor_id = p.user_id
            JOIN users u ON p.user_id = u.id
            WHERE e.student_id = ? AND cs.semester = ? AND cs.year = ? AND e.status = 'enrolled'
            ORDER BY c.course_code
        ''', (self.id, semester, year))
        
        schedule = cursor.fetchall()
        conn.close()
        return [dict(row) for row in schedule]
    
    def get_all_grades(self):
        """Get all grades across all semesters"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.course_code, c.title, c.credits, cs.semester, cs.year, 
                   e.grade, e.grade_points, u.first_name, u.last_name
            FROM enrollments e
            JOIN course_sections cs ON e.section_id = cs.id
            JOIN courses c ON cs.course_id = c.id
            JOIN professors p ON cs.professor_id = p.user_id
            JOIN users u ON p.user_id = u.id
            WHERE e.student_id = ? AND e.status = 'enrolled'
            ORDER BY cs.year DESC, cs.semester DESC, c.course_code
        ''', (self.id,))
        
        grades = cursor.fetchall()
        conn.close()
        return [dict(row) for row in grades]
    
    def rate_course(self, course_id, rating, review=None):
        """Rate a course (1-5 stars)"""
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")
        
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if student has taken this course
        cursor.execute('''
            SELECT COUNT(*) FROM enrollments e
            JOIN course_sections cs ON e.section_id = cs.id
            WHERE e.student_id = ? AND cs.course_id = ? AND e.grade_points IS NOT NULL
        ''', (self.id, course_id))
        
        if cursor.fetchone()[0] == 0:
            raise ValueError("Can only rate courses you have completed")
        
        # Insert or update rating
        cursor.execute('''
            INSERT OR REPLACE INTO course_ratings (id, student_id, course_id, rating, review)
            VALUES (?, ?, ?, ?, ?)
        ''', (str(uuid.uuid4()), self.id, course_id, rating, review))
        
        # Update course average rating
        cursor.execute('''
            SELECT AVG(rating), COUNT(*) FROM course_ratings WHERE course_id = ?
        ''', (course_id,))
        
        avg_rating, total_ratings = cursor.fetchone()
        
        cursor.execute('''
            UPDATE courses SET average_rating = ?, total_ratings = ? WHERE id = ?
        ''', (avg_rating, total_ratings, course_id))
        
        conn.commit()
        conn.close()

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
    
    @staticmethod
    def get_by_user_id(user_id):
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.*, p.employee_id, p.department, p.position, p.office_location, p.phone
            FROM users u
            JOIN professors p ON u.id = p.user_id
            WHERE u.id = ?
        ''', (user_id,))
        
        professor = cursor.fetchone()
        conn.close()
        
        return dict(professor) if professor else None
    
    def create_course_section(self, course_id, section_number, semester, year, 
                            schedule, room=None, max_capacity=30):
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
    
    def submit_grades(self, section_id, student_grades):
        """Submit grades for students in a section"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if semester has ended
        cursor.execute('''
            SELECT semester_ended FROM course_sections WHERE id = ?
        ''', (section_id,))
        
        section = cursor.fetchone()
        if section and section['semester_ended']:
            raise ValueError("Cannot submit grades - semester has ended")
        
        # Submit grades
        for student_id, grade_data in student_grades.items():
            grade_letter = grade_data['grade']
            grade_points = grade_data['points']
            
            cursor.execute('''
                UPDATE enrollments 
                SET grade = ?, grade_points = ?, can_disenroll = 0
                WHERE student_id = ? AND section_id = ?
            ''', (grade_letter, grade_points, student_id, section_id))
        
        # Mark grades as submitted
        cursor.execute('''
            UPDATE course_sections SET grades_submitted = 1 WHERE id = ?
        ''', (section_id,))
        
        conn.commit()
        conn.close()
    
    def get_teaching_sections(self, semester=None, year=None):
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        if semester and year:
            cursor.execute('''
                SELECT cs.*, c.title, c.course_code, c.credits, cs.current_enrollment, cs.max_capacity
                FROM course_sections cs
                JOIN courses c ON cs.course_id = c.id
                WHERE cs.professor_id = ? AND cs.semester = ? AND cs.year = ?
                ORDER BY c.course_code
            ''', (self.id, semester, year))
        else:
            cursor.execute('''
                SELECT cs.*, c.title, c.course_code, c.credits, cs.current_enrollment, cs.max_capacity
                FROM course_sections cs
                JOIN courses c ON cs.course_id = c.id
                WHERE cs.professor_id = ?
                ORDER BY cs.year DESC, cs.semester DESC, c.course_code
            ''', (self.id,))
        
        sections = cursor.fetchall()
        conn.close()
        return [dict(row) for row in sections]
    
    def get_section_students(self, section_id):
        """Get all students enrolled in a section"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.first_name, u.last_name, s.student_id, e.grade, e.grade_points, e.id as enrollment_id
            FROM enrollments e
            JOIN students s ON e.student_id = s.user_id
            JOIN users u ON s.user_id = u.id
            WHERE e.section_id = ?
            ORDER BY u.last_name, u.first_name
        ''', (section_id,))
        
        students = cursor.fetchall()
        conn.close()
        return [dict(row) for row in students]

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
    
    @staticmethod
    def get_statistics():
        """Get system-wide statistics"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE user_type = 'student'")
        stats['student_count'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE user_type = 'professor'")
        stats['professor_count'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM courses")
        stats['course_count'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM course_sections")
        stats['section_count'] = cursor.fetchone()[0]
        
        conn.close()
        return stats
    
    def change_student_grade(self, student_id, section_id, new_grade, new_points):
        """Admin can change grades even after semester ends"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE enrollments 
            SET grade = ?, grade_points = ?
            WHERE student_id = ? AND section_id = ?
        ''', (new_grade, new_points, student_id, section_id))
        
        conn.commit()
        conn.close()
    
    def add_past_enrollment(self, student_id, section_id, grade, grade_points):
        """Add a past semester enrollment for a student"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        enrollment_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO enrollments (id, student_id, section_id, enrollment_date, status, grade, grade_points, can_disenroll)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (enrollment_id, student_id, section_id, datetime.now().date(), 'enrolled', grade, grade_points, False))
        
        conn.commit()
        conn.close()
    
    def remove_enrollment(self, student_id, section_id):
        """Remove a student's enrollment"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM enrollments WHERE student_id = ? AND section_id = ?
        ''', (student_id, section_id))
        
        conn.commit()
        conn.close()
    
    def end_semester(self, semester, year):
        """Mark semester as ended"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE course_sections 
            SET semester_ended = 1
            WHERE semester = ? AND year = ?
        ''', (semester, year))
        
        conn.commit()
        conn.close()
    
    def create_academic_calendar(self, semester, year, start_date, end_date, 
                               enrollment_start, enrollment_end):
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        calendar_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO academic_calendar (id, semester, year, start_date, end_date, 
                                         enrollment_start, enrollment_end)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (calendar_id, semester, year, start_date, end_date, 
              enrollment_start, enrollment_end))
        
        conn.commit()
        conn.close()
        return calendar_id
    
    def create_course(self, course_code, title, description, credits, department_id, 
                     prerequisites=None, max_students=30):
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        course_id = str(uuid.uuid4())
        prerequisites_json = json.dumps(prerequisites) if prerequisites else None
        
        cursor.execute('''
            INSERT INTO courses (id, course_code, title, description, credits, 
                               department_id, prerequisites, max_students)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (course_id, course_code, title, description, credits, 
              department_id, prerequisites_json, max_students))
        
        conn.commit()
        conn.close()
        return course_id
    
    @staticmethod
    def get_all_courses():
        """Get all courses in the system"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.*, d.name as department_name
            FROM courses c
            LEFT JOIN departments d ON c.department_id = d.id
            ORDER BY c.course_code
        ''')
        
        courses = cursor.fetchall()
        conn.close()
        return [dict(row) for row in courses]
    
    @staticmethod
    def get_all_sections():
        """Get all course sections"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT cs.*, c.title, c.course_code, u.first_name, u.last_name
            FROM course_sections cs
            JOIN courses c ON cs.course_id = c.id
            JOIN professors p ON cs.professor_id = p.user_id
            JOIN users u ON p.user_id = u.id
            ORDER BY cs.year DESC, cs.semester DESC, c.course_code
        ''')
        
        sections = cursor.fetchall()
        conn.close()
        return [dict(row) for row in sections]

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
        
        total_points = sum(grade['grade_points'] * grade['credits'] for grade in grades)
        total_credits = sum(grade['credits'] for grade in grades)
        
        return round(total_points / total_credits, 2) if total_credits > 0 else 0.0
    
    @staticmethod
    def get_current_semester():
        """Get current semester based on date"""
        today = date.today()
        year = today.year
        month = today.month
        
        # Fall semester: August to December
        if month >= 8:
            return "Fall", year
        # Spring semester: January to May
        elif month <= 5:
            return "Spring", year
        # Summer semester: June to July
        else:
            return "Summer", year
    
    @staticmethod
    def grade_to_points(grade):
        """Convert letter grade to grade points"""
        grade_map = {
            'A+': 4.0, 'A': 4.0, 'A-': 3.7,
            'B+': 3.3, 'B': 3.0, 'B-': 2.7,
            'C+': 2.3, 'C': 2.0, 'C-': 1.7,
            'D+': 1.3, 'D': 1.0, 'D-': 0.7,
            'F': 0.0
        }
        return grade_map.get(grade, 0.0)
    
    @staticmethod
    def get_available_sections(student_id=None):
        """Get all available course sections for enrollment"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        current_semester, current_year = Utils.get_current_semester()
        
        cursor.execute('''
            SELECT cs.id, c.course_code, c.title, c.description, c.credits, 
                   cs.section_number, cs.schedule, cs.room, cs.current_enrollment, 
                   cs.max_capacity, u.first_name, u.last_name, c.average_rating
            FROM course_sections cs
            JOIN courses c ON cs.course_id = c.id
            JOIN professors p ON cs.professor_id = p.user_id
            JOIN users u ON p.user_id = u.id
            WHERE cs.status = 'open' AND cs.semester = ? AND cs.year = ?
            ORDER BY c.course_code, cs.section_number
        ''', (current_semester, current_year))
        
        sections = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in sections]
    
    @staticmethod
    def get_student_enrollments(student_id, section_id):
        """Check if student is enrolled in a specific section"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM enrollments 
            WHERE student_id = ? AND section_id = ? AND status = 'enrolled'
        ''', (student_id, section_id))
        
        enrollment = cursor.fetchone()
        conn.close()
        
        return dict(enrollment) if enrollment else None
