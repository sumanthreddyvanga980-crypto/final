import os
import sys
import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Base directory
base_dir = os.path.abspath(os.path.dirname(__file__))

# Add base directory to system path
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

# Avoid circular imports
sys.modules['app'] = sys.modules[__name__]

# Database configuration path
database_path = os.getenv('DATABASE_FILE', 'students.db')
if not os.path.isabs(database_path):
    database_path = os.path.join(base_dir, database_path)

# Flask app initialization
app = Flask(
    __name__,
    static_folder='static',
    template_folder='templates'
)

# Secret Keys
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-for-student-management-123')

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# SMTP Mail configuration
app.config['MAIL_SERVER'] = os.getenv("SMTP_SERVER", "smtp.gmail.com")
app.config['MAIL_PORT'] = int(os.getenv("SMTP_PORT", 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.getenv("SMTP_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("SMTP_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("SMTP_USERNAME")

# Initialize Extensions
db = SQLAlchemy(app)
mail = Mail(app)

# Flask Login Configuration
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Import User model
from models import User, Student, Mark, Attendance, Feedback

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Import routes
from routes import *

# =========================
# DATABASE AUTO-SEEDING
# =========================
with app.app_context():
    db.create_all()
    
    # Seed default administrator if not present
    if not User.query.first():
        print("Seeding default admin user account...")
        admin = User(
            username="admin",
            email="admin@studenthub.com",
            is_verified=True,
            leetcode_id="admin_coder",
            hackerearth_id="admin_coder",
            other_id="admin_github"
        )
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
        
    # Seed default students, marks, and attendance if not present
    if not Student.query.first():
        print("Seeding default student performance rosters...")
        
        default_students = [
            {
                "name": "John Doe",
                "email": "john.doe@studenthub.com",
                "course": "Computer Science",
                "leetcode": "john_doe",
                "hackerearth": "john_doe",
                "marks": [
                    ("Advanced Python", 96),
                    ("Database Management", 90),
                    ("Software Architecture", 92)
                ],
                "attendance": ["Present", "Present", "Present", "Late", "Present", "Present", "Absent", "Present", "Present", "Present"]
            },
            {
                "name": "Jane Smith",
                "email": "jane.smith@studenthub.com",
                "course": "Information Technology",
                "leetcode": "jane_smith",
                "hackerearth": "jane_smith",
                "marks": [
                    ("Advanced Python", 85),
                    ("Database Management", 94),
                    ("Software Architecture", 88)
                ],
                "attendance": ["Present", "Present", "Present", "Present", "Present", "Present", "Late", "Present", "Present", "Present"]
            },
            {
                "name": "Alex Johnson",
                "email": "alex.johnson@studenthub.com",
                "course": "Software Engineering",
                "leetcode": "alex_j",
                "hackerearth": "alex_j",
                "marks": [
                    ("Advanced Python", 72),
                    ("Database Management", 80),
                    ("Software Architecture", 74)
                ],
                "attendance": ["Present", "Late", "Present", "Present", "Absent", "Present", "Present", "Present", "Present", "Present"]
            },
            {
                "name": "Sam Wilson",
                "email": "sam.wilson@studenthub.com",
                "course": "Cybersecurity",
                "leetcode": "sam_w",
                "hackerearth": "sam_w",
                "marks": [
                    ("Advanced Python", 45),
                    ("Database Management", 40),
                    ("Software Architecture", 50)
                ],
                "attendance": ["Absent", "Absent", "Present", "Present", "Present", "Present", "Present", "Present", "Late", "Present"]
            }
        ]

        today = datetime.date.today()
        
        for s_data in default_students:
            student = Student(
                name=s_data["name"],
                email=s_data["email"],
                course=s_data["course"],
                leetcode_id=s_data["leetcode"],
                hackerearth_id=s_data["hackerearth"]
            )
            db.session.add(student)
            db.session.commit()  # commit to generate ID
            
            # Add Marks
            for subject, score in s_data["marks"]:
                mark = Mark(
                    student_id=student.id,
                    subject=subject,
                    score=score
                )
                db.session.add(mark)
                
            # Add 10 days of attendance
            for idx, status in enumerate(s_data["attendance"]):
                date_str = (today - datetime.timedelta(days=idx)).strftime("%Y-%m-%d")
                att = Attendance(
                    student_id=student.id,
                    date=date_str,
                    status=status
                )
                db.session.add(att)
                
        db.session.commit()
        print("Database seeding completed successfully.")

if __name__ == '__main__':
    app.run(
        debug=True,
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000))
    )
