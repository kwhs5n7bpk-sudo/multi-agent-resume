#!/usr/bin/env python3
"""简历管理后台 API"""

import json
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory, redirect
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
CORS(app)

DATA_DIR = Path(__file__).parent / 'data'
RESUME_FILE = DATA_DIR / 'resume.json'

def load_resume():
    if RESUME_FILE.exists():
        return json.loads(RESUME_FILE.read_text(encoding='utf-8'))
    return {}

def save_resume(data):
    DATA_DIR.mkdir(exist_ok=True)
    RESUME_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

@app.route('/')
def index():
    return redirect('/resume.html')

@app.route('/resume.html')
def resume():
    return send_from_directory('static', 'resume.html')

@app.route('/admin.html')
def admin():
    return send_from_directory('static', 'admin.html')

@app.route('/photo.png')
def photo():
    return send_from_directory('static', 'photo.png')

@app.route('/photo.jpg')
def photo_jpg():
    return send_from_directory('static', 'photo.jpg')

@app.route('/api/resume', methods=['GET'])
def get_resume():
    return jsonify(load_resume())

@app.route('/api/resume', methods=['PUT'])
def update_resume():
    data = request.get_json()
    save_resume(data)
    return jsonify({"status": "ok"})

@app.route('/api/resume/section/<section>', methods=['GET'])
def get_section(section):
    resume = load_resume()
    return jsonify(resume.get(section, {}))

@app.route('/api/resume/section/<section>', methods=['PUT'])
def update_section(section):
    resume = load_resume()
    resume[section] = request.get_json()
    save_resume(resume)
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    DATA_DIR.mkdir(exist_ok=True)
    if not RESUME_FILE.exists():
        save_resume({})
    app.run(host='0.0.0.0', port=5001, debug=True)
