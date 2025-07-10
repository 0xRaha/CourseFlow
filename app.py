from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from models import Database, User, Student, Professor, Admin, Utils
import json
from datetime import datetime, date
import uuid

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

# Initialize database and create admin user
def init_admin():
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Check if admin exists
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        admin = Admin('Admin', 'User', 'admin@university.edu', 'admin', 'admin', 3)
        admin.save()
        print("Admin user created - Username: admin, Password: admin")
    
    conn.close()

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.authenticate(username, password)
        if user:
            session['user_id'] = user['id']
            session['user_type'] = user['user_type']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_type = session['user_type']
    if user_type == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif user_type == 'professor':
        return redirect(url_for('professor_dashboard'))
    elif user_type == 'student':
        return redirect(url_for('student_dashboard'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or session['user_type'] != 'admin':
        return redirect(url_for('login'))
    
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get statistics
    cursor.execute("SELECT COUNT(*) FROM users WHERE user_type = 'student'")
    student_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE user_type = 'professor'")
    professor_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM courses")
    course_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM course_sections")
    section_count = cursor.fetchone()[0]
    
    conn.close()
    
    return render_template('admin/dashboard.html',
                         student_count=student_count,
                         professor_count=professor_count,
                         course_count=course_count,
                         section_count=section_count)

@app.route('/admin/register_user', methods=['GET', 'POST'])
def register_user():
    if 'user_id' not in session or session['user_type'] != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            email = request.form['email']
            username = request.form['username']
            password = request.form['password']
            user_type = request.form['user_type']
            
            if user_type == 'student':
                major = request.form.get('major')
                student = Student(first_name, last_name, email, username, password, major)
                student.save()
                flash(f'Student {username} registered successfully!', 'success')
            
            elif user_type == 'professor':
                department = request.form['department']
                position = request.form.get('position', 'Assistant Professor')
                office = request.form.get('office')
                phone = request.form.get('phone')
                
                professor = Professor(first_name, last_name, email, username, password, 
                                    department, position, office, phone)
                professor.save()
                flash(f'Professor {username} registered successfully!', 'success')
            
            return redirect(url_for('register_user'))
            
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
    
    return render_template('admin/register_user.html')

@app.route('/admin/manage_courses')
def manage_courses():
    if 'user_id' not in session or session['user_type'] != 'admin':
        return redirect(url_for('login'))
    
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
    return render_template('admin/manage_courses.html', courses=courses)

@app.route('/admin/create_course', methods=['GET', 'POST'])
def create_course():
    if 'user_id' not in session or session['user_type'] != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            admin = Admin('', '', '', '', '', 3)
            admin.id = session['user_id']
            
            course_code = request.form['course_code']
            title = request.form['title']
            description = request.form['description']
            credits = int(request.form['credits'])
            max_students = int(request.form.get('max_students', 30))
            
            course_id = admin.create_course(course_code, title, description, credits, 
                                          None, None, max_students)
            flash('Course created successfully!', 'success')
            return redirect(url_for('manage_courses'))
            
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
    
    return render_template('create_course.html')

@app.route('/professor/dashboard')
def professor_dashboard():
    if 'user_id' not in session or session['user_type'] != 'professor':
        return redirect(url_for('login'))
    
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get professor info
    cursor.execute('''
        SELECT u.*, p.employee_id, p.department, p.position, p.office_location, p.phone
        FROM users u
        JOIN professors p ON u.id = p.user_id
        WHERE u.id = ?
    ''', (session['user_id'],))
    professor_info = cursor.fetchone()
    
    # Get teaching sections
    cursor.execute('''
        SELECT cs.*, c.title, c.course_code, c.credits, cs.current_enrollment, cs.max_capacity
        FROM course_sections cs
        JOIN courses c ON cs.course_id = c.id
        WHERE cs.professor_id = ?
        ORDER BY cs.year DESC, cs.semester DESC
    ''', (session['user_id'],))
    sections = cursor.fetchall()
    
    conn.close()
    
    return render_template('professor_dashboard.html', 
                         professor=professor_info, 
                         sections=sections)

@app.route('/professor/create_section', methods=['GET', 'POST'])
def create_section():
    if 'user_id' not in session or session['user_type'] != 'professor':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            professor = Professor('', '', '', '', '', '', '')
            professor.id = session['user_id']
            
            course_id = request.form['course_id']
            section_number = request.form['section_number']
            semester = request.form['semester']
            year = int(request.form['year'])
            schedule = request.form['schedule']
            room = request.form.get('room')
            max_capacity = int(request.form.get('max_capacity', 30))
            
            section_id = professor.create_course_section(course_id, section_number, 
                                                       semester, year, schedule, 
                                                       room, max_capacity)
            flash('Course section created successfully!', 'success')
            return redirect(url_for('professor_dashboard'))
            
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
    
    # Get available courses
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, course_code, title FROM courses WHERE is_active = 1')
    courses = cursor.fetchall()
    conn.close()
    
    return render_template('create_section.html', courses=courses)

@app.route('/professor/section/<section_id>')
def view_section(section_id):
    if 'user_id' not in session or session['user_type'] != 'professor':
        return redirect(url_for('login'))
    
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get section info
    cursor.execute('''
        SELECT cs.*, c.title, c.course_code, c.credits
        FROM course_sections cs
        JOIN courses c ON cs.course_id = c.id
        WHERE cs.id = ? AND cs.professor_id = ?
    ''', (section_id, session['user_id']))
    section = cursor.fetchone()
    
    if not section:
        flash('Section not found', 'error')
        return redirect(url_for('professor_dashboard'))
    
    # Get enrolled students
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
    
    return render_template('section_detail.html', section=section, students=students)

@app.route('/student/dashboard')
def student_dashboard():
    if 'user_id' not in session or session['user_type'] != 'student':
        return redirect(url_for('login'))
    
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get student info
    cursor.execute('''
        SELECT u.*, s.student_id, s.gpa, s.year_level, s.major, s.status
        FROM users u
        JOIN students s ON u.id = s.user_id
        WHERE u.id = ?
    ''', (session['user_id'],))
    student_info = cursor.fetchone()
    
    # Get current semester
    current_semester, current_year = Utils.get_current_semester()
    
    # Get current enrollments
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
    ''', (session['user_id'], 'Fall', current_year))
    current_classes = cursor.fetchall()
    
    # Calculate GPA
    gpa = Utils.calculate_gpa(session['user_id'])
    
    conn.close()
    
    return render_template('student_dashboard.html', 
                         student=student_info, 
                         current_classes=current_classes,
                         gpa=gpa)

@app.route('/student/courses')
def browse_courses():
    if 'user_id' not in session or session['user_type'] != 'student':
        return redirect(url_for('login'))
    
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get current semester
    current_semester, current_year = Utils.get_current_semester()
    
    # Get available course sections
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
    ''', ('Fall', current_year))
    sections = cursor.fetchall()
    
    conn.close()
    
    return render_template('browse_courses.html', sections=sections)

@app.route('/student/enroll/<section_id>')
def enroll_in_course(section_id):
    if 'user_id' not in session or session['user_type'] != 'student':
        return redirect(url_for('login'))
    
    try:
        student = Student('', '', '', '', '', '')
        student.id = session['user_id']
        student.enroll_in_section(section_id)
        flash('Successfully enrolled in course!', 'success')
    except Exception as e:
        flash(f'Enrollment failed: {str(e)}', 'error')
    
    return redirect(url_for('browse_courses'))

@app.route('/student/grades')
def view_grades():
    if 'user_id' not in session or session['user_type'] != 'student':
        return redirect(url_for('login'))
    
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get all enrollments with grades
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
    ''', (session['user_id'],))
    grades = cursor.fetchall()
    
    # Calculate GPA
    gpa = Utils.calculate_gpa(session['user_id'])
    
    conn.close()
    
    return render_template('student_grades.html', grades=grades, gpa=gpa)

@app.route('/student/schedule')
def view_schedule():
    if 'user_id' not in session or session['user_type'] != 'student':
        return redirect(url_for('login'))
    
    # Get current semester
    current_semester, current_year = Utils.get_current_semester()
    
    student = Student('', '', '', '', '', '')
    student.id = session['user_id']
    schedule = student.get_class_schedule('Fall', current_year)
    
    return render_template('student_schedule.html', schedule=schedule)

if __name__ == '__main__':
    init_admin()
    app.run(debug=True)