import os
from datetime import datetime, timedelta
import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Force Flask to look locally and ignore missing template directories
app = Flask(__name__, template_folder='.', static_folder=None)
app.secret_key = "super-secret-world-cup-key-2026"

# Configure Flask-Login securely
login_manager = LoginManager()
login_manager.login_view = "login"  # Corrected config key
login_manager.init_app(app)

DB_FILE = "world_cup_bets.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user['id'], user['username'])
    return None

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY,
            grp TEXT,
            home_team TEXT,
            away_team TEXT,
            kickoff TEXT,
            home_score INTEGER,
            away_score INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bets (
            user TEXT NOT NULL,
            match_id INTEGER NOT NULL,
            home_bet INTEGER,
            away_bet INTEGER,
            PRIMARY KEY (user, match_id)
        )
    """)
    
    row_count = conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    if row_count == 0:
        sample_matches = [
            (1, "Group A", "Mexico", "South Africa", "2026-06-11 19:00:00"),
            (2, "Group A", "France", "Uruguay", "2026-06-11 21:30:00")
        ]
        conn.executemany("INSERT INTO matches (id, grp, home_team, away_team, kickoff) VALUES (?, ?, ?, ?, ?)", sample_matches)
        
    conn.commit()
    conn.close()

init_db()

# --- AUTHENTICATION ROUTES ---

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password")
        
        if not username or not password:
            flash("Please fill in all fields.")
            return redirect(url_for("register"))
            
        hashed_password = generate_password_hash(password)
        conn = get_db()
        try:
            conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            flash("Account created successfully! Please log in.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("That username is already taken.")
        finally:
            conn.close()
            
    return render_template_string("""
    <div style="max-width:400px; margin:80px auto; font-family:sans-serif; border:1px solid #ddd; padding:30px; border-radius:8px;">
        <h2>📝 Create Tournament Account</h2>
        {% with messages = get_flashed_messages() %}{% if messages %}{% for m in messages %}<p style="color:red;">{{m}}</p>{% endfor %}{% endif %}{% endwith %}
        <form method="POST">
            <p>Username:<br><input type="text" name="username" style="width:100%; padding:8px; margin-top:5px;" required></p>
            <p>Password:<br><input type="password" name="password" style="width:100%; padding:8px; margin-top:5px;" required></p>
            <button type="submit" style="width:100%; background:#28a745; color:white; border:none; padding:10px; font-weight:bold; cursor:pointer; border-radius:4px;">Register</button>
        </form>
        <p style="margin-top:15px; text-align:center;"><a href="/login">Already have an account? Log in here</a></p>
    </div>
    """)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password")
        
        conn = get_db()
        user_row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        
        if user_row and check_password_hash(user_row['password_hash'], password):
            user_obj = User(user_row['id'], user_row['username'])
            login_user(user_obj)
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password.")
            
    return render_template_string("""
    <div style="max-width:400px; margin:80px auto; font-family:sans-serif; border:1px solid #ddd; padding:30px; border-radius:8px;">
        <h2>🔐 Player Log-In</h2>
        {% with messages = get_flashed_messages() %}{% if messages %}{% for m in messages %}<p style="color:red;">{{m}}</p>{% endfor %}{% endif %}{% endwith %}
        <form method="POST">
            <p>Username:<br><input type="text" name="username" style="width:100%; padding:8px; margin-top:5px;" required></p>
            <p>Password:<br><input type="password" name="password" style="width:100%; padding:8px; margin-top:5px;" required></p>
            <button type="submit" style="width:100%; background:#0b3c5d; color:white; border:none; padding:10px; font-weight:bold; cursor:pointer; border-radius:4px;">Log In</button>
        </form>
        <p style="margin-top:15px; text-align:center;"><a href="/register">New player? Register your account here</a></p>
    </div>
    """)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have logged out.")
    return redirect(url_for("login"))

# --- SECURE DASHBOARD ---

@app.route("/", methods=["GET", "POST"])
@login_required
def dashboard():
    now = datetime.utcnow()
    current_username = current_user.username 
    conn = get_db()
    
    if request.method == "POST":
        db_matches = conn.execute("SELECT id, kickoff FROM matches").fetchall()
        for m in db_matches:
            kickoff_dt = datetime.strptime(m['kickoff'], "%Y-%m-%d %H:%M:%S")
            is_locked = now >= (kickoff_dt - timedelta(hours=1))
            
            if not is_locked:
                h_bet = request.form.get(f"home_bet_{m['id']}")
                a_bet = request.form.get(f"away_bet_{m['id']}")
                if h_bet != "" and h_bet is not None and a_bet != "" and a_bet is not None:
                    conn.execute("""
                        INSERT INTO bets (user, match_id, home_bet, away_bet) VALUES (?, ?, ?, ?)
                        ON CONFLICT(user, match_id) DO UPDATE SET home_bet=excluded.home_bet, away_bet=excluded.away_bet
                    """, (current_username, m['id'], int(h_bet), int(a_bet)))
        conn.commit()
        flash("Your predictions have been securely saved!")
        return redirect(url_for("dashboard"))

    db_matches = conn.execute("SELECT * FROM matches ORDER BY kickoff ASC, id ASC").fetchall()
    db_user_bets = conn.execute("SELECT * FROM bets WHERE user=?", (current_username,)).fetchall()
    user_bets = {b['match_id']: b for b in db_user_bets}
    
    match_data = []
    for m in db_matches:
        kickoff_dt = datetime.strptime(m['kickoff'], "%Y-%m-%d %H:%M:%S")
        has_official_score = m['home_score'] is not None and m['away_score'] is not None
        is_locked = now >= (kickoff_dt - timedelta(hours=1)) or has_official_score
        is_started = now >= kickoff_dt
        
        other_bets = []
        if is_started:
            db_other = conn.execute("SELECT user, home_bet, away_bet FROM bets WHERE match_id=? AND user!=?", (m['id'], current_username)).fetchall()
            for ob in db_other:
                other_bets.append({'user': ob['user'], 'home_bet': ob['home_bet'], 'away_bet': ob['away_bet']})
                
        match_data.append({
            'id': m['id'], 'grp': m['grp'], 'home_team': m['home_team'], 'away_team': m['away_team'],
            'kickoff': m['kickoff'], 'home_score': m['home_score'], 'away_score': m['away_score'],
            'is_locked': is_locked, 'is_started': is_started,
            'user_home_bet': user_bets.get(m['id'], {}).get('home_bet', ''),
            'user_away_bet': user_bets.get(m['id'], {}).get('away_bet', ''),
            'other_bets': other_bets
        })
        
    standings = []
    db_users = conn.execute("SELECT username FROM users").fetchall()
    for u_row in db_users:
        uname = u_row['username']
        pts = 0
        u_bets = conn.execute("SELECT * FROM bets WHERE user=?", (uname,)).fetchall()
        for b in u_bets:
            m = conn.execute("SELECT home_score, away_score FROM matches WHERE id=?", (b['match_id'],)).fetchone()
            if m and m['home_score'] is not None and m['away_score'] is not None:
                if b['home_bet'] == m['home_score'] and b['away_bet'] == m['away_score']:
                    pts += 10
                elif (b['home_bet'] > b['away_bet'] and m['home_score'] > m['away_score']) or \
                     (b['home_bet'] < b['away_bet'] and m['home_score'] < m['away_score']) or \
                     (b['home_bet'] == b['away_bet'] and m['home_score'] == m['away_score']):
                    pts += 4
        standings.append({'user': uname, 'points': pts})
    standings = sorted(standings, key=lambda x: x['points'], reverse=True)
    conn.close()
    
    return render_template_string(INDEX_HTML, current_user=current_username, matches=match_data, standings=standings)

# --- ADMIN VIEW ---
@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    if request.args.get("token") != "mysecret2026":
        return "🔒 Unauthorized Access", 403
    
    conn = get_db()
    if request.method == "POST":
        db_matches = conn.execute("SELECT id FROM matches").fetchall()
        for m in db_matches:
            h_val = request.form.get(f"score_h_{m['id']}")
            a_val = request.form.get(f"score_a_{m['id']}")
            if h_val is not None and h_val.strip() != "" and a_val is not None and a_val.strip() != "":
                conn.execute("UPDATE matches SET home_score=?, away_score=? WHERE id=?", (int(h_val.strip()), int(a_val.strip()), m['id']))
            else:
                conn.execute("UPDATE matches SET home_score=NULL, away_score=NULL WHERE id=?", (m['id'],))
        conn.commit()
        flash("Tournament scores updated!")
        return redirect(url_for("admin_panel", token="mysecret2026"))
        
    matches = conn.execute("SELECT * FROM matches ORDER BY kickoff ASC, id ASC").fetchall()
    conn.close()
    return render_template_string(ADMIN_HTML, matches=matches)

INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>World Cup Pool</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background:#f4f6f9; }
        .container { max-width: 1000px; margin: auto; display: flex; gap: 20px; }
        .main-panel { flex: 3; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .side-panel { flex: 1; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: center; }
        th { background: #0b3c5d; color: white; }
    </style>
</head>
<body>
    <div style="max-width:1000px; margin:auto; display:flex; justify-content:space-between; align-items:center;">
        <h2>⚽ World Cup Predictor</h2>
        <p>Logged in as: <strong>{{ current_user }}</strong> | <a href="/logout">Logout</a></p>
    </div>
    <div class="container">
        <div class="main-panel">
            <h3>📋 Match Schedule & Your Predictions</h3>
            <form method="POST">
                <table>
                    <tr><th>Group</th><th>Matchup</th><th>Official Result</th><th>Your Prediction</th><th>Opponent Selections</th></tr>
                    {% for m in matches %}
                    <tr>
                        <td>{{ m.grp }}</td>
                        <td><strong>{{ m.home_team }}</strong> vs <strong>{{ m.away_team }}</strong><br><small>{{ m.kickoff }}</small></td>
                        <td>{% if m.home_score is not none %}{{ m.home_score }} - {{ m.away_score }}{% else %}TBD{% endif %}</td>
                        <td>
                            {% if m.is_locked %}
                                <strong>{{ m.user_home_bet }} - {{ m.user_away_bet }}</strong>
                            {% else %}
                                <input type="number" name="home_bet_{{ m.id }}" value="{{ m.user_home_bet }}" style="width:40px;"> - 
                                <input type="number" name="away_bet_{{ m.id }}" value="{{ m.user_away_bet }}" style="width:40px;">
                            {% endif %}
                        </td>
                        <td>
                            {% if m.is_started %}
                                {% for ob in m.other_bets %}{{ ob.user }}: {{ ob.home_bet }}-{{ ob.away_bet }}<br>{% endfor %}
                            {% else %}
                                🔒 Locked
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </table>
                <button type="submit" style="margin-top:20px; background:#0b3c5d; color:white; padding:12px; width:100%; border:none; cursor:pointer;">💾 Save Predictions</button>
            </form>
        </div>
        <div class="side-panel">
            <h3>🏆 Leaderboard</h3>
            <table>
                <tr><th>Rank</th><th>User</th><th>Points</th></tr>
                {% for row in standings %}
                <tr><td>#{{ loop.index }}</td><td>{{ row.user }}</td><td><strong>{{ row.points }}</strong></td></tr>
                {% endfor %}
            </table>
        </div>
    </div>
</body>
</html>
"""

ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head><title>Admin Control</title></head>
<body style="font-family:sans-serif; margin:30px;">
    <h2>⚙️ Admin Match Score Entry</h2>
    <form method="POST" action="/admin?token=mysecret2026">
        <table border="1" cellpadding="8" style="border-collapse:collapse; width:100%; max-width:600px;">
            <tr style="background:#ddd;"><th>Match</th><th>Official Score</th></tr>
            {% for m in matches %}
            <tr>
                <td>{{ m.home_team }} vs {{ m.away_team }}</td>
                <td>
                    <input type="number" name="score_h_{{ m.id }}" value="{{ m.home_score }}" style="width:40px;"> - 
                    <input type="number" name="score_a_{{ m.id }}" value="{{ m.away_score }}" style="width:40px;">
                </td>
            </tr>
            {% endfor %}
        </table>
        <button type="submit" style="margin-top:15px; background:red; color:white; padding:10px; border:none; cursor:pointer;">Update Official Tournament Scores</button>
    </form>
</body>
</html>
"""
