import sqlite3, json
p='sessions.db'
conn=sqlite3.connect(p)
c=conn.cursor()
rows=c.execute('SELECT project_name, field_name, completion_pct, auto_saved, saved_at FROM sessions').fetchall()
print('ROWS:', rows)
if rows:
    r=rows[0]
    print('First:', r)
    cur=c.execute('SELECT session_json FROM sessions WHERE project_name=? AND field_name=?',(r[0],r[1])).fetchone()
    if cur and cur[0]:
        print('session_json length:', len(cur[0]))
        session=json.loads(cur[0])
        print('session keys count:', len(session.keys()))
        keys=list(session.keys())
        print(keys[:80])
conn.close()
