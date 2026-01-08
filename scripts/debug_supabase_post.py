"""Depuração: tenta inserir diretamente via REST e imprime resposta completa."""
import os
import sys
import json
import requests

from urllib.parse import urlencode

TABLE = 'recipient_group'

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.settings import SUPABASE as SETTINGS_SUPABASE

url = (os.environ.get('SUPABASE_URL') or (SETTINGS_SUPABASE.get('url') if isinstance(SETTINGS_SUPABASE, dict) else None) or '').rstrip('/')
key = os.environ.get('SUPABASE_KEY') or (SETTINGS_SUPABASE.get('key') if isinstance(SETTINGS_SUPABASE, dict) else None) or ''

if not url or not key:
    print('SUPABASE_URL ou SUPABASE_KEY não definidos nas env vars ou config.settings')
    raise SystemExit(1)

endpoint = f"{url}/rest/v1/{TABLE}"
headers = {
    'apikey': key,
    'Authorization': f'Bearer {key}',
    'Content-Type': 'application/json',
    'Prefer': 'return=representation'
}

rows = [{"group_id": 1, "name": "grupo_teste_debug", "recipients": []}]

params = {'on_conflict': 'group_id'}

full_url = endpoint + ('?' + urlencode(params) if params else '')

print('POST', full_url)
print('HEADERS:', {k: (v[:20] + '...' if k.lower().find('key')!=-1 and len(v)>20 else v) for k,v in headers.items()})
print('BODY:', json.dumps(rows))

resp = requests.post(full_url, headers=headers, json=rows)

print('STATUS:', resp.status_code)
print('RESPONSE HEADERS:', resp.headers)
print('RESPONSE TEXT:', resp.text)
try:
    print('RESPONSE JSON:', resp.json())
except Exception:
    pass

resp.raise_for_status()

print('Inserção bem sucedida')
