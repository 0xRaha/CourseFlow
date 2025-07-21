import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import json
import os
from contextlib import contextmanager
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Custom exception for database operations"""
    pass

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

class Database:
    def __init__(self):
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = os.getenv('DB_PORT', '5432')
        self.database = os.getenv('DB_NAME', 'university_db')
        self.user = os.getenv('DB_USER', 'postgres')
        self.password = os.getenv('DB_PASSWORD', 'password')
        self.init_db()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections - FIXES CONNECTION LEAKS"""
        conn = None
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                cursor_factory=RealDictCursor
            )
            yield conn
        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise DatabaseError(f"Database operation failed: {e}")
        finally:
            if conn:
                conn.close()
    
    def init_db(self):
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    # Users table (base for all user types)
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS users (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            first_name VARCHAR(100) NOT NULL,
                            last_name VARCHAR(100) NOT NULL,
                            email VARCHAR(255) UNIQUE NOT NULL,
                            username VARCHAR(50) UNIQUE NOT NULL,
                            password_hash VARCHAR(255) NOT NULL,
                            user_type VARCHAR(20) NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            is_active BOOLEAN DEFAULT TRUE
                        )
                    ''')
                    
                    # Students table
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS students (
                            user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                            student_id VARCHAR(50) UNIQUE NOT NULL,
                            enrollment_date DATE DEFAULT CURRENT_DATE,
                            graduation_date DATE,
                            gpa DECIMAL(3,2) DEFAULT 0.0,
                            year_level INTEGER DEFAULT 1,
                            major VARCHAR(100),
                            status VARCHAR(20) DEFAULT 'active',
                            max_credits INTEGER DEFAULT 20
                        )
                    ''')
                    
                    # Professors table
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS professors (
                            user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                            employee_id VARCHAR(50) UNIQUE NOT NULL,
                            department VARCHAR(100) NOT NULL,
                            position VARCHAR(100) DEFAULT 'Assistant Professor',
                            hire_date DATE DEFAULT CURRENT_DATE,
                            office_location VARCHAR(100),
                            phone VARCHAR(20),
                            research_interests TEXT
                        )
                    ''')
                    
                    # Admins table
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS admins (
                            user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                            admin_level INTEGER DEFAULT 1,
                            permissions VARCHAR(50) DEFAULT 'limited'
                        )
                    ''')
                    
                    # Departments table
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS departments (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            name VARCHAR(100) UNIQUE NOT NULL,
                            code VARCHAR(10) UNIQUE NOT NULL,
                            description TEXT,
                            head_professor_id UUID REFERENCES professors(user_id),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    
                    # Courses table
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS courses (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            course_code VARCHAR(20) UNIQUE NOT NULL,
                            title VARCHAR(200) NOT NULL,
                            description TEXT,
                            credits INTEGER NOT NULL,
                            department_id UUID REFERENCES departments(id),
                            prerequisites JSONB,
                            max_students INTEGER DEFAULT 30,
                            is_active BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    
                    # Course sections table
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS course_sections (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            course_id UUID NOT NULL REFERENCES courses(id),
                            professor_id UUID NOT NULL REFERENCES professors(user_id),
                            section_number VARCHAR(10) NOT NULL,
                            semester VARCHAR(20) NOT NULL,
                            year INTEGER NOT NULL,
                            schedule VARCHAR(100) NOT NULL,
                            room VARCHAR(50),
                            max_capacity INTEGER DEFAULT 30,
                            current_enrollment INTEGER DEFAULT 0,
                            status VARCHAR(20) DEFAULT 'open',
                            grades_submitted BOOLEAN DEFAULT FALSE,
                            semester_ended BOOLEAN DEFAULT FALSE,
                            UNIQUE(course_id, section_number, semester, year)
                        )
                    ''')
                    
                    # Enrollments table
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS enrollments (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            student_id UUID NOT NULL REFERENCES students(user_id),
                            section_id UUID NOT NULL REFERENCES course_sections(id),
                            enrollment_date DATE DEFAULT CURRENT_DATE,
                            status VARCHAR(20) DEFAULT 'enrolled',
                            grade VARCHAR(5),
                            grade_points DECIMAL(3,2),
                            can_disenroll BOOLEAN DEFAULT TRUE,
                            UNIQUE(student_id, section_id)
                        )
                    ''')
                    
                    # Academic calendar table
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS academic_calendar (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            semester VARCHAR(20) NOT NULL,
                            year INTEGER NOT NULL,
                            start_date DATE NOT NULL,
                            end_date DATE NOT NULL,
                            enrollment_start DATE,
                            enrollment_end DATE,
                            is_current BOOLEAN DEFAULT FALSE,
                            UNIQUE(semester, year)
                        )
                    ''')
                    
                    # Create indexes for better performance
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_enrollments_student ON enrollments(student_id)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_enrollments_section ON enrollments(section_id)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_course_sections_semester ON course_sections(semester, year)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_enrollments_student_section ON enrollments(student_id, section_id)')
                    
                    conn.commit()
                    logger.info("Database initialized successfully")
                except psycopg2.Error as e:
                    logger.error(f"Failed to initialize database: {e}")
                    raise DatabaseError(f"Database initialization failed: {e}")

class User:
    def __init__(self, first_name, last_name, email, username, password, user_type):
        self.id = str(uuid.uuid4())
        self.first_name = self._validate_name(first_name)
        self.last_name = self._validate_name(last_name)
        self.email = self._validate_email(email)
        self.username = self._validate_username(username)
        self.password_hash = generate_password_hash(password) if password else None
        self.user_type = user_type
        self.created_at = datetime.now()
        self.is_active = True
    
    def _validate_name(self, name):
        if not name or len(name.strip()) < 2:
            raise ValidationError("Name must be at least 2 characters long")
        return name.strip()
    
    def _validate_email(self, email):
        import re
        if not email or not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            raise ValidationError("Invalid email format")
        return email.lower().strip()
    
    def _validate_username(self, username):
        if not username or len(username) < 3:
            raise ValidationError("Username must be at least 3 characters long")
        return username.strip()
    
    def save(self):
        """FIXED: Proper transaction management and error handling"""
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.execute('''
                        INSERT INTO users (id, first_name, last_name, email, username, password_hash, user_type, created_at, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (self.id, self.first_name, self.last_name, self.email, self.username, 
                          self.password_hash, self.user_type, self.created_at, self.is_active))
                    conn.commit()
                    logger.info(f"User {self.username} created successfully")
                except psycopg2.IntegrityError as e:
                    if 'username' in str(e):
                        raise ValidationError("Username already exists")
                    elif 'email' in str(e):
                        raise ValidationError("Email already exists")
                    else:
                        raise ValidationError("User creation failed: duplicate data")
                except Exception as e:
                    logger.error(f"Failed to save user: {e}")
                    raise DatabaseError(f"User creation failed: {e}")
    
    @staticmethod
    def authenticate(username, password):
        if not username or not password:
            return None
            
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    'SELECT id, password_hash, user_type FROM users WHERE username = %s AND is_active = TRUE', 
                    (username,)
                )
                user = cursor.fetchone()
                
                if user and check_password_hash(user['password_hash'], password):
                    return {'id': str(user['id']), 'user_type': user['user_type']}
                return None
    
    @staticmethod
    def get_by_id(user_id):
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
                user = cursor.fetchone()
                return dict(user) if user else None
    
    @staticmethod
    def get_all_users(user_type=None):
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                if user_type:
                    cursor.execute('SELECT * FROM users WHERE user_type = %s AND is_active = TRUE', (user_type,))
                else:
                    cursor.execute('SELECT * FROM users WHERE is_active = TRUE')
                
                users = cursor.fetchall()
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
        self.max_credits = 20
    
    def generate_student_id(self):
        return f"STU{datetime.now().year}{str(uuid.uuid4())[:8].upper()}"
    
    def save(self):
        """FIXED: Proper transaction management"""
        super().save()
        
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.execute('''
                        INSERT INTO students (user_id, student_id, enrollment_date, gpa, year_level, major, status, max_credits)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (self.id, self.student_id, self.enrollment_date, self.gpa, self.year_level, self.major, self.status, self.max_credits))
                    conn.commit()
                    logger.info(f"Student {self.student_id} created successfully")
                except Exception as e:
                    logger.error(f"Failed to save student: {e}")
                    raise DatabaseError(f"Student creation failed: {e}")
    
    @staticmethod
    def get_by_user_id(user_id):
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT u.*, s.student_id, s.gpa, s.year_level, s.major, s.status
                    FROM users u
                    JOIN students s ON u.id = s.user_id
                    WHERE u.id = %s
                ''', (user_id,))
                
                student = cursor.fetchone()
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
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT COALESCE(SUM(c.credits), 0) as total_credits
                    FROM enrollments e
                    JOIN course_sections cs ON e.section_id = cs.id
                    JOIN courses c ON cs.course_id = c.id
                    WHERE e.student_id = %s AND cs.semester = %s AND cs.year = %s AND e.status = 'enrolled'
                ''', (self.id, semester, year))
                
                result = cursor.fetchone()
                return result['total_credits'] if result else 0
    
    def check_prerequisites(self, course_id):
        """FIXED: Check if student has completed prerequisites for a course"""
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Get course prerequisites
                cursor.execute('SELECT prerequisites FROM courses WHERE id = %s', (course_id,))
                prereq_result = cursor.fetchone()
                
                if not prereq_result or not prereq_result['prerequisites']:
                    return True
                
                prerequisites = prereq_result['prerequisites'] if prereq_result['prerequisites'] else []
                
                # Check if student has completed all prerequisites with passing grade
                for prereq_code in prerequisites:
                    cursor.execute('''
                        SELECT e.grade_points
                        FROM enrollments e
                        JOIN course_sections cs ON e.section_id = cs.id
                        JOIN courses c ON cs.course_id = c.id
                        WHERE e.student_id = %s AND c.course_code = %s AND e.grade_points >= 2.0
                    ''', (self.id, prereq_code))
                    
                    if not cursor.fetchone():
                        return False
                
                return True
    
    def has_time_conflict(self, new_section_id):
        """FIXED: Proper time conflict checking logic"""
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Get new section schedule
                cursor.execute('''
                    SELECT schedule, semester, year FROM course_sections WHERE id = %s
                ''', (new_section_id,))
                new_section = cursor.fetchone()
                
                if not new_section:
                    return False  # No conflict if section doesn't exist
                
                # Get student's current enrollments for the same semester
                cursor.execute('''
                    SELECT cs.schedule
                    FROM enrollments e
                    JOIN course_sections cs ON e.section_id = cs.id
                    WHERE e.student_id = %s AND cs.semester = %s AND cs.year = %s AND e.status = 'enrolled'
                ''', (self.id, new_section['semester'], new_section['year']))
                
                current_schedules = cursor.fetchall()
                
                # Check for time overlaps
                new_schedule = new_section['schedule']
                for current in current_schedules:
                    if self._schedules_overlap(new_schedule, current['schedule']):
                        return True  # Conflict found
                
                return False  # No conflicts
    
    def _schedules_overlap(self, schedule1, schedule2):
        """Check if two schedules overlap"""
        try:
            # Parse schedule format: "MWF 10:00-11:00"
            parts1 = schedule1.split(' ')
            parts2 = schedule2.split(' ')
            
            if len(parts1) != 2 or len(parts2) != 2:
                return False  # Invalid format, assume no conflict
            
            days1, time1 = parts1
            days2, time2 = parts2
            
            # Check if there are common days
            if not any(day in days2 for day in days1):
                return False
            
            # Parse and compare times
            start1, end1 = time1.split('-')
            start2, end2 = time2.split('-')
            
            start1_minutes = self._time_to_minutes(start1)
            end1_minutes = self._time_to_minutes(end1)
            start2_minutes = self._time_to_minutes(start2)
            end2_minutes = self._time_to_minutes(end2)
            
            # Check for time overlap
            return not (end1_minutes <= start2_minutes or end2_minutes <= start1_minutes)
            
        except (ValueError, IndexError):
            logger.warning(f"Failed to parse schedules: {schedule1}, {schedule2}")
            return False  # If parsing fails, assume no conflict
    
    def _time_to_minutes(self, time_str):
        """Convert time string to minutes since midnight"""
        try:
            hours, minutes = map(int, time_str.split(':'))
            return hours * 60 + minutes
        except ValueError:
            return 0
    
    def enroll_in_section(self, section_id):
        """FIXED: Proper transaction management, locking, and validation"""
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    # FIXED: Lock the section to prevent race conditions
                    cursor.execute(
                        'SELECT * FROM course_sections WHERE id = %s FOR UPDATE',
                        (section_id,)
                    )
                    
                    # Get section and course info with proper JOIN
                    cursor.execute('''
                        SELECT cs.current_enrollment, cs.max_capacity, cs.status, 
                               cs.semester, cs.year, c.credits, c.id as course_id,
                               c.course_code, c.title
                        FROM course_sections cs
                        JOIN courses c ON cs.course_id = c.id
                        WHERE cs.id = %s
                    ''', (section_id,))
                    
                    section = cursor.fetchone()
                    if not section:
                        raise ValidationError("Section not found")
                    
                    # Perform all validation checks
                    self._validate_enrollment(cursor, section, section_id)
                    
                    # Enroll student
                    enrollment_id = str(uuid.uuid4())
                    cursor.execute('''
                        INSERT INTO enrollments (id, student_id, section_id, enrollment_date, status, can_disenroll)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (enrollment_id, self.id, section_id, datetime.now().date(), 'enrolled', True))
                    
                    # Update section enrollment count atomically
                    cursor.execute('''
                        UPDATE course_sections 
                        SET current_enrollment = current_enrollment + 1 
                        WHERE id = %s
                    ''', (section_id,))
                    
                    conn.commit()
                    logger.info(f"Student {self.id} enrolled in section {section_id}")
                    
                except (ValidationError, DatabaseError):
                    raise
                except Exception as e:
                    logger.error(f"Enrollment failed: {e}")
                    raise DatabaseError(f"Enrollment failed: {e}")
    
    def _validate_enrollment(self, cursor, section, section_id):
        """Separate validation method for cleaner code"""
        if section['status'] != 'open':
            raise ValidationError("Section is not open for enrollment")
        
        if section['current_enrollment'] >= section['max_capacity']:
            raise ValidationError("Section is full")
        
        # Check if already enrolled
        cursor.execute(
            'SELECT id FROM enrollments WHERE student_id = %s AND section_id = %s', 
            (self.id, section_id)
        )
        if cursor.fetchone():
            raise ValidationError("Already enrolled in this section")
        
        # FIXED: Check prerequisites with correct course_id
        if not self.check_prerequisites(section['course_id']):
            raise ValidationError("Prerequisites not met")
        
        # FIXED: Time conflict check with proper method name
        if self.has_time_conflict(section_id):
            raise ValidationError("Time conflict with another enrolled course")
        
        # Check credit limit
        current_credits = self.get_current_credits(section['semester'], section['year'])
        max_credits = self.calculate_max_credits()
        
        if current_credits + section['credits'] > max_credits:
            raise ValidationError(f"Enrollment would exceed max credits ({max_credits})")
    
    def disenroll_from_section(self, section_id):
        """FIXED: Proper transaction management"""
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    # Check if can disenroll (no grades submitted)
                    cursor.execute('''
                        SELECT can_disenroll FROM enrollments 
                        WHERE student_id = %s AND section_id = %s AND status = 'enrolled'
                    ''', (self.id, section_id))
                    
                    enrollment = cursor.fetchone()
                    if not enrollment:
                        raise ValidationError("Not enrolled in this section")
                    
                    if not enrollment['can_disenroll']:
                        raise ValidationError("Cannot disenroll - grades have been submitted")
                    
                    # Remove enrollment
                    cursor.execute('''
                        DELETE FROM enrollments WHERE student_id = %s AND section_id = %s
                    ''', (self.id, section_id))
                    
                    # Update section enrollment count
                    cursor.execute('''
                        UPDATE course_sections 
                        SET current_enrollment = current_enrollment - 1 
                        WHERE id = %s
                    ''', (section_id,))
                    
                    conn.commit()
                    logger.info(f"Student {self.id} disenrolled from section {section_id}")
                    
                except ValidationError:
                    raise
                except Exception as e:
                    logger.error(f"Disenrollment failed: {e}")
                    raise DatabaseError(f"Disenrollment failed: {e}")
    
    def get_class_schedule(self, semester, year):
        """Get student's class schedule for a semester"""
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT c.course_code, c.title, c.credits, cs.section_number, 
                           cs.schedule, cs.room, u.first_name, u.last_name, e.grade
                    FROM enrollments e
                    JOIN course_sections cs ON e.section_id = cs.id
                    JOIN courses c ON cs.course_id = c.id
                    JOIN professors p ON cs.professor_id = p.user_id
                    JOIN users u ON p.user_id = u.id
                    WHERE e.student_id = %s AND cs.semester = %s AND cs.year = %s AND e.status = 'enrolled'
                    ORDER BY c.course_code
                ''', (self.id, semester, year))
                
                schedule = cursor.fetchall()
                return [dict(row) for row in schedule]
    
    def get_all_grades(self):
        """Get all grades across all semesters"""
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT c.course_code, c.title, c.credits, cs.semester, cs.year, 
                           e.grade, e.grade_points, u.first_name, u.last_name
                    FROM enrollments e
                    JOIN course_sections cs ON e.section_id = cs.id
                    JOIN courses c ON cs.course_id = c.id
                    JOIN professors p ON cs.professor_id = p.user_id
                    JOIN users u ON p.user_id = u.id
                    WHERE e.student_id = %s AND e.status = 'enrolled'
                    ORDER BY cs.year DESC, cs.semester DESC, c.course_code
                ''', (self.id,))
                
                grades = cursor.fetchall()
                return [dict(row) for row in grades]

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
        """FIXED: Proper transaction management"""
        super().save()
        
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.execute('''
                        INSERT INTO professors (user_id, employee_id, department, position, hire_date, 
                                              office_location, phone, research_interests)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (self.id, self.employee_id, self.department, self.position, self.hire_date,
                          self.office_location, self.phone, self.research_interests))
                    conn.commit()
                    logger.info(f"Professor {self.employee_id} created successfully")
                except Exception as e:
                    logger.error(f"Failed to save professor: {e}")
                    raise DatabaseError(f"Professor creation failed: {e}")
    
    @staticmethod
    def get_by_user_id(user_id):
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT u.*, p.employee_id, p.department, p.position, p.office_location, p.phone
                    FROM users u
                    JOIN professors p ON u.id = p.user_id
                    WHERE u.id = %s
                ''', (user_id,))
                
                professor = cursor.fetchone()
                return dict(professor) if professor else None
    
    def create_course_section(self, course_id, section_number, semester, year, 
                            schedule, room=None, max_capacity=30):
        """FIXED: Proper transaction management"""
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    section_id = str(uuid.uuid4())
                    cursor.execute('''
                        INSERT INTO course_sections (id, course_id, professor_id, section_number, 
                                                   semester, year, schedule, room, max_capacity)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (section_id, course_id, self.id, section_number, semester, year, 
                          schedule, room, max_capacity))
                    
                    conn.commit()
                    logger.info(f"Course section {section_id} created successfully")
                    return section_id
                except Exception as e:
                    logger.error(f"Failed to create course section: {e}")
                    raise DatabaseError(f"Course section creation failed: {e}")
    
    def submit_grades(self, section_id, student_grades):
        """FIXED: Submit grades with proper transaction management"""
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    # Check if semester has ended
                    cursor.execute('''
                        SELECT semester_ended FROM course_sections WHERE id = %s
                    ''', (section_id,))
                    
                    section = cursor.fetchone()
                    if section and section['semester_ended']:
                        raise ValidationError("Cannot submit grades - semester has ended")
                    
                    # Submit grades for all students
                    for student_id, grade_data in student_grades.items():
                        grade_letter = grade_data['grade']
                        grade_points = grade_data['points']
                        
                        cursor.execute('''
                            UPDATE enrollments 
                            SET grade = %s, grade_points = %s, can_disenroll = FALSE
                            WHERE student_id = %s AND section_id = %s
                        ''', (grade_letter, grade_points, student_id, section_id))
                    
                    # Mark grades as submitted
                    cursor.execute('''
                        UPDATE course_sections SET grades_submitted = TRUE WHERE id = %s
                    ''', (section_id,))
                    
                    conn.commit()
                    logger.info(f"Grades submitted for section {section_id}")
                    
                except ValidationError:
                    raise
                except Exception as e:
                    logger.error(f"Failed to submit grades: {e}")
                    raise DatabaseError(f"Grade submission failed: {e}")
    
    def get_teaching_sections(self, semester=None, year=None):
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                if semester and year:
                    cursor.execute('''
                        SELECT cs.*, c.title, c.course_code, c.credits, cs.current_enrollment, cs.max_capacity
                        FROM course_sections cs
                        JOIN courses c ON cs.course_id = c.id
                        WHERE cs.professor_id = %s AND cs.semester = %s AND cs.year = %s
                        ORDER BY c.course_code
                    ''', (self.id, semester, year))
                else:
                    cursor.execute('''
                        SELECT cs.*, c.title, c.course_code, c.credits, cs.current_enrollment, cs.max_capacity
                        FROM course_sections cs
                        JOIN courses c ON cs.course_id = c.id
                        WHERE cs.professor_id = %s
                        ORDER BY cs.year DESC, cs.semester DESC, c.course_code
                    ''', (self.id,))
                
                sections = cursor.fetchall()
                return [dict(row) for row in sections]
    
    def get_section_students(self, section_id):
        """Get all students enrolled in a section"""
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT u.first_name, u.last_name, s.student_id, e.grade, e.grade_points, e.id as enrollment_id
                    FROM enrollments e
                    JOIN students s ON e.student_id = s.user_id
                    JOIN users u ON s.user_id = u.id
                    WHERE e.section_id = %s
                    ORDER BY u.last_name, u.first_name
                ''', (section_id,))
                
                students = cursor.fetchall()
                return [dict(row) for row in students]

