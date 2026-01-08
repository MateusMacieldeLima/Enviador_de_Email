import requests
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode

from config.settings import SUPABASE
try:
    from config.supabase import load_config as _load_supabase_config
except Exception:
    _load_supabase_config = None

logger = logging.getLogger(__name__)

HEADERS = lambda key: {
    'apikey': key,
    'Authorization': f'Bearer {key}',
    'Content-Type': 'application/json'
}

# Map table -> primary key column name
PK_MAP = {
    'sender': 'sender_id',
    'app_password': 'app_password_id',
    'recipient_group': 'group_id',
    'recipient': 'recipient_id',
    'email': 'email_id',
    'attachment': 'attachment_id'
}


def _base_url() -> str:
    # Prefer saved config in config/supabase.py, then settings, then env var
    import os
    url = None
    if _load_supabase_config:
        try:
            cfg = _load_supabase_config()
            if cfg and cfg.get('SUPABASE_URL'):
                url = cfg.get('SUPABASE_URL')
        except Exception:
            url = None
    if not url:
        url = SUPABASE.get('url') if isinstance(SUPABASE, dict) else None
    if not url:
        url = os.environ.get('SUPABASE_URL', '')
    return (url or '').rstrip('/')


def get_all(table: str) -> List[Dict[str, Any]]:
    """Fetch all rows from Supabase table."""
    url = f"{_base_url()}/rest/v1/{table}"
    import os
    key = None
    if _load_supabase_config:
        try:
            cfg = _load_supabase_config()
            if cfg and cfg.get('SUPABASE_KEY'):
                key = cfg.get('SUPABASE_KEY')
        except Exception:
            key = None
    if not key:
        key = SUPABASE.get('key') if isinstance(SUPABASE, dict) else None
    if not key:
        key = os.environ.get('SUPABASE_KEY', '')
    headers = HEADERS(key)
    params = {'select': '*'}
    try:
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code >= 400:
            logger.error('Supabase GET %s returned %s: %s', url, resp.status_code, resp.text)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        try:
            logger.exception('Supabase GET request failed: %s', url)
            if hasattr(e, 'response') and e.response is not None:
                logger.error('Response status: %s', e.response.status_code)
                logger.error('Response text: %s', e.response.text)
        except Exception:
            pass
        raise


def upsert_rows(table: str, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Upsert multiple rows into Supabase table. Returns representation of rows.

    Uses ?on_conflict=<pk> to perform upsert by primary key when available.
    """
    if not rows:
        return []

    url = f"{_base_url()}/rest/v1/{table}"
    import os
    key = None
    if _load_supabase_config:
        try:
            cfg = _load_supabase_config()
            if cfg and cfg.get('SUPABASE_KEY'):
                key = cfg.get('SUPABASE_KEY')
        except Exception:
            key = None
    if not key:
        key = SUPABASE.get('key') if isinstance(SUPABASE, dict) else None
    if not key:
        key = os.environ.get('SUPABASE_KEY', '')
    headers = HEADERS(key)
    pk = PK_MAP.get(table)
    params = {}
    if pk:
        params['on_conflict'] = pk

    # Prefer return representation to get inserted/updated rows back
    headers['Prefer'] = 'return=representation'

    try:
        resp = requests.post(url + (f"?{urlencode(params)}" if params else ""), headers=headers, json=rows)
        if resp.status_code >= 400:
            logger.error('Supabase POST %s returned %s: %s', url, resp.status_code, resp.text)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        try:
            logger.exception('Supabase POST request failed: %s', url)
            if hasattr(e, 'response') and e.response is not None:
                logger.error('Response status: %s', e.response.status_code)
                logger.error('Response text: %s', e.response.text)
        except Exception:
            pass
        raise


def delete_row(table: str, pk_col: str, pk_val: Any) -> None:
    """Delete a single row by primary key. Requires service key or permissive policies."""
    url = f"{_base_url()}/rest/v1/{table}"
    import os
    key = None
    if _load_supabase_config:
        try:
            cfg = _load_supabase_config()
            if cfg and cfg.get('SUPABASE_KEY'):
                key = cfg.get('SUPABASE_KEY')
        except Exception:
            key = None
    if not key:
        key = SUPABASE.get('key') if isinstance(SUPABASE, dict) else None
    if not key:
        key = os.environ.get('SUPABASE_KEY', '')
    headers = HEADERS(key)
    # PostgREST filter: {col}=eq.{value}
    # For safety, convert value to string
    filter_expr = f"{pk_col}=eq.{pk_val}"
    try:
        resp = requests.delete(url, headers=headers, params={"" : ""}, data=None)
        # Use explicit filtered URL
        resp = requests.delete(url, headers=headers, params={filter_expr: ''})
        if resp.status_code >= 400:
            logger.error('Supabase DELETE %s returned %s: %s', url, resp.status_code, resp.text)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        try:
            logger.exception('Supabase DELETE request failed: %s', url)
            if hasattr(e, 'response') and e.response is not None:
                logger.error('Response status: %s', e.response.status_code)
                logger.error('Response text: %s', e.response.text)
        except Exception:
            pass
        raise


def delete_by_filters(table: str, filters: Dict[str, Any]) -> None:
    """Delete rows matching filters. `filters` is a mapping column->value and will be
    translated to PostgREST filter expressions like col=eq.value.
    """
    url = f"{_base_url()}/rest/v1/{table}"
    import os
    key = None
    if _load_supabase_config:
        try:
            cfg = _load_supabase_config()
            if cfg and cfg.get('SUPABASE_KEY'):
                key = cfg.get('SUPABASE_KEY')
        except Exception:
            key = None
    if not key:
        key = SUPABASE.get('key') if isinstance(SUPABASE, dict) else None
    if not key:
        key = os.environ.get('SUPABASE_KEY', '')
    headers = HEADERS(key)

    params = {}
    for k, v in filters.items():
        params[f"{k}"] = f"eq.{v}"

    try:
        resp = requests.delete(url, headers=headers, params=params)
        if resp.status_code >= 400:
            logger.error('Supabase DELETE %s returned %s: %s', url, resp.status_code, resp.text)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        try:
            logger.exception('Supabase DELETE by filters request failed: %s', url)
            if hasattr(e, 'response') and e.response is not None:
                logger.error('Response status: %s', e.response.status_code)
                logger.error('Response text: %s', e.response.text)
        except Exception:
            pass
        raise


def delete_all(table: str) -> None:
    """Delete all rows from a table. Requires service key with delete permissions."""
    url = f"{_base_url()}/rest/v1/{table}"
    import os
    key = None
    if _load_supabase_config:
        try:
            cfg = _load_supabase_config()
            if cfg and cfg.get('SUPABASE_KEY'):
                key = cfg.get('SUPABASE_KEY')
        except Exception:
            key = None
    if not key:
        key = SUPABASE.get('key') if isinstance(SUPABASE, dict) else None
    if not key:
        key = os.environ.get('SUPABASE_KEY', '')
    headers = HEADERS(key)
    # Use Prefer to return representation if desired
    try:
        resp = requests.delete(url, headers=headers)
        if resp.status_code >= 400:
            logger.error('Supabase DELETE %s returned %s: %s', url, resp.status_code, resp.text)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        try:
            logger.exception('Supabase DELETE request failed: %s', url)
            if hasattr(e, 'response') and e.response is not None:
                logger.error('Response status: %s', e.response.status_code)
                logger.error('Response text: %s', e.response.text)
        except Exception:
            pass
        raise
