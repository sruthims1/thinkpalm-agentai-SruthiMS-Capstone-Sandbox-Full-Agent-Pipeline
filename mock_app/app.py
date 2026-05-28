from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import date
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
from data.maritime_data import CREW_DATA, FATIGUE_DATA, PORT_CALLS, INCIDENTS, VOYAGES

app = Flask(__name__)
app.secret_key = "marineops-secret-key"


def _days_remaining(expiry_str):
    expiry = date.fromisoformat(expiry_str)
    return (expiry - date.today()).days


# ── Dashboard ──────────────────────────────────────────────────────────────────
@app.route("/")
def dashboard():
    stats = {
        "expired_certs":    sum(1 for c in CREW_DATA if c["status"] == "expired"),
        "expiring_soon":    sum(1 for c in CREW_DATA if c["status"] == "expiring_soon"),
        "fatigue_violations": sum(1 for f in FATIGUE_DATA if f["status"] == "violation"),
        "open_incidents":   sum(1 for i in INCIDENTS if i["status"] == "pending_review"),
    }
    return render_template("dashboard.html", stats=stats)


# ── Crew Certifications ────────────────────────────────────────────────────────
@app.route("/crew-certs")
def crew_certs():
    all_crew = []
    for c in CREW_DATA:
        crew = dict(c)
        crew["days_remaining"] = _days_remaining(c["expiry"])
        all_crew.append(crew)

    return render_template(
        "crew_certs.html",
        all_crew=all_crew,
        expired=[c for c in all_crew if c["status"] == "expired"],
        expiring_soon=[c for c in all_crew if c["status"] == "expiring_soon"],
    )


@app.route("/crew-certs/renew", methods=["POST"])
def renew_cert():
    crew_id   = int(request.form["crew_id"])
    new_expiry = request.form["new_expiry"]
    for c in CREW_DATA:
        if c["id"] == crew_id:
            c["expiry"] = new_expiry
            c["status"] = "valid"
            break
    flash(f"Certificate updated successfully. New expiry: {new_expiry}", "success")
    return redirect(url_for("crew_certs"))


# ── Fatigue Management ─────────────────────────────────────────────────────────
@app.route("/fatigue")
def fatigue():
    flash_message = request.args.get("flash_message")
    flash_type    = request.args.get("flash_type", "success")
    return render_template(
        "fatigue.html",
        all_officers=FATIGUE_DATA,
        violations=[f for f in FATIGUE_DATA if f["status"] == "violation"],
        violation_count=sum(1 for f in FATIGUE_DATA if f["status"] == "violation"),
        compliant_count=sum(1 for f in FATIGUE_DATA if f["status"] == "compliant"),
        total_count=len(FATIGUE_DATA),
        flash_message=flash_message,
        flash_type=flash_type,
    )


@app.route("/fatigue/log", methods=["POST"])
def log_rest():
    officer_id  = int(request.form["officer_id"])
    rest_start  = request.form["rest_start"]
    rest_end    = request.form["rest_end"]
    flash_msg   = f"Rest hours logged for officer ID {officer_id} ({rest_start} → {rest_end})."
    return redirect(url_for("fatigue", flash_message=flash_msg, flash_type="success"))


# ── Port Call Management ───────────────────────────────────────────────────────
@app.route("/port-call")
def port_call():
    return render_template("port_call.html", port_calls=PORT_CALLS)


@app.route("/port-call/new", methods=["POST"])
def new_port_call():
    new_call = {
        "id": len(PORT_CALLS) + 1,
        "vessel":           request.form["vessel"],
        "port":             request.form["port"],
        "country":          "Unknown",
        "eta":              request.form["eta"],
        "etd":              request.form["etd"],
        "pre_arrival_96h":  "pending",
        "pre_arrival_24h":  "pending",
        "customs_clearance":"pending",
        "dangerous_goods":  request.form.get("dangerous_goods", "none"),
        "agent":            request.form.get("agent", "TBC"),
        "status":           "pre_arrival",
    }
    PORT_CALLS.append(new_call)
    flash("Port call created successfully.", "success")
    return redirect(url_for("port_call"))


@app.route("/port-call/submit-notice", methods=["POST"])
def submit_notice():
    port_call_id = int(request.form["port_call_id"])
    for pc in PORT_CALLS:
        if pc["id"] == port_call_id:
            pc["pre_arrival_24h"] = "submitted"
            break
    flash("24-hour pre-arrival notice submitted successfully.", "success")
    return redirect(url_for("port_call"))


