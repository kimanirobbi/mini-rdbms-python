from typing import Any, List, Dict

from .parser import Parser, CreateTable, Insert, Select, Update, Delete, DropTable, RenameTable
from .catalog import Catalog
from .storage import Table
from .exceptions import TableNotFound


class Executor:
    """Execute parsed statements by coordinating Catalog and Table storage.

    This is intentionally small: correctness and clarity are prioritized over
    performance or full SQL compatibility.
    """

    def __init__(self, base_dir: str = "data"):
        self.catalog = Catalog(base_dir=base_dir)
        self.parser = Parser()

    def execute(self, sql: str):
        stmt = self.parser.parse(sql)
        if stmt is None:
            return None
        if isinstance(stmt, CreateTable):
            return self._exec_create(stmt)
        if isinstance(stmt, Insert):
            return self._exec_insert(stmt)
        if isinstance(stmt, Select):
            return self._exec_select(stmt)
        if isinstance(stmt, Update):
            return self._exec_update(stmt)
        if isinstance(stmt, Delete):
            return self._exec_delete(stmt)
        if isinstance(stmt, DropTable):
            return self._exec_drop(stmt)
        if isinstance(stmt, RenameTable):
            return self._exec_rename(stmt)
        raise ValueError("Unsupported statement type")

    def _exec_create(self, stmt: CreateTable):
        schema = {
            "name": stmt.name,
            "columns": stmt.columns,
            "constraints": stmt.constraints,
            # default: create indexes for UNIQUE constraints automatically
            "indexes": [c[0] for c in stmt.constraints.get("unique", []) if c]
        }
        self.catalog.create_table(schema)
        return {"status": "OK", "table": stmt.name}

    def _exec_insert(self, stmt: Insert):
        try:
            t = Table(stmt.table, catalog=self.catalog)
        except TableNotFound:
            raise
        inserted = 0
        if isinstance(stmt.values, list):
            for row in stmt.values:
                t.insert(row)
                inserted += 1
        else:
            t.insert(stmt.values)
            inserted = 1
        return {"status": "OK", "inserted": inserted}

    def _exec_drop(self, stmt: DropTable):
        # remove table files/directories
        self.catalog.drop_table(stmt.name)
        return {"status": "OK", "dropped": stmt.name}

    def _exec_rename(self, stmt: RenameTable):
        self.catalog.rename_table(stmt.old_name, stmt.new_name)
        return {"status": "OK", "renamed": f"{stmt.old_name} -> {stmt.new_name}"}

    def _exec_update(self, stmt: Update):
        t = Table(stmt.table, catalog=self.catalog)
        # find target PKs
        targets = []
        if stmt.where:
            col = stmt.where.column.split('.')[-1]
            if col == t.pk_column:
                targets = [str(stmt.where.value)]
            elif col in t.indexes:
                targets = list(t.indexes[col].lookup(stmt.where.value))
            else:
                for rpk, r in t._rows.items():
                    if r.get(col) == stmt.where.value:
                        targets.append(rpk)
        else:
            targets = list(t._rows.keys())
        updated = 0
        for pk in targets:
            t.update(pk, stmt.changes)
            updated += 1
        return {"status": "OK", "updated": updated}

    def _exec_delete(self, stmt: Delete):
        t = Table(stmt.table, catalog=self.catalog)
        targets = []
        if stmt.where:
            col = stmt.where.column.split('.')[-1]
            if col == t.pk_column:
                targets = [str(stmt.where.value)]
            elif col in t.indexes:
                targets = list(t.indexes[col].lookup(stmt.where.value))
            else:
                for rpk, r in t._rows.items():
                    if r.get(col) == stmt.where.value:
                        targets.append(rpk)
        else:
            targets = list(t._rows.keys())
        deleted = 0
        for pk in targets:
            if t.delete(pk):
                deleted += 1
        return {"status": "OK", "deleted": deleted}

    def _exec_select(self, stmt: Select):
        # single table or join
        left = Table(stmt.table, catalog=self.catalog)
        rows = []
        if stmt.join:
            right = Table(stmt.join.right_table, catalog=self.catalog)
            # nested-loop join: for each left row find matching right rows
            for l in left.scan():
                lkey = l.get(stmt.join.left_col)
                for r in right.scan():
                    if r.get(stmt.join.right_col) == lkey:
                        merged = {**l, **{f"{stmt.join.right_table}.{k}": v for k, v in r.items()}}
                        rows.append(merged)
        else:
            # try to use index if where column is simple and indexed
            if stmt.where and '.' not in stmt.where.column and stmt.where.column in left.indexes:
                pks = left.indexes[stmt.where.column].lookup(stmt.where.value)
                for pk in pks:
                    row = left.get(pk)
                    if row is not None:
                        rows.append(row)
            else:
                # full scan + filter
                for r in left.scan():
                    if stmt.where:
                        # support table.column or column
                        col = stmt.where.column.split('.')[-1]
                        if r.get(col) == stmt.where.value:
                            rows.append(r)
                    else:
                        rows.append(r)
        # projection
        if stmt.columns == ['*'] or stmt.columns == ['*']:
            return rows
        out = []
        for r in rows:
            rec = {}
            for c in stmt.columns:
                c = c.strip()
                if c == '*':
                    rec.update(r)
                else:
                    # allow table.column
                    key = c.split('.')[-1]
                    rec[c] = r.get(key)
            out.append(rec)
        return out
