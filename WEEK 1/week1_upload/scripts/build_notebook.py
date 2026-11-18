"""Builds and executes notebooks/01_baseline_routing.ipynb (no Jupyter needed).

Each cell is executed in a shared namespace; stdout and matplotlib figures are
captured and stored as notebook outputs.
"""
import base64
import contextlib
import io
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT / "notebooks")

CELLS = [
("md", """# Week 1 — Rule-Based Routing Baseline
**Project:** AI Customer Support & Ticket Management Agent (Helix Agent) · **Intern:** Rajeshwari R · **KGIT**

This notebook builds a simple **keyword/rule-based** triage system and measures how well it predicts:
1. **Category** → which team gets the ticket
2. **Priority** (Low / Medium / High / Critical)
3. **Escalation** (needs a Team Lead or not)

These numbers are the **baseline**. From Week 2 onwards, the ML classifier must beat them.

Data: `data/kgit/tickets.csv` — 50 **synthetic** labeled KGIT helpdesk tickets (10 per category). Categories are **assumed** until the mentor confirms them."""),

("code", """import re
import json
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import (accuracy_score, f1_score, classification_report,
                             confusion_matrix, ConfusionMatrixDisplay,
                             precision_score, recall_score)

df = pd.read_csv("../data/kgit/tickets.csv")
df["text"] = (df["subject"] + ". " + df["body"]).str.lower()
print(df.shape)
df[["ticket_id", "subject", "category", "priority", "assigned_team", "needs_escalation"]].head()"""),

("md", "## 1. Label distribution"),

("code", """fig, axes = plt.subplots(1, 3, figsize=(13, 3.5))
for ax, col in zip(axes, ["category", "priority", "needs_escalation"]):
    df[col].value_counts().plot.bar(ax=ax, color="#4C72B0")
    ax.set_title(col); ax.set_xlabel(""); ax.tick_params(axis="x", rotation=0)
plt.tight_layout(); plt.show()"""),

("md", """## 2. Routing rules
**Category:** count keyword hits per category; the category with the most hits wins. Ties → first in list. No hits → `General`.

**Priority:** checked from most to least severe (Critical → High → Medium); default `Low`.

**Escalation:** security/fraud/phishing, legal notice, harassment, data deletion, Critical priority, or complaint keywords."""),

("code", """CATEGORY_KEYWORDS = {
    "IT Support":         ["laptop", "vpn", "wi-fi", "wifi", "printer", "outlook", "email server", "install",
                           "software", "monitor", "blue screen", "network", "internet", "shared drive", "phishing",
                           "suspicious", "infected", "crash"],
    "Access & Accounts":  ["password", "login", "log in", "locked", "access", "github", "jira", "mfa",
                           "authenticator", "account", "new joiner", "joins", "remove his access", "permission"],
    "Training & Courses": ["course", "lms", "module", "certificate", "batch", "exam", "assessment", "trainer",
                           "session", "slides", "marks", "enroll", "recording", "class", "students"],
    "HR & Admin":         ["salary", "leave", "experience letter", "id card", "payslip", "hr portal", "harassment",
                           "colleague", "reimbursement", "holiday", "ac ", "bank details", "office"],
    "Billing & Finance":  ["fee", "charged", "receipt", "payment", "refund", "invoice", "emi", "billing",
                           "vendor", "deducted", "gst", "card", "legal notice"],
}
TEAM = {"IT Support": "IT Service Desk", "Access & Accounts": "Identity & Access Team",
        "Training & Courses": "Learning Team", "HR & Admin": "HR & Admin Team",
        "Billing & Finance": "Finance Team"}

PRIORITY_RULES = [
    ("Critical", ["fraud", "do not recognise", "did not do this", "phishing", "legal notice",
                  "entire team", "nobody can", "for all", "is down"]),
    ("High",     ["charged twice", "deducted", "salary has not", "cannot work", "cannot continue",
                  "cannot log in", "cannot get", "blue screen", "lost my phone", "remove his access",
                  "harassment", "delete my account", "whole batch", "exam starts"]),
    ("Medium",   ["slow", "not syncing", "disconnecting", "not loading", "buffering", "not received",
                  "locked", "pending", "error", "wrong", "missing", "refund", "rude", "new intern"]),
]

ESCALATION_KEYWORDS = ["fraud", "do not recognise", "did not do this", "phishing", "legal notice",
                       "harassment", "delete my account", "personal data", "rude", "insulted",
                       "unacceptable", "entire team", "nobody can"]

def predict_category(text):
    scores = {c: sum(kw in text for kw in kws) for c, kws in CATEGORY_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "IT Support"

def predict_priority(text):
    for level, kws in PRIORITY_RULES:
        if any(kw in text for kw in kws):
            return level
    return "Low"

def predict_escalation(text, priority):
    return "Yes" if priority == "Critical" or any(kw in text for kw in ESCALATION_KEYWORDS) else "No"

df["pred_category"] = df["text"].apply(predict_category)
df["pred_team"] = df["pred_category"].map(TEAM)
df["pred_priority"] = df["text"].apply(predict_priority)
df["pred_escalation"] = [predict_escalation(t, p) for t, p in zip(df["text"], df["pred_priority"])]
df[["ticket_id", "subject", "category", "pred_category", "priority", "pred_priority",
    "needs_escalation", "pred_escalation"]].head(10)"""),

("md", """## 3. Metrics
We compare the rules against a **majority-class baseline** (always predict the most common label).
Macro-F1 treats every class equally, so it is the main metric."""),

("code", """def majority(series):
    return [series.mode()[0]] * len(series)

rows = []
for task, y_true, y_pred in [
    ("Category / team", df["category"], df["pred_category"]),
    ("Priority",        df["priority"], df["pred_priority"]),
    ("Escalation",      df["needs_escalation"], df["pred_escalation"]),
]:
    rows.append({"task": task, "method": "Majority class",
                 "accuracy": accuracy_score(y_true, majority(y_true)),
                 "macro_f1": f1_score(y_true, majority(y_true), average="macro", zero_division=0)})
    rows.append({"task": task, "method": "Rule-based",
                 "accuracy": accuracy_score(y_true, y_pred),
                 "macro_f1": f1_score(y_true, y_pred, average="macro", zero_division=0)})
metrics = pd.DataFrame(rows).round(3)
metrics"""),

("code", """print("CATEGORY\\n", classification_report(df["category"], df["pred_category"], zero_division=0))
print("PRIORITY\\n", classification_report(df["priority"], df["pred_priority"],
      labels=["Critical", "High", "Medium", "Low"], zero_division=0))

esc_recall = recall_score(df["needs_escalation"], df["pred_escalation"], pos_label="Yes")
esc_precision = precision_score(df["needs_escalation"], df["pred_escalation"], pos_label="Yes")
print(f"ESCALATION  recall={esc_recall:.2f}  precision={esc_precision:.2f}")
print("Escalation recall matters most: a missed escalation is a safety risk.")"""),

("md", "## 4. Confusion matrices"),

("code", """fig, axes = plt.subplots(1, 2, figsize=(13, 5))
cats = list(CATEGORY_KEYWORDS)
ConfusionMatrixDisplay(confusion_matrix(df["category"], df["pred_category"], labels=cats),
                       display_labels=cats).plot(ax=axes[0], cmap="Blues", colorbar=False)
axes[0].set_title("Category (rule-based)"); axes[0].tick_params(axis="x", rotation=30)
pris = ["Critical", "High", "Medium", "Low"]
ConfusionMatrixDisplay(confusion_matrix(df["priority"], df["pred_priority"], labels=pris),
                       display_labels=pris).plot(ax=axes[1], cmap="Oranges", colorbar=False)
axes[1].set_title("Priority (rule-based)")
plt.tight_layout(); plt.savefig("../docs/kgit/baseline_confusion_matrix.png", dpi=120); plt.show()"""),

("md", """## 4b. Fair check — rules on tickets they were NOT written from
The keywords above were written while looking at these 50 tickets, so the scores above are **optimistic**.
Below, the same rules are run on the **450 template training tickets** (`data/kgit/train_tickets.csv`), which use different wording."""),

("code", """train = pd.read_csv("../data/kgit/train_tickets.csv")
train["pred"] = train["text"].str.lower().apply(predict_category)
unseen_acc = accuracy_score(train["category"], train["pred"])
unseen_f1 = f1_score(train["category"], train["pred"], average="macro")
print(f"Rules on 450 unseen-wording tickets: accuracy {unseen_acc:.2f}, macro-F1 {unseen_f1:.2f}")"""),

("md", "## 5. Error analysis — where do the rules fail?"),

("code", """errors = df[(df["category"] != df["pred_category"]) | (df["priority"] != df["pred_priority"])]
print(f"{len(errors)} of {len(df)} tickets have at least one wrong prediction\\n")
errors[["ticket_id", "subject", "category", "pred_category", "priority", "pred_priority"]]"""),

("md", """**Typical failure reasons**
- **Shared words across categories** — e.g. *"access"* and *"account"* appear in IT, Access and Billing tickets; *"card"* can be an ID card (HR) or a payment card (Billing).
- **Priority depends on meaning, not words** — "I cannot log in" can be Medium or High depending on impact; keywords cannot see context.
- **Rules do not generalise** — new phrasing (e.g. "money got cut twice") is missed unless a keyword is added by hand.

These limitations are the reason for the Week 2 **ML classifier** and the Week 3 **RAG + guardrails**."""),

("md", "## 6. Save baseline results"),

("code", """df[["ticket_id", "category", "pred_category", "pred_team", "priority", "pred_priority",
    "needs_escalation", "pred_escalation"]].to_csv("../data/kgit/baseline_predictions.csv", index=False)

summary = {
    "dataset": "data/kgit/tickets.csv (50 synthetic KGIT tickets)",
    "method": "keyword rule-based routing",
    "results": metrics.to_dict(orient="records"),
    "escalation_recall": round(esc_recall, 3),
    "escalation_precision": round(esc_precision, 3),
    "rules_on_unseen_wording_accuracy": round(unseen_acc, 3),
    "rules_on_unseen_wording_macro_f1": round(unseen_f1, 3),
}
with open("../docs/kgit/baseline_metrics.json", "w") as f:
    json.dump(summary, f, indent=2)
print(json.dumps(summary, indent=2))"""),

("md", """## 7. Conclusion
- The rule-based router gives a **measurable baseline** for category, priority and escalation.
- It is better than the majority-class baseline but **brittle**: on the 50 tickets the keywords were written from it looks excellent, but on 450 tickets with **different wording** its accuracy drops sharply (section 4b).
- **Next (Week 2):** train an ML classifier (TF-IDF + Logistic Regression) on a train/test split and compare against these numbers using the same metrics and confusion matrix."""),
]


