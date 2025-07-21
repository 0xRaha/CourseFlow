from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from models import Database, User, Student, Professor, Admin, Utils, ValidationError, DatabaseError
from datetime import date
import os
import logging
import uuid

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# FIXED: Proper secret key handling - no hardcoded fallback
secret_key = os.getenv('SECRET_KEY')
if not secret_key:
    secret_key = os.urandom(24).hex()
    logger.warning("SECRET_KEY not set - using generated key. Set SECRET_KEY environment variable for production!")

app.secret_key = secret_key

def validate_uuid(uuid_string):
    """Validate UUID format"""
    try:
        uuid.UUID(uuid_string)
        return True
    except (ValueError, TypeError):
        return False

def validate_session():
    """Validate session and return user info"""
    if 'user_id' not in session:
        return None
    
    if not validate_uuid(session['user_id']):
        session.clear()
        return None
    
    return {
        'user_id': session['user_id'],
        'user_type': session.get('user_type')
    }

def require_auth(user_type=None):
    """Decorator to require authentication"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            user_info = validate_session()
            if not user_info:
                flash('Please log in to access this page', 'warning')
                return redirect(url_for('login'))
            
            if user_type and user_info['user_type'] != user_type:
                flash('Access denied', 'error')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

# Initialize database and create admin user
def init_admin():
    try:
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Check if admin exists
                cursor.execute("SELECT id FROM users WHERE username = 'admin'")
                if not cursor.fetchone():
                    admin = Admin('Admin', 'User', 'admin@university.edu', 'admin', 'admin', 3)
                    admin.save()
                    logger.info("Admin user created - Username: admin, Password: admin")
    except Exception as e:
        logger.error(f"Error initializing admin: {e}")

@app.route('/')
def index():
    user_info = validate_session()
    if user_info:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            # Input validation
            if not username or not password:
                flash('Username and password are required', 'error')
                return render_template('login.html')
            
            if len(username) < 3:
                flash('Invalid username', 'error')
                return render_template('login.html')
            
            user = User.authenticate(username, password)
            if user:
                session['user_id'] = user['id']  # Already string from authenticate
                session['user_type'] = user['user_type']
                session.permanent = True
                flash('Login successful!', 'success')
                logger.info(f"User {username} logged in successfully")
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password', 'error')
                logger.warning(f"Failed login attempt for username: {username}")
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            flash('Login failed. Please try again.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    session.clear()
    flash('You have been logged out', 'info')
    if user_id:
        logger.info(f"User {user_id} logged out")
    return redirect(url_for('login'))

@app.route('/dashboard')
@require_auth()
def dashboard():
    user_info = validate_session()
    user_type = user_info['user_type']
    
    if user_type == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif user_type == 'professor':
        return redirect(url_for('professor_dashboard'))
    elif user_type == 'student':
        return redirect(url_for('student_dashboard'))
    else:
        flash('Invalid user type', 'error')
        return redirect(url_for('logout'))

@app.route('/admin/dashboard')
@require_auth('admin')
def admin_dashboard():
    try:
        stats = Admin.get_statistics()
        return render_template('admin/dashboard.html', **stats)
    except Exception as e:
        logger.error(f"Error loading admin dashboard: {e}")
        flash('Error loading dashboard', 'error')
        return redirect(url_for('logout'))

@app.route('/admin/register_user', methods=['GET', 'POST'])
@require_auth('admin')
def register_user():
    if request.method == 'POST':
        try:
            # Input validation
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            email = request.form.get('email', '').strip()
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            user_type = request.form.get('user_type', '').strip()
            
            # Validate required fields
            if not all([first_name, last_name, email, username, password, user_type]):
                flash('All fields are required', 'error')
                return render_template('admin/register_user.html')
            
            if user_type not in ['student', 'professor']:
                flash('Invalid user type', 'error')
                return render_template('admin/register_user.html')
            
            if len(password) < 6:
                flash('Password must be at least 6 characters long', 'error')
                return render_template('admin/register_user.html')
            
            if user_type == 'student':
                major = request.form.get('major', '').strip()
                student = Student(first_name, last_name, email, username, password, major)
                student.save()
                flash(f'Student {username} registered successfully!', 'success')
                logger.info(f"Student {username} registered by admin")
            
            elif user_type == 'professor':
                department = request.form.get('department', '').strip()
                position = request.form.get('position', 'Assistant Professor').strip()
                office = request.form.get('office', '').strip()
                phone = request.form.get('phone', '').strip()
                
                if not department:
                    flash('Department is required for professors', 'error')
                    return render_template('admin/register_user.html')
                
                professor = Professor(first_name, last_name, email, username, password, 
                                    department, position, office, phone)
                professor.save()
                flash(f'Professor {username} registered successfully!', 'success')
                logger.info(f"Professor {username} registered by admin")
            
            return redirect(url_for('register_user'))
            
        except ValidationError as e:
            flash(f'Validation Error: {str(e)}', 'error')
        except DatabaseError as e:
            flash(f'Database Error: {str(e)}', 'error')
        except Exception as e:
            logger.error(f"Unexpected error in user registration: {e}")
            flash('An unexpected error occurred', 'error')
    
    return render_template('admin/register_user.html')

@app.route('/admin/manage_courses')
@require_auth('admin')
def manage_courses():
    try:
        courses = Admin.get_all_courses()
        return render_template('admin/manage_courses.html', courses=courses)
    except Exception as e:
        logger.error(f"Error loading courses: {e}")
        flash('Error loading courses', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/create_course', methods=['GET', 'POST'])
@require_auth('admin')
def create_course():
    if request.method == 'POST':
        try:
            admin = Admin('', '', '', '', '', 3)
            admin.id = session['user_id']
            
            # Input validation
            course_code = request.form.get('course_code', '').strip().upper()
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            credits_str = request.form.get('credits', '').strip()
            max_students_str = request.form.get('max_students', '30').strip()
            
            if not all([course_code, title, description, credits_str]):
                flash('All fields are required', 'error')
                return render_template('admin/create_course.html')
            
            try:
                credits = int(credits_str)
                max_students = int(max_students_str)
                
                if credits < 1 or credits > 6:
                    flash('Credits must be between 1 and 6', 'error')
                    return render_template('admin/create_course.html')
                
                if max_students < 1 or max_students > 100:
                    flash('Max students must be between 1 and 100', 'error')
                    return render_template('admin/create_course.html')
                    
            except ValueError:
                flash('Credits and max students must be valid numbers', 'error')
                return render_template('admin/create_course.html')
            
            course_id = admin.create_course(course_code, title, description, credits, 
                                          None, None, max_students)
            flash('Course created successfully!', 'success')
            logger.info(f"Course {course_code} created by admin")
            return redirect(url_for('manage_courses'))
            
        except ValidationError as e:
            flash(f'Validation Error: {str(e)}', 'error')
        except DatabaseError as e:
            flash(f'Database Error: {str(e)}', 'error')
        except Exception as e:
            logger.error(f"Unexpected error creating course: {e}")
            flash('An unexpected error occurred', 'error')
    
    return render_template('admin/create_course.html')

@app.route('/admin/manage_students')
@require_auth('admin')
def manage_students():
    try:
        students = User.get_all_users('student')
        sections = Admin.get_all_sections()
        return render_template('admin/manage_students.html', students=students, sections=sections)
    except Exception as e:
        logger.error(f"Error loading students: {e}")
        flash('Error loading students', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit_enrollment', methods=['POST'])
@require_auth('admin')
def edit_enrollment():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        action = data.get('action')
        student_id = data.get('student_id')
        section_id = data.get('section_id')
        
        # Validate inputs
        if not all([action, student_id, section_id]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        if not validate_uuid(student_id) or not validate_uuid(section_id):
            return jsonify({'success': False, 'error': 'Invalid ID format'}), 400
        
        admin = Admin('', '', '', '', '', 3)
        admin.id = session['user_id']
        
        if action == 'add':
            grade = data.get('grade', 'IP')  # In Progress
            if grade not in ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F', 'IP']:
                return jsonify({'success': False, 'error': 'Invalid grade'}), 400
            
            grade_points = Utils.grade_to_points(grade)
            admin.add_past_enrollment(student_id, section_id, grade, grade_points)
            return jsonify({'success': True, 'message': 'Enrollment added successfully'})
        
        elif action == 'remove':
            admin.remove_enrollment(student_id, section_id)
            return jsonify({'success': True, 'message': 'Enrollment removed successfully'})
        
        elif action == 'change_grade':
            grade = data.get('grade')
            if not grade or grade not in ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F']:
                return jsonify({'success': False, 'error': 'Invalid grade'}), 400
            
            grade_points = Utils.grade_to_points(grade)
            admin.change_student_grade(student_id, section_id, grade, grade_points)
            return jsonify({'success': True, 'message': 'Grade updated successfully'})
        
        else:
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
            
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except DatabaseError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Error in edit_enrollment: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/professor/dashboard')
@require_auth('professor')
def professor_dashboard():
    try:
        professor_info = Professor.get_by_user_id(session['user_id'])
        if not professor_info:
            flash('Professor profile not found', 'error')
            return redirect(url_for('logout'))
        
        professor = Professor('', '', '', '', '', '', '')
        professor.id = session['user_id']
        sections = professor.get_teaching_sections()
        
        return render_template('professor/dashboard.html', 
                             professor=professor_info, 
                             sections=sections)
    except Exception as e:
        logger.error(f"Error loading professor dashboard: {e}")
        flash('Error loading dashboard', 'error')
        return redirect(url_for('logout'))

@app.route('/professor/create_section', methods=['GET', 'POST'])
@require_auth('professor')
def create_section():
    if request.method == 'POST':
        try:
            professor = Professor('', '', '', '', '', '', '')
            professor.id = session['user_id']
            
            # Input validation
            course_id = request.form.get('course_id', '').strip()
            section_number = request.form.get('section_number', '').strip()
            semester = request.form.get('semester', '').strip()
            year_str = request.form.get('year', '').strip()
            schedule = request.form.get('schedule', '').strip()
            room = request.form.get('room', '').strip()
            max_capacity_str = request.form.get('max_capacity', '30').strip()
            
            if not all([course_id, section_number, semester, year_str, schedule]):
                flash('All required fields must be filled', 'error')
                return render_template('professor/create_section.html', 
                                     courses=Admin.get_all_courses(), 
                                     current_year=date.today().year)
            
            if not validate_uuid(course_id):
                flash('Invalid course selected', 'error')
                return render_template('professor/create_section.html', 
                                     courses=Admin.get_all_courses(), 
                                     current_year=date.today().year)
            
            try:
                year = int(year_str)
                max_capacity = int(max_capacity_str)
                
                if year < 2020 or year > 2030:
                    flash('Year must be between 2020 and 2030', 'error')
                    return render_template('professor/create_section.html', 
                                         courses=Admin.get_all_courses(), 
                                         current_year=date.today().year)
                
                if max_capacity < 1 or max_capacity > 100:
                    flash('Max capacity must be between 1 and 100', 'error')
                    return render_template('professor/create_section.html', 
                                         courses=Admin.get_all_courses(), 
                                         current_year=date.today().year)
                    
            except ValueError:
                flash('Year and max capacity must be valid numbers', 'error')
                return render_template('professor/create_section.html', 
                                     courses=Admin.get_all_courses(), 
                                     current_year=date.today().year)
            
            if semester not in ['Fall', 'Spring', 'Summer']:
                flash('Invalid semester', 'error')
                return render_template('professor/create_section.html', 
                                     courses=Admin.get_all_courses(), 
                                     current_year=date.today().year)
            
            section_id = professor.create_course_section(course_id, section_number, 
                                                       semester, year, schedule, 
                                                       room, max_capacity)
            flash('Course section created successfully!', 'success')
            logger.info(f"Course section created by professor {session['user_id']}")
            return redirect(url_for('professor_dashboard'))
            
        except ValidationError as e:
            flash(f'Validation Error: {str(e)}', 'error')
        except DatabaseError as e:
            flash(f'Database Error: {str(e)}', 'error')
        except Exception as e:
            logger.error(f"Unexpected error creating section: {e}")
            flash('An unexpected error occurred', 'error')
    
    # Get available courses
    try:
        courses = Admin.get_all_courses()
        current_year = date.today().year
        return render_template('professor/create_section.html', courses=courses, current_year=current_year)
    except Exception as e:
        logger.error(f"Error loading create section page: {e}")
        flash('Error loading page', 'error')
        return redirect(url_for('professor_dashboard'))

@app.route('/professor/section/<section_id>')
@require_auth('professor')
def view_section(section_id):
    if not validate_uuid(section_id):
        flash('Invalid section ID', 'error')
        return redirect(url_for('professor_dashboard'))
    
    try:
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Get section info
                cursor.execute('''
                    SELECT cs.*, c.title, c.course_code, c.credits
                    FROM course_sections cs
                    JOIN courses c ON cs.course_id = c.id
                    WHERE cs.id = %s AND cs.professor_id = %s
                ''', (section_id, session['user_id']))
                section = cursor.fetchone()
                
                if not section:
                    flash('Section not found or access denied', 'error')
                    return redirect(url_for('professor_dashboard'))
        
        # Get enrolled students
        professor = Professor('', '', '', '', '', '', '')
        professor.id = session['user_id']
        students = professor.get_section_students(section_id)
        
        return render_template('professor/section_detail.html', section=dict(section), students=students)
        
    except Exception as e:
        logger.error(f"Error loading section: {e}")
        flash('Error loading section', 'error')
        return redirect(url_for('professor_dashboard'))

@app.route('/professor/submit_grades/<section_id>', methods=['GET', 'POST'])
@require_auth('professor')
def submit_grades(section_id):
    if not validate_uuid(section_id):
        flash('Invalid section ID', 'error')
        return redirect(url_for('professor_dashboard'))
    
    if request.method == 'POST':
        try:
            professor = Professor('', '', '', '', '', '', '')
            professor.id = session['user_id']
            
            student_grades = {}
            for key, value in request.form.items():
                if key.startswith('grade_'):
                    student_id = key.replace('grade_', '')
                    grade = value.strip()
                    
                    if not validate_uuid(student_id):
                        flash('Invalid student ID in form', 'error')
                        return redirect(url_for('view_section', section_id=section_id))
                    
                    if grade and grade in ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F']:
                        grade_points = Utils.grade_to_points(grade)
                        student_grades[student_id] = {
                            'grade': grade,
                            'points': grade_points
                        }
            
            if not student_grades:
                flash('No valid grades to submit', 'warning')
                return redirect(url_for('view_section', section_id=section_id))
            
            professor.submit_grades(section_id, student_grades)
            flash('Grades submitted successfully!', 'success')
            logger.info(f"Grades submitted for section {section_id}")
            return redirect(url_for('view_section', section_id=section_id))
            
        except ValidationError as e:
            flash(f'Validation Error: {str(e)}', 'error')
        except DatabaseError as e:
            flash(f'Database Error: {str(e)}', 'error')
        except Exception as e:
            logger.error(f"Unexpected error submitting grades: {e}")
            flash('An unexpected error occurred', 'error')
    
    return redirect(url_for('view_section', section_id=section_id))

@app.route('/professor/profile')
@require_auth('professor')
def professor_profile():
    try:
        professor_info = Professor.get_by_user_id(session['user_id'])
        if not professor_info:
            flash('Professor profile not found', 'error')
            return redirect(url_for('logout'))
        
        professor = Professor('', '', '', '', '', '', '')
        professor.id = session['user_id']
        sections = professor.get_teaching_sections()
        
        return render_template('professor/profile.html', professor=professor_info, sections=sections)
    except Exception as e:
        logger.error(f"Error loading professor profile: {e}")
        flash('Error loading profile', 'error')
        return redirect(url_for('professor_dashboard'))

@app.route('/student/dashboard')
@require_auth('student')
def student_dashboard():
    try:
        student_info = Student.get_by_user_id(session['user_id'])
        if not student_info:
            flash('Student profile not found', 'error')
            return redirect(url_for('logout'))
        
        # Get current semester
        current_semester, current_year = Utils.get_current_semester()
        
        # Get current classes
        student = Student('', '', '', '', '', '')
        student.id = session['user_id']
        current_classes = student.get_class_schedule(current_semester, current_year)
        
        # Calculate GPA
        gpa = Utils.calculate_gpa(session['user_id'])
        
        return render_template('student/dashboard.html', 
                             student=student_info, 
                             current_classes=current_classes,
                             gpa=gpa)
    except Exception as e:
        logger.error(f"Error loading student dashboard: {e}")
        flash('Error loading dashboard', 'error')
        return redirect(url_for('logout'))

@app.route('/student/courses')
@require_auth('student')
def browse_courses():
    try:
        # FIXED: Get sections with enrollment status in single query
        sections = Utils.get_available_sections(session['user_id'])
        return render_template('student/browse_courses.html', sections=sections)
    except Exception as e:
        logger.error(f"Error loading courses: {e}")
        flash('Error loading courses', 'error')
        return redirect(url_for('student_dashboard'))

@app.route('/student/enroll/<section_id>')
@require_auth('student')
def enroll_in_course(section_id):
    if not validate_uuid(section_id):
        flash('Invalid section ID', 'error')
        return redirect(url_for('browse_courses'))
    
    try:
        student = Student('', '', '', '', '', '')
        student.id = session['user_id']
        student.enroll_in_section(section_id)
        flash('Successfully enrolled in course!', 'success')
        logger.info(f"Student {session['user_id']} enrolled in section {section_id}")
    except ValidationError as e:
        flash(f'Enrollment failed: {str(e)}', 'error')
    except DatabaseError as e:
        flash(f'Enrollment failed: {str(e)}', 'error')
    except Exception as e:
        logger.error(f"Unexpected error during enrollment: {e}")
        flash('Enrollment failed: An unexpected error occurred', 'error')
    
    return redirect(url_for('browse_courses'))

@app.route('/student/drop/<section_id>')
@require_auth('student')
def drop_course(section_id):
    if not validate_uuid(section_id):
        flash('Invalid section ID', 'error')
        return redirect(url_for('browse_courses'))
    
    try:
        student = Student('', '', '', '', '', '')
        student.id = session['user_id']
        student.disenroll_from_section(section_id)
        flash('Successfully dropped the course!', 'success')
        logger.info(f"Student {session['user_id']} dropped section {section_id}")
    except ValidationError as e:
        flash(f'Drop failed: {str(e)}', 'error')
    except DatabaseError as e:
        flash(f'Drop failed: {str(e)}', 'error')
    except Exception as e:
        logger.error(f"Unexpected error during drop: {e}")
        flash('Drop failed: An unexpected error occurred', 'error')
    
    return redirect(url_for('browse_courses'))

@app.route('/student/grades')
@require_auth('student')
def view_grades():
    try:
        student = Student('', '', '', '', '', '')
        student.id = session['user_id']
        grades = student.get_all_grades()
        
        # Organize grades by semester
        grades_by_semester = {}
        for grade in grades:
            key = f"{grade['semester']} {grade['year']}"
            if key not in grades_by_semester:
                grades_by_semester[key] = []
            grades_by_semester[key].append(grade)
        
        # Calculate GPA
        gpa = Utils.calculate_gpa(session['user_id'])
        
        return render_template('student/grades.html', 
                             grades_by_semester=grades_by_semester, 
                             gpa=gpa)
    except Exception as e:
        logger.error(f"Error loading grades: {e}")
        flash('Error loading grades', 'error')
        return redirect(url_for('student_dashboard'))

@app.route('/student/schedule')
@require_auth('student')
def view_schedule():
    try:
        # Get current semester
        current_semester, current_year = Utils.get_current_semester()
        
        student = Student('', '', '', '', '', '')
        student.id = session['user_id']
        schedule = student.get_class_schedule(current_semester, current_year)
        
        # Organize schedule by day
        schedule_by_day = {
            'M': [], 'T': [], 'W': [], 'R': [], 'F': []
        }
        
        for course in schedule:
            schedule_parts = course['schedule'].split(' ')
            if len(schedule_parts) == 2:
                days, time = schedule_parts
                for day in days:
                    if day in schedule_by_day:
                        schedule_by_day[day].append({
                            'course': course,
                            'time': time
                        })
        
        # Sort each day by time
        for day in schedule_by_day:
            schedule_by_day[day].sort(key=lambda x: x['time'])
        
        return render_template('student/schedule.html', 
                             schedule=schedule, 
                             schedule_by_day=schedule_by_day,
                             current_semester=current_semester,
                             current_year=current_year)
    except Exception as e:
        logger.error(f"Error loading schedule: {e}")
        flash('Error loading schedule', 'error')
        return redirect(url_for('student_dashboard'))

@app.route('/search/professors')
def search_professors():
    try:
        professors = User.get_all_users('professor')
        return render_template('search_professors.html', professors=professors)
    except Exception as e:
        logger.error(f"Error loading professors: {e}")
        flash('Error loading professors', 'error')
        return redirect(url_for('index'))

@app.route('/professor/<professor_id>')
def view_professor(professor_id):
    if not validate_uuid(professor_id):
        flash('Invalid professor ID', 'error')
        return redirect(url_for('index'))
    
    try:
        professor_info = Professor.get_by_user_id(professor_id)
        
        if not professor_info:
            flash('Professor not found', 'error')
            return redirect(url_for('index'))
        
        professor = Professor('', '', '', '', '', '', '')
        professor.id = professor_id
        sections = professor.get_teaching_sections()
        
        return render_template('professor/profile.html', 
                             professor=professor_info, 
                             sections=sections,
                             is_public=True)
    except Exception as e:
        logger.error(f"Error loading professor profile: {e}")
        flash('Error loading professor profile', 'error')
        return redirect(url_for('index'))

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return render_template('errors/500.html'), 500

@app.errorhandler(ValidationError)
def handle_validation_error(error):
    flash(f'Validation Error: {str(error)}', 'error')
    return redirect(request.referrer or url_for('index'))

@app.errorhandler(DatabaseError)
def handle_database_error(error):
    logger.error(f"Database error: {error}")
    flash('A database error occurred. Please try again.', 'error')
    return redirect(request.referrer or url_for('index'))

if __name__ == '__main__':
    try:
        init_admin()
        app.run(debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true', 
                host=os.getenv('FLASK_HOST', '127.0.0.1'),
                port=int(os.getenv('FLASK_PORT', '5000')))
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise