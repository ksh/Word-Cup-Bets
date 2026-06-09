# --- SECRET DATABASE VIEWER ROUTE ---
@app.route("/view-db")
def view_database():
    # Only allow access if you append your admin token to the URL
    if request.args.get("token") != "mysecret2026":
        return "🔒 Unauthorized Access", 403
        
    conn = get_db()
    
    # Grab everything from your tables
    users = conn.execute("SELECT id, username FROM users").fetchall()
    bets = conn.execute("SELECT user, match_id, home_bet, away_bet FROM bets").fetchall()
    matches = conn.execute("SELECT id, home_team, away_team, home_score, away_score FROM matches").fetchall()
    conn.close()
    
    # Render a clean, raw layout of your data rows
    return render_template_string("""
    <body style="font-family:sans-serif; margin:30px; background:#f4f6f9;">
        <h2>📊 Live Database Inspector</h2>
        <p><a href="/">Back to Dashboard</a></p>
        <hr>
        <h3>👥 Registered Users Table</h3>
        <table border="1" cellpadding="8" style="border-collapse:collapse; background:white;">
            <tr style="background:#ddd;"><th>ID</th><th>Username</th></tr>
            {% for u in users %}<tr><td>{{u.id}}</td><td>{{u.username}}</td></tr>{% endfor %}
        </table>
        
        <h3>⚽ Logged Bets Table</h3>
        <table border="1" cellpadding="8" style="border-collapse:collapse; background:white;">
            <tr style="background:#ddd;"><th>Player</th><th>Match ID</th><th>Home Bet</th><th>Away Bet</th></tr>
            {% for b in bets %}<tr><td>{{b.user}}</td><td>{{b.match_id}}</td><td>{{b.home_bet}}</td><td>{{b.away_bet}}</td></tr>{% endfor %}
        </table>
    </body>
    """, users=users, bets=bets, matches=matches)
