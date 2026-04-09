from flask import Flask
from config import SECRET_KEY
from database import init_db
from routes.auth_routes import auth_bp
from routes.document_routes import doc_bp

app = Flask(__name__)
app.secret_key = SECRET_KEY

init_db()

app.register_blueprint(auth_bp)
app.register_blueprint(doc_bp)

if __name__ == '__main__':
    app.run(debug=True)
