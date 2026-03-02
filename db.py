"""
db.py — all database queries in one place
"""
import sqlite3

DB = "meetings.db"

def get_connection():
    return sqlite3.connect(DB)

def compute_health_score(meeting_id):
    """
    Health score = % of items from the PREVIOUS meeting that are 'done'.
    Returns dict with score (0-100), done count, total count, and label.
    Returns None if this is the first meeting (no previous to compare).
    """
    conn = get_connection()
    c = conn.cursor()

    # Find the previous meeting id
    c.execute("""
        SELECT id FROM meetings
        WHERE id < ?
        ORDER BY id DESC
        LIMIT 1
    """, (meeting_id,))
    row = c.fetchone()

    if not row:
        conn.close()
        return None  # first meeting, no score yet

    prev_meeting_id = row[0]

    # Count total and done items from previous meeting
    c.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as done
        FROM items
        WHERE meeting_id = ?
    """, (prev_meeting_id,))
    result = c.fetchone()
    conn.close()

    total = result[0] or 0
    done  = result[1] or 0

    if total == 0:
        return None  # previous meeting had no items

    score = round((done / total) * 100)

    # Label based on score
    if score >= 80:
        label = "Healthy"
        color = "green"
    elif score >= 50:
        label = "Moderate"
        color = "yellow"
    else:
        label = "At Risk"
        color = "red"

    return {
        "score": score,
        "done": done,
        "total": total,
        "label": label,
        "color": color
    }

def get_all_meetings():
    """Get all meetings with item counts and health scores."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT m.id, m.title, m.created_at,
               COUNT(i.id) as item_count,
               SUM(CASE WHEN i.priority = 'high' THEN 1 ELSE 0 END) as high_count,
               SUM(CASE WHEN i.status = 'done' THEN 1 ELSE 0 END) as done_count
        FROM meetings m
        LEFT JOIN items i ON i.meeting_id = m.id
        GROUP BY m.id
        ORDER BY m.id DESC
    """)
    rows = c.fetchall()
    conn.close()

    meetings = []
    for r in rows:
        meeting_id = r[0]
        health = compute_health_score(meeting_id)
        meetings.append({
            "id":         meeting_id,
            "title":      r[1],
            "created_at": r[2],
            "item_count": r[3],
            "high_count": r[4] or 0,
            "done_count": r[5] or 0,
            "health":     health
        })
    return meetings

def get_meeting_debt():
    """
    Find owners with 3+ HIGH priority items still unresolved across all meetings.
    Returns list of {owner, open_high, meetings} — sorted by worst first.
    """
    conn = get_connection()
    c = conn.cursor()

    # Get overloaded owners
    c.execute("""
        SELECT owner, COUNT(*) as open_high
        FROM items
        WHERE priority = 'high'
        AND status != 'done'
        AND owner != 'Unassigned'
        GROUP BY owner
        HAVING COUNT(*) >= 3
        ORDER BY open_high DESC
    """)
    overloaded = c.fetchall()

    results = []
    for owner, count in overloaded:
        # Find which meetings their unresolved items are from
        c.execute("""
            SELECT DISTINCT m.title
            FROM items i
            JOIN meetings m ON m.id = i.meeting_id
            WHERE i.owner = ?
            AND i.priority = 'high'
            AND i.status != 'done'
            ORDER BY m.id
        """, (owner,))
        meeting_titles = [r[0] for r in c.fetchall()]
        results.append({
            "owner": owner,
            "open_high": count,
            "meetings": meeting_titles
        })

    conn.close()
    return results

def get_owner_workload():
    """
    Returns workload stats per owner across all meetings.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT
            owner,
            COUNT(*) as total,
            SUM(CASE WHEN status != 'done' THEN 1 ELSE 0 END) as open,
            SUM(CASE WHEN status  = 'done' THEN 1 ELSE 0 END) as done,
            SUM(CASE WHEN priority = 'high' AND status != 'done' THEN 1 ELSE 0 END) as open_high
        FROM items
        GROUP BY owner
        ORDER BY open_high DESC, open DESC
    """)
    rows = c.fetchall()
    conn.close()

    result = []
    for r in rows:
        owner, total, open_count, done_count, open_high = r
        completion = round((done_count / total) * 100) if total > 0 else 0
        result.append({
            "owner":      owner,
            "total":      total,
            "open":       open_count,
            "done":       done_count,
            "open_high":  open_high,
            "completion": completion,
            "overloaded": open_high >= 3 and owner != "Unassigned"
        })
    return result
