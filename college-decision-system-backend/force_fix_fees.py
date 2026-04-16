import sqlite3
import os
from datetime import datetime

DB_PATH = "dev.db"

def fix_unique_and_sync():
    if not os.path.exists(DB_PATH):
        print(f"❌ Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("🛠️ Resolving UNIQUE Constraint Conflicts...")
        timestamp = datetime.now().isoformat()

        # البرامج والأسعار اللي هنربطها
        programs = [
            ("Intelligent Systems", 5660.0),
            ("Data Science", 5660.0)
        ]

        # 1. مسح أي داتا قديمة مرتبطة بفرع العلمين عشان نضمن إن مفيش تكرار
        cursor.execute("DELETE FROM decision_fee_items WHERE college_id_raw = 'CAI_EL_ALAMEIN'")
        cursor.execute("DELETE FROM decision_fee_amounts WHERE fee_item_id NOT IN (SELECT id FROM decision_fee_items)")

        for prog_name, amount in programs:
            print(f"🚀 Processing: {prog_name}...")

            # 2. إنشاء تعريف رسوم جديد (Unique Definition) لكل برنامج
            # عشان نتفادى الـ UNIQUE constraint failed: decision_fee_items.fee_id
            cursor.execute("""
                INSERT INTO decision_fee_definitions 
                (definition_group, definition_key, definition_value, sort_order) 
                VALUES (?, ?, ?, ?)
            """, ('FINANCIAL', f'TUITION_{prog_name.replace(" ", "_").upper()}', f'Standard Tuition for {prog_name}', 1))
            
            new_fee_id = cursor.lastrowid

            # 3. إضافة الـ Item بالـ fee_id الجديد الفريد
            cursor.execute("""
                INSERT INTO decision_fee_items 
                (fee_id, academic_year, currency, fee_mode, branch_scope, 
                 college_id_raw, college_name, program_name, track_type, 
                 partner_university, data_quality_status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (new_fee_id, '2025/2026', 'USD', 'per_semester', 'Alamein', 
                  'CAI_EL_ALAMEIN', "College of Artificial Intelligence", prog_name, 
                  'science', 'Universitat Autònoma de Barcelona', 'verified', 
                  timestamp, timestamp))
            
            new_item_id = cursor.lastrowid

            # 4. ربط السعر (5660$) بالـ Item ID الجديد
            cursor.execute("""
                INSERT INTO decision_fee_amounts 
                (fee_item_id, student_group, fee_category, amount_usd) 
                VALUES (?, ?, ?, ?)
            """, (new_item_id, 'supportive_states', 'A', amount))

            print(f"✅ Successfully linked {prog_name} (Item ID: {new_item_id}, Fee ID: {new_fee_id})")

        conn.commit()
        print("🎉 MISSION ACCOMPLISHED: The database is now perfectly synced!")
        print("💡 Final Instruction: Restart Uvicorn and run the 'Ahmed' test.")

    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_unique_and_sync()