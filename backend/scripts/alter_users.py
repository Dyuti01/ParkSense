from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv(override=True)
engine = create_engine(os.getenv('DATABASE_URL_SYNC'))
with engine.connect() as conn:
    conn.execute(text('ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS records_skipped INTEGER DEFAULT 0'))
    conn.commit()
print("Column added")
