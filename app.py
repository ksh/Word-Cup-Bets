import os
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, request, render_template, redirect, url_for, flash, send_file
from jinja2 import DictLoader

app = Flask(__name__)
app.secret_key = "world_cup_secret_key_123"
DB_FILE = "world_cup_bets.db"

# List of users for the application dropdown
USERS = ["Arthur", "Carlos","Filip", "Josee", "Mike", "Newton", "Ricardo", "Rodolfo", "Sue"]

# Initial Match Schedule Data (Normalized to UTC timestamps)
MATCH_SCHEDULE = [
    # Match ID, Group, Home Team, Away Team, Kickoff Time (UTC)
    (1, "A", "Mexico", "South Africa", "2026-06-11 19:00:00"),
    (2, "A", "South Korea", "Czechia", "2026-06-12 02:00:00"),
    (3, "B", "Canada", "Bosnia and Herzegovina", "2026-06-12 19:00:00"),
    (4, "D", "USA", "Paraguay", "2026-06-13 01:00:00"),
    (5, "C", "Haiti", "Scotland", "2026-06-14 01:00:00"),
    (6, "D", "Australia", "Türkiye", "2026-06-14 04:00:00"),
    (7, "C", "Brazil", "Morocco", "2026-06-13 22:00:00"),
    (8, "B", "Qatar", "Switzerland", "2026-06-13 19:00:00"),
    (9, "E", "Ivory Coast", "Ecuador", "2026-06-14 23:00:00"),
    (10, "E", "Germany", "Curaçao", "2026-06-14 17:00:00"),
    (11, "F", "Netherlands", "Japan", "2026-06-14 20:00:00"),
    (12, "F", "Sweden", "Tunisia", "2026-06-15 02:00:00"),
    (13, "H", "Saudi Arabia", "Uruguay", "2026-06-15 22:00:00"),
    (14, "H", "Spain", "Cape Verde", "2026-06-15 16:00:00"),
    (15, "G", "Iran", "New Zealand", "2026-06-16 01:00:00"),
    (16, "G", "Belgium", "Egypt", "2026-06-15 22:00:00"),
    (17, "I", "France", "Senegal", "2026-06-16 19:00:00"),
    (18, "I", "Iraq", "Norway", "2026-06-16 22:00:00"),
    (19, "J", "Argentina", "Algeria", "2026-06-17 01:00:00"),
    (20, "J", "Austria", "Jordan", "2026-06-17 04:00:00"),
    (21, "L", "Ghana", "Panama", "2026-06-17 23:00:00"),
    (22, "L", "England", "Croatia", "2026-06-17 20:00:00"),
    (23, "K", "Portugal", "Congo DR", "2026-06-17 17:00:00"),
    (24, "K", "Uzbekistan", "Colombia", "2026-06-18 02:00:00"),
    (25, "A", "Czechia", "South Africa", "2026-06-18 16:00:00"),
    (26, "B", "Switzerland", "Bosnia and Herzegovina", "2026-06-18 19:00:00"),
    (27, "B", "Canada", "Qatar", "2026-06-18 22:00:00"),
    (28, "A", "Mexico", "South Korea", "2026-06-19 01:00:00"),
    (29, "C", "Brazil", "Haiti", "2026-06-19 21:00:00"),
    (30, "C", "Scotland", "Morocco", "2026-06-19 22:00:00"),
    (31, "D", "Türkiye", "Paraguay", "2026-06-20 03:00:00"),
    (32, "D", "USA", "Australia", "2026-06-19 22:00:00"),
    (33, "E", "Germany", "Ivory Coast", "2026-06-20 20:00:00"),
    (34, "E", "Ecuador", "Curaçao", "2026-06-21 00:00:00"),
    (35, "F", "Netherlands", "Sweden", "2026-06-20 18:00:00"),
    (36, "F", "Tunisia", "Japan", "2026-06-21 04:00:00"),
    (37, "H", "Uruguay", "Cape Verde", "2026-06-21 22:00:00"),
    (38, "H", "Spain", "Saudi Arabia", "2026-06-21 16:00:00"),
    (39, "G", "Belgium", "Iran", "2026-06-21 22:00:00"),
    (40, "G", "New Zealand", "Egypt", "2026-06-22 01:00:00"),
    (41, "I", "Norway", "Senegal", "2026-06-22 20:00:00"),
    (42, "I", "France", "Iraq", "2026-06-22 21:00:00"),
    (43, "J", "Argentina", "Austria", "2026-06-22 18:00:00"),
    (44, "J", "Jordan", "Algeria", "2026-06-23 03:00:00"),
    (45, "L", "England", "Ghana", "2026-06-23 20:00:00"),
    (46, "L", "Panama", "Croatia", "2026-06-23 23:00:00"),
    (47, "K", "Portugal", "Uzbekistan", "2026-06-23 18:00:00"),
    (48, "K", "Colombia", "Congo DR", "2026-06-24 02:00:00"),
    (49, "B", "Switzerland", "Canada", "2026-06-24 20:00:00"),
    (50, "B", "Bosnia and Herzegovina", "Qatar", "2026-06-24 20:00:00"),
    (51, "C", "Scotland", "Brazil", "2026-06-24 23:00:00"),
    (52, "C", "Morocco", "Haiti", "2026-06-24 23:00:00"),
    (53, "A", "Czechia", "Mexico", "2026-06-25 02:00:00"),
    (54, "A", "South Africa", "South Korea", "2026-06-25 02:00:00"),
    (55, "E", "Curaçao", "Ivory Coast", "2026-06-25 22:00:00"),
    (56, "E", "Ecuador", "Germany", "2026-06-25 22:00:00"),
    (57, "F", "Japan", "Sweden", "2026-06-26 01:00:00"),
    (58, "F", "Tunisia", "Netherlands", "2026-06-26 01:00:00"),
    (59, "D", "Paraguay", "USA", "2026-06-26 04:00:00"),
    (60, "D", "Türkiye", "Australia", "2026-06-26 04:00:00"),
    (61, "I", "Norway", "France", "2026-06-26 21:00:00"),
    (62, "I", "Senegal", "Iraq", "2026-06-26 21:00:00"),
    (63, "H", "Cape Verde", "Saudi Arabia", "2026-06-27 02:00:00"),
    (64, "H", "Uruguay", "Spain", "2026-06-27 02:00:00"),
    (65, "G", "Egypt", "Iran", "2026-06-27 05:00:00"),
    (66, "G", "New Zealand", "Belgium", "2026-06-27 05:00:00"),
    (67, "J", "Jordan", "Argentina", "2026-06-27 23:00:00"),
    (68, "J", "Algeria", "Austria", "2026-06-27 23:00:00"),
    (69, "L", "Panama", "England", "2026-06-28 02:00:00"),
    (70, "L", "Croatia", "Ghana", "2026-06-28 02:00:00"),
    (71, "K", "Colombia", "Portugal", "2026-06-28 05:00:00"),
    (72, "K", "Congo DR", "Uzbekistan", "2026-06-28 05:00:00"),
]

