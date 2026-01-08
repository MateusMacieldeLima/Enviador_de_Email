"""Script de teste para verificar gravação no Supabase usando o DAO.

Uso:
  - Defina as variáveis de ambiente `SUPABASE_URL` e `SUPABASE_KEY`, ou
    chame `config.supabase.save_config(url, key)` antes de executar.
  - Execute: `python scripts/test_supabase.py`

O script irá tentar adicionar um grupo e listar os grupos existentes.
"""
import os
import sys
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.supabase import load_config
from config.settings import SUPABASE as SETTINGS_SUPABASE
from dao.recipient_group_dao import RecipientGroupDao
from models.recipient_group_model import RecipientGroupModel

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def main():
    cfg = load_config()
    if not cfg:
        # tenta usar os valores de settings como fallback de teste
        url = SETTINGS_SUPABASE.get('url') if isinstance(SETTINGS_SUPABASE, dict) else None
        key = SETTINGS_SUPABASE.get('key') if isinstance(SETTINGS_SUPABASE, dict) else None
        if url and key:
            os.environ['SUPABASE_URL'] = url
            os.environ['SUPABASE_KEY'] = key
            print('Usando SUPABASE URL/KEY a partir de config.settings para teste')
        else:
            print("Supabase nao configurado. Defina SUPABASE_URL e SUPABASE_KEY em variaveis de ambiente ou salve a configuracao com config.supabase.save_config(url, key).")
            return

    dao = RecipientGroupDao()

    # criar grupo de teste
    g = RecipientGroupModel(name="grupo_teste_script")
    try:
        added = dao.add(g)
        print("Adicionado:", added.group_id, added.name)
    except Exception as e:
        print("Falha ao adicionar grupo:", e)

    try:
        all_groups = dao.list_all()
        print(f"Total de grupos: {len(all_groups)}")
        for rg in all_groups:
            print(f"- id={rg.group_id} nome={rg.name}")
    except Exception as e:
        print("Falha ao listar grupos:", e)


if __name__ == '__main__':
    main()
