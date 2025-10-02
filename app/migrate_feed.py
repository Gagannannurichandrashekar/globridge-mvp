#!/usr/bin/env python3
"""
Database migration script for Feed System
Adds new tables for posts, reactions, comments, and connections
"""

import sqlite3
import os

def migrate_database():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'globridge.db')
    
    if not os.path.exists(db_path):
        print("Database not found. Please run the main application first.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Create posts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                post_type VARCHAR(50) DEFAULT 'text',
                media_url VARCHAR(500),
                media_thumbnail VARCHAR(500),
                article_title VARCHAR(200),
                article_summary TEXT,
                is_deleted INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create post_reactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS post_reactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                reaction_type VARCHAR(50) DEFAULT 'like',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts (id),
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(post_id, user_id)
            )
        ''')
        
        # Create post_comments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS post_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                parent_comment_id INTEGER,
                is_deleted INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts (id),
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (parent_comment_id) REFERENCES post_comments (id)
            )
        ''')
        
        # Create connections table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requester_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (requester_id) REFERENCES users (id),
                FOREIGN KEY (receiver_id) REFERENCES users (id),
                UNIQUE(requester_id, receiver_id)
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_post_reactions_post_id ON post_reactions(post_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_post_comments_post_id ON post_comments(post_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_connections_requester ON connections(requester_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_connections_receiver ON connections(receiver_id)')
        
        conn.commit()
        print("✅ Database migration completed successfully!")
        print("Added tables: posts, post_reactions, post_comments, connections")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
