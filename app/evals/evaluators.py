"""
RAG Evaluation metrics powered by Gemini 2.5 Flash (LLM-as-a-Judge) and
deterministic agentic checks (Tool Routing & Citation Compliance).
"""

import logging
import re
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

import app.config as config

logger = logging.getLogger(__name__)


class JudgeScore(BaseModel):
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalized score between 0.0 (worst) and 1.0 (best).",
    )
    reasoning: str = Field(
        ...,
        description="Concise 1-2 sentence explanation justifying the score.",
    )


def _judge_model_name() -> str:
    # Prefer Gemini 2.5 Flash for fast, low-cost, structured LLM-as-a-Judge evaluation
    model = (config.GRAPH_EXTRACTION_MODEL or "").strip()
    return model if model else "gemini-2.5-flash"


def _call_gemini_judge(prompt: str) -> JudgeScore:
    if not (config.GOOGLE_API_KEY or "").strip():
        return JudgeScore(
            score=0.0,
            reasoning="GOOGLE_API_KEY is not configured; Gemini 2.5 Flash judge could not run.",
        )

    try:
        client = genai.Client(api_key=config.GOOGLE_API_KEY)
        response = client.models.generate_content(
            model=_judge_model_name(),
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=JudgeScore,
                temperature=0.0,
            ),
        )
        parsed = response.parsed
        if isinstance(parsed, JudgeScore):
            return JudgeScore(
                score=round(max(0.0, min(1.0, float(parsed.score))), 3),
                reasoning=parsed.reasoning.strip(),
            )
        if response.text:
            obj = JudgeScore.model_validate_json(response.text)
            return JudgeScore(
                score=round(max(0.0, min(1.0, float(obj.score))), 3),
                reasoning=obj.reasoning.strip(),
            )
    except Exception as exc:
        logger.warning("Gemini 2.5 Flash judge error: %s", exc)
        return JudgeScore(
            score=0.0,
            reasoning=f"Judge evaluation failed: {str(exc)[:140]}",
        )

    return JudgeScore(score=0.0, reasoning="Empty response from Gemini 2.5 Flash judge.")


def evaluate_faithfulness(
    question: str,
    answer: str,
    contexts: list[str],
) -> dict[str, Any]:
    """
    LLM-as-a-Judge: Measures whether every factual claim in `answer` is strictly
    grounded in the retrieved `contexts` (detects hallucinations).
    """
    if not answer.strip():
        return {"key": "faithfulness", "score": 0.0, "comment": "Empty answer."}

    if not contexts:
        # If agent properly refused because nothing was retrieved, treat as faithful
        lower = answer.lower()
        if "could not find" in lower or "not found" in lower or "no relevant" in lower:
            return {
                "key": "faithfulness",
                "score": 1.0,
                "comment": "Agent accurately abstained when no context was retrieved.",
            }
        return {
            "key": "faithfulness",
            "score": 0.0,
            "comment": "Answer was generated without any retrieved context.",
        }

    context_blob = "\n\n---\n\n".join(contexts[:12])[:18000]
    prompt = f"""You are an impartial RAG Faithfulness Judge.
Evaluate whether the Assistant Answer is strictly grounded in the Retrieved Contexts.
Score from 0.0 to 1.0:
- 1.0 = Every factual claim in the answer is directly supported by the retrieved contexts (or the answer honestly states the information is missing).
- 0.5 = Mostly grounded, but contains minor unsupported extrapolations.
- 0.0 = Contains major hallucinations or fabricated facts not present in the contexts.

Question: {question}

Retrieved Contexts:
{context_blob}

Assistant Answer:
{answer}
"""
    res = _call_gemini_judge(prompt)
    return {"key": "faithfulness", "score": res.score, "comment": res.reasoning}


def evaluate_context_relevance(
    question: str,
    contexts: list[str],
) -> dict[str, Any]:
    """
    LLM-as-a-Judge: Measures whether the retrieved pgvector chunks and Neo4j triples
    contain relevant evidence for answering `question`.
    """
    if not contexts:
        return {
            "key": "context_relevance",
            "score": 0.0,
            "comment": "No chunks or knowledge graph triples were retrieved.",
        }

    context_blob = "\n\n---\n\n".join(contexts[:12])[:18000]
    prompt = f"""You are an impartial RAG Retrieval Relevance Judge.
Evaluate how relevant and sufficient the Retrieved Contexts are for answering the User Question.
Score from 0.0 to 1.0:
- 1.0 = Retrieved contexts contain clear, directly relevant evidence to answer the question.
- 0.5 = Partially relevant; contains tangential information or only part of the answer.
- 0.0 = Completely irrelevant or off-topic.

User Question: {question}

Retrieved Contexts:
{context_blob}
"""
    res = _call_gemini_judge(prompt)
    return {"key": "context_relevance", "score": res.score, "comment": res.reasoning}


