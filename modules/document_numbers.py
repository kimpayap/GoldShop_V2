from datetime import date
from database.database import get_connection

def ensure_document_sequence_schema():
    with get_connection() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS document_sequences(
            document_type TEXT NOT NULL, fiscal_year INTEGER NOT NULL,
            next_number INTEGER NOT NULL DEFAULT 1, prefix TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(document_type,fiscal_year))""");conn.commit()

def next_document_no(conn,document_type,prefix,with_year=False):
    year=date.today().year+543
    row=conn.execute("SELECT next_number FROM document_sequences WHERE document_type=? AND fiscal_year=?",(document_type,year)).fetchone()
    number=int(row["next_number"]) if row else 1
    if row:conn.execute("UPDATE document_sequences SET next_number=?,updated_at=CURRENT_TIMESTAMP WHERE document_type=? AND fiscal_year=?",(number+1,document_type,year))
    else:conn.execute("INSERT INTO document_sequences(document_type,fiscal_year,next_number,prefix) VALUES (?,?,?,?)",(document_type,year,2,prefix))
    return f"{prefix}{str(year)[-2:]}/{number:06d}" if with_year else f"{prefix}{number:06d}"

def list_document_sequences():
    ensure_document_sequence_schema()
    with get_connection() as conn:rows=conn.execute("SELECT * FROM document_sequences ORDER BY fiscal_year DESC,document_type").fetchall()
    return [dict(x) for x in rows]

ensure_document_sequence_schema()
