import os
import sqlite3
import bcrypt
import random
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.utils import secure_filename
import random
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

app = Flask(__name__)
# Secret key for session management
app.secret_key = 'smart_family_finance_secret_key'

# Configuration for file uploads
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DB_FILE = 'database.db'

def get_db_connection():
    """Establish and return a database connection."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with required tables."""
    conn = get_db_connection()
    # Create Users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            otp TEXT,
            otp_expiry TEXT
        )
    ''')
    try:
        conn.execute('ALTER TABLE users ADD COLUMN otp TEXT')
        conn.execute('ALTER TABLE users ADD COLUMN otp_expiry TEXT')
    except sqlite3.OperationalError:
        pass
    # Create Documents table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

# Initialize DB on startup
init_db()
def send_otp_email(email, otp):

    

    sender_email = "nagameenakshidarapurapu@gmail.com"
    app_password = "ofio croa rnrw hvdn"

    msg = EmailMessage()
    msg['Subject'] = "Your Login OTP - Family Finance System"
    msg['From'] = sender_email
    msg['To'] = email

    msg.set_content(f"Your OTP for login is: {otp}\n\nThis OTP is valid for 5 minutes.")

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()

        print("OTP sent successfully to:", email)
        print("Generated OTP:", otp)   # helpful for debugging

    except Exception as e:
        print("Error sending OTP:", e)


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        if not name or not email or not password or not role:
            flash('All fields are required!', 'danger')
            return redirect(url_for('register'))

        # Hash password securely using bcrypt
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)',
                         (name, email, hashed_password, role))
            conn.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email address is already registered.', 'danger')
        finally:
            conn.close()

    return render_template('register.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        # Check if user exists and password is correct using bcrypt
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            otp = random.randint(100000, 999999)
            print("Generated OTP:", otp)
            expiry = datetime.now() + timedelta(minutes=5)

            conn = get_db_connection()
            conn.execute(
                "UPDATE users SET otp = ?, otp_expiry = ? WHERE id = ?",
                (str(otp), expiry.strftime("%Y-%m-%d %H:%M:%S"), user['id'])
            )
            conn.commit()
            conn.close()

            send_otp_email(user['email'], otp)

            session['temp_user'] = user['id']

            flash("OTP sent to your email.", "info")
            return redirect(url_for('verify_otp'))
        else:
            flash("Invalid email or password", "danger")

    return render_template('login.html')


@app.route('/verify_otp', methods=['GET','POST'])
def verify_otp():

    if 'temp_user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':

        entered_otp = request.form.get('otp')

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE id=?",
            (session['temp_user'],)
        ).fetchone()

        conn.close()

        if user:

            if user['otp'] == entered_otp:

                expiry_time = datetime.strptime(user['otp_expiry'], "%Y-%m-%d %H:%M:%S")

                if datetime.now() <= expiry_time:

                    session['user_id'] = user['id']
                    session['name'] = user['name']
                    session['role'] = user['role']

                    session.pop('temp_user', None)

                    flash("Login successful with OTP verification.", "success")

                    return redirect(url_for('dashboard'))

        flash("Invalid or expired OTP.", "danger")

    return render_template("otp_verify.html")


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been successfully logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to access your dashboard.', 'warning')
        return redirect(url_for('login'))

    conn = get_db_connection()
    documents = []
    
    # Role-based document retrieval
    if session['role'] == 'admin':
        # Admin can see all documents and the username of who it belongs to
        documents = conn.execute('''
            SELECT d.id, d.filename, d.upload_date, u.name as user_name 
            FROM documents d
            JOIN users u ON d.user_id = u.id
            ORDER BY d.upload_date DESC
        ''').fetchall()
    else:
        # Members can only see documents assigned to them
        documents = conn.execute('''
            SELECT id, filename, upload_date 
            FROM documents 
            WHERE user_id = ? 
            ORDER BY upload_date DESC
        ''', (session['user_id'],)).fetchall()
        
    conn.close()
    
    return render_template('dashboard.html', documents=documents, role=session['role'], name=session['name'])


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    # Only admins can upload files
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Access denied. Only administrators can upload documents.', 'danger')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file detected.', 'danger')
            return redirect(request.url)
            
        file = request.files['file']
        user_id = request.form.get('user_id')
        
        if file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(request.url)

        if not user_id:
            flash('Please select a member to assign the document to.', 'danger')
            return redirect(request.url)

        # Process the valid file upload
        if file:
            # Secure the filename
            original_filename = secure_filename(file.filename)
            # Add a timestamp to the filename to ensure uniqueness in file system
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            unique_filename = f"{timestamp}_{original_filename}"
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)

            # Store file info in DB
            conn.execute('''
                INSERT INTO documents (user_id, filename, filepath)
                VALUES (?, ?, ?)
            ''', (user_id, original_filename, filepath))
            conn.commit()
            flash(f'Document "{original_filename}" uploaded successfully!', 'success')
            return redirect(url_for('dashboard'))

    # Get a list of users/members to assign documents to
    users = conn.execute("SELECT id, name, email FROM users WHERE role = 'member'").fetchall()
    conn.close()
    
    return render_template('upload.html', users=users, name=session['name'])


@app.route('/download/<int:doc_id>')
def download(doc_id):
    if 'user_id' not in session:
        flash('Please login to download.', 'warning')
        return redirect(url_for('login'))

    conn = get_db_connection()
    doc = conn.execute('SELECT * FROM documents WHERE id = ?', (doc_id,)).fetchone()
    conn.close()

    if not doc:
        flash('Document not found.', 'danger')
        return redirect(url_for('dashboard'))

    # Security Check: Ensure member can only download their own document
    if session['role'] != 'admin' and doc['user_id'] != session['user_id']:
        flash('Unauthorized document access.', 'danger')
        return redirect(url_for('dashboard'))

    # Serve the file securely
    try:
        # absolute path of the directory
        directory = os.path.abspath(app.config['UPLOAD_FOLDER'])
        filename_on_disk = os.path.basename(doc['filepath'])
        return send_from_directory(directory, filename_on_disk, as_attachment=True, download_name=doc['filename'])
    except Exception as e:
        flash('Error fetching file.', 'danger')
        return redirect(url_for('dashboard'))

if __name__ == '__main__':
    # Start the Flask app
    app.run(debug=True, port=5000)
