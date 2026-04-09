from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from services.auth_service import register_user, login_user, verify_user_otp

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('doc.dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        success = register_user(
            request.form['name'],
            request.form['email'],
            request.form['password'],
            request.form['role']
        )

        if not success:
            flash('Email is already registered or registration failed. Please use another email.', 'danger')
            return render_template('register.html')

        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')

@auth_bp.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = login_user(request.form['email'], request.form['password'])

        if user:
            session['temp_user'] = user['id']
            flash('OTP sent to your email. Please enter it below.', 'success')
            return redirect(url_for('auth.verify_otp'))

        flash('Invalid credentials or failed to send OTP email. Please check your login and email configuration.', 'danger')

    return render_template('login.html')

@auth_bp.route('/verify_otp', methods=['GET','POST'])
def verify_otp():
    if request.method == 'POST':
        temp_user = session.get('temp_user')
        if not temp_user:
            flash('Session expired or invalid. Please log in again.', 'warning')
            return redirect(url_for('auth.login'))

        user = verify_user_otp(temp_user, request.form['otp'])

        if user:
            session.pop('temp_user', None)
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['role'] = user['role']
            return redirect(url_for('doc.dashboard'))

        flash('Invalid or expired OTP. Please try again.', 'danger')

    return render_template('otp_verify.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))