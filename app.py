from flask import Flask, render_template, request, send_file
import sqlite3
import matplotlib.pyplot as plt
import io
import base64
from matplotlib import rcParams
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib import colors
from reportlab.lib.units import inch
import datetime

# Configure matplotlib
rcParams['font.family'] = 'Arial'
rcParams['font.size'] = 10

app = Flask(__name__)

def get_menu():
    """Returns the navigation menu HTML"""
    return '''
    <div class="menu">
        <a href="/">🏠 Home</a>
        <a href="/students">👨‍🎓 Students</a>
        <a href="/search">🔍 Search</a>
        <a href="/add_student">➕ Add Student</a>
        <a href="/enter_marks">📝 Enter Marks</a>
        <a href="/analysis">📊 Analysis</a>
    </div>
    '''

def get_instructions():
    """Returns instructions for each page"""
    return '''
    <div class="instructions">
        <h4>📋 How to Use This System:</h4>
        <p>1. <strong>Add Students</strong> first using the "Add Student" page</p>
        <p>2. <strong>Enter Marks</strong> for students in all 6 subjects</p>
        <p>3. <strong>View Results</strong> to see grades and percentages</p>
        <p>4. <strong>Download PDF</strong> of any student's result card</p>
        <p>5. <strong>Analyze Data</strong> using the Data Analysis Dashboard</p>
        <p>6. <strong>Search Students</strong> by name or roll number</p>
        <p><strong>Note:</strong> All data is stored in SQLite database</p>
    </div>
    '''

def get_subjects_info():
    """Returns BCA subjects information"""
    return '''
    <div class="subjects-info">
        <h4>📚 BCA 5th Semester Subjects:</h4>
        <p><strong>0527001</strong> - Java Programming</p>
        <p><strong>0527002</strong> - Computer Networks</p>
        <p><strong>0527003</strong> - Computer Graphics & Multimedia Applications</p>
        <p><strong>0527004</strong> - IT Trends & Technologies</p>
        <p><strong>0527065</strong> - Minor Project</p>
        <p><strong>0527080</strong> - Java & Computer Graphics Lab</p>
    </div>
    '''

def create_charts():
    """Generate charts for analysis page"""
    conn = sqlite3.connect('bca_results.db')
    cursor = conn.cursor()
    
    # Chart 1: Subject-wise Average Marks
    cursor.execute('''
        SELECT s.subject_name, AVG(m.marks) as avg_marks
        FROM marks m
        JOIN subjects s ON m.subject_id = s.id
        GROUP BY s.id
        ORDER BY avg_marks DESC
    ''')
    subject_data = cursor.fetchall()
    
    subjects = [row[0][:15] + '...' if len(row[0]) > 15 else row[0] for row in subject_data]
    averages = [row[1] for row in subject_data]
    
    # Create bar chart
    plt.figure(figsize=(10, 5))
    bars = plt.bar(subjects, averages, color=['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe'])
    plt.title('📚 Subject-wise Average Marks', fontsize=14, fontweight='bold')
    plt.xlabel('Subjects')
    plt.ylabel('Average Marks')
    plt.xticks(rotation=15)
    plt.ylim(0, 100)
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                f'{height:.1f}', ha='center', va='bottom', fontsize=9)
    
    # Save to base64
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight', dpi=100)
    img.seek(0)
    chart1_url = base64.b64encode(img.getvalue()).decode()
    plt.close()
    
    # Chart 2: Grade Distribution
    cursor.execute('''
        SELECT 
            CASE 
                WHEN marks >= 90 THEN 'O'
                WHEN marks >= 80 THEN 'A+'
                WHEN marks >= 70 THEN 'A'
                WHEN marks >= 60 THEN 'B+'
                WHEN marks >= 50 THEN 'B'
                WHEN marks >= 40 THEN 'P'
                ELSE 'F'
            END as grade,
            COUNT(*) as count
        FROM marks
        GROUP BY grade
        ORDER BY 
            CASE grade
                WHEN 'O' THEN 1
                WHEN 'A+' THEN 2
                WHEN 'A' THEN 3
                WHEN 'B+' THEN 4
                WHEN 'B' THEN 5
                WHEN 'P' THEN 6
                ELSE 7
            END
    ''')
    grade_data = cursor.fetchall()
    
    grades = [row[0] for row in grade_data]
    counts = [row[1] for row in grade_data]
    colors_list = ['#FFD700', '#4CAF50', '#2196F3', '#9C27B0', '#FF9800', '#795548', '#F44336']
    
    # Create pie chart
    plt.figure(figsize=(8, 6))
    plt.pie(counts, labels=grades, colors=colors_list, autopct='%1.1f%%', startangle=90)
    plt.title('📊 Grade Distribution', fontsize=14, fontweight='bold')
    plt.axis('equal')
    
    # Save to base64
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight', dpi=100)
    img.seek(0)
    chart2_url = base64.b64encode(img.getvalue()).decode()
    plt.close()
    
    conn.close()
    
    return chart1_url, chart2_url

