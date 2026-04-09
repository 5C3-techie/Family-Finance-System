from database import get_db_connection


def _build_search_clause(search_term):
    if not search_term:
        return "", []

    like_term = f"%{search_term.strip()}%"
    clause = '''
        AND (
            d.filename LIKE ?
            OR COALESCE(d.description, '') LIKE ?
            OR COALESCE(uploader.name, '') LIKE ?
            OR COALESCE(member.name, '') LIKE ?
        )
    '''
    params = [like_term, like_term, like_term, like_term]
    return clause, params


def save_document(uploaded_by, assigned_member, filename, filepath, description=''):
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO documents (user_id, uploaded_by, assigned_member, filename, filepath, description)
        VALUES (?,?,?,?,?,?)
        """,
        (assigned_member, uploaded_by, assigned_member, filename, filepath, description)
    )
    conn.commit()
    conn.close()


def get_admin_documents(search_term=''):
    conn = get_db_connection()
    search_clause, search_params = _build_search_clause(search_term)
    docs = conn.execute(f'''
        SELECT
            d.id,
            d.filename,
            d.filepath,
            d.description,
            d.upload_date,
            uploader.name AS uploaded_by_name,
            member.name AS assigned_member_name,
            d.assigned_member
        FROM documents d
        LEFT JOIN users uploader ON d.uploaded_by = uploader.id
        LEFT JOIN users member ON d.assigned_member = member.id
        WHERE 1=1
        {search_clause}
        ORDER BY d.upload_date DESC
    ''', search_params).fetchall()
    conn.close()
    return docs


def get_user_documents(user_id, search_term=''):
    conn = get_db_connection()
    search_clause, search_params = _build_search_clause(search_term)
    docs = conn.execute(f'''
        SELECT
            d.id,
            d.filename,
            d.filepath,
            d.description,
            d.upload_date,
            uploader.name AS uploaded_by_name,
            member.name AS assigned_member_name,
            d.assigned_member
        FROM documents d
        LEFT JOIN users uploader ON d.uploaded_by = uploader.id
        LEFT JOIN users member ON d.assigned_member = member.id
        WHERE d.assigned_member=?
        {search_clause}
        ORDER BY d.upload_date DESC
    ''', [user_id, *search_params]).fetchall()
    conn.close()
    return docs


def get_document(doc_id):
    conn = get_db_connection()
    doc = conn.execute('''
        SELECT
            d.*,
            uploader.name AS uploaded_by_name,
            member.name AS assigned_member_name
        FROM documents d
        LEFT JOIN users uploader ON d.uploaded_by = uploader.id
        LEFT JOIN users member ON d.assigned_member = member.id
        WHERE d.id=?
    ''', (doc_id,)).fetchone()
    conn.close()
    return doc


def get_members():
    conn = get_db_connection()
    members = conn.execute(
        "SELECT id, name, email, phone FROM users WHERE role='member' ORDER BY name"
    ).fetchall()
    conn.close()
    return members


def reassign_document(doc_id, assigned_member):
    conn = get_db_connection()
    doc = conn.execute("SELECT id FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not doc:
        conn.close()
        return False

    conn.execute(
        "UPDATE documents SET assigned_member=?, user_id=? WHERE id=?",
        (assigned_member, assigned_member, doc_id)
    )
    conn.commit()
    conn.close()
    return True


def delete_document(doc_id):
    conn = get_db_connection()
    doc = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
    if doc:
        conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
        conn.commit()
    conn.close()
    return doc
