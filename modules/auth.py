from database.database import get_connection


def login(username, password):
    """
    ตรวจสอบ username และ password
    """

    from modules.system_controls import ensure_control_schema, log_audit, verify_password, hash_password
    ensure_control_schema()
    name = username.strip()
    with get_connection() as conn:
        failures = conn.execute("""SELECT COUNT(*) FROM login_attempts
            WHERE username=? AND success=0 AND attempted_at>=datetime('now','-15 minutes')""", (name,)).fetchone()[0]
        if failures >= 5:
            return None

        user = conn.execute("""
            SELECT
                id,
                username,
                password,
                full_name,
                role
            FROM users
            WHERE username = ?
              AND active = 1
        """, (name,)).fetchone()

        if user and verify_password(password,user['password']):
            if not str(user['password']).startswith('pbkdf2_sha256$'):
                conn.execute("UPDATE users SET password=? WHERE id=?",(hash_password(password),user['id']))
            result = {key:user[key] for key in ('id','username','full_name','role')}
            conn.execute("DELETE FROM login_attempts WHERE username=? AND success=0",(name,))
            conn.execute("INSERT INTO login_attempts(username,success) VALUES (?,1)", (name,))
            conn.commit()
            log_audit("login", "security", result, description="เข้าสู่ระบบสำเร็จ")
            return result

        conn.execute("INSERT INTO login_attempts(username,success) VALUES (?,0)", (name,))
        conn.commit()
        return None


def login_lock_remaining(username):
    from modules.system_controls import ensure_control_schema
    ensure_control_schema()
    with get_connection() as conn:
        failures = conn.execute("""SELECT COUNT(*) FROM login_attempts
            WHERE username=? AND success=0 AND attempted_at>=datetime('now','-15 minutes')""", (str(username).strip(),)).fetchone()[0]
    return max(0, 5-failures)