# ── Incident Reporting ─────────────────────────────────────────────────────────
@app.route("/incidents")
def incidents():
    today = date.today().isoformat()
    stats = {
        "high_severity":  sum(1 for i in INCIDENTS if i["severity"] == "High"),
        "pending_review": sum(1 for i in INCIDENTS if i["status"] == "pending_review"),
        "approved":       sum(1 for i in INCIDENTS if i["status"] == "approved"),
        "total":          len(INCIDENTS),
    }
    overdue = [i for i in INCIDENTS if i["status"] == "pending_review" and i["deadline"] < today]
    return render_template("incidents.html", incidents=INCIDENTS, stats=stats, overdue=overdue)


@app.route("/incidents/new", methods=["POST"])
def new_incident():
    new_inc = {
        "id":                   f"INC-2026-{len(INCIDENTS)+1:03d}",
        "type":                 request.form["type"],
        "severity":             request.form["severity"],
        "date":                 date.today().isoformat(),
        "vessel":               request.form["vessel"],
        "location":             request.form["location"],
        "description":          request.form["description"],
        "reported_by":          "Current User",
        "status":               "pending_review",
        "officer_review":       None,
        "superintendent_approval": None,
        "authority_notified":   False,
        "deadline":             date.today().isoformat(),
    }
    INCIDENTS.append(new_inc)
    flash(f"Incident {new_inc['id']} reported successfully.", "success")
    return redirect(url_for("incidents"))


@app.route("/incidents/review", methods=["POST"])
def review_incident():
    incident_id    = request.form["incident_id"]
    officer_review = request.form["officer_review"]
    notify         = "notify_authority" in request.form
    for inc in INCIDENTS:
        if inc["id"] == incident_id:
            inc["officer_review"]       = officer_review
            inc["status"]               = "approved"
            inc["authority_notified"]   = notify
            break
    flash(f"Incident {incident_id} reviewed and approved.", "success")
    return redirect(url_for("incidents"))


# ── Voyage Planning ────────────────────────────────────────────────────────────
@app.route("/voyage")
def voyage():
    piracy_alerts = [v for v in VOYAGES if v.get("piracy_alert")]
    return render_template("voyage.html", voyages=VOYAGES, piracy_alerts=piracy_alerts)


@app.route("/voyage/new", methods=["POST"])
def new_voyage():
    new_v = {
        "id":             f"VOY-2026-{len(VOYAGES)+47:03d}",
        "vessel":         request.form["vessel"],
        "departure_port": request.form["departure_port"],
        "arrival_port":   request.form["arrival_port"],
        "departure_date": request.form["departure_date"],
        "eta":            "TBC",
        "distance_nm":    int(request.form.get("distance_nm", 0)),
        "speed_kts":      float(request.form.get("speed_kts", 0)),
        "fuel_type":      request.form.get("fuel_type", "VLSFO"),
        "bunker_qty_mt":  int(request.form.get("bunker_qty", 0)),
        "eca_zones":      [],
        "waypoints":      [],
        "status":         "planned",
        "weather_routing":"optimal",
        "piracy_alert":   False,
    }
    VOYAGES.append(new_v)
    flash(f"Voyage {new_v['id']} created successfully.", "success")
    return redirect(url_for("voyage"))


@app.route("/voyage/confirm-deviation", methods=["POST"])
def confirm_deviation():
    voyage_id = request.form["voyage_id"]
    for v in VOYAGES:
        if v["id"] == voyage_id:
            v["weather_routing"] = "deviation_confirmed"
            break
    flash("Route deviation confirmed. ETA updated.", "success")
    return redirect(url_for("voyage"))


# ── API endpoints (for Playwright testing) ────────────────────────────────────
@app.route("/api/crew")
def api_crew():
    from flask import jsonify
    return jsonify(CREW_DATA)


@app.route("/api/fatigue")
def api_fatigue():
    from flask import jsonify
    return jsonify(FATIGUE_DATA)


@app.route("/api/incidents")
def api_incidents():
    from flask import jsonify
    return jsonify(INCIDENTS)


@app.route("/api/voyages")
def api_voyages():
    from flask import jsonify
    return jsonify(VOYAGES)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
