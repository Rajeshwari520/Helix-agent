"""Guardrails: PII redaction, prompt-injection detection, sensitive-topic checks.

Used in two places:
  * triage  -> decides if a ticket must be escalated to a Team Lead
  * RAG     -> decides if the AI may draft an answer at all (refusal)
"""
import re

# ---------------------------------------------------------------- PII redaction
PII_PATTERNS = [
    ("CARD", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("UPI", re.compile(r"\b[\w.-]{2,}@(?:ok\w+|ybl|paytm|upi|ibl|axl|apl)\b", re.I)),
    ("PHONE", re.compile(r"(?<!\d)(?:\+?91[ -]?)?[6-9]\d{9}(?!\d)")),
    ("OTP", re.compile(r"\b(?:otp|code|pin)\s*(?:is|:)?\s*\d{4,8}\b", re.I)),
    ("AADHAAR", re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b")),
]


def redact_pii(text: str) -> tuple[str, list[str]]:
    """Replace personal data with [TYPE] tags. Returns (clean_text, types_found)."""
    found = []
    for name, pattern in PII_PATTERNS:
        if pattern.search(text):
            found.append(name)
            text = pattern.sub(f"[{name}]", text)
    return text, found


# ------------------------------------------------------- prompt-injection check
INJECTION_PATTERNS = [
    r"ignore (all |the |any )?(previous|prior|above) (instructions|rules|prompts?)",
    r"disregard (your|the|all) (instructions|rules|guidelines)",
    r"(reveal|show|print|tell me) (your|the) (system )?(prompt|instructions|rules)",
    r"\byou are now\b",
    r"act as (an? )?(admin|administrator|developer|system)",
    r"\b(system prompt|jailbreak|developer mode)\b",
    r"(give|grant) me (admin|full) access",
    r"(approve|issue) (a |the )?refund (automatically|without (any )?(check|approval|review))",
]
_INJECTION_RE = [re.compile(p, re.I) for p in INJECTION_PATTERNS]


def detect_injection(text: str) -> bool:
    return any(p.search(text) for p in _INJECTION_RE)


# ----------------------------------------------------------- sensitive topics
SENSITIVE_TOPICS = {
    "security_or_fraud": [
        r"\bfraud", r"\bhack(ed|er)?\b", r"unauthori[sz]ed (login|access|transaction|charge|payment)",
        r"(did not|didn't|never) (do|make|authori[sz]e) (this|that|it)",
        r"\bphishing\b", r"\bransomware\b", r"\bmalware\b", r"\bvirus\b", r"data (leak|breach)",
        r"(clicked|opened) (a |on a )?(suspicious|fake) (link|email|attachment)",
        r"\binfected\b", r"pretending to be", r"asking for (my )?(password|bank|otp|login|card|pin)",
        r"someone (has|knows|got|is using|used) my (password|account|login)", r"(never|did not|didn't) sen[dt]",
        r"(did not|didn't|never) authori[sz]e",
        r"(do not|don't) recogni[sz]e", r"someone (else )?(logged|signed) in", r"unknown (charge|device|login|transaction)",
        r"(login|sign.?in) from (another|a different|unknown)", r"\bstolen\b",
    ],
    "legal_or_media": [
        r"legal (action|notice)", r"\blawyer\b", r"\bcourt\b", r"consumer (forum|court)", r"\bpolice\b",
        r"\bjournalist\b", r"\bmedia\b", r"\bpress\b", r"writing an article",
    ],
    "privacy_request": [
        r"delete (my |our )?(\w+ )?(account|data|personal data|profile)", r"close my (\w+ )?account( permanently)?",
        r"(erase|remove) (all )?my (personal )?(data|information)"
    ],
    "hr_sensitive": [
        r"\bharass", r"\bdiscriminat", r"\bthreaten", r"sexual(ly)? (misconduct|comments?)", r"\bbull(y|ied|ying)\b", r"\bunsafe\b",
    ],
    "complaint_or_anger": [
        r"\bunacceptable\b", r"\bworst\b", r"\bdisappointing\b", r"\bterrible\b", r"\bdisgusting\b", r"\binsult",
        r"waiting (for )?\d+ days", r"\b(shouted|rude|abusive)\b", r"\bnever (got|received)\b",
    ],
}
_SENSITIVE_RE = {k: [re.compile(p, re.I) for p in v] for k, v in SENSITIVE_TOPICS.items()}

# topics where the AI must NOT draft an answer (human only)
NO_AI_ANSWER_TOPICS = {"security_or_fraud", "legal_or_media", "privacy_request", "hr_sensitive"}


def sensitive_topics(text: str) -> list[str]:
    return [topic for topic, patterns in _SENSITIVE_RE.items() if any(p.search(text) for p in patterns)]


def check(text: str) -> dict:
    """Run all input guardrails on a ticket / question."""
    clean, pii = redact_pii(text)
    topics = sensitive_topics(text)
    injection = detect_injection(text)
    return {
        "redacted_text": clean,
        "pii_found": pii,
        "prompt_injection": injection,
        "sensitive_topics": topics,
        "ai_answer_allowed": not injection and not (set(topics) & NO_AI_ANSWER_TOPICS),
    }
