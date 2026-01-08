import sys, os
from pathlib import Path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
print('sys.path[0]:', sys.path[0])
try:
    import dao.recipient_dao as rd
    print('Imported dao.recipient_dao OK')
    print('functions in module:', [n for n in dir(rd) if not n.startswith('_')][:20])
except Exception as e:
    print('Import failed:', repr(e))
    raise
