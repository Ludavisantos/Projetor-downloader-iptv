import os
import re
import json
import threading
from flask import Flask, render_template, request, jsonify, send_from_directory
import requests
from werkzeug.utils import secure_filename

USERS_FILE = 'users.json'
DOWNLOADS_DIR = 'downloads'
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'m3u'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def parse_m3u_links(m3u_path):
    with open(m3u_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    entries = []
    i = 0
    while i < len(lines):
        if lines[i].startswith('#EXTINF'):
            info = lines[i].strip()
            url = lines[i+1].strip() if i+1 < len(lines) else ''
            entries.append({'info': info, 'url': url})
            i += 2
        else:
            i += 1
    return entries

def extract_title(info):
    match = re.search(r'tvg-name="([^"]+)"', info)
    if match:
        return match.group(1)
    if ',' in info:
        return info.split(',')[-1].strip()
    return 'FilmeDesconhecido'

def extract_auth_from_url(url):
    match = re.search(r'/movie/([^/]+)/([^/]+)/', url)
    if match:
        return match.group(1), match.group(2)
    return None, None

def replace_auth_in_url(url, new_user, new_pass):
    return re.sub(r'(/movie/)([^/]+)/([^/]+)(/)', f"/movie/{new_user}/{new_pass}/", url)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/users', methods=['GET', 'POST'])
def api_users():
    if request.method == 'GET':
        return jsonify(load_users())
    data = request.json
    users = load_users()
    users.append({'user': data['user'], 'password': data['password']})
    save_users(users)
    return jsonify({'status': 'ok'})

@app.route('/api/upload', methods=['POST'])
def api_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file'}), 400
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    entries = parse_m3u_links(filepath)
    filmes = [{'title': extract_title(e['info']), 'url': e['url']} for e in entries]
    return jsonify({'filmes': filmes, 'm3u_path': filepath})

@app.route('/api/paste', methods=['POST'])
def api_paste():
    data = request.json
    text = data.get('text', '')
    if not text.strip():
        return jsonify({'error': 'Texto vazio'}), 400
    # Salvar texto temporariamente como arquivo
    filename = 'pasted_list.m3u'
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)
    entries = parse_m3u_links(filepath)
    filmes = [{'title': extract_title(e['info']), 'url': e['url']} for e in entries]
    return jsonify({'filmes': filmes, 'm3u_path': filepath})

download_status = {}

def download_file(url, filename, status_key):
    path = os.path.join(DOWNLOADS_DIR, filename)
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        download_status[status_key] = 'done'
    except Exception as e:
        download_status[status_key] = f'error: {e}'

DOWNLOADED_FILE = 'downloaded.json'

def load_downloaded():
    if not os.path.exists(DOWNLOADED_FILE):
        return set()
    with open(DOWNLOADED_FILE, 'r', encoding='utf-8') as f:
        try:
            return set(json.load(f))
        except Exception:
            return set()

def save_downloaded(downloaded):
    with open(DOWNLOADED_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(downloaded), f, ensure_ascii=False, indent=2)

@app.route('/api/download', methods=['POST'])
def api_download():
    data = request.json
    m3u_path = data['m3u_path']
    download_dir = data.get('download_dir', 'downloads')
    users = load_users()
    entries = parse_m3u_links(m3u_path)
    used_auths = set()
    threads = []
    keys = []
    os.makedirs(download_dir, exist_ok=True)
    downloaded = load_downloaded()
    for idx, entry in enumerate(entries):
        title = extract_title(entry['info'])
        url = entry['url']
        filename = f'{title}.mp4'
        # Evitar download repetido
        if filename in downloaded or url in downloaded:
            status_key = f'{idx}_{filename}'
            download_status[status_key] = 'skipped'
            keys.append({'key': status_key, 'title': title, 'skipped': True})
            continue
        orig_user, orig_pass = extract_auth_from_url(url)
        auth_idx = 0
        while auth_idx < len(users):
            candidate = (users[auth_idx]['user'], users[auth_idx]['password'])
            if candidate not in used_auths:
                used_auths.add(candidate)
                break
            auth_idx += 1
        if auth_idx == len(users):
            continue
        new_user, new_pass = users[auth_idx]['user'], users[auth_idx]['password']
        if (orig_user, orig_pass) != (new_user, new_pass):
            url = replace_auth_in_url(url, new_user, new_pass)
        status_key = f'{idx}_{filename}'
        download_status[status_key] = 'downloading'
        t = threading.Thread(target=download_file, args=(url, filename, status_key, download_dir, downloaded))
        threads.append(t)
        keys.append({'key': status_key, 'title': title})
        t.start()
    return jsonify({'status': 'started', 'keys': keys})

# Atualizar download_file para aceitar o diretório e memória

def download_file(url, filename, status_key, download_dir='downloads', downloaded=None):
    path = os.path.join(download_dir, filename)
    if downloaded is None:
        downloaded = set()
    if filename in downloaded or url in downloaded:
        download_status[status_key] = 'skipped'
        return
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        download_status[status_key] = 'done'
        downloaded.add(filename)
        downloaded.add(url)
        save_downloaded(downloaded)
    except Exception as e:
        download_status[status_key] = f'error: {e}'


@app.route('/api/status', methods=['POST'])
def api_status():
    data = request.json
    keys = data['keys']
    result = {k['key']: download_status.get(k['key'], 'pending') for k in keys}
    return jsonify(result)

@app.route('/downloads/<filename>')
def serve_download(filename):
    return send_from_directory(DOWNLOADS_DIR, filename)

if __name__ == '__main__':
    app.run(debug=True)
