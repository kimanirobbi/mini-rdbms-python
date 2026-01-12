from flask import Flask, request, render_template_string, redirect, url_for
from datetime import date, datetime
import re


def _format_display_value(v):
    if v is None:
        return ''
    # try TIMESTAMP
    if isinstance(v, str):
        s = v
        # ISO datetime with T
        try:
            if 'T' in s:
                dt = datetime.fromisoformat(s)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            # ISO date
            if re.match(r'^\d{4}-\d{2}-\d{2}$', s):
                d = datetime.fromisoformat(s)
                return d.strftime('%Y-%m-%d')
        except Exception:
            pass
    return str(v)
from rdbms.executor import Executor

app = Flask(__name__)
exe = Executor(base_dir="data")

INDEX_HTML = """
<!doctype html>
<html>
<head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <title>mini-rdbms demo</title>
        <style>body { background:#f8f9fa }</style>
        </head>
<body>
            <div class="d-flex">
                <button id="darkToggle" class="btn btn-outline-light btn-sm me-2">Dark</button>
            </div>
        </div>
    </div>
</nav>
<div class="container py-4">
        <div class="card mb-4">
            <div class="card-body">
                <h4 class="card-title">SQL Console</h4>
                <form method="post" action="/execute">
                        <div class="mb-3">
                                <textarea name="sql" class="form-control" rows="4">SELECT * FROM users;</textarea>
                        </div>
                        <button class="btn btn-primary" type="submit">Execute</button>
                </form>
            </div>
        </div>
        <div class="d-flex justify-content-between align-items-center mb-2">
                <h3>Tables</h3>
                <div>
                        <a class="btn btn-primary" href="/table/create">Create Table</a>
                </div>
        </div>
        <div class="list-group">
        {% for t in tables %}
                <div class="list-group-item d-flex justify-content-between align-items-center">
                        <div><a href="/table/{{t}}">{{t}}</a></div>
                        <div>
                                <a class="btn btn-sm btn-outline-secondary me-1" href="/table/{{t}}/rename">Rename</a>
                                <form method="post" action="/table/{{t}}/drop" style="display:inline" onsubmit="return confirm('Drop table {{t}}? This will delete all data.');">
                                        <button class="btn btn-sm btn-outline-danger" type="submit">Drop</button>
                                </form>
                        </div>
                </div>
        {% endfor %}
        </div>
</div>
</body>
</html>
"""

# Attach global UI script/CSS to templates so dark-mode works across pages
GLOBAL_UI_SCRIPT = """
<script>
// Dark mode toggle and persistence
(function(){
    const btnId = 'darkToggle';
    function applyMode(mode){
        if(mode === 'dark'){
            document.documentElement.classList.add('dark-mode');
            localStorage.setItem('mini_rdbms_theme','dark');
            const b = document.getElementById(btnId); if(b) b.textContent='Light';
            if(b) b.classList.remove('btn-outline-light'); b && b.classList.add('btn-light');
        } else {
            document.documentElement.classList.remove('dark-mode');
            localStorage.setItem('mini_rdbms_theme','light');
            const b = document.getElementById(btnId); if(b) b.textContent='Dark';
            if(b) b.classList.remove('btn-light'); b && b.classList.add('btn-outline-light');
        }
    }
    document.addEventListener('DOMContentLoaded', ()=>{
        const pref = localStorage.getItem('mini_rdbms_theme') || 'light';
        applyMode(pref);
        let btn = document.getElementById(btnId);
        if(!btn){
            // create floating toggle if page has no navbar button
            btn = document.createElement('button');
            btn.id = btnId;
            btn.className = 'btn btn-sm btn-outline-secondary';
            btn.style.position = 'fixed';
            btn.style.right = '12px';
            btn.style.bottom = '12px';
            btn.style.zIndex = '9999';
            document.body.appendChild(btn);
        }
        if(btn) btn.addEventListener('click', ()=> applyMode(document.documentElement.classList.contains('dark-mode') ? 'light' : 'dark'));
    });
})();
</script>
<style>
/* simple dark mode overrides */
.dark-mode body { background:#0f1720; color:#e6eef6 }
.dark-mode .card { background:#0b1220; color:#e6eef6 }
.dark-mode .table { color:#e6eef6 }
.dark-mode .list-group-item { background:#0b1220; color:#e6eef6 }
.dark-mode .form-control { background:#0f1726; color:#e6eef6; border-color:#243040 }
.dark-mode .navbar { background:#071018 !important }
.dark-mode pre { background:#081018; color:#dbeafe }
</style>
"""

