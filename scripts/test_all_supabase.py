"""Testa CRUD básico em todas as tabelas Supabase usadas pela app.

Executa:
  - cria grupo, remetente, app_password, destinatário
  - liga app_password ao remetente
  - lista e imprime resumos
  - remove os registros de teste

Uso: `python scripts/test_all_supabase.py`
"""
import os
import sys
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dao.recipient_group_dao import RecipientGroupDao
from dao.sender_dao import SenderDao
from dao.app_password_dao import AppPasswordDao
from dao.recipient_dao import RecipientDao

from models.recipient_group_model import RecipientGroupModel
from models.sender_model import SenderModel
from models.app_password_model import AppPasswordModel
from models.recipient_model import RecipientModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    try:
        rg_dao = RecipientGroupDao()
        s_dao = SenderDao()
        ap_dao = AppPasswordDao()
        r_dao = RecipientDao()

        # Criar grupo de teste
        g = RecipientGroupModel(name='grupo_test_all')
        g = rg_dao.add(g)
        print('Grupo criado:', g.group_id, g.name)

        # Criar sender
        s = SenderModel(address='tester@example.com')
        s = s_dao.add(s)
        print('Sender criado:', s.sender_id, s.address)

        # Criar app_password (sem ciphertext para evitar tentativa de encriptação local)
        ap = AppPasswordModel(sender_id=s.sender_id, ciphertext=None)
        ap = ap_dao.add(ap)
        print('AppPassword criado:', ap.app_password_id)

        # Atualizar sender para referenciar app_password
        s.app_password_id = ap.app_password_id
        s = s_dao.edit(s)
        print('Sender atualizado com app_password_id =', s.app_password_id)

        # Criar recipient
        rec = RecipientModel(address='recipient@example.com', group_id=g.group_id)
        try:
            rec = r_dao.add(rec)
            print('Recipient criado:', rec.recipient_id, rec.address, 'group=', rec.group_id)
        except Exception as e:
            logger.warning('Falha ao criar recipient: %s', e)
            # tentar recuperar pelo endereço caso já exista
            existing = r_dao.find_by_address(rec.address)
            if existing:
                rec = existing
                print('Recipient existente usado:', rec.recipient_id, rec.address)
            else:
                raise

        # Listagens
        groups = rg_dao.list_all()
        senders = s_dao.list_all()
        app_passwords = ap_dao.list_all()
        recipients = r_dao.list_all()

        print('\nResumo:')
        print('Groups:', len(groups))
        print('Senders:', len(senders))
        print('App passwords:', len(app_passwords))
        print('Recipients:', len(recipients))

        # Nota: não apagar os registros de teste — mantê-los no banco
        print('\nRegistros de teste criados (não removidos):')
        print('Group id:', getattr(g, 'group_id', None))
        print('Sender id:', getattr(s, 'sender_id', None))
        print('AppPassword id:', getattr(ap, 'app_password_id', None))
        print('Recipient id:', getattr(rec, 'recipient_id', None))

    except Exception as e:
        logger.exception('Erro no teste completo: %s', e)


if __name__ == '__main__':
    main()
