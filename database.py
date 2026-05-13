import sqlite3
import os
from typing import Optional


class Database:
    def __init__(self, path: str = "data/tracks.db"):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    async def init(self):
        with sqlite3.connect(self.path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    current_price REAL NOT NULL,
                    target_price REAL NOT NULL,
                    active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def add_track(self, user_id: int, url: str, current_price: float, target_price: float):
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT INTO tracks (user_id, url, current_price, target_price) VALUES (?, ?, ?, ?)",
                (user_id, url, current_price, target_price)
            )
            conn.commit()

    def get_tracks(self, user_id: int) -> list:
        with sqlite3.connect(self.path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM tracks WHERE user_id = ? AND active = 1",
                (user_id,)
            )
            return [dict(row) for row in cur.fetchall()]

    def get_all_active(self) -> list:
        with sqlite3.connect(self.path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT * FROM tracks WHERE active = 1")
            return [dict(row) for row in cur.fetchall()]

    def update_price(self, track_id: int, new_price: float):
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "UPDATE tracks SET current_price = ? WHERE id = ?",
                (new_price, track_id)
            )
            conn.commit()

    def deactivate(self, track_id: int):
        with sqlite3.connect(self.path) as conn:
            conn.execute("UPDATE tracks SET active = 0 WHERE id = ?", (track_id,))
            conn.commit()
