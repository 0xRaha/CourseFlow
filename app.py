from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from models import Database, User, Student, Professor, Admin, Utils
from datetime import date
import os

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')  # Change this in production

# Initialize database and create admin user
def init_admin():
    try:
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
    except Exception as e:
        print(f"Error initializing admin: {e}")

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
            session['user_id'] = str(user['id'])
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
    
    stats = Admin.get_statistics()
    
    return render_template('admin/dashboard.html', **stats)

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
    
    courses = Admin.get_all_courses()
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
    
    return render_template('admin/create_course.html')

@app.route('/admin/manage_students')
def manage_students():
    if 'user_id' not in session or session['user_type'] != 'admin':
        return redirect(url_for('login'))
    
    students = User.get_all_users('student')
    sections = Admin.get_all_sections()
    
    return render_template('admin/manage_students.html', students=students, sections=sections)

@app.route('/admin/edit_enrollment', methods=['POST'])
def edit_enrollment():
    if 'user_id' not in session or session['user_type'] != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        action = data.get('action')
        student_id = data.get('student_id')
        section_id = data.get('section_id')
        
        admin = Admin('', '', '', '', '', 3)
        admin.id = session['user_id']
        
        if action == 'add':
            grade = data.get('grade', 'IP')  # In Progress
            grade_points = Utils.grade_to_points(grade)
            admin.add_past_enrollment(student_id, section_id, grade, grade_points)
            return jsonify({'success': True, 'message': 'Enrollment added successfully'})
        
        elif action == 'remove':
            admin.remove_enrollment(student_id, section_id)
            return jsonify({'success': True, 'message': 'Enrollment removed successfully'})
        
        elif action == 'change_grade':
            grade = data.get('grade')
            grade_points = Utils.grade_to_points(grade)
            admin.change_student_grade(student_id, section_id, grade, grade_points)
            return jsonify({'success': True, 'message': 'Grade updated successfully'})
        
        else:
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/professor/dashboard')
def professor_dashboard():
    if 'user_id' not in session or session['user_type'] != 'professor':
        return redirect(url_for('login'))
    
    professor_info = Professor.get_by_user_id(session['user_id'])
    
    professor = Professor('', '', '', '', '', '', '')
    professor.id = session['user_id']
    sections = professor.get_teaching_sections()
    
    return render_template('professor/dashboard.html', 
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
    courses = Admin.get_all_courses()
    current_year = date.today().year
    
    return render_template('professor/create_section.html', courses=courses, current_year=current_year)

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
        WHERE cs.id = %s AND cs.professor_id = %s
    ''', (section_id, session['user_id']))
    section = cursor.fetchone()
    
    if not section:
        flash('Section not found', 'error')
        return redirect(url_for('professor_dashboard'))
    
    conn.close()
    
    # Get enrolled students
    professor = Professor('', '', '', '', '', '', '')
    professor.id = session['user_id']
    students = professor.get_section_students(section_id)
    
    return render_template('professor/section_detail.html', section=dict(section), students=students)

@app.route('/professor/submit_grades/<section_id>', methods=['GET', 'POST'])
def submit_grades(section_id):
    if 'user_id' not in session or session['user_type'] != 'professor':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            professor = Professor('', '', '', '', '', '', '')
            professor.id = session['user_id']
            
            student_grades = {}
            for key, value in request.form.items():
                if key.startswith('grade_'):
                    student_id = key.replace('grade_', '')
                    grade = value
                    grade_points = Utils.grade_to_points(grade)
                    student_grades[student_id] = {
                        'grade': grade,
                        'points': grade_points
                    }
            
            professor.submit_grades(section_id, student_grades)
            flash('Grades submitted successfully!', 'success')
            return redirect(url_for('view_section', section_id=section_id))
            
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('view_section', section_id=section_id))

@app.route('/professor/profile')
def professor_profile():
    if 'user_id' not in session or session['user_type'] != 'professor':
        return redirect(url_for('login'))
    
    professor_info = Professor.get_by_user_id(session['user_id'])
    professor = Professor('', '', '', '', '', '', '')
    professor.id = session['user_id']
    sections = professor.get_teaching_sections()
    
    return render_template('professor/profile.html', professor=professor_info, sections=sections)

@app.route('/student/dashboard')
def student_dashboard():
    if 'user_id' not in session or session['user_type'] != 'student':
        return redirect(url_for('login'))
    
    student_info = Student.get_by_user_id(session['user_id'])
    
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

@app.route('/student/courses')
def browse_courses():
    if 'user_id' not in session or session['user_type'] != 'student':
        return redirect(url_for('login'))
    
    sections = Utils.get_available_sections(session['user_id'])
    
    # Check which sections the student is already enrolled in
    for section in sections:
        enrollment = Utils.get_student_enrollments(session['user_id'], section['id'])
        section['is_enrolled'] = enrollment is not None
    
    return render_template('student/browse_courses.html', sections=sections)

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

@app.route('/student/drop/<section_id>')
def drop_course(section_id):
    if 'user_id' not in session or session['user_type'] != 'student':
        return redirect(url_for('login'))
    
    try:
        student = Student('', '', '', '', '', '')
        student.id = session['user_id']
        student.disenroll_from_section(section_id)
        flash('Successfully dropped the course!', 'success')
    except Exception as e:
        flash(f'Drop failed: {str(e)}', 'error')
    
    return redirect(url_for('browse_courses'))

@app.route('/student/grades')
def view_grades():
    if 'user_id' not in session or session['user_type'] != 'student':
        return redirect(url_for('login'))
    
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

@app.route('/student/schedule')
def view_schedule():
    if 'user_id' not in session or session['user_type'] != 'student':
        return redirect(url_for('login'))
    
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

@app.route('/search/professors')
def search_professors():
    professors = User.get_all_users('professor')
    return render_template('search_professors.html', professors=professors)

@app.route('/professor/<professor_id>')
def view_professor(professor_id):
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

if __name__ == '__main__':
    init_admin()
    app.run(debug=True)