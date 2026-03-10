"""HomePLC Data Logger - logs tag values to SQLite for historical trending."""

import sqlite3
import threading
import time
import os
from datetime import datetime, timedelta


class DataLogger:
    LOGGED_TAGS = [
        "Outdoor_Temp_F", "Elec_Current_Amps", "Elec_Peak_Amps", "Elec_Total_kWh",
        "Gen_State", "Gen_Running", "Gen_On_Generator", "Gen_Total_Run_Seconds",
        "Sump_State", "Sump_Pump_Run", "Sump_Cycle_Count", "Sump_Hourly_Cycle_Count",
        "HVAC_Furnace_Running", "HVAC_Total_Run_Seconds", "HVAC_Filter_Run_Seconds",
        "Water_Pressure_PSI", "Well_Pump_Running", "Well_Pump_Cycle_Count",
        "Garage_Door_Open", "Garage_Open_Seconds",
        "Leak_Any_Alarm", "Load_Shed_Active",
        "HVAC_Efficiency_Pct", "HVAC_HDD_Accumulated",
    ]

    def __init__(self, db_path):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._thread = None
        self._running = False
        self._last_purge = None

        # Create data directory if needed
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tag_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    tag_name TEXT,
                    value REAL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tag_time
                ON tag_log(tag_name, timestamp)
            """)
            conn.commit()

    def log_snapshot(self, tag_dict):
        """For each tag in LOGGED_TAGS, insert a row with current timestamp."""
        now = datetime.now().isoformat()
        rows = []
        for tag in self.LOGGED_TAGS:
            raw = tag_dict.get(tag)
            if raw is None:
                continue
            # Convert booleans to 0/1
            if isinstance(raw, bool):
                val = 1.0 if raw else 0.0
            else:
                try:
                    val = float(raw)
                except (ValueError, TypeError):
                    continue
            rows.append((now, tag, val))

        if rows:
            with self._lock:
                try:
                    with sqlite3.connect(self.db_path) as conn:
                        conn.executemany(
                            "INSERT INTO tag_log (timestamp, tag_name, value) VALUES (?, ?, ?)",
                            rows
                        )
                        conn.commit()
                except Exception as e:
                    print(f"DataLogger error: {e}")

    def get_history(self, tag_name, hours=24):
        """Return list of {timestamp, value} for the given tag over the last N hours."""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(
                        "SELECT timestamp, value FROM tag_log "
                        "WHERE tag_name = ? AND timestamp > ? ORDER BY timestamp",
                        (tag_name, cutoff)
                    )
                    return [{"timestamp": row[0], "value": row[1]} for row in cursor.fetchall()]
            except Exception as e:
                print(f"DataLogger query error: {e}")
                return []

    def purge_old(self, days=90):
        """Delete records older than N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("DELETE FROM tag_log WHERE timestamp < ?", (cutoff,))
                    conn.commit()
                    print(f"DataLogger: purged records older than {days} days")
            except Exception as e:
                print(f"DataLogger purge error: {e}")

    def get_available_tags(self):
        """Return list of logged tag names."""
        return list(self.LOGGED_TAGS)

    def start(self, data_source_fn, interval=60):
        """Start background thread that logs snapshots at the given interval.

        data_source_fn: callable that returns the current tag dict.
        interval: seconds between snapshots (default 60).
        """
        self._running = True

        def _run():
            while self._running:
                try:
                    tag_dict = data_source_fn()
                    if tag_dict:
                        self.log_snapshot(tag_dict)

                    # Purge old data once per day
                    now = datetime.now()
                    if self._last_purge is None or (now - self._last_purge).total_seconds() > 86400:
                        self.purge_old(days=90)
                        self._last_purge = now
                except Exception as e:
                    print(f"DataLogger thread error: {e}")

                time.sleep(interval)

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        print(f"DataLogger started (interval={interval}s, db={self.db_path})")

    def stop(self):
        self._running = False
