"""Grounded answer service (RAG) with citations and guardrails.

Flow:
  1. Input guardrails  -> refuse on prompt injection; escalate on fraud / legal / privacy
  2. Retrieve approved FAQs (top-k) using the PII-redacted text
  3. Uncertainty check -> if the best match is too weak, do NOT answer; ask a human
  4. Draft a reply ONLY from the retrieved FAQ text, with [FAQ-id vN] citations
  5. Every result has requires_human_approval = True (nothing is sent automatically)

The draft is extractive (built from approved FAQ text), so it cannot invent facts.
An LLM rewriting step can be added later once a provider is approved; it must
keep the same citations and pass the same checks.
"""
import time

from app import config
from app.services import guardrails
from app.services.retriever import RETRIEVER_VERSION, FAQRetriever

REFUSAL_MESSAGE = ("This request cannot be handled automatically. "
                   "It has been flagged for review by a support team lead.")
ESCALATION_MESSAGE = ("This ticket involves a sensitive matter ({topics}). "
                      "No AI reply was drafted; a team lead must respond personally.")
LOW_CONFIDENCE_MESSAGE = ("No approved FAQ answers this question with enough confidence "
                          "(best match {score:.2f} < {threshold:.2f}). A support agent should reply manually.")


def _citation(hit: dict) -> dict:
    return {"faq_id": hit["faq_id"], "version": hit["version"], "question": hit["question"],
            "score": hit["score"]}


def _draft(hits: list[dict], customer_name: str | None) -> str:
    top = hits[0]
    lines = [f"Hi {customer_name}," if customer_name else "Hi,", "",
             f"Thank you for contacting us. {top['answer']} [{top['faq_id']} v{top['version']}]"]
    # add a second FAQ only if it is almost as relevant and from the same category
    if len(hits) > 1 and hits[1]["category"] == top["category"] and hits[1]["score"] >= 0.8 * top["score"]:
        lines.append(f"\nYou may also find this useful: {hits[1]['answer']} [{hits[1]['faq_id']} v{hits[1]['version']}]")
    lines += ["", "If this does not solve the issue, just reply to this message and we will help further.",
              "", "Regards,", "Customer Support"]
    return "\n".join(lines)


def answer(question: str, retriever: FAQRetriever, corpus_version: str,
           customer_name: str | None = None) -> dict:
    t0 = time.perf_counter()
    guard = guardrails.check(question)
    base = {
        "requires_human_approval": True,
        "corpus_version": corpus_version,
        "retriever_version": RETRIEVER_VERSION,
        "guardrails": {k: guard[k] for k in ("pii_found", "prompt_injection", "sensitive_topics")},
    }

    def done(**kw):
        return {**base, **kw, "latency_ms": round((time.perf_counter() - t0) * 1000, 1)}

    # 1. Refusal: prompt injection
    if guard["prompt_injection"]:
        return done(status="refused", draft_reply=None, message=REFUSAL_MESSAGE, citations=[],
                    confidence=0.0, escalate=True, escalation_reasons=["prompt_injection"])

    # 1b. Escalation: topics where AI must not answer
    blocked = [t for t in guard["sensitive_topics"] if t in guardrails.NO_AI_ANSWER_TOPICS]
    if blocked:
        return done(status="escalated", draft_reply=None,
                    message=ESCALATION_MESSAGE.format(topics=", ".join(blocked)),
                    citations=[], confidence=0.0, escalate=True, escalation_reasons=blocked)

    # 2. Retrieval on redacted text (PII never goes to the index or any external model)
    hits = retriever.search(guard["redacted_text"], k=config.RETRIEVAL_TOP_K)
    best = hits[0]["score"] if hits else 0.0

    # 3. Uncertainty
    if best < config.RETRIEVAL_MIN_SCORE:
        return done(status="low_confidence", draft_reply=None,
                    message=LOW_CONFIDENCE_MESSAGE.format(score=best, threshold=config.RETRIEVAL_MIN_SCORE),
                    citations=[_citation(h) for h in hits], confidence=round(best, 3),
                    escalate=False, escalation_reasons=[])

    # 4. Grounded draft
    soft_flags = [t for t in guard["sensitive_topics"] if t not in guardrails.NO_AI_ANSWER_TOPICS]
    return done(status="answered", draft_reply=_draft(hits, customer_name),
                message="Draft ready for agent review." + (
                    f" Note: {', '.join(soft_flags)} detected - review tone carefully." if soft_flags else ""),
                citations=[_citation(h) for h in hits], confidence=round(best, 3),
                escalate=bool(soft_flags), escalation_reasons=soft_flags)
