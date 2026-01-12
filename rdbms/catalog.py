import json
import os
from typing import Dict, Any
import shutil

from .exceptions import SchemaError, TableNotFound


class Catalog:
    """Manage table schemas and table directories on disk.

    Each table lives in a folder under `base_dir` with `schema.json` and data/index files.
    """

    def __init__(self, base_dir: str = "data"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def table_path(self, table_name: str) -> str:
        return os.path.join(self.base_dir, table_name)

    def create_table(self, schema: Dict[str, Any]):
        name = schema.get("name")
        if not name:
            raise SchemaError("Schema must include a 'name' field")
        path = self.table_path(name)
        os.makedirs(path, exist_ok=True)
        schema_file = os.path.join(path, "schema.json")
        with open(schema_file, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2)

    def load_schema(self, table_name: str) -> Dict[str, Any]:
        path = self.table_path(table_name)
        schema_file = os.path.join(path, "schema.json")
        if not os.path.exists(schema_file):
            raise TableNotFound(f"Table '{table_name}' not found")
        with open(schema_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def drop_table(self, table_name: str):
        path = self.table_path(table_name)
        if not os.path.exists(path):
            raise TableNotFound(f"Table '{table_name}' not found")
        shutil.rmtree(path)

    def rename_table(self, old_name: str, new_name: str):
        old_path = self.table_path(old_name)
        new_path = self.table_path(new_name)
        if not os.path.exists(old_path):
            raise TableNotFound(f"Table '{old_name}' not found")
        if os.path.exists(new_path):
            raise SchemaError(f"Target table '{new_name}' already exists")
        os.rename(old_path, new_path)
        # update schema.json name field if present
        schema_file = os.path.join(new_path, "schema.json")
        if os.path.exists(schema_file):
            with open(schema_file, "r", encoding="utf-8") as f:
                schema = json.load(f)
            schema["name"] = new_name
            with open(schema_file, "w", encoding="utf-8") as f:
                json.dump(schema, f, indent=2)
