import json
import os
from typing import Dict, Any, Optional, List
from datetime import date, datetime

from .catalog import Catalog
from .exceptions import ConstraintViolation, TableNotFound
from .index import Index
from .types import coerce_value


class Table:
    """Represents a single table: schema, data file, and indexes.

    Data is stored in JSONL where each line is a JSON row. A primary-key index
    is kept in memory for quick lookups; other indexes are persisted via `Index`.
    """

    def __init__(self, name: str, catalog: Optional[Catalog] = None):
        self.name = name
        self.catalog = catalog or Catalog()
        self.path = self.catalog.table_path(name)
        if not os.path.exists(self.path):
            raise TableNotFound(f"Table '{name}' not found")
        self.schema = self.catalog.load_schema(name)
        self.data_file = os.path.join(self.path, "data.jsonl")
        self.pk_column = None
        self.columns = {c["name"]: c for c in self.schema.get("columns", [])}
        # determine primary key
        pk = self.schema.get("constraints", {}).get("primary_key")
        if pk:
            if len(pk) != 1:
                raise ValueError("Only single-column primary keys supported in this demo")
            self.pk_column = pk[0]
        # load data into memory structures
        self._rows: Dict[str, Dict[str, Any]] = {}
        self._load_data()
        # indexes
        self.indexes: Dict[str, Index] = {}
        for col in self.schema.get("indexes", []):
            idx_path = os.path.join(self.path, f"index_{col}.json")
            self.indexes[col] = Index(idx_path, col)

    def _load_data(self):
        if not os.path.exists(self.data_file):
            self._rows = {}
            return
        rows: Dict[str, Dict[str, Any]] = {}
        with open(self.data_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if self.pk_column is None:
                    # assign synthetic pk by line number (not ideal)
                    raise ValueError("Tables must have a primary key for this storage layer")
                pk = str(obj.get(self.pk_column))
                rows[pk] = obj
        self._rows = rows

    def _persist_all(self):
        # rewrite entire data file from in-memory rows
        with open(self.data_file + ".tmp", "w", encoding="utf-8") as f:
            for row in self._rows.values():
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        os.replace(self.data_file + ".tmp", self.data_file)

    def insert(self, row: Dict[str, Any]):
        # coerce types and validate
        if self.pk_column is None:
            raise ValueError("Table has no primary key defined")
        pk_val = row.get(self.pk_column)
        if pk_val is None:
            raise ConstraintViolation(f"Primary key '{self.pk_column}' must be provided")
        pk = str(coerce_value(pk_val, self.columns[self.pk_column]["type"]))
        if pk in self._rows:
            raise ConstraintViolation(f"PRIMARY KEY violation: {pk} already exists")
        # check uniqueness for indexed columns (single-column UNIQUE support)
        for col, idx in self.indexes.items():
            v = row.get(col, self.columns[col].get("default"))
            # support CURRENT_DATE / CURRENT_TIMESTAMP default tokens
            if v == "CURRENT_DATE":
                v = date.today().isoformat()
            elif v == "CURRENT_TIMESTAMP":
                v = datetime.now().replace(microsecond=0).isoformat()
            if v is not None:
                try:
                    if idx.lookup(v):
                        raise ConstraintViolation(f"UNIQUE constraint violation on column '{col}': {v}")
                except Exception:
                    pass
        # coerce other columns
        record: Dict[str, Any] = {}
        for name, col in self.columns.items():
            val = row.get(name, col.get("default"))
            # support CURRENT_DATE / CURRENT_TIMESTAMP default tokens
            if val == "CURRENT_DATE":
                val = date.today().isoformat()
            elif val == "CURRENT_TIMESTAMP":
                val = datetime.now().replace(microsecond=0).isoformat()
            if val is None:
                record[name] = None
            else:
                record[name] = coerce_value(val, col["type"])
        # persist append
        with open(self.data_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._rows[pk] = record
        # update indexes
        for col, idx in self.indexes.items():
            idx.add(record.get(col), pk)

    def get(self, pk: Any) -> Optional[Dict[str, Any]]:
        return self._rows.get(str(pk))

    def scan(self) -> List[Dict[str, Any]]:
        return list(self._rows.values())

    def delete(self, pk: Any):
        pk = str(pk)
        if pk not in self._rows:
            return False
        row = self._rows.pop(pk)
        # update indexes
        for col, idx in self.indexes.items():
            idx.remove(row.get(col), pk)
        self._persist_all()
        return True

    def update(self, pk: Any, changes: Dict[str, Any]):
        pk = str(pk)
        if pk not in self._rows:
            raise KeyError(f"Row with pk={pk} not found")
        row = self._rows[pk]
        # apply changes with coercion
        for name, val in changes.items():
            if name not in self.columns:
                raise KeyError(f"Unknown column {name}")
            newv = None if val is None else coerce_value(val, self.columns[name]["type"])
            # enforce uniqueness on indexed columns
            if name in self.indexes:
                existing = self.indexes[name].lookup(newv)
                # if there's any other pk with this value, violation
                if existing and not (len(existing) == 1 and pk in existing):
                    raise ConstraintViolation(f"UNIQUE constraint violation on column '{name}': {newv}")
                self.indexes[name].remove(row.get(name), pk)
                self.indexes[name].add(newv, pk)
            row[name] = newv
        self._persist_all()
