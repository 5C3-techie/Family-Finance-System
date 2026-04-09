from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from services.auth_service import register_user, login_user, verify_user_otp, update_user_role, resend_user_otp

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('doc.dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        success, role = register_user(
            request.form['name'],
            request.form['email'],
            request.form['phone'],
            request.form['password']
        )

        if not success:
            flash('Email is already registered or registration failed. Please use another email.', 'danger')
            return render_template('register.html')

        flash(f'Registration successful. Your account was created as a {role}. Please log in.', 'success')
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
    temp_user = session.get('temp_user')

    if request.method == 'GET' and not temp_user:
        flash('Please log in to receive a new OTP.', 'warning')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        if not temp_user:
            flash('Session expired or invalid. Please log in again.', 'warning')
            return redirect(url_for('auth.login'))

        action = request.form.get('action', 'verify')
        if action == 'resend':
            if resend_user_otp(temp_user):
                flash('A new OTP has been sent to your email.', 'success')
            else:
                flash('Unable to resend OTP right now. Please log in again.', 'danger')
                session.pop('temp_user', None)
                return redirect(url_for('auth.login'))
            return redirect(url_for('auth.verify_otp'))

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


@auth_bp.route('/users/<int:user_id>/role', methods=['POST'])
def update_role(user_id):
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('auth.login'))

    if session.get('role') != 'admin':
        flash('Only admins can change user roles.', 'danger')
        return redirect(url_for('doc.dashboard'))

    new_role = request.form.get('role', '').strip().lower()
    success, message = update_user_role(user_id, new_role)
    flash(message, 'success' if success else 'danger')

    if success and session.get('user_id') == user_id:
        session['role'] = new_role

    next_page = request.form.get('next_page')
    if next_page == 'upload':
        return redirect(url_for('doc.upload'))
    return redirect(url_for('doc.dashboard'))
