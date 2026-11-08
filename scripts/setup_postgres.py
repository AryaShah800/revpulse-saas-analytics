"""Create an isolated local PostgreSQL cluster; never touch the system cluster."""
import json
import os
from pathlib import Path
import secrets
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '.local'
BIN = Path(os.environ.get('POSTGRES_BIN', r'C:\Program Files\PostgreSQL\18\bin'))

def main():
    LOCAL.mkdir(exist_ok=True)
    settings = LOCAL / 'database.json'
    if not settings.exists():
        settings.write_text(json.dumps(dict(host='127.0.0.1', port=55432, dbname='postgres', user='revpulse', password=secrets.token_urlsafe(32))))
    cfg = json.loads(settings.read_text())
    data = LOCAL / 'pgdata'
    if not (data / 'PG_VERSION').exists():
        password_file = LOCAL / 'init-password.tmp'
        password_file.write_text(cfg['password'])
        try:
            subprocess.run([str(BIN/'initdb.exe'), '-D', str(data), '-U', cfg['user'], '--auth=scram-sha-256', '--encoding=UTF8', '--locale=C', f'--pwfile={password_file}'], check=True)
        finally:
            password_file.unlink(missing_ok=True)
        with (data/'postgresql.conf').open('a') as f:
            f.write("\nlisten_addresses = '127.0.0.1'\nport = 55432\n")
    status = subprocess.run([str(BIN/'pg_ctl.exe'), '-D', str(data), 'status'], capture_output=True)
    if status.returncode:
        subprocess.run([str(BIN/'pg_ctl.exe'), '-D', str(data), '-l', str(LOCAL/'postgres.log'), '-w', 'start'], check=True)
    print('Project PostgreSQL ready on 127.0.0.1:55432; credentials remain in ignored .local/database.json')

if __name__ == '__main__':
    main()
