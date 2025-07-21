import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import os
from contextlib import contextmanager

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
            raise Exception(f"Database error: {e}")
        finally:
            if conn:
                conn.close()
    
    def init_db(self):
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
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
                        is_active BOOLEAN DEFAULT TRUE
                    )
                ''')
                
                # Students table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS students (
                        user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                        student_id VARCHAR(50) UNIQUE NOT NULL,
                        major VARCHAR(100),
                        year_level INTEGER DEFAULT 1,
                        status VARCHAR(20) DEFAULT 'active'
                    )
                ''')
                
                # Professors table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS professors (
                        user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                        employee_id VARCHAR(50) UNIQUE NOT NULL,
                        department VARCHAR(100) NOT NULL,
                        position VARCHAR(100) DEFAULT 'Assistant Professor',
                        office_location VARCHAR(100),
                        phone VARCHAR(20)
                    )
                ''')
                
                # Admins table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS admins (
                        user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                        admin_level INTEGER DEFAULT 1
                    )
                ''')
                
                # Courses table (department as string field)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS courses (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        course_code VARCHAR(20) UNIQUE NOT NULL,
                        title VARCHAR(200) NOT NULL,
                        description TEXT,
                        credits INTEGER NOT NULL,
                        department VARCHAR(100),
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
                        UNIQUE(course_id, section_number, semester, year)
                    )
                ''')
                
                # Enrollments table (simplified)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS enrollments (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        student_id UUID NOT NULL REFERENCES students(user_id),
                        section_id UUID NOT NULL REFERENCES course_sections(id),
                        enrollment_date DATE DEFAULT CURRENT_DATE,
                        grade VARCHAR(5),
                        UNIQUE(student_id, section_id)
                    )
                ''')
                
                # Simple announcements table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS announcements (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        section_id UUID NOT NULL REFERENCES course_sections(id),
                        title VARCHAR(200) NOT NULL,
                        content TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Basic indexes only
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_enrollments_student ON enrollments(student_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_enrollments_section ON enrollments(section_id)')
                
                conn.commit()

class User:
    def __init__(self, first_name, last_name, email, username, password, user_type):
        self.id = str(uuid.uuid4())
        self.first_name = first_name.strip()
        self.last_name = last_name.strip()
        self.email = email.lower().strip()
        self.username = username.strip()
        self.password_hash = generate_password_hash(password) if password else None
        self.user_type = user_type
        self.created_at = datetime.now()
        self.is_active = True
    
    def save(self):
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO users (id, first_name, last_name, email, username, password_hash, user_type, created_at, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (self.id, self.first_name, self.last_name, self.email, self.username, 
                      self.password_hash, self.user_type, self.created_at, self.is_active))
                conn.commit()
    
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
    def get_all_users(user_type=None, search=None):
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                query = 'SELECT * FROM users WHERE is_active = TRUE'
                params = []
                
                if user_type:
                    query += ' AND user_type = %s'
                    params.append(user_type)
                
                if search:
                    query += ' AND (first_name ILIKE %s OR last_name ILIKE %s OR email ILIKE %s OR username ILIKE %s)'
                    search_param = f'%{search}%'
                    params.extend([search_param, search_param, search_param, search_param])
                
                cursor.execute(query, params)
                users = cursor.fetchall()
                return [dict(user) for user in users]
    
    def update_profile(self, first_name, last_name, email):
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    UPDATE users SET first_name = %s, last_name = %s, email = %s
                    WHERE id = %s
                ''', (first_name, last_name, email, self.id))
                conn.commit()

class Student(User):
    def __init__(self, first_name, last_name, email, username, password, major=None):
        super().__init__(first_name, last_name, email, username, password, 'student')
        self.student_id = f"STU{datetime.now().year}{str(uuid.uuid4())[:8].upper()}"
        self.major = major
        self.year_level = 1
        self.status = 'active'
    
    def save(self):
        super().save()
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO students (user_id, student_id, major, year_level, status)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (self.id, self.student_id, self.major, self.year_level, self.status))
                conn.commit()
    
    @staticmethod
    def get_by_user_id(user_id):
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT u.*, s.student_id, s.major, s.year_level, s.status
                    FROM users u
                    JOIN students s ON u.id = s.user_id
                    WHERE u.id = %s
                ''', (user_id,))
                
                student = cursor.fetchone()
                return dict(student) if student else None
    
    def enroll_in_section(self, section_id):
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Check if section exists and has space
                cursor.execute('''
                    SELECT current_enrollment, max_capacity, status
                    FROM course_sections WHERE id = %s
                ''', (section_id,))
                section = cursor.fetchone()
                
                if not section or section['status'] != 'open':
                    raise Exception("Section not available")
                
                if section['current_enrollment'] >= section['max_capacity']:
                    raise Exception("Section is full")
                
                # Check if already enrolled
                cursor.execute(
                    'SELECT id FROM enrollments WHERE student_id = %s AND section_id = %s', 
                    (self.id, section_id)
                )
                if cursor.fetchone():
                    raise Exception("Already enrolled")
                
                # Simple time conflict check
                if self.has_time_conflict(section_id):
                    raise Exception("Time conflict with another course")
                
                # Enroll student
                cursor.execute('''
                    INSERT INTO enrollments (student_id, section_id, enrollment_date)
                    VALUES (%s, %s, %s)
                ''', (self.id, section_id, datetime.now().date()))
                
                # Update enrollment count
                cursor.execute('''
                    UPDATE course_sections 
                    SET current_enrollment = current_enrollment + 1 
                    WHERE id = %s
                ''', (section_id,))
                
                conn.commit()
    
    def has_time_conflict(self, new_section_id):
        """Simple time conflict check"""
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT schedule, semester, year FROM course_sections WHERE id = %s
                ''', (new_section_id,))
                new_section = cursor.fetchone()
                
                if not new_section:
                    return False
                
                cursor.execute('''
                    SELECT cs.schedule
                    FROM enrollments e
                    JOIN course_sections cs ON e.section_id = cs.id
                    WHERE e.student_id = %s AND cs.semester = %s AND cs.year = %s
                ''', (self.id, new_section['semester'], new_section['year']))
                
                current_schedules = cursor.fetchall()
                
                # Simple overlap check - if days overlap, assume conflict
                new_days = new_section['schedule'].split(' ')[0] if ' ' in new_section['schedule'] else ''
                for current in current_schedules:
                    current_days = current['schedule'].split(' ')[0] if ' ' in current['schedule'] else ''
                    if any(day in current_days for day in new_days):
                        return True
                
                return False
    
    def drop_course(self, section_id):
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    'DELETE FROM enrollments WHERE student_id = %s AND section_id = %s',
                    (self.id, section_id)
                )
                
                cursor.execute('''
                    UPDATE course_sections 
                    SET current_enrollment = current_enrollment - 1 
                    WHERE id = %s
                ''', (section_id,))
                
                conn.commit()
    
    def get_class_schedule(self, semester, year):
        """Get student's class schedule"""
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
                    WHERE e.student_id = %s AND cs.semester = %s AND cs.year = %s
                    ORDER BY c.course_code
                ''', (self.id, semester, year))
                
                return [dict(row) for row in cursor.fetchall()]
    
    def get_all_grades(self):
        """Get all grades"""
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT c.course_code, c.title, c.credits, cs.semester, cs.year, 
                           e.grade, u.first_name, u.last_name
                    FROM enrollments e
                    JOIN course_sections cs ON e.section_id = cs.id
                    JOIN courses c ON cs.course_id = c.id
                    JOIN professors p ON cs.professor_id = p.user_id
                    JOIN users u ON p.user_id = u.id
                    WHERE e.student_id = %s
                    ORDER BY cs.year DESC, cs.semester DESC, c.course_code
                ''', (self.id,))
                
                return [dict(row) for row in cursor.fetchall()]
    
    def get_announcements(self):
        """Get announcements for enrolled courses"""
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT a.title, a.content, a.created_at, c.course_code, c.title as course_title
                    FROM announcements a
                    JOIN course_sections cs ON a.section_id = cs.id
                    JOIN courses c ON cs.course_id = c.id
                    JOIN enrollments e ON cs.id = e.section_id
                    WHERE e.student_id = %s
                    ORDER BY a.created_at DESC
                    LIMIT 10
                ''', (self.id,))
                
                return [dict(row) for row in cursor.fetchall()]

