import sqlite3
import os
import uuid

DB_PATH = "dev.db"

def run_smart_fix():
    if not os.path.exists(DB_PATH):
        print(f"❌ Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    def get_cols(table):
        cursor.execute(f"PRAGMA table_info({table})")
        return [info[1] for info in cursor.fetchall()]

    try:
        print("🕵️ Exploring Database Schema...")
        
        # 1. استكشاف العواميد عشان ما نغلطش تاني
        item_cols = get_cols('decision_fee_items')
        amount_cols = get_cols('decision_fee_amounts')
        
        print(f"📊 Columns in decision_fee_items: {item_cols}")
        print(f"📊 Columns in decision_fee_amounts: {amount_cols}")

        # 2. تحديد المعطيات
        program_id = "CAI_EL_ALAMEIN__INTELLIGENT_SYSTEMS"
        amount_a = 5660.0
        amount_b = 6405.0

        # 3. محاولة الحقن الذكي
        # هندور على fee_item مربوط بالذكاء الاصطناعي أو نكريته
        print("💉 Injecting Data...")
        
        # لو مفيش program_id في decision_fee_items، غالباً الربط في جدول تاني
        # بس إحنا هنضيف الـ Item ونربطه بالـ Amount
        item_id = str(uuid.uuid4())
        
        # هنضيف الـ Item (بناءً على العواميد اللي عندك)
        # غالباً العواميد هي (id, name, fee_type) أو (id, fee_definition_id)
        if 'name' in item_cols:
            cursor.execute("INSERT OR IGNORE INTO decision_fee_items (id, name) VALUES (?, ?)", (item_id, 'Tuition Fees'))
        else:
            cursor.execute("INSERT OR IGNORE INTO decision_fee_items (id) VALUES (?)", (item_id,))

        # 4. الحقن في جدول الـ Amounts (هنا السعر الحقيقي)
        # هنستخدم الـ Column names اللي طلعت من الاستكشاف
        final_item_id = cursor.execute("SELECT id FROM decision_fee_items LIMIT 1").fetchone()[0]
        
        # التأكد من أسماء عواميد المبالغ
        col_a = 'category_a_amount' if 'category_a_amount' in amount_cols else 'amount'
        col_b = 'category_b_amount' if 'category_b_amount' in amount_cols else 'amount_b'
        
        sql = f"""
            INSERT OR REPLACE INTO decision_fee_amounts 
            (id, fee_item_id, {col_a}, {col_b}, currency, quality_status)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        cursor.execute(sql, (str(uuid.uuid4()), final_item_id, amount_a, amount_b, 'USD', 'verified'))

        conn.commit()
        print(f"🚀 SUCCESS! Injected {amount_a} USD into decision_fee_amounts.")
        print("💡 Restart Uvicorn and test 'Ahmed' again!")

    except Exception as e:
        print(f"❌ Error during injection: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_smart_fix()