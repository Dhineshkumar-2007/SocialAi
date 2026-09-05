import os, sqlite3

db_path = 'societal_ai.db'
print('DB exists:', os.path.exists(db_path))

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    print('Tables:', tables)

    required_tables = ['problems', 'assignments', 'universities', 'projects', 'assignment_history', 'project_milestones', 'resolution_feedback', 'matcher_learning_adjustments', 'evidence']
    for t in required_tables:
        if t in tables:
            cursor.execute(f'PRAGMA table_info({t});')
            cols = [(c[1], c[2], c[3], c[4], c[5]) for c in cursor.fetchall()]
            print(f'=== TABLE {t} ===')
            for col in cols:
                print('  ', col)
        else:
            print(f'=== TABLE {t}: MISSING ===')
    conn.close()
else:
    print('DB NOT FOUND')