def evaluate_answer_correctness(
    question: str,
    answer: str,
    expected_answer: str | None = None,
) -> dict[str, Any]:
    """
    LLM-as-a-Judge: Compares `answer` against `expected_answer` (or evaluates
    direct answer relevance & completeness if no reference answer is provided).
    """
    if not answer.strip():
        return {"key": "answer_correctness", "score": 0.0, "comment": "Empty answer."}

    if expected_answer and expected_answer.strip():
        prompt = f"""You are an impartial RAG Answer Correctness Judge.
Compare the Assistant Answer against the Reference Expected Answer for the given Question.
Score from 0.0 to 1.0:
- 1.0 = Factually accurate, complete, and consistent with the Reference Expected Answer.
- 0.5 = Partially correct or missing important key details from the Reference Expected Answer.
- 0.0 = Incorrect, contradictory, or fails to answer the question.

Question: {question}

Reference Expected Answer:
{expected_answer}

Assistant Answer:
{answer}
"""
    else:
        prompt = f"""You are an impartial RAG Answer Quality Judge.
Evaluate how directly, clearly, and completely the Assistant Answer addresses the User Question.
Score from 0.0 to 1.0:
- 1.0 = Clear, direct, well-structured, and completely addresses the question.
- 0.5 = Partially addresses the question or is vague.
- 0.0 = Off-topic or fails to answer.

Question: {question}

Assistant Answer:
{answer}
"""
    res = _call_gemini_judge(prompt)
    return {"key": "answer_correctness", "score": res.score, "comment": res.reasoning}


def evaluate_tool_routing(
    tools_used: list[str],
    expected_tools: list[str] | None = None,
) -> dict[str, Any]:
    """
    Deterministic check: Verifies that the Google ADK agent invoked the expected
    retrieval tools (or at least one retrieval tool when none are specified).
    """
    used_set = set(tools_used or [])
    if expected_tools:
        expected_set = set(expected_tools)
        matched = used_set & expected_set
        score = round(len(matched) / len(expected_set), 3) if expected_set else 1.0
        if matched == expected_set:
            comment = f"Matched all expected tools: {sorted(expected_set)}."
        else:
            comment = (
                f"Used {sorted(used_set) or ['none']}; expected {sorted(expected_set)}."
            )
        return {"key": "tool_routing", "score": score, "comment": comment}

    if used_set:
        return {
            "key": "tool_routing",
            "score": 1.0,
            "comment": f"Agent routed via {sorted(used_set)}.",
        }
    return {
        "key": "tool_routing",
        "score": 0.0,
        "comment": "Agent did not invoke any retrieval or graph tools.",
    }


def evaluate_citation_compliance(
    answer: str,
    contexts: list[str],
) -> dict[str, Any]:
    """
    Deterministic check: Verifies presence of `[Source: ...]` or `[Graph: ...]`
    citations when supporting contexts were retrieved.
    """
    if not contexts:
        return {
            "key": "citation_compliance",
            "score": 1.0,
            "comment": "No contexts retrieved; citations not applicable.",
        }

    has_source = bool(re.search(r"\[Source:\s*[^\]]+\]", answer, re.IGNORECASE))
    has_graph = bool(re.search(r"\[Graph:\s*[^\]]+\]", answer, re.IGNORECASE))

    if has_source or has_graph:
        kinds = []
        if has_source:
            kinds.append("Source")
        if has_graph:
            kinds.append("Graph")
        return {
            "key": "citation_compliance",
            "score": 1.0,
            "comment": f"Included verifiable {' + '.join(kinds)} citations.",
        }
    return {
        "key": "citation_compliance",
        "score": 0.0,
        "comment": "Missing [Source: ...] or [Graph: ...] citations.",
    }


def evaluate_single_example(
    question: str,
    answer: str,
    contexts: list[str],
    tools_used: list[str],
    expected_answer: str | None = None,
    expected_tools: list[str] | None = None,
) -> dict[str, Any]:
    """
    Run all 5 RAG evaluators on a single ADK agent turn.
    Returns `{"metrics": {...}, "overall_score": float}`.
    """
    results = [
        evaluate_faithfulness(question, answer, contexts),
        evaluate_context_relevance(question, contexts),
        evaluate_answer_correctness(question, answer, expected_answer),
        evaluate_tool_routing(tools_used, expected_tools),
        evaluate_citation_compliance(answer, contexts),
    ]
    metrics = {item["key"]: item for item in results}
    overall_score = round(sum(item["score"] for item in results) / len(results), 3) if results else 0.0
    return {
        "metrics": metrics,
        "overall_score": overall_score,
    }