class Professor(User):
    def __init__(self, first_name, last_name, email, username, password, department, 
                 position="Assistant Professor", office_location=None, phone=None):
        super().__init__(first_name, last_name, email, username, password, 'professor')
        self.employee_id = f"EMP{datetime.now().year}{str(uuid.uuid4())[:8].upper()}"
        self.department = department
        self.position = position
        self.office_location = office_location
        self.phone = phone
    
    def save(self):
        super().save()
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO professors (user_id, employee_id, department, position, office_location, phone)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (self.id, self.employee_id, self.department, self.position, 
                      self.office_location, self.phone))
                conn.commit()
    
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
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                section_id = str(uuid.uuid4())
                cursor.execute('''
                    INSERT INTO course_sections (id, course_id, professor_id, section_number, 
                                               semester, year, schedule, room, max_capacity)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (section_id, course_id, self.id, section_number, semester, year, 
                      schedule, room, max_capacity))
                conn.commit()
                return section_id
    
    def get_teaching_sections(self, semester=None, year=None):
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                query = '''
                    SELECT cs.*, c.title, c.course_code, c.credits
                    FROM course_sections cs
                    JOIN courses c ON cs.course_id = c.id
                    WHERE cs.professor_id = %s
                '''
                params = [self.id]
                
                if semester and year:
                    query += ' AND cs.semester = %s AND cs.year = %s'
                    params.extend([semester, year])
                
                query += ' ORDER BY cs.year DESC, cs.semester DESC, c.course_code'
                
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
    
    def get_section_students(self, section_id):
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT u.first_name, u.last_name, s.student_id, e.grade, e.id as enrollment_id
                    FROM enrollments e
                    JOIN students s ON e.student_id = s.user_id
                    JOIN users u ON s.user_id = u.id
                    WHERE e.section_id = %s
                    ORDER BY u.last_name, u.first_name
                ''', (section_id,))
                
                return [dict(row) for row in cursor.fetchall()]
    
    def submit_grades(self, section_id, student_grades):
        """Submit grades - simplified"""
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                for enrollment_id, grade in student_grades.items():
                    cursor.execute('''
                        UPDATE enrollments SET grade = %s
                        WHERE id = %s
                    ''', (grade, enrollment_id))
                conn.commit()
    
    def create_announcement(self, section_id, title, content):
        """Create course announcement"""
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO announcements (section_id, title, content, created_at)
                    VALUES (%s, %s, %s, %s)
                ''', (section_id, title, content, datetime.now()))
                conn.commit()

class Admin(User):
    def __init__(self, first_name, last_name, email, username, password, admin_level=1):
        super().__init__(first_name, last_name, email, username, password, 'admin')
        self.admin_level = admin_level
    
    def save(self):
        super().save()
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO admins (user_id, admin_level)
                    VALUES (%s, %s)
                ''', (self.id, self.admin_level))
                conn.commit()
    
    @staticmethod
    def get_statistics():
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
    
    def create_course(self, course_code, title, description, credits, department=None, max_students=30):
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                course_id = str(uuid.uuid4())
                cursor.execute('''
                    INSERT INTO courses (id, course_code, title, description, credits, department, max_students)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (course_id, course_code, title, description, credits, department, max_students))
                conn.commit()
                return course_id
    
    def update_course(self, course_id, course_code, title, description, credits, department=None, max_students=30):
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    UPDATE courses 
                    SET course_code = %s, title = %s, description = %s, credits = %s, department = %s, max_students = %s
                    WHERE id = %s
                ''', (course_code, title, description, credits, department, max_students, course_id))
                conn.commit()
    
    def delete_course(self, course_id):
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('DELETE FROM courses WHERE id = %s', (course_id,))
                conn.commit()
    
    @staticmethod
    def get_all_courses(search=None, department=None):
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                query = 'SELECT * FROM courses WHERE is_active = TRUE'
                params = []
                
                if search:
                    query += ' AND (course_code ILIKE %s OR title ILIKE %s)'
                    search_param = f'%{search}%'
                    params.extend([search_param, search_param])
                
                if department:
                    query += ' AND department = %s'
                    params.append(department)
                
                query += ' ORDER BY course_code'
                
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_course_by_id(course_id):
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT * FROM courses WHERE id = %s', (course_id,))
                course = cursor.fetchone()
                return dict(course) if course else None

