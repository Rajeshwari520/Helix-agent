"""Urgency scoring engine.

Each matched signal adds points. The total maps to a priority level, and every
matched signal is returned as a human-readable reason (explainability).

    score >= 5   -> Critical
    score >= 3   -> High
    score >= 1.5 -> Medium
    otherwise    -> Low

GENERIC_SIGNALS apply to every helpdesk. Each domain can add its own signals in
data/<domain>/domain.json ("extra_signals").
"""
import re
from functools import lru_cache

from app import config

GENERIC_SIGNALS = [
    # (name, points, patterns)
    ("security / fraud risk", 5, [
        r"\bfraud", r"\bhack(ed)?\b", r"unauthori[sz]ed (login|access|transaction|charge)",
        r"(did not|didn't) do this", r"(do not|don't) recogni[sz]e",
        r"someone (else )?(logged|signed) in", r"unknown (charge|device|login)",
        r"\bphishing\b", r"\bransomware\b", r"\bmalware\b", r"\bvirus\b", r"\binfected\b", r"data (leak|breach)",
        r"pretending to be", r"asking for (my )?(password|bank|otp|login|card|pin)",
        r"someone (has|knows|got|is using|used) my (password|account|login)", r"(never|did not|didn't) sen[dt]",
        r"(did not|didn't|never) authori[sz]e"]),
    ("threat to personal safety", 5, [r"\bthreaten", r"\bunsafe\b", r"\bviolen(ce|t)\b"]),
    ("legal threat", 5, [r"legal (action|notice)", r"\blawyer\b", r"\bcourt\b", r"consumer forum"]),
    ("service outage / business blocked", 5, [
        r"(error|http|status)\s*500", r"500 (error|internal)", r"internal server error",
        r"(site|service|system|server|portal|vpn|network|internet|email server) (is |are |has |went )?(completely )?down",
        r"\boutage\b", r"(no one|nobody|everyone)( here)? (can'?t|cannot|is unable to|can) (work|access|log ?in|connect|use)",
        r"whole team is blocked"]),
    ("money lost or wrongly charged", 3, [
        r"(charged|debited|deducted|paid) (twice|two times|2 times|double)", r"double charg",
        r"(money|amount)? ?deducted", r"without (my )?permission", r"billed .* never", r"auto.?(debit|renew)",
        r"(money|amount|fee)( was)? (taken|debited) from", r"(taken|debited) from my (account|card|bank)",
        r"salary[^.]{0,30}\bless\b"]),
    ("user blocked from working", 3, [
        r"\bcrash", r"shuts down", r"closes immediately", r"can(not|'t) (get|log ?in|sign ?in|access|connect)",
        r"\bblank\b", r"white screen", r"\bfreez", r"(unable|not able) to (log ?in|access|connect|work)",
        r"can(not|'t) (work|continue|open|start|use|sign ?in)", r"\brejected\b", r"\bdisabled\b",
        r"won'?t (start|boot|open|turn on)", r"stuck on", r"not turning on"]),
    ("sensitive HR / safety matter", 3, [r"\bharass", r"\bdiscriminat", r"\bthreaten", r"\bbull(y|ied|ying)\b"]),
    ("data deletion request", 3, [r"delete (my |our )?(\w+ )?(account|data|profile)", r"close my (\w+ )?account"]),
    ("long wait / repeated contact", 3, [r"waiting (for )?\d+ days", r"(third|3rd) time", r"again and again"]),
    ("problem with a workaround", 1.5, [
        r"\brefund", r"not (coming|arriving|receiving|working|received|credited)", r"\bslow\b", r"forever",
        r"\bwrong\b", r"\berror\b", r"\bfail", r"\blocked\b", r"\bmissing\b", r"\bstuck\b", r"timing out",
        r"\bempty\b", r"corrupt", r"\brude\b", r"not (scheduled|updated)", r"does nothing", r"\bexpired?\b",
        r"not (syncing|loading|opening|connecting|updating|available|visible|showing|uploaded|published|reimbursed|paid|responding|detected|displaying)",
        r"disconnect", r"\bpending\b", r"buffering", r"flicker", r"\bunpaid\b", r"\bleak", r"stopped (working|responding)",
        r"(forgot|can'?t remember|cannot remember) (my |the )?password", r"(joins|joining|starts|starting) (tomorrow|on monday|next week)",
        r"needs? (an? )?(\w+ )?login", r"\bjammed?\b"]),
    ("cosmetic only (spelling / name)", -1.5, [r"spell(ed|ing)", r"wrong name", r"name is (shown|spelled) wrong"]),
    ("urgent wording", 1, [r"\burgent", r"\basap\b", r"immediately", r"!!"]),
    ("angry customer", 1, [r"unacceptable", r"\bworst\b", r"disappointing", r"terrible", r"shouted"]),
]

LEVELS = [(5, "Critical"), (3, "High"), (1.5, "Medium"), (0, "Low")]


@lru_cache(maxsize=None)
def _compiled(domain_name: str):
    extra = [(s["name"], s["points"], s["patterns"]) for s in config.load_domain(domain_name).extra_signals]
    return [(name, pts, [re.compile(p, re.I) for p in pats]) for name, pts, pats in GENERIC_SIGNALS + extra]


def score(text: str) -> dict:
    total, reasons = 0.0, []
    for name, pts, patterns in _compiled(config.domain().name):
        if any(p.search(text) for p in patterns):
            total += pts
            reasons.append(f"{name} (+{pts:g})")
    priority = next(level for threshold, level in LEVELS if total >= threshold)
    return {"priority": priority, "urgency_score": total, "reasons": reasons or ["no urgency signal"]}
