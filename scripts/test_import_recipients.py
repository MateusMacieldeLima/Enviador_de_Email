import logging
import os
import sys

# Ensure project root is on sys.path so imports work when running the script directly
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from dao.recipient_dao import RecipientDao
from dao.recipient_group_dao import RecipientGroupDao
from controller.recipient_controller import RecipientController
from controller.recipient_group_controller import RecipientGroupController
from models.recipient_group_model import RecipientGroupModel

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

TMP_CSV = os.path.join(os.path.dirname(__file__), 'tmp_recipients.csv')

# create a small CSV
with open(TMP_CSV, 'w', encoding='utf-8') as f:
    f.write('email\n')
    f.write('alice@example.com\n')
    f.write('bob@example.com\n')
    f.write('carol@example.com\n')

print('CSV created at', TMP_CSV)

# Use shared DAOs so controllers operate on same data
recipient_dao = RecipientDao()
group_dao = RecipientGroupDao()
rc = RecipientController(recipient_dao, group_dao)
rgc = RecipientGroupController(recipient_dao, group_dao)

# cleanup any existing test group
for g in rgc.list_groups():
    if g.name == 'testgroup':
        print('Removing existing testgroup', g.group_id)
        rgc.delete_group(g.group_id)

# create group
grp = rgc.add_group('testgroup')
print('Created group', grp.group_id, grp.name, 'recipients:', grp.recipients)

# process file
addresses = rc.process_recipient_file(TMP_CSV)
print('Addresses extracted:', addresses)

# add recipients
for a in addresses:
    r = rc.add_recipient(a, group_id=grp.group_id)
    print('Added recipient', a, '-> id', getattr(r, 'recipient_id', None))

# show current state
print('After import:')
for g in rgc.list_groups():
    print('Group', g.group_id, g.name, 'recipients list len:', len(g.recipients))

print('Recipients table:')
for r in rc.list_recipients():
    print('Recipient', r.recipient_id, r.address, 'group_id', r.group_id)

# simulate restart by creating fresh DAOs
print('\nSimulating restart...')
new_recipient_dao = RecipientDao()
new_group_dao = RecipientGroupDao()
new_rgc = RecipientGroupController(new_recipient_dao, new_group_dao)
new_rc = RecipientController(new_recipient_dao, new_group_dao)

for g in new_rgc.list_groups():
    if g.name == 'testgroup':
        print('After restart - group', g.group_id, g.name, 'recipients list len:', len(g.recipients))
        members = new_rgc.list_group_recipients(g.group_id)
        print('After restart - group members count via recipients table:', len(members))

print('After restart - recipients table:')
for r in new_rc.list_recipients():
    print('Recipient', r.recipient_id, r.address, 'group_id', r.group_id)

# cleanup tmp file
os.remove(TMP_CSV)
print('Done')
