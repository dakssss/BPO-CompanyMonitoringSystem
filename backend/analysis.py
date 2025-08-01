# analysis.py

from collections import defaultdict
from datetime import datetime
from typing import List

def analyze_pc_activity(logs: List[dict]) -> dict:
    daily_stats = defaultdict(lambda: {"active": 0, "idle": 0})

    for log in logs:
        ts = log["timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)  # convert string to datetime
        day = ts.date()
        status = log["status"].lower()

        if status == "active":
            daily_stats[day]["active"] += 1
        elif status == "idle":
            daily_stats[day]["idle"] += 1

    result = {}
    for day, stats in daily_stats.items():
        total = stats["active"] + stats["idle"]
        if total == 0:
            continue
        result[str(day)] = {
            "active_percent": round((stats["active"] / total) * 100, 2),
            "idle_percent": round((stats["idle"] / total) * 100, 2),
            "active_count": stats["active"],
            "idle_count": stats["idle"],
            "total_logs": total
        }

    return result

def analyze_window_usage_per_day(logs: List[dict]) -> dict:
    """
    Group and summarize window usage by app and main tab.
    """
    from collections import defaultdict
    from datetime import datetime

    daily_usage = defaultdict(lambda: defaultdict(int))

    for log in logs:
        ts = log['timestamp']
        if isinstance(ts, str):
            ts = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        date_str = ts.date().isoformat()

        raw_window = log.get('active_window') or "Unknown"

        # Keep only first 2 segments separated by '|'
        parts = [p.strip() for p in raw_window.split('|') if p.strip()]
        grouped_window = " | ".join(parts[:2]) if parts else "Unknown"

        daily_usage[date_str][grouped_window] += 1

    # Convert to percentage format
    result = {}
    for date, counts in daily_usage.items():
        total = sum(counts.values())
        result[date] = {
            window: round((count / total) * 100, 2)
            for window, count in counts.items()
        }

    return result