class Admin(User):
    def __init__(self, first_name, last_name, email, username, password, admin_level=1):
        super().__init__(first_name, last_name, email, username, password, 'admin')
        self.admin_level = admin_level
        self.permissions = "full" if admin_level >= 3 else "limited"
    
    def save(self):
        """FIXED: Proper transaction management"""
        super().save()
        
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.execute('''
                        INSERT INTO admins (user_id, admin_level, permissions)
                        VALUES (%s, %s, %s)
                    ''', (self.id, self.admin_level, self.permissions))
                    conn.commit()
                    logger.info(f"Admin user created successfully")
                except Exception as e:
                    logger.error(f"Failed to save admin: {e}")
                    raise DatabaseError(f"Admin creation failed: {e}")
    
    @staticmethod
    def get_statistics():
        """Get system-wide statistics"""
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                stats = {}
                
                cursor.execute("SELECT COUNT(*) as count FROM users WHERE user_type = 'student'")
                stats['student_count'] = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM users WHERE user_type = 'professor'")
                stats['professor_count'] = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM courses")
                stats['course_count'] = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM course_sections")
                stats['section_count'] = cursor.fetchone()['count']
                
                return stats
    
    def change_student_grade(self, student_id, section_id, new_grade, new_points):
        """FIXED: Admin can change grades with proper transaction management"""
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.execute('''
                        UPDATE enrollments 
                        SET grade = %s, grade_points = %s
                        WHERE student_id = %s AND section_id = %s
                    ''', (new_grade, new_points, student_id, section_id))
                    
                    if cursor.rowcount == 0:
                        raise ValidationError("Enrollment not found")
                    
                    conn.commit()
                    logger.info(f"Grade changed for student {student_id} in section {section_id}")
                    
                except ValidationError:
                    raise
                except Exception as e:
                    logger.error(f"Failed to change grade: {e}")
                    raise DatabaseError(f"Grade change failed: {e}")
    
    def add_past_enrollment(self, student_id, section_id, grade, grade_points):
        """FIXED: Add past enrollment with proper transaction management"""
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    enrollment_id = str(uuid.uuid4())
                    cursor.execute('''
                        INSERT INTO enrollments (id, student_id, section_id, enrollment_date, status, grade, grade_points, can_disenroll)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (enrollment_id, student_id, section_id, datetime.now().date(), 'enrolled', grade, grade_points, False))
                    
                    conn.commit()
                    logger.info(f"Past enrollment added for student {student_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to add past enrollment: {e}")
                    raise DatabaseError(f"Past enrollment creation failed: {e}")
    
    def remove_enrollment(self, student_id, section_id):
        """FIXED: Remove enrollment with proper transaction management"""
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.execute('''
                        DELETE FROM enrollments WHERE student_id = %s AND section_id = %s
                    ''', (student_id, section_id))
                    
                    if cursor.rowcount == 0:
                        raise ValidationError("Enrollment not found")
                    
                    conn.commit()
                    logger.info(f"Enrollment removed for student {student_id}")
                    
                except ValidationError:
                    raise
                except Exception as e:
                    logger.error(f"Failed to remove enrollment: {e}")
                    raise DatabaseError(f"Enrollment removal failed: {e}")
    
    def create_course(self, course_code, title, description, credits, department_id, 
                     prerequisites=None, max_students=30):
        """FIXED: Create course with proper transaction management"""
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    course_id = str(uuid.uuid4())
                    prerequisites_json = json.dumps(prerequisites) if prerequisites else None
                    
                    cursor.execute('''
                        INSERT INTO courses (id, course_code, title, description, credits, 
                                           department_id, prerequisites, max_students)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (course_id, course_code, title, description, credits, 
                          department_id, prerequisites_json, max_students))
                    
                    conn.commit()
                    logger.info(f"Course {course_code} created successfully")
                    return course_id
                    
                except Exception as e:
                    logger.error(f"Failed to create course: {e}")
                    raise DatabaseError(f"Course creation failed: {e}")
    
    @staticmethod
    def get_all_courses():
        """Get all courses in the system"""
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT c.*, d.name as department_name
                    FROM courses c
                    LEFT JOIN departments d ON c.department_id = d.id
                    ORDER BY c.course_code
                ''')
                
                courses = cursor.fetchall()
                return [dict(row) for row in courses]
    
    @staticmethod
    def get_all_sections():
        """Get all course sections"""
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT cs.*, c.title, c.course_code, u.first_name, u.last_name
                    FROM course_sections cs
                    JOIN courses c ON cs.course_id = c.id
                    JOIN professors p ON cs.professor_id = p.user_id
                    JOIN users u ON p.user_id = u.id
                    ORDER BY cs.year DESC, cs.semester DESC, c.course_code
                ''')
                
                sections = cursor.fetchall()
                return [dict(row) for row in sections]

