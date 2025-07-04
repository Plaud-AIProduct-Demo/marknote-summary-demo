import os
import pymysql
from contextlib import contextmanager

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")
MYSQL_DB = os.getenv("MYSQL_DB", "marknote")

@contextmanager
def get_connection():
    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        charset="utf8mb4"
    )
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS mark_note_summary (
                id INT AUTO_INCREMENT PRIMARY KEY,
                summary_id VARCHAR(128),
                scenario VARCHAR(64),
                language VARCHAR(32),
                mark_time INT,
                time_range INT,
                content TEXT,
                mark_type VARCHAR(16),
                image_url TEXT,
                user_notes TEXT,
                mark_note TEXT,
                start_time INT,
                end_time INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            ''')
        conn.commit()

def insert_mark_note_summary(data: dict):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            sql = '''
            INSERT INTO mark_note_summary
            (summary_id, scenario, language, mark_time, time_range, content, prompt, mark_type, image_url, user_notes, mark_note, start_time, end_time)
            VALUES (%(summary_id)s, %(scenario)s, %(language)s, %(mark_time)s, %(time_range)s, %(content)s, %(prompt)s, %(mark_type)s, %(image_url)s, %(user_notes)s, %(mark_note)s, %(start_time)s, %(end_time)s)
            '''
            cursor.execute(sql, data)
        conn.commit()
