# CourseFlow 📚
*A Modern University Administration System*

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)
![SQLite](https://img.shields.io/badge/Database-SQLite3-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Version](https://img.shields.io/badge/Version-v0.1.0--alpha-red.svg)

## 🎯 Overview

CourseFlow is a comprehensive university administration system designed to streamline academic operations for students, professors, and administrators. Built with Flask and SQLite3, it provides a robust foundation for managing courses, enrollments, grades, and academic workflows.

## ✨ Features (v0.1.0-alpha)

### 🎓 For Students
- Browse and explore available courses
- View detailed course information and prerequisites
- Enroll in course sections
- Track academic progress and GPA
- View class schedules and attendance

### 👨‍🏫 For Professors
- Create and manage course sections
- Track student enrollments and performance
- Manage assignments and grading
- Post course announcements
- Monitor class attendance

### 🔧 For Administrators
- Manage users (students, professors, admins)
- Create and maintain course catalog
- Oversee department structure
- Generate reports and analytics
- Control system permissions

## 🏗️ Architecture

### Database Schema
CourseFlow uses a comprehensive SQLite3 database with the following core entities:

- **Users**: Base authentication and profile management
- **Students/Professors/Admins**: Role-specific information
- **Departments**: Academic department organization
- **Courses**: Course catalog and descriptions
- **Course Sections**: Specific course offerings per semester
- **Enrollments**: Student-course relationships
- **Assignments & Submissions**: Assignment management system
- **Announcements**: Communication platform
- **Attendance**: Class attendance tracking

### Key Models
```python
# Core user management
User (base class)
├── Student
├── Professor
└── Admin

# Academic structure
Department
Course
CourseSection
Enrollment

# Learning management
Assignment
Submission
Announcement
Attendance
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Installation
```bash
# Clone the repository
git clone https://github.com/0xRaha/courseflow.git
cd courseflow

# Install dependencies
pip install -r requirements.txt

# Initialize the database
python -c "from models import Database; Database()"

# Run the application
python app.py
```

### First Run
1. Access the application at `http://localhost:5000`
2. Create an admin account through the signup form
3. Log in and start configuring your university structure

## 📁 Project Structure
```
courseflow/
├── app.py                 # Main Flask application
├── models.py             # Database models and schema
├── utils.py              # Utility functions
├── requirements.txt      # Python dependencies
├── templates/            # HTML templates
│   ├── index.html
│   └── signup.html
├── static/              # CSS, JS, and images
└── university.db        # SQLite database (auto-generated)
```

## 🔧 Configuration

### Database
CourseFlow uses SQLite3 by default, which requires no additional setup. The database file (`university.db`) is automatically created when you first run the application.

## 🛠️ Development Status

### Current Version: v0.1.0-alpha
This is an **alpha release** focusing on core database models and basic functionality.

#### ✅ Completed
- Comprehensive database schema design
- Core model classes (User, Student, Professor, Admin)
- Basic Flask application structure
- User authentication foundation
- Course and enrollment management models

#### 🚧 In Progress
- Complete Flask route implementation
- HTML template development
- User interface design
- Authentication system integration

#### 📋 Planned Features
- **v0.2.0**: Complete UI implementation and core workflows
- **v0.3.0**: Advanced features (reporting, analytics)
- **v1.0.0**: Production-ready release

## 👥 Development Team

This project is being developed as a university project by:

- **0xRaha** - *Lead Developer* - [GitHub](https://github.com/0xRaha)
- **Yashar** - *Co-Developer* - [GitHub](https://github.com/YounesKhafan)

*Note: This is a closed university project. Contributions are limited to the development team members only.*

## 📋 Requirements

### Python Dependencies
```
Flask==2.3.3
Werkzeug==2.3.7
uuid==1.30
```

### System Requirements
- Python 3.8+
- 50MB disk space
- 256MB RAM minimum

## 🗺️ Roadmap

### Short Term (v0.2.0)
- Complete Flask routes implementation
- Responsive web UI
- User authentication system
- Core CRUD operations

### Medium Term (v0.3.0)
- Advanced reporting features
- Communication System
- Enhanced security features

### Long Term (v1.0.0)
- Complete feature set
- Enhanced user experience
- Performance optimizations

---

**Note**: This is an alpha release intended for development and testing purposes.

## 📊 Project Stats

- **Lines of Code**: ~500+
- **Database Tables**: 10+
- **Model Classes**: 8
- **Estimated Development Time**: 6-7 weeks
- **Target Users**: Students, Professors, Administrators

## 🔗 Links

- [Project Homepage](https://github.com/0xRaha/courseflow)
- [Issue Tracker](https://github.com/0xRaha/courseflow/issues)
- [Releases](https://github.com/0xRaha/courseflow/releases)
