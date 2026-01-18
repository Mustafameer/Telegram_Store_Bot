#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
List all tables in the database
"""
import os
import psycopg2
from urllib.parse import urlparse

database_url = os.environ.get('DATABASE_URL')

if not database_url:
    print("DATABASE_URL not set!")
    exit(1)

try:
    result = urlparse(database_url)
    conn = psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port,
        sslmode='require'
    )
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    
    tables = cursor.fetchall()
    print("Tables in the database:")
    for (table_name,) in tables:
        print(f"  - {table_name}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
