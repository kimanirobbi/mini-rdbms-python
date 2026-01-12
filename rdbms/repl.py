from .executor import Executor


def repl_loop(base_dir: str = "data"):
    exe = Executor(base_dir=base_dir)
    print("mini-rdbms REPL. Enter SQL statements terminated with ';'. Type .exit to quit.")
    print("Commands: .exit, .tables, .schema <table>")
    buffer = []
    while True:
        try:
            line = input("> ")
        except EOFError:
            break
        if not line:
            continue
        stripped = line.strip()
        if stripped == ".exit":
            break
        if stripped == ".tables":
            # list tables by scanning the catalog directory
            try:
                cats = exe.catalog.base_dir
                import os

                tables = [d for d in os.listdir(cats) if os.path.isdir(os.path.join(cats, d))]
                print("Tables:", tables)
            except Exception as e:
                print("Error listing tables:", e)
            continue
        if stripped.startswith(".schema"):
            parts = stripped.split(None, 1)
            if len(parts) == 2:
                tbl = parts[1].strip()
                try:
                    schema = exe.catalog.load_schema(tbl)
                    print(schema)
                except Exception as e:
                    print("Error:", e)
            else:
                print("Usage: .schema <table>")
            continue
        buffer.append(line)
        if stripped.endswith(";"):
            sql = "\n".join(buffer)
            buffer = []
            try:
                res = exe.execute(sql)
                print(res)
            except Exception as e:
                print(f"Error: {e}")
