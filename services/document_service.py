from database import get_db_connection

def save_document(user_id, filename, filepath, description=''):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO documents (user_id, filename, filepath, description) VALUES (?,?,?,?)",
        (user_id, filename, filepath, description)
    )
    conn.commit()
    conn.close()

def get_admin_documents():
    conn = get_db_connection()
    docs = conn.execute('''
        SELECT d.id, d.filename, d.upload_date, u.name as user_name
        FROM documents d JOIN users u ON d.user_id=u.id
    ''').fetchall()
    conn.close()
    return docs

def get_user_documents(user_id):
    conn = get_db_connection()
    docs = conn.execute(
        "SELECT * FROM documents WHERE user_id=?",
        (user_id,)
    ).fetchall()
    conn.close()
    return docs

def get_document(doc_id):
    conn = get_db_connection()
    doc = conn.execute(
        "SELECT * FROM documents WHERE id=?",
        (doc_id,)
    ).fetchone()
    conn.close()
    return doc

def delete_document(doc_id):
    conn = get_db_connection()
    doc = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
    if doc:
        conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
        conn.commit()
    conn.close()
    return doc