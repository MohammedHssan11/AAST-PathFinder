import sqlite3

def find_all_cai():
    conn = sqlite3.connect('dev.db')
    cursor = conn.cursor()
    
    print("--- Searching for ANY College with 'Artificial' or 'AI' in name ---")
    cursor.execute("SELECT id, college_name, branch, city FROM decision_colleges WHERE college_name LIKE '%Artificial%' OR college_name LIKE '%AI%';")
    for r in cursor.fetchall():
        print(r)

    print("\n--- Searching for ANY Program with 'AI' or 'Artificial' in name ---")
    cursor.execute("SELECT id, program_name, college_id FROM decision_programs WHERE program_name LIKE '%Artificial%' OR program_name LIKE '%AI%';")
    for r in cursor.fetchall():
        print(r)
    
    conn.close()

if __name__ == "__main__":
    find_all_cai()
