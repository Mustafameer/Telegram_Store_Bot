#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from bot import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

try:
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
    tables = cursor.fetchall()
    print('TABLES:')
    for t in tables:
        tname = t[0]
        if 'seller' in tname.lower() or 'categor' in tname.lower():
            print(f'  {tname}')
            
finally:
    cursor.close()
    conn.close()
