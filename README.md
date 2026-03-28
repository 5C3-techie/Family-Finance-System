# Family Finance System

A Flask-based web application for managing family financial documents with user authentication, OTP verification, and document upload/download features.

## Project Structure

The code is organized into separate folders for better maintainability:

- **app.py**: Main application entry point.
- **config.py**: Configuration settings (SMTP, DB path, secret key).
- **database.py**: Database connection and initialization.
- **models/**: Data models (user_model.py, document_model.py).
- **routes/**: Flask routes (auth_routes.py for login/register, document_routes.py for dashboard/upload).
- **services/**: Business logic (auth_service.py for authentication, document_service.py for documents, otp_service.py for OTP generation).
- **templates/**: HTML templates (login.html, register.html, dashboard.html, etc.).
- **utils/**: Utility functions (email_utils.py for sending emails, file_utils.py for file handling).

## Features

- User registration and login with email/password.
- OTP (One-Time Password) verification via email.
- Role-based access (Member/Admin).
- Document upload and download.
- Dashboard to view uploaded documents.

## Setup Instructions

1. **Clone the repository**:
   ```
   git clone <your-repo-url>
   cd Family-Finance-System
   ```

2. **Install dependencies**:
   ```
   pip install -r requirements.txt
   ```

3. **Configure settings**:
   - Copy `config.py` and update:
     - `SENDER_EMAIL`: Your Gmail address.
     - `SENDER_PASSWORD`: Your Gmail app password (enable 2FA and generate app password).
     - Other settings as needed.

4. **Run the app**:
   ```
   python app.py
   ```
   - Open http://127.0.0.1:5000 in browser.

## App Flow and Data Flow

When you start the app with `python app.py`:

1. **Initialization**:
   - Flask app is created.
   - Database tables are initialized via `init_db()` in `database.py`.
   - Blueprints (auth and document routes) are registered.

2. **User Interaction**:
   - User visits `/` → Redirects to login if not logged in.
   - **Registration/Login**:
     - Routes in `routes/auth_routes.py` handle GET/POST.
     - Calls `services/auth_service.py` for logic (e.g., hash password, generate OTP).
     - OTP sent via `utils/email_utils.py` using SMTP.
     - Templates in `templates/` render pages with Bootstrap styling.

3. **Dashboard and Documents**:
   - After login/OTP, user goes to dashboard.
   - `routes/document_routes.py` fetches documents from DB via `services/document_service.py`.
   - Templates display data; files handled by `utils/file_utils.py`.

4. **Data Flow**:
   - User input → Routes → Services (business logic) → Database/Models → Templates (render response).
   - Emails: Services → Utils (SMTP send).
   - Files: Uploaded to `uploads/` folder, paths stored in DB.

## Requirements

- Python 3.x
- Flask
- SQLite (built-in)
- Gmail account for OTP (with app password)

## Security Notes

- Passwords are hashed with bcrypt.
- OTP expires in 5 minutes.
- Sensitive files (config.py, database.db) are ignored in .gitignore.
