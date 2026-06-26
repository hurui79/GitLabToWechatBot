import sqlite3
import os
import time
from config import DB_PATH


def get_db():
    """获取数据库连接"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS webhook_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            gitlab_token TEXT NOT NULL UNIQUE,
            wechat_url TEXT NOT NULL,
            events TEXT DEFAULT '*',
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS push_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mapping_id INTEGER,
            event_type TEXT,
            project TEXT,
            status TEXT,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mapping_id) REFERENCES webhook_mappings(id)
        );
        CREATE INDEX IF NOT EXISTS idx_token ON webhook_mappings(gitlab_token);
        CREATE INDEX IF NOT EXISTS idx_logs_time ON push_logs(created_at);
    ''')
    conn.commit()
    conn.close()


# ---------- 映射 CRUD ----------

def get_all_mappings():
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM webhook_mappings ORDER BY created_at DESC'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_mapping_by_token(token):
    conn = get_db()
    row = conn.execute(
        'SELECT * FROM webhook_mappings WHERE gitlab_token = ? AND enabled = 1',
        (token,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_mapping_by_id(mapping_id):
    conn = get_db()
    row = conn.execute(
        'SELECT * FROM webhook_mappings WHERE id = ?', (mapping_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def add_mapping(name, gitlab_token, wechat_url, events='*'):
    conn = get_db()
    conn.execute(
        'INSERT INTO webhook_mappings (name, gitlab_token, wechat_url, events) VALUES (?, ?, ?, ?)',
        (name, gitlab_token, wechat_url, events)
    )
    conn.commit()
    conn.close()


def update_mapping(mapping_id, name, gitlab_token, wechat_url, events='*', enabled=1):
    conn = get_db()
    conn.execute(
        'UPDATE webhook_mappings SET name=?, gitlab_token=?, wechat_url=?, events=?, enabled=? WHERE id=?',
        (name, gitlab_token, wechat_url, events, enabled, mapping_id)
    )
    conn.commit()
    conn.close()


def delete_mapping(mapping_id):
    conn = get_db()
    conn.execute('DELETE FROM webhook_mappings WHERE id=?', (mapping_id,))
    conn.commit()
    conn.close()


# ---------- 日志 ----------

def add_log(mapping_id, event_type, project, status, message):
    conn = get_db()
    conn.execute(
        'INSERT INTO push_logs (mapping_id, event_type, project, status, message) VALUES (?, ?, ?, ?, ?)',
        (mapping_id, event_type, project, status, message)
    )
    conn.commit()
    conn.close()


def get_logs(limit=100):
    conn = get_db()
    rows = conn.execute('''
        SELECT l.*, m.name as mapping_name
        FROM push_logs l
        LEFT JOIN webhook_mappings m ON l.mapping_id = m.id
        ORDER BY l.created_at DESC
        LIMIT ?
    ''', (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def clean_old_logs(days=30):
    """清理过期日志"""
    conn = get_db()
    conn.execute(
        "DELETE FROM push_logs WHERE created_at < datetime('now', ?)",
        (f'-{days} days',)
    )
    conn.commit()
    conn.close()
