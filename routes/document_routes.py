from flask import Blueprint, render_template, request, redirect, session, url_for, send_from_directory, flash
from services.document_service import *
from utils.file_utils import save_file
from config import UPLOAD_FOLDER
import os
import sqlite3
from database import get_db_connection
from werkzeug.utils import secure_filename
from datetime import datetime

doc_bp = Blueprint('doc', __name__)
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@doc_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to access your dashboard.', 'warning')
        return redirect(url_for('auth.login'))

    documents = []
    conn = None
    try:
        conn = get_db_connection()
        # All documents are globally visible, fetch uploader info regardless of role
        documents = conn.execute('''
            SELECT d.id, d.filename, d.description, d.upload_date, u.name as user_name
            FROM documents d
            JOIN users u ON d.user_id = u.id
            ORDER BY d.upload_date DESC
        ''').fetchall()
    except sqlite3.Error:
        flash('Unable to load documents right now. Please try again shortly.', 'danger')
    finally:
        if conn is not None:
            conn.close()

    return render_template('dashboard.html', documents=documents, role=session['role'], name=session['name'])

@doc_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('auth.login'))
        
    if session['role'] != 'admin':
        flash('Access denied. Only administrators can upload documents.', 'danger')
        return redirect(url_for('doc.dashboard'))

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

        if not allowed_file(file.filename):
            flash('Invalid file type. Please upload a PDF, JPG, JPEG, or PNG file.', 'danger')
            return redirect(request.url)

        original_filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_filename = f"{timestamp}_{original_filename}"

        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        try:
            file.save(filepath)

            save_document(user_id, original_filename, filepath, description)

            flash(f'Document "{original_filename}" uploaded successfully!', 'success')
            return redirect(url_for('doc.dashboard'))
        except Exception:
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except OSError:
                    pass
            flash('An error occurred while uploading. Please try again.', 'danger')

    return render_template('upload.html', name=session['name'])

@doc_bp.route('/download/<int:doc_id>')
def download(doc_id):
    if 'user_id' not in session:
        flash('Please login to download.', 'warning')
        return redirect(url_for('auth.login'))

    doc = get_document(doc_id)

    if not doc:
        flash('Document not found.', 'danger')
        return redirect(url_for('doc.dashboard'))

    try:
        directory = os.path.abspath(UPLOAD_FOLDER)
        filename_on_disk = os.path.basename(doc['filepath'])
        return send_from_directory(directory, filename_on_disk, as_attachment=True, download_name=doc['filename'])
    except Exception as e:
        flash('Error fetching file. It might have been deleted.', 'danger')
        return redirect(url_for('doc.dashboard'))

@doc_bp.route('/delete/<int:doc_id>', methods=['POST'])
def delete(doc_id):
    if 'user_id' not in session:
        flash('Please login to delete documents.', 'warning')
        return redirect(url_for('auth.login'))
        
    if session['role'] != 'admin':
        flash('Access denied. Only administrators can delete documents.', 'danger')
        return redirect(url_for('doc.dashboard'))

    doc = get_document(doc_id)
    
    if not doc:
        flash('Document not found.', 'danger')
        return redirect(url_for('doc.dashboard'))
        
    try:
        # Delete the actual file from filesystem
        if os.path.exists(doc['filepath']):
            os.remove(doc['filepath'])
        # Delete DB record
        delete_document(doc_id)
        flash('Document deleted successfully.', 'success')
    except Exception as e:
        flash('An error occurred while deleting the document.', 'danger')

    return redirect(url_for('doc.dashboard'))
