from flask import (
    render_template,
    request,
    redirect,
    flash,
    url_for,
    session,
    jsonify
)
from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user
)
from app import app, db
from models import User, Student, Mark, Attendance, Feedback
from utils import generate_otp, send_otp_email
import datetime

# =========================
# HOME
# =========================

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


# =========================
# EMAIL VERIFICATION / REGISTER WIZARD
# =========================

@app.route('/register/send-otp', methods=['POST'])
def send_otp():
    try:
        data = request.get_json() or {}
        email = data.get('email', '').strip().lower()

        if not email:
            return jsonify({"status": "error", "message": "Email address is required."}), 400

        # Check if email is already taken by a verified user
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.is_verified:
            return jsonify({"status": "error", "message": "Email is already registered."}), 400

        otp = generate_otp()
        
        # Save verification state in Flask session
        session['register_email'] = email
        session['register_otp'] = otp
        session['email_verified'] = False

        # Attempt to send email
        email_sent = send_otp_email(email, otp)
        
        if not email_sent:
            # Fallback: OTP logged to console. Return it in response for dev testing if credentials are placeholders.
            return jsonify({
                "status": "success", 
                "fallback_otp": otp,
                "message": "OTP verification code generated. Since SMTP is not configured, the code is printed in the terminal console, or you can use the code displayed here: " + otp
            })

        return jsonify({"status": "success", "message": "Verification code sent to your email!"})

    except Exception as e:
        print("SEND OTP ERROR:", e)
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500


@app.route('/register/verify-otp', methods=['POST'])
def verify_otp_ajax():
    try:
        data = request.get_json() or {}
        entered_otp = data.get('otp', '').strip()
        email = data.get('email', '').strip().lower()

        saved_otp = session.get('register_otp')
        saved_email = session.get('register_email')

        if not entered_otp:
            return jsonify({"status": "error", "message": "OTP code is required."}), 400

        if saved_email != email or saved_otp != entered_otp:
            return jsonify({"status": "error", "message": "Invalid OTP code or email mismatch."}), 400

        session['email_verified'] = True
        return jsonify({"status": "success", "message": "Email verified successfully! You can now complete your registration."})

    except Exception as e:
        print("VERIFY OTP ERROR:", e)
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')

            # Check that email verification happened
            if not session.get('email_verified') or session.get('register_email') != email:
                flash("Please verify your email address first.", "danger")
                return redirect(url_for('register'))

            if not username or not email or not password or not confirm_password:
                flash("All fields are required.", "danger")
                return redirect(url_for('register'))

            if password != confirm_password:
                flash("Passwords do not match.", "danger")
                return redirect(url_for('register'))

            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash("Username is already taken.", "danger")
                return redirect(url_for('register'))

            # Check email one last time
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                # If there's an unverified registration of this email, reuse or update it
                user = existing_email
                user.username = username
                user.set_password(password)
                user.is_verified = True
                user.otp = None
            else:
                user = User(
                    username=username,
                    email=email,
                    is_verified=True,
                    otp=None
                )
                user.set_password(password)
                db.session.add(user)

            db.session.commit()

            # Clear session
            session.pop('register_otp', None)
            session.pop('register_email', None)
            session.pop('email_verified', None)

            flash("Account registered successfully! Please login.", "success")
            return redirect(url_for('login'))

        except Exception as e:
            db.session.rollback()
            print("REGISTER FORM ERROR:", e)
            flash(f"Registration Error: {str(e)}", "danger")
            return redirect(url_for('register'))

    return render_template('register.html')


# =========================
# LOGIN / LOGOUT
# =========================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')

            user = User.query.filter_by(username=username).first()
            if not user:
                flash("User account not found.", "danger")
                return redirect(url_for('login'))

            if not user.is_verified:
                flash("Email address is not verified.", "danger")
                return redirect(url_for('login'))

            if user.check_password(password):
                login_user(user)
                flash(f"Welcome back, {username}! Access granted.", "success")
                return redirect(url_for('dashboard'))
            else:
                flash("Incorrect password.", "danger")

        except Exception as e:
            print("LOGIN ROUTE ERROR:", e)
            flash(f"Login system error: {str(e)}", "danger")

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    username = current_user.username
    logout_user()
    flash(f"Log out successful. Goodbye, {username}!", "success")
    return redirect(url_for('login'))


# =========================
# DASHBOARD
# =========================

