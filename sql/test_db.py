import os
import sys
from sqlalchemy import text

# Base paths adjustment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.db import engine, SessionLocal
    from src.etl import run_etl
    from src.analytics import get_ride_demand_patterns, get_revenue_analytics
except ImportError as e:
    print(f"❌ Import Error: Files properly configured nahi hain. Error: {e}")
    sys.exit(1)

def test_everything():
    print("\n🤖 Uber Analytics Platform Testing Shuru Ho Rahi Hai...\n")
    
    # 1. Database Connection Check
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        print("✅ Step 1: Postgres Database se connection ekdum mast hai!")
    except Exception as e:
        print(f"❌ Step 1 Failed: Database connect nahi ho pa raha hai.")
        print(f"Exact Error: {e}")
        return

    # 2. Schema Deployment Check
    try:
        print("\n⏳ Step 2: Schema (`sql/schema.sql`) deploy kar rahe hain...")
        # Path fixed since we are inside sql/ folder
        schema_path = "schema.sql" 
        if not os.path.exists(schema_path):
            schema_path = "../sql/schema.sql"
            
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        
        statements = schema_sql.split(";")
        for statement in statements:
            if statement.strip():
                db.execute(text(statement))
        db.commit()
        print("✅ Step 2: Tables, Indexes aur Materialized View successfully deploy ho gaye!")
    except Exception as e:
        db.rollback()
        print(f"❌ Step 2 Failed: Schema apply nahi hua. Error: {e}")
        return

    # 3. ETL (CSV to DB Migration) Check
    try:
        print("\n⏳ Step 3: ETL Pipeline chala kar tables populate kar rahe hain...")
        run_etl()
        print("✅ Step 3: ETL execution perfectly completed!")
    except Exception as e:
        print(f"❌ Step 3 Failed: ETL run fail ho gaya. Error: {e}")
        return

    # 4. Analytics Query Framework Check
    try:
        print("\n⏳ Step 4: Core analytics SQL logic verify kar rahe hain...")
        demand_data = get_ride_demand_patterns(db)
        revenue_data = get_revenue_analytics(db)
        
        print(f"📊 Demand Records Fetched: {len(demand_data)} rows")
        print(f"💰 Revenue Records Fetched: {len(revenue_data)} rows")
        
        print("\n🎉 MUBARAK HO AMAN BHAI! Pure project ka database, ETL aur analytics framework 100% chal raha hai!")
    except Exception as e:
        print(f"❌ Step 4 Failed: Analytics core functions execute nahi ho paaye. Error: {e}")
    finally:
        db.close()

# Yeh line check karna zaroori hai execute karne ke liye!
if __name__ == "__main__":
    test_everything()