import os
import sqlite3
import bcrypt
import random
import smtplib
import logging
from email.message import EmailMessage
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.utils import secure_filename

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
# Secret key for session management and flash messages
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
        pass # Columns already exist
        
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
    try:
        conn.execute('ALTER TABLE documents ADD COLUMN description TEXT')
    except sqlite3.OperationalError:
        pass # Column already exists
        
    conn.commit()
    conn.close()

# Initialize DB on startup
init_db()

def send_otp_email(email, otp):
    """Sends OTP via email."""
    sender_email = "nagameenakshidarapurapu@gmail.com"
    app_password = "ofio croa rnrw hvdn" # Make sure to replace this in production

    msg = EmailMessage()
    msg['Subject'] = "Your Login OTP - Family Finance System"
    msg['From'] = sender_email
    msg['To'] = email
    msg.set_content(f"Your OTP for login is: {otp}\n\nThis OTP is valid for 5 minutes.")

    try:
        logging.info(f"Attempting to send OTP email to {email}...")
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()
        logging.info("OTP sent successfully to: " + email)
        logging.debug("Generated OTP: " + str(otp)) # helpful for debugging locally
    except Exception as e:
        logging.error(f"Error sending OTP to {email}: {e}")

@app.route('/')
def index():
    logging.debug("Accessed index route.")
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

        logging.debug(f"Registration attempt for email: {email}, role: {role}")

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
            logging.info(f"User {email} registered successfully.")
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            logging.warning(f"Registration failed: Email {email} already exists.")
            flash('Email address is already registered.', 'danger')
        except Exception as e:
            logging.error(f"Exception during registration: {e}")
            flash('An error occurred during registration.', 'danger')
        finally:
            conn.close()

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        logging.debug(f"Login attempt for email: {email}")

        if not email or not password:
            flash("Email and password are required.", "danger")
            return redirect(url_for('login'))

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            logging.info(f"Password validated for {email}. Generating OTP.")
            otp = str(random.randint(100000, 999999))
            expiry = datetime.now() + timedelta(minutes=5)

            conn = get_db_connection()
            conn.execute(
                "UPDATE users SET otp = ?, otp_expiry = ? WHERE id = ?",
                (otp, expiry.strftime("%Y-%m-%d %H:%M:%S"), user['id'])
            )
            conn.commit()
            conn.close()

            send_otp_email(user['email'], otp)

            # Store temporary user id in session to verify OTP
            session['temp_user'] = user['id']
            flash("OTP sent to your email. Please verify.", "info")
            return redirect(url_for('verify_otp'))
        else:
            logging.warning(f"Invalid credentials for email: {email}")
            flash("Invalid email or password", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if 'temp_user' not in session:
        logging.warning("Attempted to access verify_otp without temp_user in session.")
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        entered_otp = request.form.get('otp')
        logging.debug(f"OTP verification attempt for temp_user_id: {session['temp_user']}")

        if not entered_otp:
            flash("Please enter the OTP.", "danger")
            return redirect(url_for('verify_otp'))

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE id=?", (session['temp_user'],)).fetchone()
        conn.close()

        if user:
            logging.debug(f"Stored OTP: {user['otp']}, Entered OTP: {entered_otp}")
            # Ensure safe comparison
            if user['otp'] and str(user['otp']).strip() == str(entered_otp).strip():
                try:
                    expiry_time = datetime.strptime(user['otp_expiry'], "%Y-%m-%d %H:%M:%S")
                    if datetime.now() <= expiry_time:
                        logging.info(f"OTP verified successfully for user_id: {user['id']}")
                        
                        # OTP matched and not expired: Log the user in
                        session['user_id'] = user['id']
                        session['name'] = user['name']
                        session['role'] = user['role']

                        # Remove temporary session variable
                        session.pop('temp_user', None)

                        flash("Login successful with OTP verification.", "success")
                        return redirect(url_for('dashboard'))
                    else:
                        logging.warning(f"OTP expired for user_id: {user['id']}")
                        flash("OTP has expired. Please log in again to generate a new one.", "danger")
                        session.pop('temp_user', None)
                        return redirect(url_for('login'))
                except ValueError as e:
                    logging.error(f"Error parsing OTP expiry datetime: {e}")
                    flash("An internal error occurred while validating OTP.", "danger")
                    return redirect(url_for('verify_otp'))
            else:
                logging.warning(f"Incorrect OTP entered for user_id: {user['id']}")
                flash("Invalid OTP.", "danger")
                return redirect(url_for('verify_otp'))
        else:
            logging.error(f"User not found for temp_user_id: {session['temp_user']}")
            flash("User no longer exists or session invalid.", "danger")
            session.pop('temp_user', None)
            return redirect(url_for('login'))

    return render_template("otp_verify.html")

@app.route('/logout')
def logout():
    session.clear()
    logging.info("User logged out.")
    flash('You have been successfully logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        logging.warning("Unauthorized access attempt to dashboard.")
        flash('Please log in to access your dashboard.', 'warning')
        return redirect(url_for('login'))

    conn = get_db_connection()
    
    # All documents are globally visible, fetch uploader info regardless of role
    logging.debug(f"Dashboard accessed by {session['name']} ({session['role']})")
    documents = conn.execute('''
        SELECT d.id, d.filename, d.description, d.upload_date, u.name as user_name 
        FROM documents d
        JOIN users u ON d.user_id = u.id
        ORDER BY d.upload_date DESC
    ''').fetchall()
        
    conn.close()
    
    # Ensure a valid response object is returned
    return render_template('dashboard.html', documents=documents, role=session['role'], name=session['name'])

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
        
    if session['role'] != 'admin':
        logging.warning(f"Non-admin user ({session['user_id']}) attempted to access upload page.")
        flash('Access denied. Only administrators can upload documents.', 'danger')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file detected in upload.', 'danger')
            return redirect(request.url)
            
        file = request.files['file']
        user_id = session['user_id']
        description = request.form.get('description', '')
        
        if file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(request.url)

        if file:
            original_filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            unique_filename = f"{timestamp}_{original_filename}"
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            try:
                file.save(filepath)
                
                conn.execute('''
                    INSERT INTO documents (user_id, filename, filepath, description)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, original_filename, filepath, description))
                conn.commit()
                
                logging.info(f"File {original_filename} uploaded and assigned to user_id {user_id}")
                flash(f'Document "{original_filename}" uploaded successfully!', 'success')
                return redirect(url_for('dashboard'))
            except Exception as e:
                logging.error(f"Error saving uploaded file: {e}")
                flash('An error occurred while uploading. Please try again.', 'danger')

    conn.close()
    
    return render_template('upload.html', name=session['name'])

@app.route('/download/<int:doc_id>')
def download(doc_id):
    if 'user_id' not in session:
        flash('Please login to download.', 'warning')
        return redirect(url_for('login'))

    conn = get_db_connection()
    doc = conn.execute('SELECT * FROM documents WHERE id = ?', (doc_id,)).fetchone()
    conn.close()

    if not doc:
        logging.warning(f"User {session['user_id']} attempted to download non-existent doc_id {doc_id}")
        flash('Document not found.', 'danger')
        return redirect(url_for('dashboard'))



    try:
        directory = os.path.abspath(app.config['UPLOAD_FOLDER'])
        filename_on_disk = os.path.basename(doc['filepath'])
        logging.info(f"User {session['user_id']} downloaded document {doc_id}")
        return send_from_directory(directory, filename_on_disk, as_attachment=True, download_name=doc['filename'])
    except Exception as e:
        logging.error(f"Error serving file for download (doc_id {doc_id}): {e}")
        flash('Error fetching file. It might have been deleted.', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/delete/<int:doc_id>', methods=['POST'])
def delete(doc_id):
    if 'user_id' not in session:
        flash('Please login to delete documents.', 'warning')
        return redirect(url_for('login'))
        
    if session['role'] != 'admin':
        logging.warning(f"Non-admin user ({session['user_id']}) attempted to delete document {doc_id}.")
        flash('Access denied. Only administrators can delete documents.', 'danger')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    doc = conn.execute('SELECT * FROM documents WHERE id = ?', (doc_id,)).fetchone()
    
    if not doc:
        conn.close()
        flash('Document not found.', 'danger')
        return redirect(url_for('dashboard'))
        
    try:
        # Delete the actual file from filesystem
        if os.path.exists(doc['filepath']):
            os.remove(doc['filepath'])
        # Delete DB record
        conn.execute('DELETE FROM documents WHERE id = ?', (doc_id,))
        conn.commit()
        logging.info(f"Document {doc_id} deleted by Admin {session['user_id']}")
        flash('Document deleted successfully.', 'success')
    except Exception as e:
        logging.error(f"Error deleting document {doc_id}: {e}")
        flash('An error occurred while deleting the document.', 'danger')
    finally:
        conn.close()

    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    logging.info("Starting Family Finance Document Management System...")
    app.run(debug=True, port=5000)
