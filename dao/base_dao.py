from typing import Optional, Dict, Any, List
from utils.files import load_json, create_system_directory, save_json, join_paths

# Optional Supabase integration
from config.settings import SUPABASE
from dao import supabase_client
try:
    from config.supabase import load_config as _load_supabase_config
except Exception:
    _load_supabase_config = None

# Default mapping from BaseDao.data_name -> supabase table name
DEFAULT_TABLE_MAP = {
    'senders': 'sender',
    'app_passwords': 'app_password',
    'recipients': 'recipient',
    'groups': 'recipient_group'
}

class BaseDao:
    """
    Base DAO class for managing JSON-persisted data.

    Args:
        path (Optional[str]): Path to the JSON file for storing data.
        data_name (str): The key name in the JSON for the list of items.
    """
    def __init__(self, path: Optional[str] = None, data_name: str = "", remote_only: bool = False):
        base = create_system_directory('appdata', 'Enviador de Email')
        self.path = path or join_paths(base, f"data/{data_name}.json")

        self.data_name = data_name

        # Supabase remote mode: prefer saved config in appdata, then settings, then env vars
        import os
        cfg_enabled = False
        if _load_supabase_config:
            try:
                cfg = _load_supabase_config()
                if cfg and cfg.get('SUPABASE_URL') and cfg.get('SUPABASE_KEY'):
                    cfg_enabled = True
            except Exception:
                cfg_enabled = False
        env_enabled = bool(os.environ.get('SUPABASE_URL') and os.environ.get('SUPABASE_KEY'))
        self._remote = cfg_enabled or (SUPABASE.get('enabled', False) if isinstance(SUPABASE, dict) else False) or env_enabled
        self._remote_only = bool(remote_only)
        if self._remote_only and not self._remote:
            raise RuntimeError("BaseDao configured as remote_only but Supabase is not configured")
        # Resolve table name: explicit mapping in settings overrides default
        table_map = SUPABASE.get('table_map', {}) if isinstance(SUPABASE, dict) else {}
        self._table = table_map.get(data_name, DEFAULT_TABLE_MAP.get(data_name, data_name))

        self._data = {"next_id": 1, f"{data_name}": []}
        self._load()

    def _load(self):
        """
        Load data from JSON file.
        """
        if self._remote:
            # Load from Supabase table
            try:
                rows = supabase_client.get_all(self._table)
                # Ensure list and compute next_id
                items = rows or []
                # Normalize keys: already expected as dicts
                max_id = 0
                pk = None
                # Guess primary key name
                for k in items[0].keys() if items else []:
                    if k.endswith('_id'):
                        pk = k
                        break
                if pk:
                    for r in items:
                        try:
                            v = int(r.get(pk) or 0)
                            if v > max_id:
                                max_id = v
                        except Exception:
                            continue
                self._data = {"next_id": max_id + 1 if max_id else 1, f"{self.data_name}": items}
            except Exception:
                # If remote-only mode is requested, propagate the error instead of falling back
                if self._remote_only:
                    raise
                # Fallback to local file if remote load fails
                data = load_json(self.path)
                if data:
                    self._data = {"next_id": data.get("next_id", 1), f"{self.data_name}": data.get(f"{self.data_name}", [])}
        else:
            data = load_json(self.path)
            if data:
                self._data = {"next_id": data.get("next_id", 1), f"{self.data_name}": data.get(f"{self.data_name}", [])}

    def _save(self):
        """
        Save data to JSON file.
        """
        if self._remote:
            try:
                rows = self._data.get(self.data_name, [])
                # Upsert current rows into remote table. Avoid deleting all (requires service key).
                returned = supabase_client.upsert_rows(self._table, rows)
                if returned:
                    self._data[f"{self.data_name}"] = returned
                    # recompute next_id
                    max_id = 0
                    for r in returned:
                        for k, v in r.items():
                            if k.endswith('_id'):
                                try:
                                    vi = int(v)
                                    if vi > max_id:
                                        max_id = vi
                                except Exception:
                                    continue
                    self._data["next_id"] = max_id + 1 if max_id else self._data.get("next_id", 1)
                # Also persist a local copy unless remote-only mode is enabled
                if not self._remote_only:
                    save_json(self.path, self._data)
            except Exception:
                # On any remote error, if remote-only requested propagate error, else fallback to local-only save
                if self._remote_only:
                    raise
                save_json(self.path, self._data)
        else:
            save_json(self.path, self._data)

    def upsert_one(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Upsert a single item to the remote Supabase table and update local cache with returned row.

        Returns the returned representation when available.
        """
        if not self._remote:
            # fallback to local save
            self._save()
            return None
        try:
            returned = supabase_client.upsert_rows(self._table, [item])
            if returned:
                # replace or append the returned row in local cache
                row = returned[0]
                pk = None
                for k in row.keys():
                    if k.endswith('_id'):
                        pk = k
                        break
                if pk:
                    # find existing
                    found = False
                    for idx, r in enumerate(self._data[self.data_name]):
                        if r.get(pk) == row.get(pk):
                            self._data[self.data_name][idx] = row
                            found = True
                            break
                    if not found:
                        self._data[self.data_name].append(row)
                else:
                    # no pk found, append
                    self._data[self.data_name].append(row)
                # recompute next_id
                max_id = 0
                for r in self._data[self.data_name]:
                    for k, v in r.items():
                        if k.endswith('_id'):
                            try:
                                vi = int(v)
                                if vi > max_id:
                                    max_id = vi
                            except Exception:
                                continue
                self._data['next_id'] = max_id + 1 if max_id else self._data.get('next_id', 1)
                if not self._remote_only:
                    save_json(self.path, self._data)
                return row
        except Exception:
            if self._remote_only:
                raise
            # fallback to local save
            save_json(self.path, self._data)
        return None