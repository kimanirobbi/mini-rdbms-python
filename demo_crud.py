from rdbms.executor import Executor

exe = Executor(base_dir="data")

print("Creating table 'items'")
exe.execute("CREATE TABLE items (id INT, name TEXT, qty INT, PRIMARY KEY (id), UNIQUE (name));")
print("Inserting rows")
exe.execute("INSERT INTO items (id, name, qty) VALUES (1, 'apple', 10);")
exe.execute("INSERT INTO items (id, name, qty) VALUES (2, 'banana', 5);")
print("Selecting all")
print(exe.execute("SELECT * FROM items;"))
print("Updating qty for id=1")
print(exe.execute("UPDATE items SET qty = 15 WHERE id = 1;"))
print("Selecting id=1")
print(exe.execute("SELECT * FROM items WHERE id = 1;"))
print("Deleting id=2")
print(exe.execute("DELETE FROM items WHERE id = 2;"))
print("Final rows")
print(exe.execute("SELECT * FROM items;"))
