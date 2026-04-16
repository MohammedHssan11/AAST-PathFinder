import sqlite3
import os

db_path = "dev.db"

def audit_db():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("--- Colleges in Alamein ---")
    cursor.execute("SELECT id, college_name, branch, city FROM decision_colleges WHERE branch LIKE '%Alamein%' OR city LIKE '%Alamein%';")
    colleges = cursor.fetchall()
    college_ids = []
    for c in colleges:
        print(c)
        college_ids.append(c[0])

    print("\n--- AI/Computing Programs ---")
    cursor.execute("SELECT id, program_name, college_id, summary FROM decision_programs WHERE program_name LIKE '%Artificial Intelligence%' OR program_name LIKE '%AI%' OR program_name LIKE '%Computing%' OR program_name LIKE '%Software%';")
    programs = cursor.fetchall()
    for p in programs:
        match_marker = "[MATCH]" if p[2] in college_ids else ""
        print(f"{p} {match_marker}")

    conn.close()

if __name__ == "__main__":
    audit_db()
