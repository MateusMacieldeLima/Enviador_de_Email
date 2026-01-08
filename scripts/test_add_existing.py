import logging
import os
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from controller.recipient_controller import RecipientController
from controller.recipient_group_controller import RecipientGroupController
from dao.recipient_dao import RecipientDao
from dao.recipient_group_dao import RecipientGroupDao

rc = RecipientController(RecipientDao(), RecipientGroupDao())
rgc = RecipientGroupController(RecipientDao(), RecipientGroupDao())

recipients = rc.list_recipients()
if not recipients:
    print('No recipients available')
    sys.exit(0)

recipient = recipients[0]
print('Using existing recipient:', recipient.recipient_id, recipient.address, 'group', recipient.group_id)

# create new group
grp = rgc.add_group('existing_member_test')
print('Created group', grp.group_id)

# attempt to add existing recipient via RecipientController.add_recipient
try:
    rec = rc.add_recipient(recipient.address, group_id=grp.group_id)
    print('add_recipient returned recipient id:', getattr(rec, 'recipient_id', None))
except Exception as e:
    print('add_recipient raised:', e)

# check membership table
from dao.recipient_group_membership_dao import RecipientGroupMembershipDao
mdao = RecipientGroupMembershipDao()
print('Memberships for recipient:', mdao.list_recipient_groups(recipient.recipient_id))
print('Members for group:', mdao.list_group_members(grp.group_id))
