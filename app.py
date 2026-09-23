import os
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Актуальные даты четвертей Беларуси на 2026/2027 учебный год
QUARTERS = {
    1: ('2026-09-01', '2026-10-31'),
    2: ('2026-11-09', '2026-12-24'),
    3: ('2027-01-11', '2027-03-27'),
    4: ('2027-04-05', '2027-05-29')
}

DAY_MAP = {
    'пн': 0, 'вт': 1, 'ср': 2, 'чт': 3, 'пт': 4, 'сб': 5,
    'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5,
    '1': 0, '2': 1, '3': 2, '4': 3, '5': 4, '6': 5
}

DB_PATH = os.path.join(os.path.dirname(__file__), 'journal.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS class_subjects (
        class_id INTEGER, subject_id INTEGER,
        PRIMARY KEY (class_id, subject_id),
        FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE,
        FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT, class_id INTEGER,
        FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS lessons (
        id INTEGER PRIMARY KEY AUTOINCREMENT, class_id INTEGER, subject_id INTEGER,
        date_str TEXT, full_date TEXT, quarter INTEGER, topic TEXT, homework TEXT, work_type TEXT,
        FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE,
        FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE
    )''')
    
    # Проверка на наличие колонки homework для старых баз
    cursor.execute("PRAGMA table_info(lessons)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'homework' not in columns:
        cursor.execute("ALTER TABLE lessons ADD COLUMN homework TEXT DEFAULT ''")
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS grades (
        id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER, lesson_id INTEGER, val TEXT,
        FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
        FOREIGN KEY(lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
    )''')
    
    cursor.execute("SELECT COUNT(*) FROM classes")
    if cursor.fetchone()[0] == 0:
        classes = ['6 "А"', '6 "Б"', '7 "А"', '7 "Б"', '8 "А"', '8 "Б"', '9 "А"', '9 "Б"', '10 "А"', '10 "Б"']
        for c in classes:
            cursor.execute("INSERT INTO classes (name) VALUES (?)", (c,))
            
        subjects = ['Информатика', 'Математика', 'Физика', 'Английский язык']
        for s in subjects:
            cursor.execute("INSERT INTO subjects (name) VALUES (?)", (s,))
            
        cursor.execute("SELECT id FROM classes")
        c_ids = [r[0] for r in cursor.fetchall()]
        cursor.execute("SELECT id FROM subjects")
        s_ids = [r[0] for r in cursor.fetchall()]
        for cid in c_ids:
            for sid in s_ids:
                cursor.execute("INSERT INTO class_subjects (class_id, subject_id) VALUES (?, ?)", (cid, sid))

        cursor.execute("SELECT id FROM classes WHERE name = '6 \"А\"'")
        c6a = cursor.fetchone()
        if c6a:
            for st in ['Иванов Иван', 'Петров Пётр', 'Сидорова Анна', 'Смирнов Алексей']:
                cursor.execute("INSERT INTO students (full_name, class_id) VALUES (?, ?)", (st, c6a[0]))
                
    conn.commit()
    conn.close()

init_db()

def determine_quarter(dt_str):
    for q_num, (start_str, end_str) in QUARTERS.items():
        if start_str <= dt_str <= end_str:
            return q_num
    return 1

@app.route('/')
def index():
    return render_template('index.html')

# === API: КЛАССЫ ===
@app.route('/api/classes', methods=['GET', 'POST'])
def handle_classes():
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        name = request.json.get('name')
        if name:
            cursor.execute("INSERT OR IGNORE INTO classes (name) VALUES (?)", (name,))
            conn.commit()
        conn.close()
        return jsonify({'status': 'ok'})
    else:
        cursor.execute('''SELECT c.id, c.name, COUNT(DISTINCT s.id) 
                          FROM classes c 
                          LEFT JOIN students s ON c.id = s.class_id 
                          GROUP BY c.id ORDER BY c.name''')
        rows = cursor.fetchall()
        conn.close()
        return jsonify([{'id': r[0], 'name': r[1], 'students_count': r[2]} for r in rows])