def generate_pdf(student_id):
    """Generate PDF result card for a student"""
    conn = sqlite3.connect('bca_results.db')
    cursor = conn.cursor()
    
    # Get student data
    cursor.execute('SELECT roll_no, name, semester FROM students WHERE id=?', (student_id,))
    student = cursor.fetchone()
    
    if not student:
        conn.close()
        return None
    
    # Get marks data
    cursor.execute('''
        SELECT s.subject_code, s.subject_name, m.marks
        FROM marks m
        JOIN subjects s ON m.subject_id = s.id
        WHERE m.student_id = ?
        ORDER BY s.subject_code
    ''', (student_id,))
    
    marks = cursor.fetchall()
    conn.close()
    
    if not marks:
        return None
    
    # Calculate total and percentage
    total_marks = sum([m[2] for m in marks])
    percentage = (total_marks / (len(marks) * 100)) * 100
    
    # Determine grade
    if percentage >= 90:
        grade = 'O (Outstanding)'
        grade_color = colors.gold
    elif percentage >= 80:
        grade = 'A+ (Excellent)'
        grade_color = colors.green
    elif percentage >= 70:
        grade = 'A (Very Good)'
        grade_color = colors.blue
    elif percentage >= 60:
        grade = 'B+ (Good)'
        grade_color = colors.purple
    elif percentage >= 50:
        grade = 'B (Above Average)'
        grade_color = colors.orange
    elif percentage >= 45:
        grade = 'C (Average)'
        grade_color = colors.brown
    elif percentage >= 40:
        grade = 'P (Pass)'
        grade_color = colors.grey
    else:
        grade = 'F (Fail)'
        grade_color = colors.red
    
    # Create PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, 
                          rightMargin=72, leftMargin=72,
                          topMargin=72, bottomMargin=72)
    
    # Create styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=12
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6
    )
    
    # Build PDF content
    story = []
    
    # Title
    story.append(Paragraph("🎓 ALPINE COLLEGE OF EDUCATION", title_style))
    story.append(Paragraph("BCA 5th Semester - Result Card", styles['Heading2']))
    story.append(Spacer(1, 20))
    
    # Student Information
    story.append(Paragraph(f"<b>Student Name:</b> {student[1]}", normal_style))
    story.append(Paragraph(f"<b>Roll Number:</b> {student[0]}", normal_style))
    story.append(Paragraph(f"<b>Semester:</b> {student[2]}", normal_style))
    story.append(Paragraph(f"<b>Date Generated:</b> {datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}", normal_style))
    story.append(Spacer(1, 20))
    
    # Marks Table
    story.append(Paragraph("<b>Subject-wise Marks:</b>", header_style))
    
    # Table data
    table_data = [['Subject Code', 'Subject Name', 'Marks Obtained', 'Max Marks']]
    for subject_code, subject_name, mark in marks:
        table_data.append([subject_code, subject_name, str(mark), '100'])
    
    # Create table
    marks_table = Table(table_data, colWidths=[1.5*inch, 3*inch, 1.5*inch, 1.2*inch])
    marks_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
    ]))
    
    story.append(marks_table)
    story.append(Spacer(1, 30))
    
    # Result Summary
    story.append(Paragraph("<b>Result Summary:</b>", header_style))
    
    summary_data = [
        ['Total Subjects', f'{len(marks)} out of 6'],
        ['Total Marks Obtained', f'{total_marks} / {len(marks) * 100}'],
        ['Percentage', f'{percentage:.2f}%'],
        ['Grade', grade],
        ['Status', 'PASS' if percentage >= 40 else 'FAIL']
    ]
    
    summary_table = Table(summary_data, colWidths=[2.5*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 30))
    
    # Footer
    story.append(Paragraph("<i>This is a computer-generated result card. No signature required.</i>", 
                          ParagraphStyle('Footer', parent=styles['Italic'], fontSize=9, textColor=colors.grey)))
    story.append(Paragraph("<i>© Alpine College of Education - BCA Department</i>", 
                          ParagraphStyle('Footer', parent=styles['Italic'], fontSize=9, textColor=colors.grey)))
    
    # Build PDF
    doc.build(story)
    
    buffer.seek(0)
    return buffer

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>BCA Result System</title>
        <style>
           body {
    font-family: Arial;
    margin: 40px;
    background-image: url("/static/background.png");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}

            .header {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px;}
            .menu {margin: 20px 0;}
            .menu a {display: inline-block; margin: 10px; padding: 12px 20px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;}
            .container {background: white; padding: 25px; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1);}
            .instructions, .subjects-info {background: #f0f8ff; padding: 15px; border-radius: 8px; margin: 15px 0;}
            .card {background: white; padding: 20px; border-radius: 10px; box-shadow: 0 3px 10px rgba(0,0,0,0.1); margin: 15px 0;}
            .feature-grid {display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin: 25px 0;}
            .feature-card {background: white; padding: 20px; border-radius: 10px; box-shadow: 0 3px 10px rgba(0,0,0,0.1); text-align: center;}
            .pdf-badge {background: #e74c3c; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; margin-left: 10px;}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎓 BCA Result Management System <span class="pdf-badge">PDF Export</span></h1>
            <p>Alpine College of Education - 5th Semester</p>
        </div>
        
        ''' + get_menu() + '''
        
        <div class="container">
            <h2>Welcome to Result Management System</h2>
            
            ''' + get_subjects_info() + '''
            
            <h3>📱 System Features:</h3>
            <div class="feature-grid">
                <div class="feature-card">
                    <h4>👨‍🎓 Student Management</h4>
                    <p>Manage 46 students with real names</p>
                </div>
                <div class="feature-card">
                    <h4>📊 Data Analysis</h4>
                    <p>Charts & statistics for performance</p>
                </div>
                <div class="feature-card">
                    <h4>📄 PDF Export</h4>
                    <p>Download result cards as PDF</p>
                </div>
                <div class="feature-card">
                    <h4>🔍 Smart Search</h4>
                    <p>Find students instantly</p>
                </div>
            </div>
            
            <h3>🚀 Quick Access:</h3>
            <div class="card">
                <h4>1. View All Students</h4>
                <p>Click "👨‍🎓 Students" to see all 46 students with result cards</p>
                <p><strong>NEW:</strong> Each student has a "📄 Download PDF" button!</p>
            </div>
            
            <div class="card">
                <h4>2. Search Students</h4>
                <p>Click "🔍 Search" to find students by name or roll number</p>
            </div>
            
            <div class="card">
                <h4>3. Data Analysis</h4>
                <p>Click "📊 Analysis" to see charts and statistics</p>
            </div>
            
            <div class="card">
                <h4>4. Enter Marks</h4>
                <p>Click "📝 Enter Marks" to add/update student marks</p>
            </div>
            
            ''' + get_instructions() + '''
        </div>
        
        <div style="margin-top: 30px; color: #666; font-size: 14px;">
            <hr>
            <p>BCA 5th Semester Project • Alpine College of Education • Data Analyst Project</p>
            <p>📊 Now with Charts, Search & PDF Export Features!</p>
        </div>
    </body>
    </html>
    '''

@app.route('/students')
def view_students():
    conn = sqlite3.connect('bca_results.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM students')
    students = cursor.fetchall()
    conn.close()
    
    student_rows = ""
    for student in students:
        student_rows += f"""
        <tr>
            <td>{student[0]}</td>
            <td>{student[1]}</td>
            <td>{student[2]}</td>
            <td>{student[3]}</td>
            <td>
                <a href='/view_result/{student[0]}' style='color: #2196F3; margin-right: 10px;'>👁️ View Result</a>
                <a href='/download_pdf/{student[0]}' style='color: #e74c3c;'>📄 Download PDF</a>
            </td>
        </tr>
        """
    
    html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>Students List</title>
    <style>
        body{{
    font-family: Arial;
    margin: 40px;
    background-image: url("/static/background.png");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}
        .header {{background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px;}}
        .menu {{margin: 20px 0;}}
        .menu a {{display: inline-block; margin: 10px; padding: 12px 20px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;}}
        .container {{background: white; padding: 25px; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1);}}
        table {{width: 100%; border-collapse: collapse; margin: 20px 0;}}
        th, td {{border: 1px solid #ddd; padding: 10px; text-align: left;}}
        th {{background: #4CAF50; color: white;}}
        .instructions {{background: #f0f8ff; padding: 15px; border-radius: 8px; margin: 15px 0;}}
        .stats {{background: #e8f5e9; padding: 15px; border-radius: 8px; margin: 15px 0;}}
        .pdf-btn {{background: #e74c3c; color: white; padding: 8px 15px; border-radius: 5px; text-decoration: none; font-size: 14px;}}
        .pdf-btn:hover {{background: #c0392b;}}
    </style>
</head>
<body>
    <div class="header">
        <h1>👨‍🎓 Students List <span style="background: #e74c3c; color: white; padding: 5px 10px; border-radius: 15px; font-size: 14px;">PDF READY</span></h1>
        <p>BCA 5th Semester - All Registered Students (Click 📄 to download PDF)</p>
    </div>
    
    {get_menu()}
    
    <div class="container">
        <div class="stats">
            <h3>📊 Quick Stats</h3>
            <p><strong>Total Students:</strong> {len(students)}</p>
            <p><strong>New Feature:</strong> Download any student's result as PDF!</p>
            <p><strong>Need to find a specific student?</strong> Use the <a href="/search" style="color: #2196F3; font-weight: bold;">🔍 Search</a> feature!</p>
        </div>
        
        <h2>Registered Students</h2>
        
        <table>
            <tr>
                <th>ID</th>
                <th>Roll No</th>
                <th>Name</th>
                <th>Semester</th>
                <th>Actions</th>
            </tr>
            {student_rows}
        </table>
        
        <div style="background: #fff8e1; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <h4>📄 PDF Export Instructions:</h4>
            <p>1. Click <strong>"📄 Download PDF"</strong> next to any student</p>
            <p>2. PDF will download automatically</p>
            <p>3. Print or save the professional result card</p>
            <p>4. PDF includes all subject marks, percentage, grade, and college branding</p>
        </div>
        
        {get_instructions()}
        {get_subjects_info()}
        
        <br>
        <a href="/" style="padding: 10px 20px; background: #2196F3; color: white; text-decoration: none; border-radius: 5px;">← Back to Home</a>
    </div>
</body>
</html>'''
    
    return html_content

@app.route('/download_pdf/<int:student_id>')
def download_pdf(student_id):
    """Download student result as PDF"""
    pdf_buffer = generate_pdf(student_id)
    
    if pdf_buffer:
        # Get student name for filename
        conn = sqlite3.connect('bca_results.db')
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM students WHERE id=?', (student_id,))
        student_name = cursor.fetchone()[0]
        conn.close()
        
        # Clean filename
        filename = f"Result_{student_name.replace(' ', '_')}.pdf"
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    else:
        return '''
        <div style="text-align: center; padding: 50px;">
            <h2>PDF Generation Failed</h2>
            <p>Student data not found or marks not available.</p>
            <p><a href="/students" style="color: #2196F3;">Back to Students</a> | <a href="/" style="color: #2196F3;">Home</a></p>
        </div>
        '''

@app.route('/search', methods=['GET', 'POST'])
def search_students():
    search_results = ""
    search_query = ""
    
    if request.method == 'POST':
        search_query = request.form['search_query']
        
        conn = sqlite3.connect('bca_results.db')
        cursor = conn.cursor()
        
        # Search in name and roll number
        cursor.execute('''
            SELECT * FROM students 
            WHERE name LIKE ? OR roll_no LIKE ?
            ORDER BY name
        ''', (f'%{search_query}%', f'%{search_query}%'))
        
        students = cursor.fetchall()
        conn.close()
        
        if students:
            search_results = "<h3>🔍 Search Results:</h3>"
            search_results += f"<p>Found {len(students)} student(s) for '{search_query}'</p>"
            search_results += '<table><tr><th>ID</th><th>Roll No</th><th>Name</th><th>Semester</th><th>Actions</th></tr>'
            
            for student in students:
                search_results += f'''
                <tr>
                    <td>{student[0]}</td>
                    <td>{student[1]}</td>
                    <td>{student[2]}</td>
                    <td>{student[3]}</td>
                    <td>
                        <a href="/view_result/{student[0]}" style="color: #2196F3; margin-right: 10px;">👁️ View</a>
                        <a href="/download_pdf/{student[0]}" style="color: #e74c3c;">📄 PDF</a>
                    </td>
                </tr>
                '''
            
            search_results += '</table>'
        else:
            search_results = f'<div class="alert" style="background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0;">No students found for "{search_query}"</div>'
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Search Students</title>
        <style>
             body {{
    font-family: Arial;
    margin: 40px;
    background-image: url("/static/background.png");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}
            .header {{background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px;}}
            .menu {{margin: 20px 0;}}
            .menu a {{display: inline-block; margin: 10px; padding: 12px 20px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;}}
            .container {{background: white; padding: 25px; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1);}}
            .search-box {{background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;}}
            input[type="text"] {{width: 70%; padding: 12px; border: 2px solid #ddd; border-radius: 5px; font-size: 16px;}}
            input[type="submit"] {{padding: 12px 30px; background: #2196F3; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px;}}
            table {{width: 100%; border-collapse: collapse; margin: 20px 0;}}
            th, td {{border: 1px solid #ddd; padding: 10px; text-align: left;}}
            th {{background: #4CAF50; color: white;}}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔍 Search Students</h1>
            <p>BCA 5th Semester - Find Students by Name or Roll Number</p>
        </div>
        
        {get_menu()}
        
        <div class="container">
            <div class="search-box">
                <h3>Search Student Database</h3>
                <form method="POST">
                    <input type="text" name="search_query" value="{search_query}" placeholder="Enter student name or roll number..." required>
                    <input type="submit" value="Search">
                </form>
                <p style="color: #666; margin-top: 10px;">Search by: Name (e.g., "Aarav") or Roll No (e.g., "BCA2024001")</p>
            </div>
            
            {search_results}
            
            <br>
            <a href="/students" style="padding: 10px 20px; background: #2196F3; color: white; text-decoration: none; border-radius: 5px;">← Back to All Students</a>
        </div>
    </body>
    </html>
    '''

# [The rest of your routes remain EXACTLY THE SAME - add_student, enter_marks, view_result, analysis]
# Just copy all your existing routes from your current app.py (excluding home, students, search, download_pdf)

# Continue with your existing add_student route (copy from your current app.py)
@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        roll_no = request.form['roll_no']
        name = request.form['name']
        
        conn = sqlite3.connect('bca_results.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO students (roll_no, name, semester) VALUES (?, ?, 5)', (roll_no, name))
        conn.commit()
        conn.close()
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Success</title>
            <style>
                body {{
    font-family: Arial;
    margin: 40px;
    background-image: url("/static/background.png");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}
                .success-box {{background: white; padding: 40px; border-radius: 10px; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.1); max-width: 500px; margin: auto;}}
            </style>
        </head>
        <body>
            <div class="success-box">
                <h2 style="color: #4CAF50;">✅ Student Added Successfully!</h2>
                <p><strong>Name:</strong> {name}</p>
                <p><strong>Roll No:</strong> {roll_no}</p>
                <p><strong>Semester:</strong> BCA 5th</p>
                
                <div style="margin: 30px 0;">
                    <a href="/add_student" style="padding: 10px 20px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">Add Another Student</a>
                    <a href="/enter_marks" style="padding: 10px 20px; background: #2196F3; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">Enter Marks</a>
                    <a href="/" style="padding: 10px 20px; background: #666; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">Home</a>
                </div>
                
                <div style="background: #f0f8ff; padding: 15px; border-radius: 8px; margin-top: 20px;">
                    <h4>Next Steps:</h4>
                    <p>1. Add more students if needed</p>
                    <p>2. Enter marks for this student in all 6 subjects</p>
                    <p>3. View the student's result</p>
                    <p>4. Download PDF result card</p>
                </div>
            </div>
        </body>
        </html>
        '''
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Add Student</title>
        <style>
            body {{
    font-family: Arial;
    margin: 40px;
    background-image: url("/static/background.png");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}
            .header {{background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px;}}
            .menu {{margin: 20px 0;}}
            .menu a {{display: inline-block; margin: 10px; padding: 12px 20px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;}}
            .container {{background: white; padding: 30px; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); max-width: 500px; margin: auto;}}
            form {{margin-top: 20px;}}
            label {{display: block; margin: 15px 0 5px; font-weight: bold;}}
            input[type="text"] {{width: 100%; padding: 10px; margin: 5px 0 20px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box;}}
            input[type="submit"] {{background: #4CAF50; color: white; padding: 12px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px;}}
            input[type="submit"]:hover {{background: #45a049;}}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>➕ Add New Student</h1>
            <p>BCA 5th Semester - Register New Student</p>
        </div>
        
        ''' + get_menu() + '''
        
        <div class="container">
            <h2>Add Student Form</h2>
            
            <form method="POST">
                <label for="roll_no">Roll Number:</label>
                <input type="text" name="roll_no" id="roll_no" placeholder="e.g., BCA2024001" required>
                
                <label for="name">Student Name:</label>
                <input type="text" name="name" id="name" placeholder="e.g., Rahul Sharma" required>
                
                <input type="submit" value="Add Student">
            </form>
            
            ''' + get_instructions() + get_subjects_info() + '''
            
            <br>
            <a href="/" style="color: #2196F3; text-decoration: none;">← Back to Home</a>
        </div>
    </body>
    </html>
    '''

# Continue with your existing enter_marks route (copy from your current app.py)
@app.route('/enter_marks', methods=['GET', 'POST'])
def enter_marks():
    conn = sqlite3.connect('bca_results.db')
    cursor = conn.cursor()
    
    if request.method == 'POST':
        student_id = request.form['student_id']
        subject_id = request.form['subject_id']
        marks = int(request.form['marks'])
        
        cursor.execute('SELECT id FROM marks WHERE student_id=? AND subject_id=?', (student_id, subject_id))
        
        if cursor.fetchone():
            cursor.execute('UPDATE marks SET marks=? WHERE student_id=? AND subject_id=?', 
                          (marks, student_id, subject_id))
            message = "✅ Marks updated successfully!"
        else:
            cursor.execute('INSERT INTO marks (student_id, subject_id, marks) VALUES (?, ?, ?)', 
                          (student_id, subject_id, marks))
            message = "✅ Marks entered successfully!"
        
        conn.commit()
        conn.close()
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Success</title>
            <style>
                body {{
    font-family: Arial;
    margin: 40px;
    background-image: url("/static/background.png");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}
                .success-box {{background: white; padding: 40px; border-radius: 10px; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.1); max-width: 500px; margin: auto;}}
            </style>
        </head>
        <body>
            <div class="success-box">
                <h2 style="color: #4CAF50;">{message}</h2>
                
                <div style="margin: 30px 0;">
                    <a href="/enter_marks" style="padding: 10px 20px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">Enter More Marks</a>
                    <a href="/students" style="padding: 10px 20px; background: #2196F3; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">View Students</a>
                    <a href="/" style="padding: 10px 20px; background: #666; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">Home</a>
                </div>
                
                <div style="background: #f0f8ff; padding: 15px; border-radius: 8px; margin-top: 20px;">
                    <h4>Next Steps:</h4>
                    <p>1. Enter marks for other subjects</p>
                    <p>2. Check student's result</p>
                    <p>3. View data analysis for insights</p>
                    <p>4. Download PDF result card</p>
                </div>
            </div>
        </body>
        </html>
        '''
    
    cursor.execute('SELECT id, roll_no, name FROM students ORDER BY name')
    students = cursor.fetchall()
    
    cursor.execute('SELECT id, subject_code, subject_name FROM subjects ORDER BY subject_code')
    subjects = cursor.fetchall()
    
    conn.close()
    
    student_options = ""
    for student in students:
        student_options += f'<option value="{student[0]}">{student[1]} - {student[2]}</option>'
    
    subject_options = ""
    for subject in subjects:
        subject_options += f'<option value="{subject[0]}">{subject[1]} - {subject[2]}</option>'
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Enter Marks</title>
        <style>
            body {{
    font-family: Arial;
    margin: 40px;
    background-image: url("/static/background.png");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}
            .header {{background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px;}}
            .menu {{margin: 20px 0;}}
            .menu a {{display: inline-block; margin: 10px; padding: 12px 20px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;}}
            .container {{background: white; padding: 30px; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); max-width: 600px; margin: auto;}}
            form {{margin-top: 20px;}}
            label {{display: block; margin: 15px 0 5px; font-weight: bold;}}
            select, input[type="number"] {{width: 100%; padding: 10px; margin: 5px 0 20px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box;}}
            input[type="submit"] {{background: #4CAF50; color: white; padding: 12px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px;}}
            input[type="submit"]:hover {{background: #45a049;}}
            .instructions {{background: #f0f8ff; padding: 15px; border-radius: 8px; margin: 20px 0;}}
            .subjects-list {{background: #f9f9f9; padding: 15px; border-radius: 8px; margin: 20px 0;}}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📝 Enter Student Marks</h1>
            <p>BCA 5th Semester - All 6 Subjects</p>
        </div>
        
        ''' + get_menu() + '''
        
        <div class="container">
            <h2>Enter Marks Form</h2>
            
            <form method="POST">
                <label for="student">Select Student:</label>
                <select name="student_id" id="student" required>
                    <option value="">-- Select Student --</option>
                    {student_options}
                </select>
                
                <label for="subject">Select Subject:</label>
                <select name="subject_id" id="subject" required>
                    <option value="">-- Select Subject --</option>
                    {subject_options}
                </select>
                
                <label for="marks">Enter Marks (0-100):</label>
                <input type="number" name="marks" id="marks" min="0" max="100" placeholder="Enter marks between 0-100" required>
                
                <input type="submit" value="Save Marks">
            </form>
            
            ''' + get_instructions() + get_subjects_info() + '''
            
            <br>
            <a href="/" style="color: #2196F3; text-decoration: none;">← Back to Home</a>
        </div>
    </body>
    </html>
    '''

# Continue with your existing view_result route (copy from your current app.py)
# BUT add PDF download button at the bottom

@app.route('/view_result/<int:student_id>')
def view_result(student_id):
    conn = sqlite3.connect('bca_results.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT roll_no, name, semester FROM students WHERE id=?', (student_id,))
    student = cursor.fetchone()
    
    if not student:
        conn.close()
        return '''
        <div style="text-align: center; padding: 50px;">
            <h2>Student not found</h2>
            <p><a href="/students" style="color: #2196F3;">View Students</a> | <a href="/" style="color: #2196F3;">Home</a></p>
        </div>
        '''
    
    cursor.execute('''
        SELECT s.subject_code, s.subject_name, m.marks
        FROM marks m
        JOIN subjects s ON m.subject_id = s.id
        WHERE m.student_id = ?
        ORDER BY s.subject_code
    ''', (student_id,))
    
    marks = cursor.fetchall()
    conn.close()
    
    if not marks:
        return f'''
        <div style="text-align: center; padding: 50px;">
            <h2>No marks found for {student[1]}</h2>
            <p>Please enter marks for this student first.</p>
            <p><a href="/enter_marks" style="color: #2196F3;">Enter Marks</a> | <a href="/" style="color: #2196F3;">Home</a></p>
        </div>
        '''
    
    total_marks = sum([m[2] for m in marks])
    percentage = (total_marks / (len(marks) * 100)) * 100
    
    if percentage >= 90:
        grade = 'O (Outstanding)'
        grade_color = '#FFD700'
    elif percentage >= 80:
        grade = 'A+ (Excellent)'
        grade_color = '#4CAF50'
    elif percentage >= 70:
        grade = 'A (Very Good)'
        grade_color = '#2196F3'
    elif percentage >= 60:
        grade = 'B+ (Good)'
        grade_color = '#9C27B0'
    elif percentage >= 50:
        grade = 'B (Above Average)'
        grade_color = '#FF9800'
    elif percentage >= 45:
        grade = 'C (Average)'
        grade_color = '#795548'
    elif percentage >= 40:
        grade = 'P (Pass)'
        grade_color = '#607D8B'
    else:
        grade = 'F (Fail)'
        grade_color = '#F44336'
    
    marks_table = ""
    for subject_code, subject_name, mark in marks:
        marks_table += f'<tr><td>{subject_code}<br><small>{subject_name}</small></td><td>{mark}</td><td>100</td></tr>'
    
    html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>Student Result</title>
    <style>
        body {{
    font-family: Arial;
    margin: 40px;
    background-image: url("/static/background.png");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}
        .header {{background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 15px 15px 0 0;}}
        .menu {{margin: 20px 0;}}
        .menu a {{display: inline-block; margin: 10px; padding: 12px 20px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;}}
        .result-card {{background: white; padding: 30px; border-radius: 0 0 15px 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1);}}
        table {{width: 100%; border-collapse: collapse; margin: 25px 0;}}
        th, td {{border: 1px solid #ddd; padding: 12px; text-align: left;}}
        th {{background: #f8f9fa;}}
        .total-box {{background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 25px 0; border-left: 5px solid #4CAF50;}}
        .grade {{font-size: 28px; font-weight: bold; padding: 10px; border-radius: 8px; display: inline-block;}}
        .btn {{display: inline-block; padding: 12px 25px; background: #2196F3; color: white; text-decoration: none; border-radius: 8px; margin: 10px 5px;}}
        .pdf-btn {{background: #e74c3c; color: white; padding: 12px 25px; border-radius: 8px; text-decoration: none; display: inline-block;}}
        .pdf-btn:hover {{background: #c0392b;}}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎓 Student Result Card</h1>
        <p>Alpine College of Education • BCA 5th Semester • All 6 Subjects</p>
    </div>
    
    {get_menu()}
    
    <div class="result-card">
        <h2>{student[1]} <span style="color: #666;">(Roll No: {student[0]})</span></h2>
        <p><strong>Semester:</strong> {student[2]}</p>
        
        <h3>📚 Subject-wise Marks:</h3>
        <table>
            <tr>
                <th>Subject (Code)</th>
                <th>Marks Obtained</th>
                <th>Maximum Marks</th>
            </tr>
            {marks_table}
        </table>
        
        <div class="total-box">
            <h3>📊 Result Summary</h3>
            <p><strong>Total Subjects:</strong> {len(marks)} out of 6</p>
            <p><strong>Total Marks Obtained:</strong> {total_marks} / {len(marks) * 100}</p>
            <p><strong>Percentage:</strong> <span style="font-size: 24px; font-weight: bold;">{percentage:.2f}%</span></p>
            <p><strong>Grade:</strong> <span class="grade" style="background-color: {grade_color}; color: white;">{grade}</span></p>
            <p><strong>Status:</strong> <span style="color: {'#4CAF50' if percentage >= 40 else '#F44336'}; font-weight: bold; font-size: 20px;">{'PASS' if percentage >= 40 else 'FAIL'}</span></p>
        </div>
        
        <div style="background: #e8f4f8; padding: 20px; border-radius: 10px; margin: 25px 0;">
            <h3>📄 Download Result Card</h3>
            <p>Click the button below to download a professional PDF version of this result card:</p>
            <a href="/download_pdf/{student_id}" class="pdf-btn">
                📄 Download PDF Result Card
            </a>
            <p style="color: #666; font-size: 14px; margin-top: 10px;">
                PDF includes: All subject marks, percentage, grade, college branding, and date stamp.
            </p>
        </div>
        
        <div style="text-align: center; margin-top: 30px;">
            <a href="/students" class="btn">← Back to Students</a>
            <a href="/" class="btn">🏠 Home</a>
            <a href="/enter_marks" class="btn">📝 Enter More Marks</a>
            <a href="/analysis" class="btn">📊 View Analysis</a>
        </div>
    </div>
</body>
</html>'''
    
    return html_content

# Continue with your existing analysis route (copy from your current app.py)
@app.route('/analysis')
def data_analysis():
    conn = sqlite3.connect('bca_results.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            COUNT(DISTINCT s.id) as total_students,
            COUNT(m.id) as total_marks_entries,
            AVG(m.marks) as avg_marks,
            MAX(m.marks) as highest_mark,
            MIN(m.marks) as lowest_mark,
            SUM(CASE WHEN m.marks >= 40 THEN 1 ELSE 0 END) * 100.0 / COUNT(m.id) as pass_percentage
        FROM students s
        LEFT JOIN marks m ON s.id = m.student_id
    ''')
    overall_stats = cursor.fetchone()
    
    cursor.execute('''
        SELECT 
            sub.subject_code,
            sub.subject_name,
            COUNT(m.id) as total_students,
            AVG(m.marks) as avg_marks,
            MAX(m.marks) as highest,
            MIN(m.marks) as lowest,
            SUM(CASE WHEN m.marks >= 40 THEN 1 ELSE 0 END) as passed,
            COUNT(m.id) as total
        FROM subjects sub
        LEFT JOIN marks m ON sub.id = m.subject_id
        GROUP BY sub.id
        ORDER BY sub.subject_code
    ''')
    subject_stats = cursor.fetchall()
    
    cursor.execute('''
        SELECT 
            s.name,
            s.roll_no,
            AVG(m.marks) as avg_marks,
            SUM(m.marks) as total_marks
        FROM students s
        JOIN marks m ON s.id = m.student_id
        GROUP BY s.id
        ORDER BY avg_marks DESC
        LIMIT 5
    ''')
    top_students = cursor.fetchall()
    
    cursor.execute('''
        SELECT 
            CASE 
                WHEN marks >= 90 THEN 'O (90-100)'
                WHEN marks >= 80 THEN 'A+ (80-89)'
                WHEN marks >= 70 THEN 'A (70-79)'
                WHEN marks >= 60 THEN 'B+ (60-69)'
                WHEN marks >= 50 THEN 'B (50-59)'
                WHEN marks >= 45 THEN 'C (45-49)'
                WHEN marks >= 40 THEN 'P (40-44)'
                ELSE 'F (Below 40)'
            END as grade_range,
            COUNT(*) as count,
            COUNT(*) * 100.0 / (SELECT COUNT(*) FROM marks) as percentage
        FROM marks
        GROUP BY grade_range
        ORDER BY 
            CASE grade_range
                WHEN 'O (90-100)' THEN 1
                WHEN 'A+ (80-89)' THEN 2
                WHEN 'A (70-79)' THEN 3
                WHEN 'B+ (60-69)' THEN 4
                WHEN 'B (50-59)' THEN 5
                WHEN 'C (45-49)' THEN 6
                WHEN 'P (40-44)' THEN 7
                ELSE 8
            END
    ''')
    grade_distribution = cursor.fetchall()
    
    conn.close()
    
    # Generate charts
    chart1_url, chart2_url = create_charts()
    
    subject_table = ""
    for subject in subject_stats:
        pass_rate = (subject[6] / subject[7] * 100) if subject[7] > 0 else 0
        subject_table += f'''
        <tr>
            <td>{subject[0]}<br><small>{subject[1]}</small></td>
            <td>{subject[2]}</td>
            <td>{subject[3]:.1f}</td>
            <td>{subject[4]}</td>
            <td>{subject[5]}</td>
            <td>{pass_rate:.1f}%</td>
        </tr>
        '''
    
    top_students_table = ""
    for rank, student in enumerate(top_students, 1):
        top_students_table += f'''
        <tr>
            <td>{rank}</td>
            <td>{student[1]}</td>
            <td>{student[0]}</td>
            <td>{student[2]:.1f}</td>
            <td>{student[3]}</td>
        </tr>
        '''
    
    grade_table = ""
    for grade in grade_distribution:
        grade_table += f'''
        <tr>
            <td>{grade[0]}</td>
            <td>{grade[1]}</td>
            <td>{grade[2]:.1f}%</td>
        </tr>
        '''
    
    html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>Data Analysis</title>
    <style>
        body {{
    font-family: Arial;
    margin: 40px;
    background-image: url("/static/background.png");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}
        .header {{background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px;}}
        .menu {{margin: 20px 0;}}
        .menu a {{display: inline-block; margin: 10px; padding: 12px 20px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;}}
        .container {{background: white; padding: 25px; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1);}}
        .stats-grid {{display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin: 25px 0;}}
        .stat-card {{background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px;}}
        table {{width: 100%; border-collapse: collapse; margin: 20px 0;}}
        th, td {{border: 1px solid #ddd; padding: 10px; text-align: left;}}
        th {{background: #4CAF50; color: white;}}
        .instructions {{background: #f0f8ff; padding: 15px; border-radius: 8px; margin: 15px 0;}}
        .chart-container {{display: flex; flex-wrap: wrap; gap: 20px; margin: 30px 0;}}
        .chart-box {{flex: 1; min-width: 300px; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 3px 10px rgba(0,0,0,0.1);}}
        .pdf-feature {{background: #ffeaa7; padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 5px solid #e74c3c;}}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Data Analysis Dashboard</h1>
        <p>BCA 5th Semester - Performance Statistics & Insights</p>
    </div>
    
    {get_menu()}
    
    <div class="container">
        <div class="pdf-feature">
            <h3>📄 NEW: PDF Export Feature!</h3>
            <p>Now you can download professional PDF result cards for any student!</p>
            <p>Visit <a href="/students" style="color: #2196F3; font-weight: bold;">Students Page</a> and click "📄 Download PDF" next to any student.</p>
        </div>
        
        <h2>📈 Overall Statistics</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <h3>👨‍🎓 Total Students</h3>
                <p style="font-size: 36px; margin: 10px 0;">{overall_stats[0] or 0}</p>
            </div>
            <div class="stat-card">
                <h3>📝 Total Marks Entries</h3>
                <p style="font-size: 36px; margin: 10px 0;">{overall_stats[1] or 0}</p>
            </div>
            <div class="stat-card">
                <h3>📊 Average Marks</h3>
                <p style="font-size: 36px; margin: 10px 0;">{overall_stats[2] or 0:.1f}</p>
            </div>
            <div class="stat-card">
                <h3>🏆 Pass Percentage</h3>
                <p style="font-size: 36px; margin: 10px 0;">{overall_stats[5] or 0:.1f}%</p>
            </div>
        </div>
        
        <h2>📊 Visual Analysis</h2>
        <div class="chart-container">
            <div class="chart-box">
                <h3>📚 Subject Performance</h3>
                <img src="data:image/png;base64,{chart1_url}" style="width: 100%; border-radius: 5px;">
                <p style="text-align: center; color: #666; font-size: 12px; margin-top: 10px;">
                    Average marks across all 6 subjects
                </p>
            </div>
            
            <div class="chart-box">
                <h3>🎯 Grade Distribution</h3>
                <img src="data:image/png;base64,{chart2_url}" style="width: 100%; border-radius: 5px;">
                <p style="text-align: center; color: #666; font-size: 12px; margin-top: 10px;">
                    Overall grade distribution of all students
                </p>
            </div>
        </div>
        
        <h2>📚 Subject-wise Analysis</h2>
        <table>
            <tr>
                <th>Subject</th>
                <th>Students</th>
                <th>Average</th>
                <th>Highest</th>
                <th>Lowest</th>
                <th>Pass Rate</th>
            </tr>
            {subject_table}
        </table>
        
        <h2>🏆 Top 5 Students</h2>
        <table>
            <tr>
                <th>Rank</th>
                <th>Roll No</th>
                <th>Name</th>
                <th>Average</th>
                <th>Total Marks</th>
            </tr>
            {top_students_table}
        </table>
        
        <h2>📊 Grade Distribution</h2>
        <table>
            <tr>
                <th>Grade Range</th>
                <th>Count</th>
                <th>Percentage</th>
            </tr>
            {grade_table}
        </table>
        
        {get_instructions()}
        {get_subjects_info()}
        
        <br>
        <a href="/" style="padding: 10px 20px; background: #2196F3; color: white; text-decoration: none; border-radius: 5px;">← Back to Home</a>
    </div>
</body>
</html>'''
    
    return html_content

if __name__ == '__main__':
    app.run(debug=True, port=5001)