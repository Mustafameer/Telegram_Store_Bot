#!/usr/bin/env python3
"""
Enable polling locally after disabling it for Railway
"""
import os
import sys
import sqlite3

conn = sqlite3.connect('data/telegramstorebot.db')
cursor = conn.cursor()

cursor.execute("""
    UPDATE FeatureFlags SET FlagValue=0 WHERE FlagName='DISABLE_POLLING'
""")

conn.commit()
print("✅ Set DISABLE_POLLING=0 - Polling enabled locally")
conn.close()