class Utils:
    @staticmethod
    def calculate_gpa(student_id):
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT grade_points, c.credits
                    FROM enrollments e
                    JOIN course_sections cs ON e.section_id = cs.id
                    JOIN courses c ON cs.course_id = c.id
                    WHERE e.student_id = %s AND e.grade_points IS NOT NULL
                ''', (student_id,))
                
                grades = cursor.fetchall()
                
                if not grades:
                    return 0.0
                
                total_points = sum(float(grade['grade_points']) * grade['credits'] for grade in grades)
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
        """FIXED: Get available sections with optimized query"""
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                current_semester, current_year = Utils.get_current_semester()
                
                if student_id:
                    # Get sections with enrollment status for specific student
                    cursor.execute('''
                        SELECT cs.id, c.course_code, c.title, c.description, c.credits, 
                               cs.section_number, cs.schedule, cs.room, cs.current_enrollment, 
                               cs.max_capacity, u.first_name, u.last_name,
                               CASE WHEN e.id IS NOT NULL THEN true ELSE false END as is_enrolled
                        FROM course_sections cs
                        JOIN courses c ON cs.course_id = c.id
                        JOIN professors p ON cs.professor_id = p.user_id
                        JOIN users u ON p.user_id = u.id
                        LEFT JOIN enrollments e ON cs.id = e.section_id AND e.student_id = %s AND e.status = 'enrolled'
                        WHERE cs.status = 'open' AND cs.semester = %s AND cs.year = %s
                        ORDER BY c.course_code, cs.section_number
                    ''', (student_id, current_semester, current_year))
                else:
                    cursor.execute('''
                        SELECT cs.id, c.course_code, c.title, c.description, c.credits, 
                               cs.section_number, cs.schedule, cs.room, cs.current_enrollment, 
                               cs.max_capacity, u.first_name, u.last_name
                        FROM course_sections cs
                        JOIN courses c ON cs.course_id = c.id
                        JOIN professors p ON cs.professor_id = p.user_id
                        JOIN users u ON p.user_id = u.id
                        WHERE cs.status = 'open' AND cs.semester = %s AND cs.year = %s
                        ORDER BY c.course_code, cs.section_number
                    ''', (current_semester, current_year))
                
                sections = cursor.fetchall()
                return [dict(row) for row in sections]
    
    @staticmethod
    def get_student_enrollments(student_id, section_id):
        """Check if student is enrolled in a specific section"""
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT * FROM enrollments 
                    WHERE student_id = %s AND section_id = %s AND status = 'enrolled'
                ''', (student_id, section_id))
                
                enrollment = cursor.fetchone()
                return dict(enrollment) if enrollment else None