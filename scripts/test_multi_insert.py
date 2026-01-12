from rdbms.executor import Executor

exe = Executor(base_dir='data')

print('Creating table bots (may overwrite schema)')
try:
    exe.execute("CREATE TABLE bots (ProductID INT, ProductName TEXT, Price FLOAT, PRIMARY KEY (ProductID));")
    print('Created')
except Exception as e:
    print('Create error:', e)

sql = "INSERT INTO bots (ProductID, ProductName, Price) VALUES (1, 'Laptop', 1200.00), (2, 'Mouse', 25.50), (3, 'Keyboard', 75.00);"
print('Running insert:')
try:
    res = exe.execute(sql)
    print('Insert result:', res)
except Exception as e:
    print('Insert error:', e)

print('Selecting rows:')
try:
    rows = exe.execute('SELECT * FROM bots;')
    print(rows)
except Exception as e:
    print('Select error:', e)