def run():
    ns = {}
    nb_cells = []
    exec_count = 0
    for kind, src in CELLS:
        lines = src.splitlines(keepends=True)
        if kind == "md":
            nb_cells.append({"cell_type": "markdown", "metadata": {}, "source": lines})
            continue
        exec_count += 1
        outputs = []
        buf = io.StringIO()
        # Split off the last expression so it is displayed like Jupyter does
        body, last = src, None
        src_lines = src.rstrip().splitlines()
        tail = src_lines[-1]
        if tail and not tail.startswith((" ", "\t", "plt.", "print", "for ", "with ", "def ")) and "=" not in tail.split("(")[0]:
            body, last = "\n".join(src_lines[:-1]), tail
        with contextlib.redirect_stdout(buf):
            exec(compile(body, f"cell{exec_count}", "exec"), ns)
            value = eval(last, ns) if last else None
        if buf.getvalue():
            outputs.append({"output_type": "stream", "name": "stdout",
                            "text": buf.getvalue().splitlines(keepends=True)})
        for num in plt.get_fignums():
            fig = plt.figure(num)
            png = io.BytesIO(); fig.savefig(png, format="png", dpi=90, bbox_inches="tight")
            outputs.append({"output_type": "display_data", "metadata": {},
                            "data": {"image/png": base64.b64encode(png.getvalue()).decode(),
                                     "text/plain": ["<Figure>"]}})
        plt.close("all")
        if value is not None:
            data = {"text/plain": repr(value).splitlines(keepends=True)}
            if hasattr(value, "to_html"):
                data["text/html"] = value.to_html().splitlines(keepends=True)
            outputs.append({"output_type": "execute_result", "execution_count": exec_count,
                            "metadata": {}, "data": data})
        nb_cells.append({"cell_type": "code", "execution_count": exec_count, "metadata": {},
                         "outputs": outputs, "source": lines})

    nb = {"cells": nb_cells, "nbformat": 4, "nbformat_minor": 5,
          "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                       "language_info": {"name": "python"}}}
    with open("01_baseline_routing.ipynb", "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)
    print("Notebook written")


plt.show = lambda *a, **k: None  # figures are captured instead
run()
