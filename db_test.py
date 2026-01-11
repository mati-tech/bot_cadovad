# test_final_sync.py
from sqlalchemy import create_engine, text

def test():
    # Your Neon connection string for synchronous connection
    # Use "postgresql://" instead of "postgresql+asyncpg://"
    DATABASE_URL = "postgresql://neondb_owner:YOUR_PASSWORD@ep-tiny-meadow-a1u4li8z-pooler.aws.neon.tech/quick_sell_db?sslmode=require"
    
    try:
        # Test with SSL parameters
        engine = create_engine(
            DATABASE_URL,
            echo=True,  # Set to True to see SQL queries
            pool_size=5,
            max_overflow=10
        )
        
        print("🔧 Creating connection...")
        
        with engine.connect() as conn:
            print("✅ Connection successful!")
            
            # Test a simple query
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()
            print(f"📊 PostgreSQL version: {version[0]}")
            
            # Test database name
            result = conn.execute(text("SELECT current_database()"))
            db_name = result.fetchone()
            print(f"📁 Database name: {db_name[0]}")
            
            # Test if tables exist (optional)
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            table_count = result.fetchone()
            print(f"📈 Tables in database: {table_count[0]}")
            
        print("\n🎉 All tests passed!")
            
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test()