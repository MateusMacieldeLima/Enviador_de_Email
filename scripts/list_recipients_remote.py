import sys, os
from pathlib import Path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dao import supabase_client

rows = supabase_client.get_all('recipient')
print(f'Total recipients: {len(rows)}')
for r in rows[:50]:
    print(r)
