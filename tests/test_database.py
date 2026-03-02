import tempfile
import os
from finance_dashboard.database import connect, insert_query, list_queries


def test_insert_and_list() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp: # Avoids using the database file used by UI.
        db_path = tmp.name
    
    try:
        conn = connect(db_path)
        qid = insert_query(conn, "manual", "AAPL, MSFT", ["AAPL", "MSFT"])
        queries = list_queries(conn)
        assert len(queries) == 1
        assert queries[0][0] == qid  # Check ID matches
        conn.close()
    finally:
        os.unlink(db_path)