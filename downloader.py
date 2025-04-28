import os
import re
import json
import threading
import requests
from urllib.parse import urlparse

USERS_FILE = 'users.json'
DOWNLOADS_DIR = 'downloads'

# Utilidade para carregar usuários cadastrados
def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

# Utilidade para salvar usuários cadastrados
def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

# Adicionar novo usuário/senha
def add_user():
    user = input('Usuário: ').strip()
    password = input('Senha: ').strip()
    users = load_users()
    users.append({'user': user, 'password': password})
    save_users(users)
    print('Usuário adicionado!')

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
    # fallback: pegar após última vírgula
    if ',' in info:
        return info.split(',')[-1].strip()
    return 'FilmeDesconhecido'

def extract_auth_from_url(url):
    # Ex: http://rota66.bar:80/movie/7332hU/RyMPPu/342756.mp4
    match = re.search(r'/movie/([^/]+)/([^/]+)/', url)
    if match:
        return match.group(1), match.group(2)
    return None, None

def replace_auth_in_url(url, new_user, new_pass):
    return re.sub(r'(/movie/)([^/]+)/([^/]+)(/)', f"/movie/{new_user}/{new_pass}/", url)

def download_file(url, filename):
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    path = os.path.join(DOWNLOADS_DIR, filename)
    print(f'Baixando: {filename}')
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        print(f'Concluído: {filename}')
    except Exception as e:
        print(f'Erro ao baixar {filename}: {e}')

def main():
    print('1. Adicionar usuário')
    print('2. Baixar filmes de arquivo M3U')
    op = input('Escolha uma opção: ')
    if op == '1':
        add_user()
    elif op == '2':
        m3u_path = input('Caminho do arquivo .m3u: ').strip()
        users = load_users()
        if not users:
            print('Cadastre pelo menos um usuário antes!')
            return
        entries = parse_m3u_links(m3u_path)
        print(f'{len(entries)} filmes encontrados.')
        used_auths = set()
        threads = []
        for idx, entry in enumerate(entries):
            title = extract_title(entry['info'])
            url = entry['url']
            orig_user, orig_pass = extract_auth_from_url(url)
            # Selecionar usuário/senha não usados
            auth_idx = 0
            while auth_idx < len(users):
                candidate = (users[auth_idx]['user'], users[auth_idx]['password'])
                if candidate not in used_auths:
                    used_auths.add(candidate)
                    break
                auth_idx += 1
            if auth_idx == len(users):
                print(f'Sem usuários livres para {title}, pulando...')
                continue
            new_user, new_pass = users[auth_idx]['user'], users[auth_idx]['password']
            if (orig_user, orig_pass) != (new_user, new_pass):
                url = replace_auth_in_url(url, new_user, new_pass)
            filename = f'{title}.mp4'
            t = threading.Thread(target=download_file, args=(url, filename))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        print('Downloads finalizados!')
    else:
        print('Opção inválida!')

if __name__ == '__main__':
    main()
