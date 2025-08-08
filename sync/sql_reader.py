import pyodbc
from typing import List, Dict, Any

class SQLReader:
    def __init__(self, db_name: str, host: str, username: str, password: str):
        self.conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={host};"
            f"DATABASE={db_name};"
            f"UID={username};"
            f"PWD={password};"
            "TrustServerCertificate=yes;"
        )

    def fetch_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        try:
            with pyodbc.connect(self.conn_str) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                columns = [column[0] for column in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            print(f"🛑 خطأ في SQL: {e}")
            return []