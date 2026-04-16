
import sqlite3
import os

def check_db():
    db_path = 'dev.db'
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found!")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- Programs with 'Artificial Intelligence' ---")
    cursor.execute("SELECT id, program_name, college_id FROM decision_programs WHERE program_name LIKE '%Artificial Intelligence%'")
    programs = cursor.fetchall()
    for p in programs:
        print(p)
        
    print("\n--- Fee items for AI_ALAMEIN (Detailed) ---")
    cursor.execute("SELECT * FROM decision_fee_items WHERE college_id_raw = 'AI_ALAMEIN'")
    columns = [d[0] for d in cursor.description]
    items = cursor.fetchall()
    for row in items:
        print(dict(zip(columns, row)))
        
    print("\n--- Fee amounts for AI_ALAMEIN fee items ---")
    cursor.execute("""
        SELECT a.fee_item_id, a.student_group, a.fee_category, a.amount_usd 
        FROM decision_fee_amounts a
        JOIN decision_fee_items i ON a.fee_item_id = i.id
        WHERE i.college_id_raw = 'AI_ALAMEIN'
    """)
    amounts = cursor.fetchall()
    for a in amounts:
        print(a)
        
    print("\n--- Fee Category Rules for AI_ALAMEIN ---")
    cursor.execute("""
        SELECT r.rule_id, r.certificate_type, r.student_group, r.branch_scope
        FROM decision_fee_category_rules r
        JOIN decision_fee_rule_colleges c ON r.id = c.fee_rule_id
        WHERE c.college_id_raw = 'AI_ALAMEIN'
    """)
    rules = cursor.fetchall()
    for r in rules:
        print(r)

    conn.close()

if __name__ == "__main__":
    check_db()
