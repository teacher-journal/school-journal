from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)

DATA_FILE = 'journal_data.json'

def load_data():
    if not os.path.exists(DATA_FILE):
        default_data = {
            "classes": [
                {"id": 1, "name": "5 А"},
                {"id": 2, "name": "6 Б"}
            ],
            "students": [],
            "grades": {}
        }
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, ensure_ascii=False, indent=2)
        return default_data
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/get_data', methods=['GET'])
def get_data():
    return jsonify(load_data())

@app.route('/api/add_class', methods=['POST'])
def add_class():
    data = load_data()
    req_data = request.json
    class_name = req_data.get('name', '').strip()
    
    if not class_name:
        return jsonify({"error": "Пустое имя класса"}), 400
        
    new_id = max([c['id'] for c in data['classes']], default=0) + 1
    new_class = {"id": new_id, "name": class_name}
    data['classes'].append(new_class)
    save_data(data)
    return jsonify({"success": True, "class": new_class})

@app.route('/api/add_student', methods=['POST'])
def add_student():
    data = load_data()
    req_data = request.json
    name = req_data.get('name', '').strip()
    class_id = req_data.get('class_id')
    group = req_data.get('group', '1')
    
    if not name or not class_id:
        return jsonify({"error": "Заполните имя и класс"}), 400
        
    new_id = max([s['id'] for s in data['students']], default=0) + 1
    new_student = {"id": new_id, "name": name, "class_id": int(class_id), "group": str(group)}
    data['students'].append(new_student)
    save_data(data)
    return jsonify({"success": True, "student": new_student})

@app.route('/api/add_students_bulk', methods=['POST'])
def add_students_bulk():
    data = load_data()
    req_data = request.json
    raw_text = req_data.get('text', '')
    class_id = req_data.get('class_id')
    group = str(req_data.get('group', '1'))

    if not raw_text or not class_id:
        return jsonify({"error": "Пустой список или не выбран класс"}), 400

    lines = raw_text.strip().split('\n')
    added_count = 0
    current_max_id = max([s['id'] for s in data['students']], default=0)

    for line in lines:
        cleaned_name = line.strip()
        if cleaned_name:
            current_max_id += 1
            data['students'].append({
                "id": current_max_id,
                "name": cleaned_name,
                "class_id": int(class_id),
                "group": group
            })
            added_count += 1

    save_data(data)
    return jsonify({"success": True, "count": added_count})

@app.route('/api/delete_student', methods=['POST'])
def delete_student():
    data = load_data()
    req_data = request.json
    student_id = req_data.get('student_id')
    
    data['students'] = [s for s in data['students'] if s['id'] != student_id]
    
    str_id = str(student_id)
    if str_id in data['grades']:
        del data['grades'][str_id]
        
    save_data(data)
    return jsonify({"success": True})

@app.route('/api/update_student_group', methods=['POST'])
def update_student_group():
    data = load_data()
    req_data = request.json
    student_id = req_data.get('student_id')
    new_group = str(req_data.get('group', '1'))
    
    for st in data['students']:
        if st['id'] == student_id:
            st['group'] = new_group
            break
            
    save_data(data)
    return jsonify({"success": True})

@app.route('/api/save_grade', methods=['POST'])
def save_grade():
    data = load_data()
    req_data = request.json
    student_id = str(req_data.get('student_id'))
    col_index = str(req_data.get('col_index'))
    value = req_data.get('value', '').strip()
    
    if student_id not in data['grades']:
        data['grades'][student_id] = {}
        
    data['grades'][student_id][col_index] = value
    save_data(data)
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True)
