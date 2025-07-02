from flask import Flask, render_template, redirect, flash, url_for
from requests import request
from .models import Student, Professor
from .utils import *

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        email = request.form['email']
        username = request.form['username']
        password = generate_password(request.form['password'])
        user_type = request.form['user_type']
        unique_id = generate_userid()
        department = request.form.get('department', '')

        try:
            if user_type == 'student':
                user = Student(unique_id, firstname, lastname, email, username, password)
            elif user_type == 'teacher':
                if not department:
                    flash('Department is required for professors.')
                    print("Signup failed: Department required for Professor.")
                    return render_template('signup.html')
                user = Professor(unique_id, firstname, lastname, email, username, password, department)
            else:
                flash('User type is unvalid!')
                print("Signup failed: Invalid user type.")
                return render_template('signup.html')

            return redirect(url_for('index'))
        except ValueError as e:
            flash(str(e))
            print(f"Signup error: {str(e)}")
            return render_template('signup.html')

    return render_template('signup.html')

app.run(debug=True)