# Insert `GLOBAL_UI_SCRIPT` before the closing </body></html> so it executes inside the page
INDEX_HTML = INDEX_HTML.replace("</body>\n</html>", GLOBAL_UI_SCRIPT + "\n</body>\n</html>")
TABLE_HTML = TABLE_HTML.replace("</body>\n</html>", GLOBAL_UI_SCRIPT + "\n</body>\n</html>")
FORM_HTML = FORM_HTML.replace("</body>\n</html>", GLOBAL_UI_SCRIPT + "\n</body>\n</html>")
CREATE_TABLE_HTML = CREATE_TABLE_HTML.replace("</body>\n</html>", GLOBAL_UI_SCRIPT + "\n</body>\n</html>")



TABLE_HTML = """
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <title>Table: {{table}}</title>
</head>
<body class="p-4">
<div class="container py-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <div>
            <a class="btn btn-secondary me-2" href="/">Back</a>
            <a class="btn btn-success" href="/table/{{table}}/insert">Insert New</a>
        </div>
        <h1 class="mb-0">Table: {{table}}</h1>
    </div>
    <div class="card">
      <div class="card-body">
        <h5 class="card-title">Rows</h5>
        <div class="table-responsive">
        <table class="table table-striped">
    <thead>
    <tr>
    {% for h in headers %}
        <th>{{h}}</th>
    {% endfor %}
        <th>Actions</th>
    </tr>
    </thead>
    <tbody>
    {% for r in rows %}
    <tr>
    {% for h in headers %}
        <td>{{ r.get(h) }}</td>
    {% endfor %}
        <td>
            <a class="btn btn-sm btn-primary" href="/table/{{table}}/edit/{{ rows_raw[loop.index0].get(headers[0]) }}">Edit</a>
            <form method="post" action="/table/{{table}}/delete/{{ rows_raw[loop.index0].get(headers[0]) }}" style="display:inline">
                <button class="btn btn-sm btn-danger" type="submit">Delete</button>
            </form>
        </td>
    </tr>
    {% endfor %}
    </tbody>
        </table>
        </div>
      </div>
    </div>
</div>
</body>
</html>
"""

