"""Versioned PostgreSQL schemas; publication is a single authoritative pointer."""
import json
import os
from pathlib import Path
import psycopg
from psycopg import sql
from .core import CONTRACTS,write_csv,json_write

def connect(root):
    dsn=os.environ.get('REVPULSE_DATABASE_URL')
    if dsn:return psycopg.connect(dsn)
    config=Path(root)/'.local/database.json'
    if not config.exists():raise ValueError('Set REVPULSE_DATABASE_URL or run scripts/setup_postgres.py')
    return psycopg.connect(**json.loads(config.read_text()))

def load(conn,root,schema,tables,audit):
    conn.execute('CREATE EXTENSION IF NOT EXISTS btree_gist')
    conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    conn.execute(sql.SQL('SET search_path TO {},public').format(sql.Identifier(schema)))
    conn.execute((Path(root)/'sql/migrations/001_core.sql').read_text())
    for table,fields in CONTRACTS.items():
        query=sql.SQL('COPY {} ({}) FROM STDIN').format(sql.Identifier(table),sql.SQL(',').join(map(sql.Identifier,fields)))
        with conn.cursor().copy(query) as copy:
            for row in tables[table]:copy.write_row([row.get(c) for c in fields])
    with conn.cursor().copy('COPY source_lineage FROM STDIN') as copy:
        for r in audit:copy.write_row([r['table'],r['source_row'],r['key'],r['disposition'],r['reason'],r['original_json']])

def query_export(conn,query,path):
    cur=conn.execute(query);fields=[c.name for c in cur.description]
    rows=[dict(zip(fields,row)) for row in cur.fetchall()]
    write_csv(path,rows,fields)
    return rows
