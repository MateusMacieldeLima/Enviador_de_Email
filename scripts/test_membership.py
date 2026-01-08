import logging
import os
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from controller.recipient_group_controller import RecipientGroupController
from controller.recipient_controller import RecipientController
from dao.recipient_dao import RecipientDao
from dao.recipient_group_dao import RecipientGroupDao

rc = RecipientController(RecipientDao(), RecipientGroupDao())
rgc = RecipientGroupController(RecipientDao(), RecipientGroupDao())

# pick an existing recipient if any
recipients = rc.list_recipients()
if not recipients:
    print('No recipients available to test. Run import first.')
    sys.exit(0)

recipient = recipients[0]
print('Testing with recipient:', recipient.recipient_id, recipient.address, 'current group', recipient.group_id)

# create a new group
grp = rgc.add_group('membership_test_group')
print('Created group:', grp.group_id)

# try to add recipient to this new group
try:
    ok = rgc.add_recipient_to_group(recipient.recipient_id, grp.group_id)
    print('add_recipient_to_group returned:', ok)
except Exception as e:
    print('add_recipient_to_group raised:', e)

# list memberships using membership DAO raw
from dao.recipient_group_membership_dao import RecipientGroupMembershipDao
mdao = RecipientGroupMembershipDao()
print('Membership entries for recipient:', mdao.list_recipient_groups(recipient.recipient_id))
print('Membership entries for group:', mdao.list_group_members(grp.group_id))

# show groups and recipients
print('Groups:')
for g in rgc.list_groups():
    print(g.group_id, g.name)

print('Recipients:')
for r in rc.list_recipients():
    print(r.recipient_id, r.address, r.group_id)