class Utils:
    @staticmethod
    def calculate_gpa(student_id):
        """Simplified GPA calculation"""
        grade_points = {'A': 4.0, 'B': 3.0, 'C': 2.0, 'D': 1.0, 'F': 0.0}
        
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT e.grade, c.credits
                    FROM enrollments e
                    JOIN course_sections cs ON e.section_id = cs.id
                    JOIN courses c ON cs.course_id = c.id
                    WHERE e.student_id = %s AND e.grade IS NOT NULL
                ''', (student_id,))
                
                grades = cursor.fetchall()
                
                if not grades:
                    return 0.0
                
                total_points = 0
                total_credits = 0
                
                for grade in grades:
                    if grade['grade'] in grade_points:
                        points = grade_points[grade['grade']]
                        credits = grade['credits']
                        total_points += points * credits
                        total_credits += credits
                
                return round(total_points / total_credits, 2) if total_credits > 0 else 0.0
    
    @staticmethod
    def get_current_semester():
        today = date.today()
        year = today.year
        month = today.month
        
        if month >= 8:
            return "Fall", year
        elif month <= 5:
            return "Spring", year
        else:
            return "Summer", year
    
    @staticmethod
    def get_available_sections(student_id=None, search=None, department=None):
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                current_semester, current_year = Utils.get_current_semester()
                
                query = '''
                    SELECT cs.id, c.course_code, c.title, c.description, c.credits, c.department,
                           cs.section_number, cs.schedule, cs.room, cs.current_enrollment, 
                           cs.max_capacity, u.first_name, u.last_name, cs.professor_id
                '''
                params = [current_semester, current_year]
                
                if student_id:
                    query += ', CASE WHEN e.id IS NOT NULL THEN true ELSE false END as is_enrolled'
                    query += '''
                        FROM course_sections cs
                        JOIN courses c ON cs.course_id = c.id
                        JOIN professors p ON cs.professor_id = p.user_id
                        JOIN users u ON p.user_id = u.id
                        LEFT JOIN enrollments e ON cs.id = e.section_id AND e.student_id = %s
                    '''
                    params = [student_id] + params
                else:
                    query += '''
                        FROM course_sections cs
                        JOIN courses c ON cs.course_id = c.id
                        JOIN professors p ON cs.professor_id = p.user_id
                        JOIN users u ON p.user_id = u.id
                    '''
                
                query += ' WHERE cs.status = %s AND cs.semester = %s AND cs.year = %s'
                params.extend(['open'])
                
                if search:
                    query += ' AND (c.course_code ILIKE %s OR c.title ILIKE %s)'
                    search_param = f'%{search}%'
                    params.extend([search_param, search_param])
                
                if department:
                    query += ' AND c.department = %s'
                    params.append(department)
                
                query += ' ORDER BY c.course_code, cs.section_number'
                
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_departments():
        """Get list of departments"""
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT DISTINCT department FROM courses WHERE department IS NOT NULL ORDER BY department')
                return [row['department'] for row in cursor.fetchall()]