@app.route('/dashboard')
@login_required
def dashboard():
    student_count = Student.query.count()

    # Calculate average attendance
    all_attendance = Attendance.query.all()
    avg_attendance = "N/A"
    if all_attendance:
        presents = sum(1 for att in all_attendance if att.status in ['Present', 'Late'])
        avg_attendance = f"{(presents / len(all_attendance)) * 100:.1f}%"

    # Calculate average mark class grade
    all_marks = Mark.query.all()
    avg_grade = "N/A"
    if all_marks:
        avg_score = sum(mark.score for mark in all_marks) / len(all_marks)
        if avg_score >= 90: avg_grade = "A"
        elif avg_score >= 80: avg_grade = "A-"
        elif avg_score >= 70: avg_grade = "B"
        elif avg_score >= 60: avg_grade = "C"
        else: avg_grade = "D"

    # Get student marks and attendance list to display inside dashboard charts
    students = Student.query.all()
    
    chart_data = {
        "labels": [s.name for s in students[:5]],
        "marks": [],
        "attendance": []
    }
    
    for s in students[:5]:
        # Avg mark score
        s_marks = [m.score for m in s.marks]
        avg_m = sum(s_marks)/len(s_marks) if s_marks else 0
        chart_data["marks"].append(round(avg_m, 1))

        # Attendance score
        s_att = s.attendance
        presents = sum(1 for att in s_att if att.status in ['Present', 'Late'])
        att_pct = (presents / len(s_att)) * 100 if s_att else 0
        chart_data["attendance"].append(round(att_pct, 1))

    return render_template(
        'dashboard.html',
        student_count=student_count,
        avg_attendance=avg_attendance,
        avg_grade=avg_grade,
        chart_data=chart_data
    )


# =========================
# STUDENTS ROSTER
# =========================

@app.route('/students')
@login_required
def students_list():
    students = Student.query.all()
    return render_template('students.html', students=students)


