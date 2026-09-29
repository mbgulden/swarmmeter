from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from .types import MeterStats, QuotaExhausted, QuotaPolicy, TokenUsage


class QuotaManager:
    """Manages cluster-wide budget quotas."""

    def __init__(self, policy: QuotaPolicy, db_path: Path | None = None):
        self.policy = policy
        self.db_path = db_path or Path(":memory:")
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self._lock:
            self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT,
                    tokens_in INTEGER,
                    tokens_out INTEGER,
                    cost_usd REAL,
                    timestamp REAL,
                    model TEXT,
                    provider TEXT
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date TEXT PRIMARY KEY,
                    total_cost_usd REAL,
                    total_tokens INTEGER,
                    breaker_trips INTEGER,
                    quota_violations INTEGER
                )
            """)
            self.conn.commit()

    def record_usage(self, usage: TokenUsage):
        """Persist usage and check quota."""
        with self._lock:
            self.conn.execute("""
                INSERT INTO usage (agent_id, tokens_in, tokens_out, cost_usd, timestamp, model, provider)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (usage.agent_id, usage.tokens_in, usage.tokens_out, usage.cost_usd, usage.timestamp, usage.model, usage.provider))
            self.conn.commit()
            
            if not self._is_within_quota_unlocked(usage.agent_id):
                self.conn.execute("UPDATE daily_stats SET quota_violations = coalesce(quota_violations, 0) + 1 WHERE date = date('now')")
                self.conn.commit()
                raise QuotaExhausted("Quota exhausted")

    def _is_within_quota_unlocked(self, agent_id: str | None = None) -> bool:
        cursor = self.conn.cursor()
        
        # Check daily cluster budget
        if self.policy.daily_budget_usd > 0:
            cursor.execute("SELECT sum(cost_usd) FROM usage WHERE date(timestamp, 'unixepoch') = date('now')")
            row = cursor.fetchone()
            total_cost = row[0] if row and row[0] is not None else 0.0
            if total_cost > self.policy.daily_budget_usd:
                return False

        # Check per-agent budget
        if agent_id and self.policy.per_agent_budget_usd > 0:
            cursor.execute("SELECT sum(cost_usd) FROM usage WHERE agent_id = ? AND date(timestamp, 'unixepoch') = date('now')", (agent_id,))
            row = cursor.fetchone()
            agent_cost = row[0] if row and row[0] is not None else 0.0
            if agent_cost > self.policy.per_agent_budget_usd:
                return False
                
        return True

    def is_within_quota(self, agent_id: str | None = None) -> bool:
        with self._lock:
            return self._is_within_quota_unlocked(agent_id)

    def remaining_budget(self, agent_id: str | None = None) -> float:
        """Remaining USD budget."""
        with self._lock:
            cursor = self.conn.cursor()
            if agent_id:
                if self.policy.per_agent_budget_usd <= 0:
                    return float('inf')
                cursor.execute("SELECT sum(cost_usd) FROM usage WHERE agent_id = ? AND date(timestamp, 'unixepoch') = date('now')", (agent_id,))
                row = cursor.fetchone()
                spent = row[0] if row and row[0] is not None else 0.0
                return max(0.0, self.policy.per_agent_budget_usd - spent)
            else:
                if self.policy.daily_budget_usd <= 0:
                    return float('inf')
                cursor.execute("SELECT sum(cost_usd) FROM usage WHERE date(timestamp, 'unixepoch') = date('now')")
                row = cursor.fetchone()
                spent = row[0] if row and row[0] is not None else 0.0
                return max(0.0, self.policy.daily_budget_usd - spent)

    def reset_daily(self):
        """Reset daily counters (simulated by deleting today's usage for testing)."""
        with self._lock:
            self.conn.execute("DELETE FROM usage WHERE date(timestamp, 'unixepoch') = date('now')")
            self.conn.commit()

    def stats(self) -> MeterStats:
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT sum(tokens_in + tokens_out), sum(cost_usd), count(DISTINCT agent_id) FROM usage")
            row = cursor.fetchone()
            total_tokens = row[0] if row and row[0] is not None else 0
            total_cost_usd = row[1] if row and row[1] is not None else 0.0
            active_agents = row[2] if row and row[2] is not None else 0
            
            cursor.execute("SELECT sum(breaker_trips), sum(quota_violations) FROM daily_stats")
            row = cursor.fetchone()
            breaker_trips = row[0] if row and row[0] is not None else 0
            quota_violations = row[1] if row and row[1] is not None else 0

            return MeterStats(
                total_tokens=total_tokens,
                total_cost_usd=total_cost_usd,
                active_agents=active_agents,
                breaker_trips=breaker_trips,
                quota_violations=quota_violations
            )
