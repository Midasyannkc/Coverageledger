"""
Render the Tableau/QuickSight-equivalent dashboard as static charts (the
JD's stated BI tools; the sandbox cannot reach either SaaS product -- see
docs/cost-tradeoffs.md). Same validated categorical/sequential palette
approach used elsewhere in this portfolio.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.seed_mongo import get_client, seed
from src.reconcile_pmpm import pmpm

OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "dashboard"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID_COLOR = "#e3e2dd"
SEQ_RAMP = "#1a4f8a"  # single hue, dark step


def _style_axes(ax):
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(GRID_COLOR)
    ax.spines["bottom"].set_color(GRID_COLOR)
    ax.tick_params(colors=TEXT_SECONDARY, labelsize=9)
    ax.xaxis.grid(True, color=GRID_COLOR, linewidth=0.8)
    ax.set_axisbelow(True)


def chart_pmpm_by_client():
    db = _seeded_db()
    results = pmpm(db)
    rows = sorted(results.items(), key=lambda kv: kv[1]["pmpm"] or 0, reverse=True)
    labels = [k for k, _ in rows]
    values = [v["pmpm"] or 0 for _, v in rows]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(labels, values, color=SEQ_RAMP, height=0.55)
    for i, v in enumerate(values):
        ax.text(v + 5, i, f"${v:,.0f}", va="center", fontsize=9, color=TEXT_PRIMARY)
    _style_axes(ax)
    ax.invert_yaxis()
    ax.set_title("PMPM by client (reconciled)", color=TEXT_PRIMARY, fontsize=12, loc="left")
    ax.set_xlabel("PMPM (USD)", color=TEXT_SECONDARY, fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "01_pmpm_by_client.png", dpi=150)
    plt.close(fig)


def chart_enrollment_lifecycle():
    db = _seeded_db()
    adds = db.enrollment_events.count_documents({"event_type": "add"})
    terms = db.enrollment_events.count_documents({"event_type": "terminate"})
    active = adds - terms

    fig, ax = plt.subplots(figsize=(6, 4.5))
    bars = ax.bar(["Adds", "Terminations", "Net Active"], [adds, terms, active],
                   color=["#2a78d6", "#e34948", "#1baf7a"], width=0.55)
    for b, v in zip(bars, [adds, terms, active]):
        ax.text(b.get_x() + b.get_width() / 2, v + 2, str(v), ha="center", fontsize=10, color=TEXT_PRIMARY)
    _style_axes(ax)
    ax.set_title("Enrollment lifecycle (real event counts)", color=TEXT_PRIMARY, fontsize=12, loc="left")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "02_enrollment_lifecycle.png", dpi=150)
    plt.close(fig)


def chart_transmission_exactly_once():
    from src.transmit_834 import transmit
    db = _seeded_db()
    sent_counts = []
    for client in db.clients.find():
        sent_counts.append(transmit(db, client["group_code"], control_number=1))
    retried_counts = []
    for i, client in enumerate(db.clients.find(), start=2):
        retried_counts.append(transmit(db, client["group_code"], control_number=i))  # retry, should be 0 new

    fig, ax = plt.subplots(figsize=(7, 4.5))
    x = range(len(sent_counts))
    ax.bar([i - 0.2 for i in x], sent_counts, width=0.4, color="#2a78d6", label="First transmit")
    ax.bar([i + 0.2 for i in x], retried_counts, width=0.4, color="#eb6834", label="Retry (same run)")
    _style_axes(ax)
    ax.set_xticks(list(x))
    ax.set_xticklabels([c["group_code"] for c in db.clients.find()], fontsize=8)
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("Termination transmission: exactly-once under retry", color=TEXT_PRIMARY, fontsize=12, loc="left")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "03_transmission_exactly_once.png", dpi=150)
    plt.close(fig)


_DB_CACHE = {}


def _seeded_db():
    if "db" not in _DB_CACHE:
        client = get_client()
        db = client["coverageledger"]
        seed(db)
        _DB_CACHE["db"] = db
    return _DB_CACHE["db"]


if __name__ == "__main__":
    chart_pmpm_by_client()
    chart_enrollment_lifecycle()
    chart_transmission_exactly_once()
    print("wrote charts to", OUT_DIR)
