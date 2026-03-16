from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime

app = Flask(__name__)

DB = "model_portfolio.db"


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


# -----------------------------
# Main comparison screen
# -----------------------------
@app.route("/")
def index():

    conn = get_db()

    holdings = conn.execute("""
        SELECT fund_id,fund_name,current_value
        FROM client_holdings
        WHERE client_id='C001'
    """).fetchall()

    plan = conn.execute("SELECT * FROM model_funds").fetchall()

    plan_dict = {f["fund_id"]: f for f in plan}

    total = sum(h["current_value"] for h in holdings)

    results = []

    total_buy = 0
    total_sell = 0

    for h in holdings:

        fund_id = h["fund_id"]
        current = h["current_value"]

        current_pct = (current / total) * 100

        if fund_id in plan_dict:

            target_pct = plan_dict[fund_id]["allocation_pct"]

            drift = target_pct - current_pct

            amount = drift / 100 * total

            if amount > 0:
                action = "BUY"
                total_buy += amount
            else:
                action = "SELL"
                total_sell += abs(amount)

        else:

            target_pct = None
            drift = None
            amount = current
            action = "REVIEW"

        results.append({
            "fund": h["fund_name"],
            "current_pct": round(current_pct,2),
            "target_pct": target_pct,
            "drift": None if drift is None else round(drift,2),
            "action": action,
            "amount": round(abs(amount))
        })

    conn.close()

    return render_template(
        "index.html",
        funds=results,
        total=total,
        buy=round(total_buy),
        sell=round(total_sell),
        cash=round(total_buy-total_sell)
    )


# -----------------------------
# Holdings screen
# -----------------------------
@app.route("/holdings")
def holdings():

    conn = get_db()

    data = conn.execute("""
        SELECT fund_name,current_value
        FROM client_holdings
        WHERE client_id='C001'
    """).fetchall()

    total = sum(d["current_value"] for d in data)

    conn.close()

    return render_template("holdings.html",data=data,total=total)


# -----------------------------
# History screen
# -----------------------------
@app.route("/history")
def history():

    conn = get_db()

    sessions = conn.execute("""
        SELECT * FROM rebalance_sessions
        ORDER BY created_at DESC
    """).fetchall()

    conn.close()

    return render_template("history.html",sessions=sessions)


# -----------------------------
# Save recommendation
# -----------------------------
@app.route("/save")
def save():

    conn = get_db()

    total = conn.execute("""
        SELECT SUM(current_value)
        FROM client_holdings
        WHERE client_id='C001'
    """).fetchone()[0]

    now = datetime.now()

    conn.execute("""
        INSERT INTO rebalance_sessions
        (client_id,created_at,portfolio_value,total_to_buy,total_to_sell,net_cash_needed,status)
        VALUES (?,?,?,?,?,?,?)
    """,("C001",now,total,200000,120000,80000,"PENDING"))

    conn.commit()
    conn.close()

    return redirect("/history")


# -----------------------------
# Edit plan
# -----------------------------
@app.route("/edit",methods=["GET","POST"])
def edit():

    conn = get_db()

    if request.method == "POST":

        for fund_id in request.form:

            pct = request.form[fund_id]

            conn.execute("""
                UPDATE model_funds
                SET allocation_pct=?
                WHERE fund_id=?
            """,(pct,fund_id))

        conn.commit()

        return redirect("/")

    funds = conn.execute("SELECT * FROM model_funds").fetchall()

    conn.close()

    return render_template("edit_plan.html",funds=funds)



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)