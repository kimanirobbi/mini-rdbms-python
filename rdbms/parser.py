import re
from dataclasses import dataclass
from typing import List, Optional, Any, Dict


@dataclass
class CreateTable:
    name: str
    columns: List[dict]
    constraints: dict


@dataclass
class Insert:
    table: str
    # values can be a single dict for one-row insert or a list of dicts for multi-row
    values: Any


@dataclass
class Where:
    column: str
    value: Any


@dataclass
class Join:
    right_table: str
    left_col: str
    right_col: str


@dataclass
class Select:
    columns: List[str]
    table: str
    where: Optional[Where] = None
    join: Optional[Join] = None


@dataclass
class Update:
    table: str
    changes: Dict[str, Any]
    where: Optional[Where] = None


@dataclass
class Delete:
    table: str
    where: Optional[Where] = None


@dataclass
class DropTable:
    name: str


@dataclass
class RenameTable:
    old_name: str
    new_name: str


class Parser:
    """Tiny ad-hoc parser for a small subset of SQL-like syntax.

    Supported examples:
    - CREATE TABLE users (id INT, name TEXT, PRIMARY KEY (id), UNIQUE (email))
    - INSERT INTO users (id, name) VALUES (1, 'alice')
    - SELECT id, name FROM users WHERE id = 1
    - SELECT * FROM a INNER JOIN b ON a.x = b.y WHERE a.x = 5
    """

    _ws_re = re.compile(r"\s+")

    def parse(self, sql: str):
        sql = sql.strip().rstrip(";")
        if not sql:
            return None
        head = sql.split(None, 1)[0].upper()
        if head == "CREATE":
            return self._parse_create(sql)
        if head == "INSERT":
            return self._parse_insert(sql)
        if head == "SELECT":
            return self._parse_select(sql)
        if head == "UPDATE":
            return self._parse_update(sql)
        if head == "DELETE":
            return self._parse_delete(sql)
        if head == "DROP":
            return self._parse_drop(sql)
        if head == "RENAME":
            return self._parse_rename(sql)
        raise ValueError(f"Unsupported statement: {head}")

    def _parse_create(self, sql: str) -> CreateTable:
        m = re.match(r"CREATE\s+TABLE\s+(\w+)\s*\((.*)\)", sql, re.I | re.S)
        if not m:
            raise ValueError("Invalid CREATE TABLE syntax")
        name = m.group(1)
        body = m.group(2).strip()
        parts = [p.strip() for p in self._split_commas(body)]
        cols = []
        constraints = {"primary_key": None, "unique": []}
        for p in parts:
            up = p.upper()
            if up.startswith("PRIMARY KEY"):
                inner = re.search(r"\(([^)]+)\)", p)
                if inner:
                    cols_pk = [c.strip() for c in inner.group(1).split(",")]
                    constraints["primary_key"] = cols_pk
                continue
            if up.startswith("UNIQUE"):
                inner = re.search(r"\(([^)]+)\)", p)
                if inner:
                    cols_u = [c.strip() for c in inner.group(1).split(",")]
                    constraints["unique"].append(cols_u)
                continue
            # column definition: name TYPE [DEFAULT ...]
            mcol = re.match(r"(\w+)\s+(\w+)(?:\s+DEFAULT\s+(.+))?", p, re.I)
            if not mcol:
                raise ValueError(f"Invalid column definition: {p}")
            col_name = mcol.group(1)
            col_type = mcol.group(2)
            default = None
            if mcol.group(3):
                d = mcol.group(3).strip()
                # strip surrounding quotes for string defaults
                if d.startswith("'") and d.endswith("'"):
                    default = d[1:-1]
                else:
                    # canonicalize CURRENT_DATE/CURRENT_TIMESTAMP
                    up = d.upper()
                    if up in ("CURRENT_DATE", "CURRENT_TIMESTAMP"):
                        default = up
                    else:
                        # try numeric
                        try:
                            if '.' in d:
                                default = float(d)
                            else:
                                default = int(d)
                        except Exception:
                            default = d
            col = {"name": col_name, "type": col_type}
            if default is not None:
                col["default"] = default
            cols.append(col)
        return CreateTable(name=name, columns=cols, constraints=constraints)

    def _split_commas(self, s: str) -> List[str]:
        parts = []
        cur = []
        depth = 0
        for ch in s:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            if ch == ',' and depth == 0:
                parts.append(''.join(cur))
                cur = []
            else:
                cur.append(ch)
        if cur:
            parts.append(''.join(cur))
        return parts

    def _parse_insert(self, sql: str) -> Insert:
        # very small parser: INSERT INTO table (col,...) VALUES (v,...)
        m = re.match(r"INSERT\s+INTO\s+(\w+)\s*\(([^)]+)\)\s+VALUES\s*(.*)$", sql, re.I | re.S)
        if not m:
            raise ValueError("Invalid INSERT syntax")
        table = m.group(1)
        cols = [c.strip() for c in m.group(2).split(",")]
        values_block = m.group(3).strip()
        # remove trailing semicolon if present
        if values_block.endswith(";"):
            values_block = values_block[:-1].strip()
        # support multi-row: values_block may be like "(1, 'a'), (2, 'b')"
        # split into top-level tuple strings
        tuples = self._split_commas(values_block)
        rows = []
        for t in tuples:
            t = t.strip()
            if t.startswith('(') and t.endswith(')'):
                inner = t[1:-1].strip()
            else:
                inner = t
            vals = self._parse_values_list(inner)
            if len(cols) != len(vals):
                raise ValueError("Column count does not match value count")
            data = {c: v for c, v in zip(cols, vals)}
            rows.append(data)
        if len(rows) == 1:
            return Insert(table=table, values=rows[0])
        return Insert(table=table, values=rows)

    def _parse_values_list(self, s: str):
        parts = self._split_commas(s)
        vals = []
        for p in parts:
            p = p.strip()
            if p.startswith("'") and p.endswith("'"):
                vals.append(p[1:-1])
            elif p.upper() in ("TRUE", "FALSE"):
                vals.append(p.upper() == "TRUE")
            else:
                try:
                    if '.' in p:
                        vals.append(float(p))
                    else:
                        vals.append(int(p))
                except Exception:
                    vals.append(p)
        return vals

    def _parse_select(self, sql: str) -> Select:
        # basic: SELECT cols FROM table [INNER JOIN other ON a.b = c.d] [WHERE expr]
        # This is intentionally simple and brittle—good enough for demo.
        where = None
        join = None
        # split WHERE
        parts = re.split(r"\bWHERE\b", sql, flags=re.I)
        main = parts[0].strip()
        if len(parts) > 1:
            cond = parts[1].strip()
            mwhere = re.match(r"(\w+(?:\.\w+)?)\s*=\s*(.+)$", cond)
            if mwhere:
                col = mwhere.group(1).strip()
                val = mwhere.group(2).strip()
                if val.startswith("'") and val.endswith("'"):
                    val = val[1:-1]
                else:
                    try:
                        val = int(val)
                    except Exception:
                        try:
                            val = float(val)
                        except Exception:
                            if val.upper() in ("TRUE", "FALSE"):
                                val = val.upper() == "TRUE"
                where = Where(column=col, value=val)
        # handle SELECT ... FROM ... [INNER JOIN]
        m = re.match(r"SELECT\s+(.*?)\s+FROM\s+(\w+)(.*)$", main, re.I | re.S)
        if not m:
            raise ValueError("Invalid SELECT syntax")
        cols = [c.strip() for c in m.group(1).split(",")]
        table = m.group(2)
        rest = m.group(3).strip()
        if rest:
            mj = re.search(r"INNER\s+JOIN\s+(\w+)\s+ON\s+(\w+\.\w+)\s*=\s*(\w+\.\w+)", rest, re.I)
            if mj:
                right = mj.group(1)
                leftcol = mj.group(2)
                rightcol = mj.group(3)
                # leftcol like a.x; strip table prefixes
                left_col_name = leftcol.split('.', 1)[1] if '.' in leftcol else leftcol
                right_col_name = rightcol.split('.', 1)[1] if '.' in rightcol else rightcol
                join = Join(right_table=right, left_col=left_col_name, right_col=right_col_name)
        return Select(columns=cols, table=table, where=where, join=join)

    def _parse_update(self, sql: str) -> Update:
        # UPDATE <table> SET col = val, ... WHERE col = val
        m = re.match(r"UPDATE\s+(\w+)\s+SET\s+(.*?)\s*(?:WHERE\s+(.*))?$", sql, re.I | re.S)
        if not m:
            raise ValueError("Invalid UPDATE syntax")
        table = m.group(1)
        set_clause = m.group(2)
        where_clause = m.group(3)
        changes = {}
        for part in self._split_commas(set_clause):
            left, right = part.split("=", 1)
            key = left.strip()
            val = right.strip()
            if val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            else:
                try:
                    if '.' in val:
                        val = float(val)
                    else:
                        val = int(val)
                except Exception:
                    if val.upper() in ("TRUE", "FALSE"):
                        val = val.upper() == "TRUE"
            changes[key] = val
        where = None
        if where_clause:
            mwhere = re.match(r"(\w+(?:\.\w+)?)\s*=\s*(.+)$", where_clause.strip())
            if mwhere:
                col = mwhere.group(1).strip()
                val = mwhere.group(2).strip()
                if val.startswith("'") and val.endswith("'"):
                    val = val[1:-1]
                else:
                    try:
                        val = int(val)
                    except Exception:
                        try:
                            val = float(val)
                        except Exception:
                            if val.upper() in ("TRUE", "FALSE"):
                                val = val.upper() == "TRUE"
                where = Where(column=col, value=val)
        return Update(table=table, changes=changes, where=where)

    def _parse_delete(self, sql: str) -> Delete:
        # DELETE FROM <table> [WHERE col = val]
        m = re.match(r"DELETE\s+FROM\s+(\w+)\s*(?:WHERE\s+(.*))?$", sql, re.I | re.S)
        if not m:
            raise ValueError("Invalid DELETE syntax")
        table = m.group(1)
        where_clause = m.group(2)
        where = None
        if where_clause:
            mwhere = re.match(r"(\w+(?:\.\w+)?)\s*=\s*(.+)$", where_clause.strip())
            if mwhere:
                col = mwhere.group(1).strip()
                val = mwhere.group(2).strip()
                if val.startswith("'") and val.endswith("'"):
                    val = val[1:-1]
                else:
                    try:
                        val = int(val)
                    except Exception:
                        try:
                            val = float(val)
                        except Exception:
                            if val.upper() in ("TRUE", "FALSE"):
                                val = val.upper() == "TRUE"
                where = Where(column=col, value=val)
        return Delete(table=table, where=where)

    def _parse_drop(self, sql: str) -> DropTable:
        m = re.match(r"DROP\s+TABLE\s+(\w+)\s*;?$", sql.strip(), re.I)
        if not m:
            raise ValueError("Invalid DROP TABLE syntax")
        return DropTable(name=m.group(1))

    def _parse_rename(self, sql: str) -> RenameTable:
        # support: RENAME TABLE old TO new;
        m = re.match(r"RENAME\s+TABLE\s+(\w+)\s+TO\s+(\w+)\s*;?$", sql.strip(), re.I)
        if not m:
            # support ALTER TABLE old RENAME TO new
            m2 = re.match(r"ALTER\s+TABLE\s+(\w+)\s+RENAME\s+TO\s+(\w+)\s*;?$", sql.strip(), re.I)
            if not m2:
                raise ValueError("Invalid RENAME syntax")
            return RenameTable(old_name=m2.group(1), new_name=m2.group(2))
        return RenameTable(old_name=m.group(1), new_name=m.group(2))
