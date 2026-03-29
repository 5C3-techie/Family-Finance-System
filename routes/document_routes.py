from flask import Blueprint, render_template, request, redirect, session, url_for, send_from_directory
from services.document_service import *
from utils.file_utils import save_file
from config import UPLOAD_FOLDER
import os

doc_bp = Blueprint('doc', __name__)

@doc_bp.route('/dashboard')
def dashboard():
    if session['role'] == 'admin':
        docs = get_admin_documents()
    else:
        docs = get_user_documents(session['user_id'])

    return render_template('dashboard.html', documents=docs)

@doc_bp.route('/upload', methods=['GET','POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        user_id = request.form['user_id']

        filename, filepath = save_file(file, UPLOAD_FOLDER)
        save_document(user_id, filename, filepath)

        return redirect(url_for('doc.dashboard'))

    return render_template('upload.html')

@doc_bp.route('/download/<int:doc_id>')
def download(doc_id):
    doc = get_document(doc_id)

    directory = os.path.abspath(UPLOAD_FOLDER)
    filename = os.path.basename(doc['filepath'])

    return send_from_directory(directory, filename)