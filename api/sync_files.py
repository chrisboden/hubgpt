import sqlite3
import os
import json
from pathlib import Path
from uuid import uuid4
from datetime import datetime

# Connect to database
conn = sqlite3.connect('hubgpt.db')
c = conn.cursor()

# User ID
user_id = 'fb706bca-aef9-4a03-9336-d4868e2d5e04'

# Base directory for user files
base_dir = Path('../storage/users') / user_id / 'files'

# Walk through files
for root, dirs, files in os.walk(base_dir):
    for file in files:
        file_path = Path(root) / file
        rel_path = file_path.relative_to(base_dir)
        size = file_path.stat().st_size
        file_type = file_path.suffix.lstrip('.') or 'txt'
        
        print(f"Adding file: {rel_path}")
        
        # Insert into database
        c.execute('''
            INSERT INTO user_files (id, user_id, file_path, file_type, size_bytes, is_public, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid4()),
            user_id,
            str(rel_path),
            file_type,
            size,
            False,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))

conn.commit()
conn.close()
print('Done!') 