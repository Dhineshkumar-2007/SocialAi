def _cols(db, table):
    return {r[1] for r in db.execute('PRAGMA table_info(%s)' % table).fetchall()}

def _add(db, table, col, typ):
    if col not in _cols(db, table): db.execute('ALTER TABLE %s ADD COLUMN %s %s' % (table,col,typ))

def migrate(db):
    for col, typ in [('title_relevance','REAL DEFAULT 0'),('description_relevance','REAL DEFAULT 0'),('image_relevance','REAL DEFAULT 0'),('evidence_status',"TEXT DEFAULT 'pending'"),('mime','TEXT'),('relevance','REAL DEFAULT 0'),('quality','REAL DEFAULT 0')]: _add(db,'evidence',col,typ)
    for col, typ in [('account_type', "TEXT DEFAULT 'individual'"),('position','TEXT'),('department','TEXT'),('organization_name','TEXT'),('phone','TEXT')]: _add(db,'users',col,typ)
    for col, typ in [('institution_type',"TEXT DEFAULT 'university'"),('website','TEXT'),('address','TEXT'),('state',"TEXT DEFAULT 'Tamil Nadu'"),('pincode','TEXT'),('contact_phone','TEXT'),('email_domain','TEXT'),('accreditation','TEXT'),('research_summary','TEXT'),('expertise_summary','TEXT'),('programs_summary','TEXT'),('facilities_summary','TEXT')]: _add(db,'universities',col,typ)
    if 'created_at' not in _cols(db, 'universities'):
        db.execute('ALTER TABLE universities ADD COLUMN created_at TEXT')
    db.execute('CREATE TABLE IF NOT EXISTS institution_research_areas (id INTEGER PRIMARY KEY AUTOINCREMENT, university_id INTEGER NOT NULL, area TEXT NOT NULL, keywords TEXT, FOREIGN KEY(university_id) REFERENCES universities(id))')
    db.execute('CREATE TABLE IF NOT EXISTS institution_facilities (id INTEGER PRIMARY KEY AUTOINCREMENT, university_id INTEGER NOT NULL, name TEXT NOT NULL, type TEXT, capabilities TEXT, FOREIGN KEY(university_id) REFERENCES universities(id))')
    db.execute('CREATE TABLE IF NOT EXISTS institution_programs (id INTEGER PRIMARY KEY AUTOINCREMENT, university_id INTEGER NOT NULL, name TEXT NOT NULL, department TEXT, focus TEXT, FOREIGN KEY(university_id) REFERENCES universities(id))')
    db.commit()