FORM_HTML = """
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <title>{{title}}</title>
</head>
<body class="p-4">
<div class="container">
    <h1>{{title}}</h1>
        <form method="post">
        {% for col in columns %}
                <div class="mb-3">
                        <label class="form-label">{{col.name}}</label>
                        {% set t = (col.type or '').upper() %}
                        {% if t == 'INT' %}
                            <input class="form-control" type="number" step="1" name="{{col.name}}" value="{{ values.get(col.name, '') }}" {% if primary_key and col.name==primary_key %}readonly{% endif %}>
                        {% elif t == 'FLOAT' %}
                            <input class="form-control" type="number" step="any" name="{{col.name}}" value="{{ values.get(col.name, '') }}" {% if primary_key and col.name==primary_key %}readonly{% endif %}>
                        {% elif t == 'BOOL' %}
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" name="{{col.name}}" value="1" id="chk_{{col.name}}" {% if values.get(col.name) in [True, 'True', 'true', '1', 1] %}checked{% endif %}>
                                <label class="form-check-label" for="chk_{{col.name}}">True</label>
                            </div>
                        {% elif t == 'TIMESTAMP' %}
                            <div class="d-flex gap-2 align-items-center">
                                <input class="form-control" type="datetime-local" name="{{col.name}}" value="{{ (values.get(col.name) or '')[:16] }}" {% if primary_key and col.name==primary_key %}readonly{% endif %}>
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" name="use_now_{{col.name}}" id="use_now_{{col.name}}" {% if values.get(col.name) == 'CURRENT_TIMESTAMP' %}checked{% endif %}>
                                    <label class="form-check-label small" for="use_now_{{col.name}}">Use current time</label>
                                </div>
                            </div>
                            <div><small class="text-muted">Tip: checking 'Use current time' stores a token evaluated on insert/update; leaving blank auto-fills current time at submit; entering a time uses that specific timestamp.</small></div>
                        {% elif t == 'DATE' %}
                            <div class="d-flex gap-2 align-items-center">
                                <input class="form-control" type="date" name="{{col.name}}" value="{{ values.get(col.name, '') }}" {% if primary_key and col.name==primary_key %}readonly{% endif %}>
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" name="use_today_{{col.name}}" id="use_today_{{col.name}}" {% if values.get(col.name) == 'CURRENT_DATE' %}checked{% endif %}>
                                    <label class="form-check-label small" for="use_today_{{col.name}}">Use today's date</label>
                                </div>
                            </div>
                            <div><small class="text-muted">Tip: checking 'Use today's date' stores a token evaluated on insert/update; leaving blank auto-fills today's date at submit time; entering a date uses that specific date.</small></div>
                        {% else %}
                            <input class="form-control" type="text" name="{{col.name}}" value="{{ values.get(col.name, '') }}" {% if primary_key and col.name==primary_key %}readonly{% endif %}>
                        {% endif %}
                </div>
        {% endfor %}
        <button class="btn btn-primary" type="submit">Submit</button>
        <a class="btn btn-secondary" href="/table/{{table}}">Cancel</a>
    </form>
</div>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    import os

    cats = exe.catalog.base_dir
    tables = [d for d in os.listdir(cats) if os.path.isdir(os.path.join(cats, d))]
    return render_template_string(INDEX_HTML, tables=tables)

@app.route("/execute", methods=["POST"])
def execute():
    sql = request.form.get("sql")
    try:
        res = exe.execute(sql)
    except Exception as e:
        res = {"error": str(e)}

    # render nicely: errors as alert, lists as tables, dicts as key/value
    RESULT_HTML = """
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <title>Result</title>
    </head>
    <body class="p-4">
    <div class="container">
        <a href="/" class="btn btn-secondary mb-3">Back</a>
        <h3>Executed SQL</h3>
        <pre class="bg-light p-3">{{sql}}</pre>
        {% if res.error %}
            <div class="alert alert-danger">{{ res.error }}</div>
        {% else %}
            {% if res is mapping and res.status %}
                <div class="alert alert-success">Status: {{ res.status }}{% if res.inserted is defined %} — inserted {{res.inserted}}{% endif %}{% if res.updated is defined %} — updated {{res.updated}}{% endif %}{% if res.deleted is defined %} — deleted {{res.deleted}}{% endif %}</div>
                <pre>{{ res }}</pre>
            {% elif res is sequence and res|length>0 and res[0] is mapping %}
                <h4>Rows ({{ res|length }})</h4>
                <table class="table table-striped">
                    <thead><tr>{% for h in headers %}<th>{{h}}</th>{% endfor %}</tr></thead>
                    <tbody>
                    {% for r in res %}
                        <tr>{% for h in headers %}<td>{{ r.get(h) }}</td>{% endfor %}</tr>
                    {% endfor %}
                    </tbody>
                </table>
            {% else %}
                <pre>{{ res }}</pre>
            {% endif %}
        {% endif %}
    </div>
    </body>
    </html>
    """

    headers = []
    if isinstance(res, list) and res and isinstance(res[0], dict):
        # format values for display
        formatted = []
        keys = set()
        for r in res:
            keys.update(r.keys())
            formatted.append({k: _format_display_value(v) for k, v in r.items()})
        headers = sorted(keys)
        res = formatted

    return render_template_string(RESULT_HTML + GLOBAL_UI_SCRIPT, res=res, sql=sql, headers=headers)
    

@app.route("/table/<table>")
def show_table(table):
    try:
        rows_raw = exe.execute(f"SELECT * FROM {table};")
        rows = []
        if isinstance(rows_raw, list):
            for r in rows_raw:
                rows.append({k: _format_display_value(v) for k, v in r.items()})
    except Exception as e:
        rows_raw = []
        rows = []
    headers = []
    if rows and isinstance(rows, list):
        # collect union of keys
        keys = set()
        for r in rows:
            keys.update(r.keys())
        headers = sorted(keys)
    # also pass raw rows for action links (preserve original PK values)
    return render_template_string(TABLE_HTML, table=table, rows=rows, headers=headers, rows_raw=rows_raw)


def _format_value_for_sql(val, typ):
    if val is None or val == "":
        return 'NULL'
    typ = typ.upper()
    if typ == 'TEXT':
        s = str(val).replace("'", "\\'")
        return f"'{s}'"
    if typ == 'BOOL':
        if str(val).lower() in ('1', 'true', 't', 'yes'):
            return 'TRUE'
        return 'FALSE'
    return str(val)


CREATE_TABLE_HTML = """
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <title>Create Table</title>
    <script>
        let nextIdx = 0;
        function makeRow(idx){
            return `
                <div class="row g-2 mb-2" id="col_row_${idx}">
                    <div class="col-4"><input class="form-control" name="col_name_${idx}" placeholder="column_name"></div>
                    <div class="col-3">
                        <select class="form-select" name="col_type_${idx}">
                            <option>TEXT</option>
                            <option>INT</option>
                            <option>FLOAT</option>
                            <option>BOOL</option>
                            <option>DATE</option>
                        </select>
                    </div>
                    <div class="col-3"><input class="form-control" name="col_default_${idx}" placeholder="default (optional)"></div>
                    <div class="col-2 d-flex gap-2 align-items-center">
                        <div class="form-check"><input class="form-check-input" type="radio" name="pk_col" value="${idx}"></div>
                        <div class="form-check"><input class="form-check-input" type="checkbox" name="col_index_${idx}"></div>
                        <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeRow(${idx})">Remove</button>
                    </div>
                </div>`;
        }
        function addColumnRow(){
            const tbl = document.getElementById('cols');
            tbl.insertAdjacentHTML('beforeend', makeRow(nextIdx));
            nextIdx += 1;
        }
        function removeRow(idx){
            const el = document.getElementById('col_row_' + idx);
            if(el) el.remove();
        }
        function validateAndPrepare(form){
            // remove any rows with empty column names
            const names = form.querySelectorAll('[name^="col_name_"]');
            let hasCol = false;
            names.forEach(n => {
                if(!n.value.trim()){
                    const row = n.closest('.row');
                    if(row) row.remove();
                } else {
                    hasCol = true;
                }
            });
            if(!form.table_name.value.trim()){
                alert('Table name is required');
                return false;
            }
            if(!hasCol){
                alert('Add at least one column with a name');
                return false;
            }
            return true;
        }
        document.addEventListener('DOMContentLoaded', ()=>{
            // initialize with one row
            addColumnRow();
        });
    </script>
