import sqlite3
import random

print("🎓 Adding Real Student Names & Marks...")

conn = sqlite3.connect('bca_results.db')
cursor = conn.cursor()

# Clear existing data
cursor.execute("DELETE FROM marks")
cursor.execute("DELETE FROM students")

# Real Indian student names (46 students)
students_data = [
    ("BCA2024001", "Aarav Sharma"),
    ("BCA2024002", "Vivaan Verma"),
    ("BCA2024003", "Aditya Patel"),
    ("BCA2024004", "Vihaan Kumar"),
    ("BCA2024005", "Arjun Singh"),
    ("BCA2024006", "Sai Reddy"),
    ("BCA2024007", "Krishna Joshi"),
    ("BCA2024008", "Reyansh Mehta"),
    ("BCA2024009", "Atharv Gupta"),
    ("BCA2024010", "Advik Khan"),
    ("BCA2024011", "Ananya Malhotra"),
    ("BCA2024012", "Saanvi Jain"),
    ("BCA2024013", "Diya Bhatt"),
    ("BCA2024014", "Anika Nair"),
    ("BCA2024015", "Aadhya Desai"),
    ("BCA2024016", "Navya Iyer"),
    ("BCA2024017", "Pari Yadav"),
    ("BCA2024018", "Myra Agarwal"),
    ("BCA2024019", "Avni Bansal"),
    ("BCA2024020", "Kiara Chopra"),
    ("BCA2024021", "Rahul Das"),
    ("BCA2024022", "Priya Kapoor"),
    ("BCA2024023", "Amit Mishra"),
    ("BCA2024024", "Sneha Rao"),
    ("BCA2024025", "Vikram Saxena"),
    ("BCA2024026", "Anjali Thakur"),
    ("BCA2024027", "Rajesh Kaur"),
    ("BCA2024028", "Meera Mathur"),
    ("BCA2024029", "Karan Naik"),
    ("BCA2024030", "Neha Pandey"),
    ("BCA2024031", "Rohan Rathore"),
    ("BCA2024032", "Swati Seth"),
    ("BCA2024033", "Sanjay Trivedi"),
    ("BCA2024034", "Pooja Ahuja"),
    ("BCA2024035", "Deepak Bhardwaj"),
    ("BCA2024036", "Ritu Chaudhry"),
    ("BCA2024037", "Manoj Dubey"),
    ("BCA2024038", "Sunita Gokhale"),
    ("BCA2024039", "Vijay Kulkarni"),
    ("BCA2024040", "Lata Menon"),
    ("BCA2024041", "Raj Pillai"),
    ("BCA2024042", "Seema Sharma"),
    ("BCA2024043", "Anil Verma"),
    ("BCA2024044", "Kavita Patel"),
    ("BCA2024045", "Suresh Kumar"),
    ("BCA2024046", "Geeta Singh")
]

# Add students
print("✅ Adding 46 students with real names...")
student_ids = []

for roll_no, name in students_data:
    cursor.execute(
        "INSERT INTO students (roll_no, name, semester) VALUES (?, ?, ?)",
        (roll_no, name, 5)
    )
    student_ids.append(cursor.lastrowid)

# Get subject IDs
cursor.execute("SELECT id FROM subjects ORDER BY id")
subject_ids = [row[0] for row in cursor.fetchall()]

print("✅ Adding realistic marks for all students...")

# Add marks with realistic distribution
for i, student_id in enumerate(student_ids):
    for subject_id in subject_ids:
        # Create realistic mark distribution
        base_performance = (i % 10) + 1
        
        if base_performance <= 2:  # Top 20%
            marks = random.randint(85, 95)
        elif base_performance <= 5:  # Next 30%
            marks = random.randint(75, 84)
        elif base_performance <= 8:  # Next 30%
            marks = random.randint(60, 74)
        else:  # Bottom 20%
            marks = random.randint(40, 59)
        
        marks += random.randint(-5, 5)
        marks = max(35, min(100, marks))
        
        cursor.execute(
            "INSERT INTO marks (student_id, subject_id, marks) VALUES (?, ?, ?)",
            (student_id, subject_id, marks)
        )
    
    if (i + 1) % 10 == 0:
        print(f"   ✅ Added marks for {i + 1} students...")

conn.commit()
conn.close()

print("\n" + "="*50)
print("🎉 REAL STUDENT DATA ADDED SUCCESSFULLY!")
print("="*50)
print(f"👨‍🎓 Students: 46")
print(f"📚 Subjects: {len(subject_ids)}")
print(f"📝 Marks Entries: {46 * len(subject_ids)}")
print("\n📊 Performance Distribution:")
print("   • 20% Excellent (85-95 marks)")
print("   • 30% Very Good (75-84 marks)")
print("   • 30% Good (60-74 marks)")
print("   • 20% Average (40-59 marks)")
print("\n🚀 Run: python app.py")
print("🌐 Open: http://localhost:5001")
