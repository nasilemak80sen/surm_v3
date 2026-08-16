import sqlite3
conn = sqlite3.connect('sessions.db')
cur = conn.execute('SELECT project_name, field_name, phase, completion_pct, auto_saved, saved_at FROM sessions')
rows = cur.fetchall()
for r in rows:
    print(r)
conn.close()
