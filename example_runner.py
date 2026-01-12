"""Small example demonstrating catalog, table creation, insert, and simple lookup."""
from rdbms.catalog import Catalog
from rdbms.storage import Table


def bootstrap():
    cat = Catalog(base_dir="data")
    # simple users table schema
    users = {
        "name": "users",
        "columns": [
            {"name": "id", "type": "INT"},
            {"name": "username", "type": "TEXT"},
            {"name": "email", "type": "TEXT"},
        ],
        "constraints": {"primary_key": ["id"], "unique": [["email"]]},
        "indexes": ["email"]
    }
    cat.create_table(users)
    t = Table("users", catalog=cat)
    print("Inserting rows...")
    t.insert({"id": 1, "username": "alice", "email": "alice@example.com"})
    t.insert({"id": 2, "username": "bob", "email": "bob@example.com"})
    print("All rows:")
    for r in t.scan():
        print(r)


if __name__ == "__main__":
    bootstrap()
