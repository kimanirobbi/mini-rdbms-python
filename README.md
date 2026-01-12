
mini-rdbms-python
=================

A small educational RDBMS implemented in Python for portfolio/demo purposes.

Design summary
- Parser: ad-hoc handwritten parser supporting CREATE TABLE, INSERT, SELECT, UPDATE, DELETE, and simple INNER JOIN with equality predicates.
- Storage: per-table directory under data/ with schema.json, data.jsonl (newline-delimited JSON rows), and index files index_<col>.json.
- Indexes: simple hash-based value -> list of primary keys persisted as JSON.
- Executor: coordinates catalog, storage and indexes to run statements and enforce PRIMARY KEY and single-column UNIQUE constraints.
- REPL: interactive shell in `rdbms/repl.py`.
- Demo webapp: minimal Flask app in `webapp/app.py` that exposes a SQL console and table viewer.

Supported SQL subset
- CREATE TABLE name (col TYPE, ..., PRIMARY KEY (col), UNIQUE (col))
- INSERT INTO table (cols...) VALUES (vals...)
- SELECT cols FROM table [INNER JOIN table2 ON a.col = b.col] [WHERE col = value]
- UPDATE table SET col = value [, ...] [WHERE col = value]
- DELETE FROM table [WHERE col = value]

Limitations and trade-offs
- Single-column PRIMARY KEY only.
- UNIQUE enforcement implemented for single columns only and via index checks.
- No transactions, concurrency control, or WAL. Not suitable for production.
- Data stored as JSONL for clarity and simplicity (not optimized for large datasets).
- Parser is minimal and not robust for complex SQL.

Quick start
1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the example scripts to create demo tables and try CRUD:

```bash
python example_runner.py
python demo_crud.py
```

3. Run the web demo:

```bash
python webapp/app.py
# then open http://127.0.0.1:5000
```

Project structure
- `rdbms/` core library: `catalog.py`, `storage.py`, `index.py`, `parser.py`, `executor.py`, `repl.py`, `types.py`, `exceptions.py`.
- `webapp/app.py` minimal Flask demo.
- `example_runner.py`, `demo_crud.py` - small scripts that exercise the system.

Credits
- AI-assisted development (code suggestions) — see project notes.