@app.route('/add_student', methods=['POST'])
@login_required
def add_student():
    try:
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        course = request.form.get('course', '').strip()
        leetcode_id = request.form.get('leetcode_id', '').strip()
        hackerearth_id = request.form.get('hackerearth_id', '').strip()

        if not name or not email or not course:
            flash("Name, Email, and Course fields are required.", "danger")
            return redirect(url_for('students_list'))

        existing_student = Student.query.filter_by(email=email).first()
        if existing_student:
            flash("Student email already exists in the system database.", "danger")
            return redirect(url_for('students_list'))

        new_student = Student(
            name=name,
            email=email,
            course=course,
            leetcode_id=leetcode_id if leetcode_id else None,
            hackerearth_id=hackerearth_id if hackerearth_id else None
        )

        db.session.add(new_student)
        db.session.commit()

        # Seed some default grades and attendance for the newly enrolled student
        subjects = ["Advanced Python", "Database Management", "Software Architecture"]
        for sub in subjects:
            score = 70 + (new_student.id * 7) % 31  # semi-random default marks between 70 and 100
            db.session.add(Mark(student_id=new_student.id, subject=sub, score=score))

        # Seed 10 days of attendance
        today = datetime.date.today()
        statuses = ["Present", "Present", "Present", "Late", "Present", "Present", "Absent", "Present", "Present", "Present"]
        for i in range(10):
            date_str = (today - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            status = statuses[(i + new_student.id) % len(statuses)]
            db.session.add(Attendance(student_id=new_student.id, date=date_str, status=status))

        db.session.commit()
        flash(f"Student '{name}' added and configured successfully!", "success")

    except Exception as e:
        db.session.rollback()
        print("ADD STUDENT ERROR:", e)
        flash(f"Failed to add student: {str(e)}", "danger")

    return redirect(url_for('students_list'))


@app.route('/delete_student/<int:id>')
@login_required
def delete_student(id):
    try:
        student = Student.query.get_or_404(id)
        name = student.name
        db.session.delete(student)
        db.session.commit()
        flash(f"Student '{name}' has been deleted from records.", "success")
    except Exception as e:
        db.session.rollback()
        print("DELETE STUDENT ERROR:", e)
        flash(f"Deletion failed: {str(e)}", "danger")

    return redirect(url_for('students_list'))


# =========================
# STUDENT PROFILE DETAIL PAGE (WITH GRAPHS)
# =========================

@app.route('/student/<int:id>', methods=['GET', 'POST'])
@login_required
def student_profile(id):
    student = Student.query.get_or_404(id)

    if request.method == 'POST':
        try:
            student.name = request.form.get('name', '').strip()
            student.course = request.form.get('course', '').strip()
            student.leetcode_id = request.form.get('leetcode_id', '').strip() or None
            student.hackerearth_id = request.form.get('hackerearth_id', '').strip() or None

            db.session.commit()
            flash("Student profile records updated successfully.", "success")
            return redirect(url_for('student_profile', id=id))
        except Exception as e:
            db.session.rollback()
            print("UPDATE STUDENT PROFILE ERROR:", e)
            flash(f"Profile update failed: {str(e)}", "danger")

    # Format chart data
    subjects = [m.subject for m in student.marks]
    scores = [m.score for m in student.marks]

    # Attendance summary
    att_history = student.attendance
    presents = sum(1 for a in att_history if a.status == "Present")
    lates = sum(1 for a in att_history if a.status == "Late")
    absents = sum(1 for a in att_history if a.status == "Absent")
    total_days = len(att_history)

    att_summary = {
        "present": presents,
        "late": lates,
        "absent": absents,
        "total": total_days,
        "percentage": round(((presents + lates) / total_days) * 100, 1) if total_days > 0 else 0
    }

    # Chart details
    attendance_labels = [a.date for a in reversed(att_history[-10:])]
    attendance_scores = []
    
    # Cumulative or daily status tracker for lines (1 for Present/Late, 0 for Absent)
    for a in reversed(att_history[-10:]):
        attendance_scores.append(100 if a.status == "Present" else (70 if a.status == "Late" else 0))

    return render_template(
        'student_profile.html',
        student=student,
        subjects=subjects,
        scores=scores,
        att_summary=att_summary,
        attendance_labels=attendance_labels,
        attendance_scores=attendance_scores
    )


# =========================
# ATTENDANCE MANAGEMENT SHEET
# =========================

@app.route('/attendance', methods=['GET', 'POST'])
@login_required
def attendance():
    students = Student.query.all()
    today = datetime.date.today().strftime("%Y-%m-%d")

    if request.method == 'POST':
        try:
            date_input = request.form.get('date', today)
            for student in students:
                status = request.form.get(f'status_{student.id}', 'Present')
                # Check if attendance already recorded for this student on this day
                record = Attendance.query.filter_by(student_id=student.id, date=date_input).first()
                if record:
                    record.status = status
                else:
                    new_record = Attendance(student_id=student.id, date=date_input, status=status)
                    db.session.add(new_record)
            db.session.commit()
            flash(f"Attendance register updated successfully for date {date_input}.", "success")
            return redirect(url_for('attendance'))
        except Exception as e:
            db.session.rollback()
            print("UPDATE ATTENDANCE SHEET ERROR:", e)
            flash(f"Failed to record attendance: {str(e)}", "danger")

    # Compile weekly percentage summary for each student
    student_att_info = []
    for s in students:
        records = s.attendance
        presents = sum(1 for r in records if r.status in ['Present', 'Late'])
        percentage = round((presents / len(records)) * 100, 1) if records else 100.0
        
        # Today's status check
        today_record = Attendance.query.filter_by(student_id=s.id, date=today).first()
        today_status = today_record.status if today_record else "Not Marked"
        
        student_att_info.append({
            "student": s,
            "percentage": percentage,
            "today_status": today_status
        })

    return render_template(
        'attendance.html',
        student_att_info=student_att_info,
        today=today
    )


# =========================
# GRADES / MARKS REGISTER
# =========================

@app.route('/marks', methods=['GET', 'POST'])
@login_required
def marks():
    students = Student.query.all()

    if request.method == 'POST':
        try:
            student_id = request.form.get('student_id')
            subject = request.form.get('subject', '').strip()
            score = int(request.form.get('score', 0))
            max_score = int(request.form.get('max_score', 100))

            if not student_id or not subject:
                flash("Student and Subject fields are required.", "danger")
                return redirect(url_for('marks'))

            # Check if record exists for student + subject
            record = Mark.query.filter_by(student_id=student_id, subject=subject).first()
            if record:
                record.score = score
                record.max_score = max_score
            else:
                new_record = Mark(student_id=student_id, subject=subject, score=score, max_score=max_score)
                db.session.add(new_record)

            db.session.commit()
            flash("Academic scores register updated successfully.", "success")
            return redirect(url_for('marks'))
        except Exception as e:
            db.session.rollback()
            print("UPDATE MARKS REGISTER ERROR:", e)
            flash(f"Failed to record scores: {str(e)}", "danger")

    # Get subject score listing
    all_scores = []
    for s in students:
        for m in s.marks:
            all_scores.append({
                "student": s,
                "subject": m.subject,
                "score": m.score,
                "max_score": m.max_score
            })

    return render_template(
        'marks.html',
        students=students,
        scores=all_scores
    )


# =========================
# ADMINISTRATOR PROFILE CONFIG
# =========================

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        try:
            current_user.leetcode_id = request.form.get('leetcode_id', '').strip() or None
            current_user.hackerearth_id = request.form.get('hackerearth_id', '').strip() or None
            current_user.other_id = request.form.get('other_id', '').strip() or None

            db.session.commit()
            flash("Administrator profile handles updated successfully.", "success")
            return redirect(url_for('profile'))
        except Exception as e:
            db.session.rollback()
            print("UPDATE USER PROFILE ERROR:", e)
            flash(f"Failed to save profile changes: {str(e)}", "danger")

    return render_template('profile.html', user=current_user)


# =========================
# FEEDBACK stream
# =========================

@app.route('/feedback', methods=['GET', 'POST'])
def feedback_panel():
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip().lower()
            type_fb = request.form.get('type', 'feedback').strip()
            message = request.form.get('message', '').strip()

            if not name or not email or not message:
                flash("Name, Email, and Message are required to submit feedback.", "danger")
                return redirect(url_for('feedback_panel'))

            fb = Feedback(
                user_id=current_user.id if current_user.is_authenticated else None,
                name=name,
                email=email,
                type=type_fb,
                message=message
            )
            db.session.add(fb)
            db.session.commit()
            flash("Thank you for your valuable feedback! Submitted successfully.", "success")
            return redirect(url_for('feedback_panel'))

        except Exception as e:
            db.session.rollback()
            print("SUBMIT FEEDBACK ERROR:", e)
            flash(f"Submission failed: {str(e)}", "danger")

    feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).all()
    return render_template('feedback.html', feedbacks=feedbacks)
