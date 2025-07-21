from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from models import Database, User, Student, Professor, Admin, Utils
from datetime import date
import os
import uuid

app = Flask(__name__)

# Simple secret key handling
secret_key = os.getenv('SECRET_KEY')
if not secret_key:
    secret_key = os.urandom(24).hex()
    
app.secret_key = secret_key

def validate_uuid(uuid_string):
    """Validate UUID format"""
    try:
        uuid.UUID(uuid_string)
        return True
    except:
        return False

def require_auth(user_type=None):
    """Simple authentication decorator"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in', 'error')
                return redirect(url_for('login'))
            
            if not validate_uuid(session['user_id']):
                session.clear()
                flash('Invalid session', 'error')
                return redirect(url_for('login'))
            
            if user_type and session.get('user_type') != user_type:
                flash('Access denied', 'error')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

# Initialize admin user
def init_admin():
    try:
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM users WHERE username = 'admin'")
                if not cursor.fetchone():
                    admin = Admin('Admin', 'User', 'admin@university.edu', 'admin', 'admin', 3)
                    admin.save()
    except:
        pass

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Username and password required', 'error')
            return render_template('login.html')
        
        user = User.authenticate(username, password)
        if user:
            session['user_id'] = user['id']
            session['user_type'] = user['user_type']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@require_auth()
def dashboard():
    user_type = session.get('user_type')
    
    if user_type == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif user_type == 'professor':
        return redirect(url_for('professor_dashboard'))
    elif user_type == 'student':
        return redirect(url_for('student_dashboard'))
    else:
        return redirect(url_for('logout'))

# Profile editing
@app.route('/profile/edit', methods=['GET', 'POST'])
@require_auth()
def edit_profile():
    user = User.get_by_id(session['user_id'])
    if not user:
        return redirect(url_for('logout'))
    
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        
        if first_name and last_name and email:
            try:
                user_obj = User(user['first_name'], user['last_name'], user['email'], 
                               user['username'], None, user['user_type'])
                user_obj.id = session['user_id']
                user_obj.update_profile(first_name, last_name, email)
                flash('Profile updated!', 'success')
                return redirect(url_for('dashboard'))
            except:
                flash('Update failed', 'error')
        else:
            flash('All fields required', 'error')
    
    return render_template('edit_profile.html', user=user)

# ADMIN ROUTES
@app.route('/admin/dashboard')
@require_auth('admin')
def admin_dashboard():
    stats = Admin.get_statistics()
    return render_template('admin/dashboard.html', **stats)

@app.route('/admin/register_user', methods=['GET', 'POST'])
@require_auth('admin')
def register_user():
    if request.method == 'POST':
        try:
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            email = request.form.get('email', '').strip()
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            user_type = request.form.get('user_type', '').strip()
            
            if not all([first_name, last_name, email, username, password, user_type]):
                flash('All fields required', 'error')
                return render_template('admin/register_user.html')
            
            if user_type == 'student':
                major = request.form.get('major', '').strip()
                student = Student(first_name, last_name, email, username, password, major)
                student.save()
                flash(f'Student {username} registered!', 'success')
            
            elif user_type == 'professor':
                department = request.form.get('department', '').strip()
                position = request.form.get('position', 'Assistant Professor').strip()
                office = request.form.get('office', '').strip()
                phone = request.form.get('phone', '').strip()
                
                professor = Professor(first_name, last_name, email, username, password, 
                                    department, position, office, phone)
                professor.save()
                flash(f'Professor {username} registered!', 'success')
            
            return redirect(url_for('register_user'))
            
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
    
    return render_template('admin/register_user.html')

@app.route('/admin/manage_courses')
@require_auth('admin')
def manage_courses():
    search = request.args.get('search', '')
    department = request.args.get('department', '')
    
    courses = Admin.get_all_courses(search=search if search else None, 
                                   department=department if department else None)
    departments = Utils.get_departments()
    
    return render_template('admin/manage_courses.html', 
                          courses=courses, 
                          departments=departments,
                          search=search,
                          selected_department=department)

@app.route('/admin/create_course', methods=['GET', 'POST'])
@require_auth('admin')
def create_course():
    if request.method == 'POST':
        try:
            admin = Admin('', '', '', '', '', 3)
            admin.id = session['user_id']
            
            course_code = request.form.get('course_code', '').strip().upper()
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            credits = int(request.form.get('credits', '3'))
            department = request.form.get('department', '').strip()
            max_students = int(request.form.get('max_students', '30'))
            
            if not all([course_code, title, description]):
                flash('Required fields missing', 'error')
                return render_template('admin/create_course.html')
            
            admin.create_course(course_code, title, description, credits, department, max_students)
            flash('Course created!', 'success')
            return redirect(url_for('manage_courses'))
            
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
    
    return render_template('admin/create_course.html')

@app.route('/admin/course/<course_id>/edit', methods=['GET', 'POST'])
@require_auth('admin')
def edit_course(course_id):
    if not validate_uuid(course_id):
        flash('Invalid course ID', 'error')
        return redirect(url_for('manage_courses'))
    
    course = Admin.get_course_by_id(course_id)
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('manage_courses'))
    
    if request.method == 'POST':
        try:
            admin = Admin('', '', '', '', '', 3)
            admin.id = session['user_id']
            
            course_code = request.form.get('course_code', '').strip().upper()
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            credits = int(request.form.get('credits', '3'))
            department = request.form.get('department', '').strip()
            max_students = int(request.form.get('max_students', '30'))
            
            admin.update_course(course_id, course_code, title, description, 
                              credits, department, max_students)
            flash('Course updated!', 'success')
            return redirect(url_for('manage_courses'))
            
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
    
    return render_template('admin/edit_course.html', course=course)

@app.route('/admin/course/<course_id>/delete', methods=['POST'])
@require_auth('admin')
def delete_course(course_id):
    if not validate_uuid(course_id):
        flash('Invalid course ID', 'error')
        return redirect(url_for('manage_courses'))
    
    try:
        admin = Admin('', '', '', '', '', 3)
        admin.id = session['user_id']
        admin.delete_course(course_id)
        flash('Course deleted!', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('manage_courses'))

@app.route('/admin/manage_students')
@require_auth('admin')
def manage_students():
    search = request.args.get('search', '')
    students = User.get_all_users('student', search if search else None)
    return render_template('admin/manage_students.html', students=students, search=search)

# PROFESSOR ROUTES
@app.route('/professor/dashboard')
@require_auth('professor')
def professor_dashboard():
    professor_info = Professor.get_by_user_id(session['user_id'])
    if not professor_info:
        return redirect(url_for('logout'))
    
    professor = Professor('', '', '', '', '', '', '')
    professor.id = session['user_id']
    sections = professor.get_teaching_sections()
    
    return render_template('professor/dashboard.html', 
                         professor=professor_info, 
                         sections=sections)

@app.route('/professor/create_section', methods=['GET', 'POST'])
@require_auth('professor')
def create_section():
    if request.method == 'POST':
        try:
            professor = Professor('', '', '', '', '', '', '')
            professor.id = session['user_id']
            
            course_id = request.form.get('course_id', '').strip()
            section_number = request.form.get('section_number', '').strip()
            semester = request.form.get('semester', '').strip()
            year = int(request.form.get('year', ''))
            schedule = request.form.get('schedule', '').strip()
            room = request.form.get('room', '').strip()
            max_capacity = int(request.form.get('max_capacity', '30'))
            
            section_id = professor.create_course_section(course_id, section_number, 
                                                       semester, year, schedule, 
                                                       room, max_capacity)
            flash('Section created!', 'success')
            return redirect(url_for('professor_dashboard'))
            
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
    
    courses = Admin.get_all_courses()
    current_year = date.today().year
    return render_template('professor/create_section.html', 
                          courses=courses, 
                          current_year=current_year)

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
                cursor.execute('''
                    SELECT cs.*, c.title, c.course_code, c.credits
                    FROM course_sections cs
                    JOIN courses c ON cs.course_id = c.id
                    WHERE cs.id = %s AND cs.professor_id = %s
                ''', (section_id, session['user_id']))
                section = cursor.fetchone()
                
                if not section:
                    flash('Section not found', 'error')
                    return redirect(url_for('professor_dashboard'))
        
        professor = Professor('', '', '', '', '', '', '')
        professor.id = session['user_id']
        students = professor.get_section_students(section_id)
        
        return render_template('professor/section_detail.html', 
                             section=dict(section), 
                             students=students)
        
    except Exception as e:
        flash('Error loading section', 'error')
        return redirect(url_for('professor_dashboard'))

@app.route('/professor/submit_grades/<section_id>', methods=['POST'])
@require_auth('professor')
def submit_grades(section_id):
    if not validate_uuid(section_id):
        return redirect(url_for('professor_dashboard'))
    
    try:
        professor = Professor('', '', '', '', '', '', '')
        professor.id = session['user_id']
        
        student_grades = {}
        for key, value in request.form.items():
            if key.startswith('grade_'):
                enrollment_id = key.replace('grade_', '')
                grade = value.strip()
                
                if grade and grade in ['A', 'B', 'C', 'D', 'F']:
                    student_grades[enrollment_id] = grade
        
        if student_grades:
            professor.submit_grades(section_id, student_grades)
            flash('Grades submitted!', 'success')
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('view_section', section_id=section_id))

@app.route('/professor/section/<section_id>/announcement', methods=['GET', 'POST'])
@require_auth('professor')
def create_announcement(section_id):
    if not validate_uuid(section_id):
        return redirect(url_for('professor_dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        
        if title and content:
            try:
                professor = Professor('', '', '', '', '', '', '')
                professor.id = session['user_id']
                professor.create_announcement(section_id, title, content)
                flash('Announcement created!', 'success')
                return redirect(url_for('view_section', section_id=section_id))
            except Exception as e:
                flash(f'Error: {str(e)}', 'error')
        else:
            flash('Title and content required', 'error')
    
    return render_template('professor/create_announcement.html', section_id=section_id)

@app.route('/professor/profile')
@require_auth('professor')
def professor_profile():
    professor_info = Professor.get_by_user_id(session['user_id'])
    if not professor_info:
        return redirect(url_for('logout'))
    
    professor = Professor('', '', '', '', '', '', '')
    professor.id = session['user_id']
    sections = professor.get_teaching_sections()
    
    return render_template('professor/profile.html', 
                          professor=professor_info, 
                          sections=sections)

# STUDENT ROUTES
@app.route('/student/dashboard')
@require_auth('student')
def student_dashboard():
    student_info = Student.get_by_user_id(session['user_id'])
    if not student_info:
        return redirect(url_for('logout'))
    
    current_semester, current_year = Utils.get_current_semester()
    
    student = Student('', '', '', '', '', '')
    student.id = session['user_id']
    current_classes = student.get_class_schedule(current_semester, current_year)
    announcements = student.get_announcements()
    
    gpa = Utils.calculate_gpa(session['user_id'])
    
    return render_template('student/dashboard.html', 
                         student=student_info, 
                         current_classes=current_classes,
                         announcements=announcements,
                         gpa=gpa)

@app.route('/student/courses')
@require_auth('student')
def browse_courses():
    search = request.args.get('search', '')
    department = request.args.get('department', '')
    
    sections = Utils.get_available_sections(
        session['user_id'], 
        search if search else None,
        department if department else None
    )
    departments = Utils.get_departments()
    
    return render_template('student/browse_courses.html', 
                          sections=sections, 
                          departments=departments,
                          search=search,
                          selected_department=department)

@app.route('/student/enroll/<section_id>')
@require_auth('student')
def enroll_in_course(section_id):
    if not validate_uuid(section_id):
        return redirect(url_for('browse_courses'))
    
    try:
        student = Student('', '', '', '', '', '')
        student.id = session['user_id']
        student.enroll_in_section(section_id)
        flash('Enrolled successfully!', 'success')
    except Exception as e:
        flash(f'Enrollment failed: {str(e)}', 'error')
    
    return redirect(url_for('browse_courses'))

@app.route('/student/drop/<section_id>')
@require_auth('student')
def drop_course(section_id):
    if not validate_uuid(section_id):
        return redirect(url_for('browse_courses'))
    
    try:
        student = Student('', '', '', '', '', '')
        student.id = session['user_id']
        student.drop_course(section_id)
        flash('Course dropped!', 'success')
    except Exception as e:
        flash(f'Drop failed: {str(e)}', 'error')
    
    return redirect(url_for('browse_courses'))

@app.route('/student/grades')
@require_auth('student')
def view_grades():
    student = Student('', '', '', '', '', '')
    student.id = session['user_id']
    grades = student.get_all_grades()
    
    # Group by semester
    grades_by_semester = {}
    for grade in grades:
        key = f"{grade['semester']} {grade['year']}"
        if key not in grades_by_semester:
            grades_by_semester[key] = []
        grades_by_semester[key].append(grade)
    
    gpa = Utils.calculate_gpa(session['user_id'])
    
    return render_template('student/grades.html', 
                         grades_by_semester=grades_by_semester, 
                         gpa=gpa)

@app.route('/student/schedule')
@require_auth('student')
def view_schedule():
    try:
        current_semester, current_year = Utils.get_current_semester()
        
        student = Student('', '', '', '', '', '')
        student.id = session['user_id']
        schedule = student.get_class_schedule(current_semester, current_year)
        
        # Create weekly schedule view
        schedule_by_day = {'Monday': [], 'Tuesday': [], 'Wednesday': [], 'Thursday': [], 'Friday': []}
        day_mapping = {'M': 'Monday', 'T': 'Tuesday', 'W': 'Wednesday', 'R': 'Thursday', 'F': 'Friday'}
        
        for course in schedule:
            if course['schedule'] and ' ' in course['schedule']:
                days_part = course['schedule'].split(' ')[0]
                time_part = course['schedule'].split(' ')[1] if len(course['schedule'].split(' ')) > 1 else ''
                
                for day_char in days_part:
                    if day_char in day_mapping:
                        day_name = day_mapping[day_char]
                        schedule_by_day[day_name].append({
                            'course': course,
                            'time': time_part
                        })
        
        # Sort by time for each day
        for day in schedule_by_day:
            schedule_by_day[day].sort(key=lambda x: x['time'])
        
        return render_template('student/schedule.html', 
                             schedule=schedule, 
                             schedule_by_day=schedule_by_day,
                             current_semester=current_semester,
                             current_year=current_year)
    except Exception as e:
        flash('Error loading schedule', 'error')
        return redirect(url_for('student_dashboard'))

# PUBLIC ROUTES
@app.route('/search/professors')
def search_professors():
    search = request.args.get('search', '')
    professors = User.get_all_users('professor', search if search else None)
    return render_template('search_professors.html', professors=professors, search=search)

@app.route('/professor/<professor_id>')
def view_professor(professor_id):
    if not validate_uuid(professor_id):
        return redirect(url_for('search_professors'))
    
    professor_info = Professor.get_by_user_id(professor_id)
    if not professor_info:
        return redirect(url_for('search_professors'))
    
    professor = Professor('', '', '', '', '', '', '')
    professor.id = professor_id
    sections = professor.get_teaching_sections()
    
    return render_template('professor/profile.html', 
                         professor=professor_info, 
                         sections=sections,
                         is_public=True)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    init_admin()
    app.run(debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true')