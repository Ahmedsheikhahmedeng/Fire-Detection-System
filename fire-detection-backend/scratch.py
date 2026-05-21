from app.core.database import engine
from sqlalchemy import text

try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE hotspots ADD COLUMN acq_time VARCHAR(50);"))
        conn.execute(text("ALTER TABLE hotspots ADD COLUMN city VARCHAR(100);"))
        conn.commit()
    print("Columns added successfully!")
except Exception as e:
    print(f"Migration error or columns already exist: {e}")