</head>
<body class="p-4">
<div class="container">
    <h1>Create Table</h1>
    <form method="post" onsubmit="return validateAndPrepare(this)">
        <div class="mb-3">
            <label class="form-label">Table name</label>
            <input class="form-control" name="table_name">
        </div>
        <div id="cols"></div>
        <div class="mb-3">
            <button type="button" class="btn btn-outline-secondary" onclick="addColumnRow()">Add column</button>
        </div>
        <div class="mb-3">
            <small class="text-muted">Select the radio in the column you want to be the primary key. Check box to create an index for that column. Use Remove to drop a column row before submitting.</small>
        </div>
        <button class="btn btn-primary" type="submit">Create Table</button>
        <a class="btn btn-secondary" href="/">Cancel</a>
    </form>
</div>
</body>
</html>
"""

# Attach global UI script/CSS to templates so dark-mode works across pages
INDEX_HTML = INDEX_HTML + GLOBAL_UI_SCRIPT
TABLE_HTML = TABLE_HTML + GLOBAL_UI_SCRIPT
FORM_HTML = FORM_HTML + GLOBAL_UI_SCRIPT
CREATE_TABLE_HTML = CREATE_TABLE_HTML + GLOBAL_UI_SCRIPT


@app.route('/table/<table>/insert', methods=['GET', 'POST'])
def insert_row(table):
    schema = exe.catalog.load_schema(table)
    cols = schema.get('columns', [])
    pk_col = schema.get('constraints', {}).get('primary_key', [None])[0]
    if request.method == 'POST':
        values = {}
        for c in cols:
            values[c['name']] = request.form.get(c['name'])
        # handle DATE options: explicit 'use today' checkbox or autofill when empty
        for c in cols:
            name = c['name']
            t = (c.get('type') or '').upper()
            if t == 'DATE':
                if request.form.get(f"use_today_{name}"):
                    values[name] = 'CURRENT_DATE'
                elif not values.get(name):
                    values[name] = date.today().isoformat()
            if t == 'TIMESTAMP':
                if request.form.get(f"use_now_{name}"):
                    values[name] = 'CURRENT_TIMESTAMP'
                elif not values.get(name):
                    values[name] = datetime.now().replace(microsecond=0).isoformat()
                else:
                    # browser datetime-local posts like 'YYYY-MM-DDTHH:MM', append seconds if missing
                    v = values[name]
                    if 'T' in v and len(v) == 16:
                        values[name] = v + ':00'
        # build INSERT statement
        col_names = ', '.join([c['name'] for c in cols])
        vals = ', '.join([_format_value_for_sql(values[c['name']], c['type']) for c in cols])
        sql = f"INSERT INTO {table} ({col_names}) VALUES ({vals});"
        try:
            exe.execute(sql)
            return redirect(url_for('show_table', table=table))
        except Exception as e:
            # For insert, allow editing PK (do not mark readonly)
            return render_template_string(FORM_HTML, title=f"Insert into {table}", columns=cols, values=values, table=table, error=str(e), primary_key=None)
    # For insert form, allow editing primary key
    return render_template_string(FORM_HTML, title=f"Insert into {table}", columns=cols, values={}, table=table, primary_key=None)


@app.route('/table/<table>/rename', methods=['GET', 'POST'])
def rename_table(table):
        if request.method == 'POST':
                new_name = request.form.get('new_name')
                if not new_name:
                        return render_template_string("<div class='alert alert-danger'>New name required</div><a href='/' class='btn btn-secondary'>Back</a>")
                try:
                        exe.execute(f"RENAME TABLE {table} TO {new_name};")
                        return redirect(url_for('index'))
                except Exception as e:
                        return render_template_string("<div class='alert alert-danger'>{{err}}</div><a href='/' class='btn btn-secondary'>Back</a>", err=str(e))
        # GET: simple form
        RENAME_HTML = """
        <!doctype html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <title>Rename table</title>
        </head>
        <body class="p-4">
        <div class="container">
            <h1>Rename table '{{table}}'</h1>
            <form method="post">
                <div class="mb-3">
                    <label class="form-label">New name</label>
                    <input class="form-control" name="new_name">
                </div>
                <button class="btn btn-primary" type="submit">Rename</button>
                <a class="btn btn-secondary" href="/">Cancel</a>
            </form>
        </div>
        </body>
        </html>
        """
        return render_template_string(RENAME_HTML, table=table)


@app.route('/table/<table>/drop', methods=['POST'])
def drop_table(table):
        try:
                exe.execute(f"DROP TABLE {table};")
        except Exception as e:
                return render_template_string("<div class='alert alert-danger'>{{err}}</div><a href='/' class='btn btn-secondary'>Back</a>", err=str(e))
        return redirect(url_for('index'))


@app.route('/table/<table>/edit/<pk>', methods=['GET', 'POST'])
def edit_row(table, pk):
    schema = exe.catalog.load_schema(table)
    cols = schema.get('columns', [])
    pk_col = schema.get('constraints', {}).get('primary_key', [cols[0]['name']])[0]
    # fetch existing
    rows = exe.execute(f"SELECT * FROM {table} WHERE {schema.get('constraints', {}).get('primary_key', [cols[0]['name']])[0]} = {pk};")
    values = {}
    if rows:
        values = rows[0]
    if request.method == 'POST':
        changes = {}
        for c in cols:
            changes[c['name']] = request.form.get(c['name'])
        # handle DATE/TIMESTAMP checkbox override on edit
        for c in cols:
            name = c['name']
            t = (c.get('type') or '').upper()
            if t == 'DATE':
                if request.form.get(f"use_today_{name}"):
                    changes[name] = 'CURRENT_DATE'
            if t == 'TIMESTAMP':
                if request.form.get(f"use_now_{name}"):
                    changes[name] = 'CURRENT_TIMESTAMP'
                else:
                    v = changes.get(name)
                    if v and 'T' in v and len(v) == 16:
                        changes[name] = v + ':00'
        # build UPDATE excluding pk
        pk_col = schema.get('constraints', {}).get('primary_key', [cols[0]['name']])[0]
        set_clause = ', '.join([f"{c['name']} = {_format_value_for_sql(changes[c['name']], c['type'])}" for c in cols if c['name'] != pk_col])
        sql = f"UPDATE {table} SET {set_clause} WHERE {pk_col} = {pk};"
        try:
            exe.execute(sql)
            return redirect(url_for('show_table', table=table))
        except Exception as e:
            return render_template_string(FORM_HTML, title=f"Edit {table}", columns=cols, values=changes, table=table, error=str(e), primary_key=pk_col)
    return render_template_string(FORM_HTML, title=f"Edit {table}", columns=cols, values=values, table=table, primary_key=pk_col)


@app.route('/table/<table>/delete/<pk>', methods=['POST'])
def delete_row(table, pk):
    schema = exe.catalog.load_schema(table)
    pk_col = schema.get('constraints', {}).get('primary_key', [None])[0]
    if pk_col is None:
        return redirect(url_for('show_table', table=table))
    try:
        exe.execute(f"DELETE FROM {table} WHERE {pk_col} = {pk};")
    except Exception:
        pass
    return redirect(url_for('show_table', table=table))


@app.route('/table/create', methods=['GET', 'POST'])
def create_table():
    if request.method == 'POST':
        name = request.form.get('table_name')
        # collect indices from POST keys like col_name_0, col_name_1 ...
        idxs = set()
        for k in request.form.keys():
            m = re.match(r'col_name_(\d+)', k)
            if m:
                idxs.add(int(m.group(1)))
        cols = []
        indexes = []
        if not name:
            return "Table name required", 400
        for i in sorted(idxs):
            n = request.form.get(f'col_name_{i}')
            if not n or not n.strip():
                continue
            t = request.form.get(f'col_type_{i}', 'TEXT')
            d = request.form.get(f'col_default_{i}')
            col = {'name': n.strip(), 'type': t.strip().upper()}
            if d:
                col['default'] = d
            cols.append(col)
            if request.form.get(f'col_index_{i}'):
                indexes.append(n.strip())
        if not cols:
            return "At least one column required", 400
        pk_val = request.form.get('pk_col')
        pk_col = None
        if pk_val is not None and pk_val != '':
            try:
                pk_idx = int(pk_val)
                # find corresponding column name by matching index order
                # build a mapping from index to col name
                mapping = {i: request.form.get(f'col_name_{i}') for i in sorted(idxs)}
                pk_col = mapping.get(pk_idx)
            except Exception:
                pk_col = None
        schema = {'name': name, 'columns': cols, 'constraints': {'primary_key': [pk_col] if pk_col else None, 'unique': []}, 'indexes': indexes}
        try:
            exe.catalog.create_table(schema)
            return redirect(url_for('index'))
        except Exception as e:
            return f"Error creating table: {e}", 400
    return render_template_string(CREATE_TABLE_HTML)

if __name__ == "__main__":
    app.run(port=5000)
