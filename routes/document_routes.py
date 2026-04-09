from flask import Blueprint, render_template, request, redirect, session, url_for, send_from_directory, flash
from services.auth_service import get_all_users
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
    users = []
    search_term = request.args.get('search', '').strip()
    try:
        if session['role'] == 'admin':
            documents = get_admin_documents(search_term)
            users = get_all_users()
        else:
            documents = get_user_documents(session['user_id'], search_term)
    except sqlite3.Error:
        flash('Unable to load documents right now. Please try again shortly.', 'danger')

    return render_template(
        'dashboard.html',
        documents=documents,
        users=users,
        role=session['role'],
        name=session['name'],
        search_term=search_term
    )

@doc_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('auth.login'))
        
    if session['role'] != 'admin':
        flash('Access denied. Only administrators can upload documents.', 'danger')
        return redirect(url_for('doc.dashboard'))

    members = []
    users = []
    try:
        members = get_members()
        users = get_all_users()
    except sqlite3.Error:
        flash('Unable to load members right now. Please try again shortly.', 'danger')

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file detected in upload.', 'danger')
            return redirect(request.url)
            
        file = request.files['file']
        uploaded_by = session['user_id']
        description = request.form.get('description', '')
        assigned_member = request.form.get('assigned_member')
        
        if file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(request.url)

        if not assigned_member:
            flash('Please select a member to assign this document to.', 'danger')
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

            save_document(uploaded_by, int(assigned_member), original_filename, filepath, description)

            flash(f'Document "{original_filename}" uploaded successfully!', 'success')
            return redirect(url_for('doc.dashboard'))
        except Exception:
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except OSError:
                    pass
            flash('An error occurred while uploading. Please try again.', 'danger')

    return render_template('upload.html', name=session['name'], members=members, users=users)

@doc_bp.route('/download/<int:doc_id>')
def download(doc_id):
    if 'user_id' not in session:
        flash('Please login to download.', 'warning')
        return redirect(url_for('auth.login'))

    doc = get_document(doc_id)

    if not doc:
        flash('Document not found.', 'danger')
        return redirect(url_for('doc.dashboard'))

    if session['role'] != 'admin' and doc['assigned_member'] != session['user_id']:
        flash('Access denied. You can only download documents assigned to you.', 'danger')
        return redirect(url_for('doc.dashboard'))

    try:
        directory = os.path.abspath(UPLOAD_FOLDER)
        filename_on_disk = os.path.basename(doc['filepath'])
        return send_from_directory(directory, filename_on_disk, as_attachment=True, download_name=doc['filename'])
    except Exception as e:
        flash('Error fetching file. It might have been deleted.', 'danger')
        return redirect(url_for('doc.dashboard'))


@doc_bp.route('/view/<int:doc_id>')
def view(doc_id):
    if 'user_id' not in session:
        flash('Please login to view documents.', 'warning')
        return redirect(url_for('auth.login'))

    doc = get_document(doc_id)

    if not doc:
        flash('Document not found.', 'danger')
        return redirect(url_for('doc.dashboard'))

    if session['role'] != 'admin' and doc['assigned_member'] != session['user_id']:
        flash('Access denied. You can only view documents assigned to you.', 'danger')
        return redirect(url_for('doc.dashboard'))

    try:
        directory = os.path.abspath(UPLOAD_FOLDER)
        filename_on_disk = os.path.basename(doc['filepath'])
        return send_from_directory(directory, filename_on_disk, as_attachment=False, download_name=doc['filename'])
    except Exception:
        flash('Error opening file. It might have been deleted.', 'danger')
        return redirect(url_for('doc.dashboard'))


@doc_bp.route('/reassign/<int:doc_id>', methods=['POST'])
def reassign(doc_id):
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('auth.login'))

    if session['role'] != 'admin':
        flash('Only administrators can reassign documents.', 'danger')
        return redirect(url_for('doc.dashboard'))

    assigned_member = request.form.get('assigned_member')
    if not assigned_member:
        flash('Please select a member before reassigning.', 'danger')
        return redirect(url_for('doc.dashboard'))

    try:
        success = reassign_document(doc_id, int(assigned_member))
    except Exception:
        success = False

    if success:
        flash('Document reassigned successfully.', 'success')
    else:
        flash('Unable to reassign document. Please try again.', 'danger')

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
