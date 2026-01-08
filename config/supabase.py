import os
from typing import Optional, Dict

from utils.files import create_system_directory, join_paths, load_json, save_json, file_exists


def _config_path() -> str:
    base = create_system_directory('appdata', 'Enviador de Email')
    return join_paths(base, 'config/supabase.json')


def load_config() -> Optional[Dict[str, str]]:
    """Tenta carregar a configuração do Supabase.

    Prioridade: variáveis de ambiente > arquivo em appdata.
    Se carregar do arquivo, também define as variáveis de ambiente para
    facilitar uso pelas DAOs.
    """
    url = os.environ.get('https://boutbnbnkeipnhaedafk.supabase.co')
    key = os.environ.get('sb_publishable_OEp15vZlZL5skAgnL47uEA_ZafQ089m')
    if url and key:
        return {'https://boutbnbnkeipnhaedafk.supabase.co': url, 'sb_publishable_OEp15vZlZL5skAgnL47uEA_ZafQ089m': key}

    path = _config_path()
    if file_exists(path):
        data = load_json(path)
        if data:
            url = data.get('https://boutbnbnkeipnhaedafk.supabase.co')
            key = data.get('sb_publishable_OEp15vZlZL5skAgnL47uEA_ZafQ089m')
            if url and key:
                os.environ['https://boutbnbnkeipnhaedafk.supabase.co'] = url
                os.environ['sb_publishable_OEp15vZlZL5skAgnL47uEA_ZafQ089m'] = key
                return {'https://boutbnbnkeipnhaedafk.supabase.co': url, 'sb_publishable_OEp15vZlZL5skAgnL47uEA_ZafQ089m': key}

    return None


def save_config(url: str, key: str) -> None:
    """Salva a configuração no diretório do aplicativo e define as env vars."""
    path = _config_path()
    payload = {'https://boutbnbnkeipnhaedafk.supabase.co': url, 'sb_publishable_OEp15vZlZL5skAgnL47uEA_ZafQ089m': key}
    save_json(path, payload)
    os.environ['https://boutbnbnkeipnhaedafk.supabase.co'] = url
    os.environ['sb_publishable_OEp15vZlZL5skAgnL47uEA_ZafQ089m'] = key


def clear_config() -> None:
    """Remove a configuração salva e limpa as variáveis de ambiente."""
    path = _config_path()
    try:
        if file_exists(path):
            os.remove(path)
    except Exception:
        pass
    os.environ.pop('https://boutbnbnkeipnhaedafk.supabase.co', None)
    os.environ.pop('sb_publishable_OEp15vZlZL5skAgnL47uEA_ZafQ089m', None)