@app.route('/api/classes/<int:class_id>', methods=['DELETE'])
def delete_class(class_id):
    conn = get_db()
    conn.execute("DELETE FROM classes WHERE id = ?", (class_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

# === API: ПРЕДМЕТЫ КЛАССА ===
@app.route('/api/classes/<int:class_id>/subjects', methods=['GET', 'POST'])
def handle_class_subjects(class_id):
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        subj_name = request.json.get('name')
        if subj_name:
            cursor.execute("INSERT OR IGNORE INTO subjects (name) VALUES (?)", (subj_name,))
            cursor.execute("SELECT id FROM subjects WHERE name = ?", (subj_name,))
            sid = cursor.fetchone()[0]
            cursor.execute("INSERT OR IGNORE INTO class_subjects (class_id, subject_id) VALUES (?, ?)", (class_id, sid))
            conn.commit()
        conn.close()
        return jsonify({'status': 'ok'})
    else:
        cursor.execute('''SELECT s.id, s.name FROM subjects s 
                          JOIN class_subjects cs ON s.id = cs.subject_id 
                          WHERE cs.class_id = ? ORDER BY s.name''', (class_id,))
        rows = cursor.fetchall()
        conn.close()
        return jsonify([{'id': r[0], 'name': r[1]} for r in rows])

@app.route('/api/classes/<int:class_id>/subjects/<int:subject_id>', methods=['DELETE'])
def delete_class_subject(class_id, subject_id):
    conn = get_db()
    conn.execute("DELETE FROM class_subjects WHERE class_id = ? AND subject_id = ?", (class_id, subject_id))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

# === API: УЧАЩИЕСЯ ===
@app.route('/api/classes/<int:class_id>/students', methods=['GET', 'POST'])
def handle_students(class_id):
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        full_name = request.json.get('full_name')
        if full_name:
            cursor.execute("INSERT INTO students (full_name, class_id) VALUES (?, ?)", (full_name, class_id))
            conn.commit()
        conn.close()
        return jsonify({'status': 'ok'})
    else:
        cursor.execute("SELECT id, full_name FROM students WHERE class_id = ? ORDER BY full_name", (class_id,))
        rows = cursor.fetchall()
        conn.close()
        return jsonify([{'id': r[0], 'full_name': r[1]} for r in rows])

@app.route('/api/students/<int:student_id>', methods=['DELETE'])
def delete_student(student_id):
    conn = get_db()
    conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

# === API: УРОКИ И АВТОГЕНЕРАЦИЯ ===
@app.route('/api/lessons', methods=['POST'])
def add_lesson():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    
    date_str = data['date_str']
    try:
        parts = date_str.split('.')
        day = int(parts[0])
        month = int(parts[1])
        year = 2026 if month >= 9 else 2027
        dt = datetime(year, month, day)
        full_date = dt.strftime("%Y-%m-%d")
    except:
        full_date = "2026-09-01"
        
    quarter = determine_quarter(full_date)
    
    cursor.execute("INSERT INTO lessons (class_id, subject_id, date_str, full_date, quarter, topic, homework, work_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (data['class_id'], data['subject_id'], date_str, full_date, quarter, data.get('topic', ''), data.get('homework', ''), data.get('work_type', 'Урок')))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/api/lessons/generate', methods=['POST'])
def generate_lessons():
    data = request.json
    class_id = data['class_id']
    subject_id = data['subject_id']
    target_quarter = int(data.get('quarter', 0))
    days = data.get('days', [])
    
    if not days:
        return jsonify({'status': 'error', 'message': 'Дни недели не выбраны'}), 400
        
    quarters_to_generate = [target_quarter] if target_quarter in [1, 2, 3, 4] else [1, 2, 3, 4]
    
    conn = get_db()
    cursor = conn.cursor()
    added_count = 0
    
    for q_num in quarters_to_generate:
        start_dt = datetime.strptime(QUARTERS[q_num][0], "%Y-%m-%d")
        end_dt = datetime.strptime(QUARTERS[q_num][1], "%Y-%m-%d")
        
        curr = start_dt
        while curr <= end_dt:
            if curr.weekday() in days:
                date_display = curr.strftime("%d.%m")
                full_date = curr.strftime("%Y-%m-%d")
                
                cursor.execute("SELECT id FROM lessons WHERE class_id = ? AND subject_id = ? AND full_date = ?", 
                               (class_id, subject_id, full_date))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO lessons (class_id, subject_id, date_str, full_date, quarter, topic, homework, work_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                   (class_id, subject_id, date_display, full_date, q_num, '', '', 'Урок'))
                    added_count += 1
            curr += timedelta(days=1)
            
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'added': added_count})

@app.route('/api/lessons/<int:lesson_id>', methods=['DELETE', 'PUT'])
def handle_lesson_item(lesson_id):
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'DELETE':
        cursor.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))
    elif request.method == 'PUT':
        data = request.json
        cursor.execute("UPDATE lessons SET topic = ?, homework = ?, work_type = ? WHERE id = ?",
                       (data.get('topic', ''), data.get('homework', ''), data.get('work_type', 'Урок'), lesson_id))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

# === API: ЖУРНАЛ ===
@app.route('/api/journal/<int:class_id>/<int:subject_id>', methods=['GET'])
def get_journal(class_id, subject_id):
    quarter = request.args.get('quarter', 0, type=int)
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, full_name FROM students WHERE class_id = ? ORDER BY full_name", (class_id,))
    students = [{'id': r[0], 'name': r[1]} for r in cursor.fetchall()]
    
    if quarter in [1, 2, 3, 4]:
        cursor.execute("SELECT id, date_str, topic, homework, work_type, quarter FROM lessons WHERE class_id = ? AND subject_id = ? AND quarter = ? ORDER BY full_date, id", (class_id, subject_id, quarter))
    else:
        cursor.execute("SELECT id, date_str, topic, homework, work_type, quarter FROM lessons WHERE class_id = ? AND subject_id = ? ORDER BY full_date, id", (class_id, subject_id))
        
    lessons = [{'id': r[0], 'date_str': r[1], 'topic': r[2] or '', 'homework': r[3] or '', 'work_type': r[4] or 'Урок', 'quarter': r[5]} for r in cursor.fetchall()]
    
    lesson_ids = [l['id'] for l in lessons]
    grades = {}
    
    if lesson_ids:
        placeholders = ','.join('?' for _ in lesson_ids)
        cursor.execute(f"SELECT student_id, lesson_id, val FROM grades WHERE lesson_id IN ({placeholders})", lesson_ids)
        for sid, lid, val in cursor.fetchall():
            if str(sid) not in grades: 
                grades[str(sid)] = {}
            grades[str(sid)][str(lid)] = val
        
    conn.close()
    return jsonify({'students': students, 'lessons': lessons, 'grades': grades})

@app.route('/api/grade', methods=['POST'])
def save_grade():
    data = request.json
    sid, lid, val = data['student_id'], data['lesson_id'], str(data['val']).strip()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM grades WHERE student_id = ? AND lesson_id = ?", (sid, lid))
    if val != "":
        cursor.execute("INSERT INTO grades (student_id, lesson_id, val) VALUES (?, ?, ?)", (sid, lid, val))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)