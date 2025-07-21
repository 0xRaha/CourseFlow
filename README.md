# 🎓 University Management System

A simple yet comprehensive full-stack web application for managing university operations including student enrollment, course management, and academic records.

## ✨ Features

### 👨‍💼 Admin Features
- **User Management**: Register new students and professors
- **Course Management**: Create, edit, and delete courses
- **Student Management**: Search and view student information
- **System Overview**: Dashboard with statistics and quick actions

### 👨‍🏫 Professor Features
- **Course Sections**: Create and manage course sections
- **Grade Management**: Submit and update student grades
- **Class Roster**: View enrolled students
- **Announcements**: Create course announcements for students
- **Teaching Schedule**: View all teaching sections

### 🎓 Student Features
- **Course Enrollment**: Browse, search, and enroll in available courses
- **Schedule Management**: View weekly class schedule
- **Grade Tracking**: View all grades and GPA calculation
- **Course Announcements**: See announcements from enrolled courses
- **Profile Management**: Edit personal information

### 🔍 Public Features
- **Faculty Directory**: Search and view professor profiles
- **Course Catalog**: Browse available courses by department

## 🛠 Technology Stack

- **Backend**: Python Flask
- **Database**: PostgreSQL
- **Frontend**: HTML, CSS, JavaScript (Vanilla)
- **Authentication**: Flask Sessions with password hashing
- **Styling**: Custom CSS with gradient design

## 📋 Prerequisites

- Python 3.8+
- PostgreSQL 12+
- pip (Python package manager)

## 🚀 Setup Instructions

### 1. Clone the Repository
```bash
git clone <repository-url>
cd university-management-system
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Setup

#### Install PostgreSQL
- Download and install PostgreSQL from [postgresql.org](https://www.postgresql.org/downloads/)
- Create a new database named `university_db`

#### Configure Database Connection
Create a `.env` file in the project root:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=university_db
DB_USER=postgres
DB_PASSWORD=your_password
SECRET_KEY=your_secret_key_here
FLASK_DEBUG=True
```

### 5. Initialize Database
The application will automatically create all necessary tables on first run.

### 6. Run the Application
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## 🔑 Default Login Credentials

After first run, an admin account is automatically created:
- **Username**: `admin`
- **Password**: `admin`

⚠️ **Important**: Change the default admin password in production!

## 📁 Project Structure

```
university-management-system/
├── app.py                 # Main Flask application
├── models.py             # Database models and business logic
├── requirements.txt      # Python dependencies
├── README.md            # Project documentation
├── templates/           # HTML templates
│   ├── base.html        # Base template
│   ├── login.html       # Login page
│   ├── edit_profile.html # Profile editing
│   ├── admin/           # Admin templates
│   ├── professor/       # Professor templates
│   ├── student/         # Student templates
│   └── errors/          # Error pages
└── .env                 # Environment variables (create this)
```

## 🎯 Usage Guide

### Getting Started
1. Start the application and navigate to `http://localhost:5000`
2. Login with admin credentials (`admin` / `admin`)
3. Create some courses via "Manage Courses"
4. Register professors and students via "Register User"
5. Professors can create course sections
6. Students can browse and enroll in courses

### Creating Sample Data
1. **Admin Login**: Use admin account to access admin panel
2. **Create Courses**: Add courses like "CS101 - Intro to Programming"
3. **Register Users**: Create professor and student accounts
4. **Create Sections**: Professors create sections for courses
5. **Student Enrollment**: Students browse and enroll in sections

## 🔧 Key Features Demonstrated

- **Full-Stack Architecture**: Backend API with frontend interface
- **Database Design**: Normalized PostgreSQL schema with relationships
- **Authentication & Authorization**: Role-based access control
- **CRUD Operations**: Create, Read, Update, Delete functionality
- **Search & Filtering**: Dynamic content filtering
- **Responsive Design**: Mobile-friendly interface
- **Error Handling**: User-friendly error pages and messages

## 🎨 Design Highlights

- **Modern UI**: Gradient backgrounds with glassmorphism effects
- **Responsive Layout**: Works on desktop, tablet, and mobile
- **Intuitive Navigation**: Role-based navigation menus
- **Visual Feedback**: Hover effects and smooth transitions
- **Data Visualization**: Statistics cards and progress bars

## 🔍 Testing the Application

### Sample Workflow
1. **Admin**: Create courses and register users
2. **Professor**: Create sections and post announcements
3. **Student**: Enroll in courses and view schedule
4. **All Users**: Edit profiles and view faculty directory

### Features to Test
- User registration and authentication
- Course creation and management
- Section creation and enrollment
- Grade submission and GPA calculation
- Search and filtering functionality
- Responsive design on different devices

## ⚠️ Notes

- This is a college project designed for demonstration purposes
- Database indexes are minimal for simplicity
- Error handling is simplified for educational clarity
- No production security measures implemented
- File uploads and advanced features are not included

## 🤝 Contributing

This is an educational project. Feel free to fork and enhance it for your own learning purposes.

## 📄 License

This project is created for educational purposes. Use it as a reference for learning full-stack web development.

---

**Happy Learning! 🎓**
