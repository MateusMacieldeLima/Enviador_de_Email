"""Gera e aplica um CREATE TABLE IF NOT EXISTS teste (...) com colunas aleatórias.

Uso:
  - Passe a connection string como argumento:
    python scripts/create_test_table.py "postgres://user:pass@host:5432/db"
  - Ou defina a env var `DATABASE_URL` e rode sem argumento:
    set DATABASE_URL=postgres://user:pass@host:5432/db
    python scripts/create_test_table.py

Observação: usa `psycopg2` para executar o SQL.
"""
import os
import sys
import random
import string
import argparse

def rand_name(n=6):
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(n))

def generate_columns():
    types = [
        ('int', 'INTEGER'),
        ('txt', 'TEXT'),
        ('bool', 'BOOLEAN'),
        ('ts', 'TIMESTAMP'),
        ('json', 'JSONB')
    ]
    n = random.randint(3, 6)
    cols = []
    used = set()
    for i in range(n):
        prefix, t = random.choice(types)
        name = f"{prefix}_{rand_name(4)}"
        while name in used:
            name = f"{prefix}_{rand_name(4)}"
        used.add(name)
        # Add a simple default for some types to make testing easier
        if t == 'INTEGER':
            cols.append(f"{name} {t} DEFAULT 0")
        elif t == 'TEXT':
            cols.append(f"{name} {t} DEFAULT ''")
        elif t == 'BOOLEAN':
            cols.append(f"{name} {t} DEFAULT false")
        elif t == 'TIMESTAMP':
            cols.append(f"{name} {t} DEFAULT now()")
        elif t == 'JSONB':
            cols.append(f"{name} {t} DEFAULT '{{}}'::jsonb")
    return cols

def build_create_sql(table_name='teste'):
    cols = generate_columns()
    # include id primary key
    cols_sql = ',\n  '.join(cols)
    sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n  id SERIAL PRIMARY KEY,\n  {cols_sql}\n);"
    return sql

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('db', nargs='?', help='Postgres connection string (postgres://...)')
    args = parser.parse_args()

    db_url = args.db or os.environ.get('https://boutbnbnkeipnhaedafk.supabase.co')
    if not db_url:
        print('DATABASE_URL não fornecido. Passe como argumento ou defina env var DATABASE_URL')
        sys.exit(1)

    sql = build_create_sql('teste')
    print('SQL a ser executado:\n')
    print(sql)

    try:
        import psycopg2
    except Exception:
        print('psycopg2 não instalado. Instale com: pip install psycopg2-binary')
        raise

    print('\nConectando ao banco...')
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute(sql)
        print('Tabela criada (ou já existente): teste')
    except Exception as e:
        print('Falha ao criar tabela:', e)
        raise
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass

if __name__ == '__main__':
    main()
