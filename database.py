import sqlite3
import os

def create_database():
    # Delete old database if exists
    if os.path.exists('bca_results.db'):
        os.remove('bca_results.db')
        print("🗑️ Old database deleted")
    
    conn = sqlite3.connect('bca_results.db')
    cursor = conn.cursor()
    
    # Students Table
    cursor.execute('''
    CREATE TABLE students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_no VARCHAR(20) UNIQUE NOT NULL,
        name VARCHAR(100) NOT NULL,
        semester INTEGER DEFAULT 5,
        email VARCHAR(100),
        phone VARCHAR(15)
    )
    ''')
    
    # Subjects Table - SIMPLIFIED without subject_type
    cursor.execute('''
    CREATE TABLE subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_code VARCHAR(20) UNIQUE,
        subject_name VARCHAR(100) NOT NULL,
        credits INTEGER DEFAULT 4
    )
    ''')
    
    # Insert ALL your BCA 5th Semester Subjects
    bca_subjects = [
        ('0527001', 'Java Programming', 4),
        ('0527002', 'Computer Networks', 4),
        ('0527003', 'Computer Graphics & Multimedia Applications', 4),
        ('0527004', 'IT Trends & Technologies', 4),
        ('0527065', 'Minor Project', 4),
        ('0527080', 'Java & Computer Graphics Lab', 4)
    ]
    
    cursor.executemany('INSERT INTO subjects (subject_code, subject_name, credits) VALUES (?, ?, ?)', bca_subjects)
    
    # Marks Table
    cursor.execute('''
    CREATE TABLE marks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        subject_id INTEGER,
        marks INTEGER,
        FOREIGN KEY (student_id) REFERENCES students(id),
        FOREIGN KEY (subject_id) REFERENCES subjects(id)
    )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database created with ALL 6 BCA subjects!")
    print("   Subjects added:")
    for code, name, _ in bca_subjects:
        print(f"   • {code} - {name}")

if __name__ == "__main__":
    create_database()