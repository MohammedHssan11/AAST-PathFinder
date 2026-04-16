import sqlite3

def find_alamein_ca():
    conn = sqlite3.connect('dev.db')
    cursor = conn.cursor()
    
    query = """
    SELECT dc.id, dc.college_name, dp.id, dp.program_name, dp.summary
    FROM decision_programs dp
    JOIN decision_colleges dc ON dp.college_id = dc.id
    WHERE dc.branch = 'El Alamein'
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    
    print(f"Found {len(rows)} programs in El Alamein branch.")
    for r in rows:
        print(f"ColID: {r[0]} | College: {r[1]} | ProgID: {r[2]} | Program: {r[3]}")
    
    conn.close()

if __name__ == "__main__":
    find_alamein_ca()
