from app import db
from flask_login import UserMixin
import bcrypt


# =========================
# USER MODEL
# =========================

class User(db.Model, UserMixin):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(100), nullable=False)

    # OTP verification fields
    otp = db.Column(db.String(6), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)

    # Profile fields (for the administrator profile settings)
    leetcode_id = db.Column(db.String(100), nullable=True)
    hackerearth_id = db.Column(db.String(100), nullable=True)
    other_id = db.Column(db.String(100), nullable=True)

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_verified": self.is_verified,
            "leetcode_id": self.leetcode_id,
            "hackerearth_id": self.hackerearth_id,
            "other_id": self.other_id
        }


# =========================
# STUDENT MODEL
# =========================

class Student(db.Model):
    __tablename__ = 'student'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    course = db.Column(db.String(100), nullable=False)

    # LeetCode and HackerEarth handles for students
    leetcode_id = db.Column(db.String(100), nullable=True)
    hackerearth_id = db.Column(db.String(100), nullable=True)

    # Relationships with cascade delete
    marks = db.relationship('Mark', backref='student', lazy=True, cascade='all, delete-orphan')
    attendance = db.relationship('Attendance', backref='student', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "course": self.course,
            "leetcode_id": self.leetcode_id,
            "hackerearth_id": self.hackerearth_id,
            "marks": [mark.to_dict() for mark in self.marks],
            "attendance": [record.to_dict() for record in self.attendance]
        }


# =========================
# MARK MODEL (GRADES)
# =========================

class Mark(db.Model):
    __tablename__ = 'mark'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    max_score = db.Column(db.Integer, default=100, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "subject": self.subject,
            "score": self.score,
            "max_score": self.max_score
        }


# =========================
# ATTENDANCE MODEL
# =========================

class Attendance(db.Model):
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    date = db.Column(db.String(10), nullable=False)  # format YYYY-MM-DD
    status = db.Column(db.String(10), nullable=False)  # Present, Late, Absent

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date,
            "status": self.status
        }


# =========================
# FEEDBACK MODEL
# =========================

class Feedback(db.Model):
    __tablename__ = 'feedback'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # compliment, feedback
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "email": self.email,
            "type": self.type,
            "message": self.message,
            "created_at": (
                self.created_at.strftime('%Y-%m-%d %H:%M:%S')
                if self.created_at else None
            )
        }
