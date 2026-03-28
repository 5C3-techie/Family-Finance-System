import os
from werkzeug.utils import secure_filename
from datetime import datetime

def save_file(file, upload_folder):
    original_filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_filename = f"{timestamp}_{original_filename}"

    filepath = os.path.join(upload_folder, unique_filename)
    file.save(filepath)

    return original_filename, filepath