# HTML Templates stored clean and handled by a custom Dictionary Template Loader
BASE_LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>World Cup 2026 Bet Tracker</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; max-width: 1000px; margin: 30px auto; padding: 0 20px; background: #f4f6f9; color: #333; }
        h1, h2 { color: #0b3c5d; }
        .nav { margin-bottom: 20px; padding: 10px; background: #fff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .nav a { margin-right: 15px; text-decoration: none; color: #328cc1; font-weight: bold; }
        .card { background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 25px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; background: #fff; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #0b3c5d; color: #fff; }
        tr:hover { background: #f9f9f9; }
        .badge { background: #e2f0d9; color: #385723; padding: 4px 8px; border-radius: 4px; font-size: 0.85em; font-weight: bold; }
        .badge-locked { background: #fce4d6; color: #c65911; }
        .badge-live { background: #fff2cc; color: #7f6000; }
        .input-score { width: 40px; text-align: center; font-size: 1em; padding: 4px; border: 1px solid #ccc; border-radius: 4px; }
        .btn { background: #328cc1; color: #fff; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: bold; }
        .btn:hover { background: #0b3c5d; }
        .flash { padding: 10px; background: #d4edda; color: #155724; border-radius: 4px; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="nav">
        <a href="/">📋 Dashboard & Bets</a>
        <a href="/admin">⚙️ Admin Input</a>
        <span style="float: right;">🕒 Server Time (UTC): <strong>{{ current_time }}</strong></span>
    </div>
    
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        {% for msg in messages %}<div class="flash">{{ msg }}</div>{% endfor %}
      {% endif %}
    {% endwith %}

    {% block content %}{% endblock %}
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="card">
    <h2>🏆 Friends Leaderboard</h2>
    <table>
        <tr><th>Rank</th><th>Player</th><th>Total Points</th></tr>
        {% for user, pts in leaderboard %}
        <tr>
            <td><strong>#{{ loop.index }}</strong></td>
            <td>{{ user }}</td>
            <td><span class="badge">{{ pts }} pts</span></td>
        </tr>
        {% endfor %}
    </table>
</div>

<div class="card">
    <h2>⚽ Fixtures & Placed Bets</h2>
    <form method="GET" action="/">
        <label for="active_user"><strong>View / Place Bet As: </strong></label>
        <select name="active_user" id="active_user" onchange="this.form.submit()">
            {% for u in users %}
            <option value="{{ u }}" {% if u == active_user %}selected{% endif %}>{{ u }}</option>
            {% endfor %}
        </select>
    </form>
    
    <form method="POST" action="/place-bet">
        <input type="hidden" name="user" value="{{ active_user }}">
        <table>
            <tr>
                <th>Group</th>
                <th>Matchup</th>
                <th>Kickoff (UTC)</th>
                <th>Your Bet</th>
                <th>Status</th>
                <th>Others' Bets</th>
                <th>Official Score</th>
            </tr>
            {% for m in match_data %}
            <tr>
                <td><span class="badge">{{ m.grp }}</span></td>
                <td><strong>{{ m.home_team }}</strong> vs <strong>{{ m.away_team }}</strong></td>
                <td><small>{{ m.kickoff }}</small></td>
                <td>
                    {% if m.is_locked %}
                        <strong>{{ m.my_bet_h if m.my_bet_h is not none else '-' }} - {{ m.my_bet_a if m.my_bet_a is not none else '-' }}</strong>
                    {% else %}
                        <input type="number" class="input-score" name="bet_h_{{ m.id }}" value="{{ m.my_bet_h if m.my_bet_h is not none else '' }}" min="0">
                        -
                        <input type="number" class="input-score" name="bet_a_{{ m.id }}" value="{{ m.my_bet_a if m.my_bet_a is not none else '' }}" min="0">
                    {% endif %}
                </td>
                <td>
                    {% if m.is_locked %}
                        {% if m.is_started %}
                            <span class="badge badge-live">Live/Ended</span>
                        {% else %}
                            <span class="badge badge-locked">Locked (-1h)</span>
                        {% endif %}
                    {% else %}
                        <span class="badge" style="background:#e6f4ea; color:#137333;">Open</span>
                    {% endif %}
                </td>
                <td>
                    {% if m.is_started %}
                        <small>
                        {% for other_u, b_h, b_a in m.other_bets %}
                            <strong>{{ other_u }}</strong>: {{ b_h }}-{{ b_a }}{% if not loop.last %}, {% endif %}
                        {% else %}
                            No other bets
                        {% endfor %}
                        </small>
                    {% else %}
                        <span class="badge badge-locked">Hidden until Kickoff</span>
                    {% endif %}
                </td>
                <td>
                    <strong>{{ m.home_score if m.home_score is not none else '' }} - {{ m.away_score if m.away_score is not none else '' }}</strong>
                </td>
            </tr>
            {% endfor %}
        </table>
        <div style="margin-top: 20px; text-align: right;">
            <button type="submit" class="btn">💾 Save All Open Bets</button>
        </div>
    </form>
</div>
{% endblock %}
"""

ADMIN_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="card">
    <h2>⚙️ Administrator: Input Official Scores</h2>
    <p>Entering values here automatically evaluates outcome matrix math and pushes score adjustments out to the main leaderboard.</p>
    <form method="POST" action="{{ url_for('admin_save', token=request.args.get('token')) }}">
        <table>
            <tr>
                <th>ID</th>
                <th>Group</th>
                <th>Matchup</th>
                <th>Kickoff (UTC)</th>
                <th>Official Fulltime Score</th>
            </tr>
            {% for m in matches %}
            <tr>
                <td>#{{ m.id }}</td>
                <td>{{ m.grp }}</td>
                <td><strong>{{ m.home_team }}</strong> vs <strong>{{ m.away_team }}</strong></td>
                <td><small>{{ m.kickoff }}</small></td>
                <td>
                    <input type="number" class="input-score" name="score_h_{{ m.id }}" value="{{ m.home_score if m.home_score is not none else '' }}" min="0">
                    -
                    <input type="number" class="input-score" name="score_a_{{ m.id }}" value="{{ m.away_score if m.away_score is not none else '' }}" min="0">
                </td>
            </tr>
            {% endfor %}
        </table>
        <div style="margin-top: 20px; text-align: right;">
            <button type="submit" class="btn" style="background: #d9534f;">Update Tournament Database</button>
        </div>
    </form>
</div>
{% endblock %}
"""

# Registering templates smoothly into Flask's Jinja Environment
app.jinja_loader = DictLoader({
    'base': BASE_LAYOUT,
    'dashboard': DASHBOARD_TEMPLATE,
    'admin': ADMIN_TEMPLATE
})

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY,
                grp TEXT, home_team TEXT, away_team TEXT,
                kickoff TEXT, home_score INTEGER, away_score INTEGER
            )""")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bets (
                user TEXT, match_id INTEGER,
                home_bet INTEGER, away_bet INTEGER,
                PRIMARY KEY (user, match_id)
            )""")
        
        if not conn.execute("SELECT 1 FROM matches LIMIT 1").fetchone():
            conn.executemany(
                "INSERT INTO matches (id, grp, home_team, away_team, kickoff) VALUES (?, ?, ?, ?, ?)",
                MATCH_SCHEDULE
            )
            conn.commit()

init_db()

def compute_leaderboard():
    conn = get_db()
    matches = {m['id']: m for m in conn.execute("SELECT * FROM matches").fetchall()}
    bets = conn.execute("SELECT * FROM bets").fetchall()
    conn.close()
    
    scores = {user: 0 for user in USERS}
    for bet in bets:
        m = matches.get(bet['match_id'])
        if m and m['home_score'] is not None and m['away_score'] is not None:
            act_h, act_a = m['home_score'], m['away_score']
            bet_h, bet_a = bet['home_bet'], bet['away_bet']
            
            if act_h == bet_h and act_a == bet_a:
                scores[bet['user']] += 10
            elif (act_h > act_a and bet_h > bet_a) or (act_h < act_a and bet_h < bet_a) or (act_h == act_a and bet_h == bet_a):
                scores[bet['user']] += 4
                
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)

@app.route("/")
def dashboard():
    active_user = request.args.get("active_user", USERS[0])
    now = datetime.utcnow()
    
    conn = get_db()
    db_matches = conn.execute("SELECT * FROM matches ORDER BY kickoff ASC, id ASC").fetchall()
    db_bets = conn.execute("SELECT * FROM bets").fetchall()
    conn.close()
    
    bets_lookup = {}
    for b in db_bets:
        bets_lookup.setdefault(b['match_id'], {})[b['user']] = (b['home_bet'], b['away_bet'])
        
    match_data = []
    for m in db_matches:
        kickoff_dt = datetime.strptime(m['kickoff'], "%Y-%m-%d %H:%M:%S")
        
        # Stricter Lockout: Lock bets if time is up, OR if an admin has already entered an official score line
        has_official_score = m['home_score'] is not None and m['away_score'] is not None
        
        is_locked = now >= (kickoff_dt - timedelta(hours=1)) or has_official_score
        is_started = now >= kickoff_dt
        
        # COPA RULE FIX: If someone inputs a score early for testing, DO NOT leak other bets 
        # unless the official tournament calendar clock says the game has legally kicked off.
        if has_official_score and not is_started:
            is_reveal_allowed = False
        else:
            is_reveal_allowed = is_started
            
        user_bets = bets_lookup.get(m['id'], {})
        my_bet = user_bets.get(active_user)
        
        other_bets = []
        if is_reveal_allowed:  # <-- Updated here
            for u in USERS:
                if u != active_user and u in user_bets:
                    other_bets.append((u, user_bets[u][0], user_bets[u][1]))
                    
        match_data.append({
            "id": m['id'], "grp": m['grp'], "home_team": m['home_team'], "away_team": m['away_team'],
            "kickoff": m['kickoff'], "home_score": m['home_score'], "away_score": m['away_score'],
            "is_locked": is_locked, "is_started": is_started,
            "my_bet_h": my_bet[0] if my_bet else None, "my_bet_a": my_bet[1] if my_bet else None,
            "other_bets": other_bets
        })
        
    leaderboard = compute_leaderboard()
    
    return render_template(
        'dashboard',
        current_time=now.strftime("%Y-%m-%d %H:%M:%S"),
        leaderboard=leaderboard,
        users=USERS,
        active_user=active_user,
        match_data=match_data
    )

@app.route("/place-bet", methods=["POST"])
def place_bet():
    user = request.form.get("user")
    now = datetime.utcnow()
    
    conn = get_db()
    db_matches = conn.execute("SELECT id, kickoff FROM matches").fetchall()
    
    for m in db_matches:
        kickoff_dt = datetime.strptime(m['kickoff'], "%Y-%m-%d %H:%M:%S")
        if now >= (kickoff_dt - timedelta(hours=1)):
            continue
            
        h_val = request.form.get(f"bet_h_{m['id']}")
        a_val = request.form.get(f"bet_a_{m['id']}")
        
        if h_val != "" and h_val is not None and a_val != "" and a_val is not None:
            conn.execute("""
                INSERT INTO bets (user, match_id, home_bet, away_bet)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user, match_id) DO UPDATE SET home_bet=excluded.home_bet, away_bet=excluded.away_bet
            """, (user, m['id'], int(h_val), int(a_val)))
            
    conn.commit()
    conn.close()
    flash(f"Open predictions saved successfully for {user}!")
    return redirect(url_for("dashboard", active_user=user))

@app.route("/admin")
def admin_panel():
    # Changed 'pass' to 'token' to avoid Python keyword conflicts
    password = request.args.get("token")
    if password != "mysecret2026":
        flash("🔒 Unauthorized Access! The admin panel is locked to prevent accidental score updates.")
        return redirect(url_for("dashboard"))

    conn = get_db()
    matches = conn.execute("SELECT * FROM matches ORDER BY kickoff ASC, id ASC").fetchall()
    conn.close()
    return render_template(
        'admin',
        current_time=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        matches=matches
    )

@app.route("/admin/save", methods=["POST"])
def admin_save():
    # Changed 'pass' to 'token' here as well
    password = request.args.get("token")
    if password != "mysecret2026":
        flash("🔒 Unauthorized! Score update rejected.")
        return redirect(url_for("dashboard"))

    conn = get_db()
    db_matches = conn.execute("SELECT id FROM matches").fetchall()
    
    for m in db_matches:
        h_val = request.form.get(f"score_h_{m['id']}")
        a_val = request.form.get(f"score_a_{m['id']}")
        
        if h_val is not None and h_val.strip() != "" and a_val is not None and a_val.strip() != "":
            conn.execute(
                "UPDATE matches SET home_score=?, away_score=? WHERE id=?",
                (int(h_val.strip()), int(a_val.strip()), m['id'])
            )
        else:
            conn.execute(
                "UPDATE matches SET home_score=NULL, away_score=NULL WHERE id=?",
                (m['id'],)
            )
            
    conn.commit()
    conn.close()
    flash("Database synchronized! Blank entries successfully reset to TBD.")
    return redirect(url_for("admin_panel", token=password))
    
@app.route("/download-db-backup-xyz")
def download_db():
    if os.path.exists(DB_FILE):
        return send_file(DB_FILE, as_attachment=True)
    else:
        return "Database file not found yet!", 404

if __name__ == "__main__":
    app.run(debug=True)
