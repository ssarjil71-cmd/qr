#!/usr/bin/env python3
"""
Fix QR paths in database:
1. Remove 'static/' prefix (only keep qr/qr_...png)
2. Convert backslashes to forward slashes for web URLs
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from services.db import get_conn

def fix_qr_paths():
    app = create_app()
    with app.app_context():
        conn = get_conn()
        cur = conn.cursor()
        
        try:
            # Get all users with QR paths
            cur.execute('SELECT id, qr_path FROM users WHERE qr_path IS NOT NULL')
            users = cur.fetchall()
            
            count = 0
            for user_id, qr_path in users:
                if qr_path:
                    # Convert backslashes to forward slashes
                    corrected_path = qr_path.replace('\\', '/')
                    # Remove 'static/' prefix if present
                    if corrected_path.startswith('static/'):
                        corrected_path = corrected_path.replace('static/', '', 1)
                    
                    if corrected_path != qr_path:
                        cur.execute('UPDATE users SET qr_path=%s WHERE id=%s', (corrected_path, user_id))
                        print(f"Updated user {user_id}:")
                        print(f"  From: {qr_path}")
                        print(f"  To:   {corrected_path}")
                        count += 1
            
            conn.commit()
            print(f"\nTotal fixed: {count} QR paths")
            
        except Exception as e:
            print(f"Error: {e}")
            conn.rollback()
        finally:
            cur.close()
            conn.close()

if __name__ == '__main__':
    fix_qr_paths()

