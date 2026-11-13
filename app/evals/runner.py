"""
Evaluation Runner for ADK Agentic RAG + Knowledge Graph.
Executes the real Google ADK Runner on evaluation test cases, scores outputs
with Gemini 2.5 Flash (LLM-as-a-Judge) + deterministic checks, and optionally
syncs datasets & experiments to LangSmith.
"""

import argparse
import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Any
import uuid

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import root_agent
import app.config as config
from app.evals.dataset import generate_synthetic_dataset, sync_dataset_to_langsmith
from app.evals.evaluators import (
    evaluate_answer_correctness,
    evaluate_citation_compliance,
    evaluate_context_relevance,
    evaluate_faithfulness,
    evaluate_single_example,
    evaluate_tool_routing,
)
from app.tracing import get_langsmith_client, is_langsmith_configured, ls_trace

logger = logging.getLogger(__name__)

APP_EVAL_NAME = "document_rag_eval"
_EVAL_RUNS: dict[str, list[dict[str, Any]]] = {}


def get_eval_runs(user_id: str) -> list[dict[str, Any]]:
    """Return recent evaluation runs for `user_id` (most recent first)."""
    return list(_EVAL_RUNS.get(user_id, []))


def _extract_contexts_from_response(resp: Any) -> list[str]:
    """Normalize tool response payloads from pgvector and Neo4j into context strings."""
    if not isinstance(resp, dict):
        return []

    extracted: list[str] = []

    # pgvector / hybrid_search results
    results = resp.get("results")
    if isinstance(results, list):
        for item in results:
            if not isinstance(item, dict):
                continue
            filename = item.get("filename", "unknown")
            content = item.get("content", "")
            if content:
                extracted.append(f"[Source: {filename}] {content}")

    # Neo4j graph_search / get_entity_relationships entities
    entities = resp.get("entities")
    if isinstance(entities, list):
        for ent in entities:
            if isinstance(ent, dict):
                name = ent.get("name") or ent.get("entity") or ""
                etype = ent.get("type") or ent.get("label") or ""
                desc = ent.get("description") or ""
                if name:
                    extracted.append(f"[Graph Entity: {name} ({etype})] {desc}".strip())

    # Neo4j relationships
    relationships = resp.get("relationships")
    if isinstance(relationships, list):
        for rel in relationships:
            if isinstance(rel, dict):
                src = rel.get("source") or rel.get("from") or ""
                rtype = rel.get("type") or rel.get("relationship") or "RELATED_TO"
                tgt = rel.get("target") or rel.get("to") or ""
                desc = rel.get("description") or ""
                if src and tgt:
                    extracted.append(f"[Graph: {src} -[{rtype}]-> {tgt}] {desc}".strip())

    return extracted


async def _run_adk_agent_once(user_id: str, question: str) -> dict[str, Any]:
    """Execute the real ADK agent on a single isolated question session."""
    session_service = InMemorySessionService()
    runner = Runner(
        app_name=APP_EVAL_NAME,
        agent=root_agent,
        session_service=session_service,
    )
    session = await session_service.create_session(
        app_name=APP_EVAL_NAME,
        user_id=user_id,
    )
    message = types.Content(
        role="user",
        parts=[types.Part(text=question)],
    )

    answer_text = ""
    tools_used: list[str] = []
    contexts: list[str] = []
    started = time.perf_counter()

    with ls_trace(
        name="adk_rag_eval_target",
        run_type="chain",
        inputs={"question": question, "user_id": user_id},
        tags=["eval", "adk-rag"],
    ):
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=message,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    fn_call = getattr(part, "function_call", None)
                    if fn_call and getattr(fn_call, "name", None):
                        if fn_call.name not in tools_used:
                            tools_used.append(fn_call.name)

                    fn_resp = getattr(part, "function_response", None)
                    if fn_resp and getattr(fn_resp, "response", None):
                        contexts.extend(_extract_contexts_from_response(fn_resp.response))

            if event.is_final_response() and event.content:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        answer_text += part.text

    latency_ms = round((time.perf_counter() - started) * 1000, 1)
    if not answer_text:
        answer_text = "I could not generate a response."

    return {
        "answer": answer_text,
        "tools_used": tools_used,
        "contexts": contexts,
        "latency_ms": latency_ms,
    }


def _compute_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {
            "total_cases": 0,
            "faithfulness": 0.0,
            "context_relevance": 0.0,
            "answer_correctness": 0.0,
            "tool_routing": 0.0,
            "citation_compliance": 0.0,
            "overall_score": 0.0,
            "avg_latency_ms": 0.0,
        }

    keys = [
        "faithfulness",
        "context_relevance",
        "answer_correctness",
        "tool_routing",
        "citation_compliance",
    ]
    summary: dict[str, Any] = {"total_cases": len(results)}
    for k in keys:
        vals = [r["metrics"][k]["score"] for r in results]
        summary[k] = round(sum(vals) / len(vals), 3)

    overall_vals = [r["overall_score"] for r in results]
    latencies = [r.get("latency_ms", 0.0) for r in results]
    summary["overall_score"] = round(sum(overall_vals) / len(overall_vals), 3)
    summary["avg_latency_ms"] = round(sum(latencies) / len(latencies), 1)
    return summary


async def _run_local_cases(
    user_id: str,
    examples: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    case_results: list[dict[str, Any]] = []
    for idx, ex in enumerate(examples, start=1):
        question = ex["question"]
        expected_answer = ex.get("expected_answer", "")
        expected_tools = ex.get("expected_tools", [])
        expected_sources = ex.get("expected_sources", [])

        agent_out = await _run_adk_agent_once(user_id=user_id, question=question)
        scored = evaluate_single_example(
            question=question,
            answer=agent_out["answer"],
            contexts=agent_out["contexts"],
            tools_used=agent_out["tools_used"],
            expected_answer=expected_answer,
            expected_tools=expected_tools,
        )
        case_results.append(
            {
                "id": ex.get("id") or f"case-{idx}",
                "question": question,
                "expected_answer": expected_answer,
                "expected_sources": expected_sources,
                "expected_tools": expected_tools,
                "answer": agent_out["answer"],
                "tools_used": agent_out["tools_used"],
                "contexts_count": len(agent_out["contexts"]),
                "latency_ms": agent_out["latency_ms"],
                "metrics": scored["metrics"],
                "overall_score": scored["overall_score"],
            }
        )
    return case_results


async def run_evaluation(
    user_id: str,
    examples: list[dict[str, Any]],
    dataset_name: str = "adk-rag-eval-dataset",
    experiment_prefix: str = "adk-rag-eval",
) -> dict[str, Any]:
    """
    Execute an end-to-end RAG evaluation run.
    If LangSmith is configured, syncs the dataset and logs the experiment via
    `langsmith.evaluation.aevaluate`, falling back gracefully to local mode on error.
    """
    if not examples:
        raise ValueError("At least one evaluation test case is required.")

    run_id = str(uuid.uuid4())[:8]
    langsmith_url: str | None = None
    langsmith_experiment: str | None = None
    langsmith_warning: str | None = None
    case_results: list[dict[str, Any]] = []

    if is_langsmith_configured():
        sync_info = sync_dataset_to_langsmith(dataset_name=dataset_name, examples=examples)
        if sync_info.get("synced"):
            try:
                from langsmith.evaluation import aevaluate

                client = get_langsmith_client()
                collected_by_q: dict[str, dict[str, Any]] = {}

                async def ls_target(inputs: dict[str, Any]) -> dict[str, Any]:
                    q = inputs["question"]
                    out = await _run_adk_agent_once(user_id=user_id, question=q)
                    collected_by_q[q] = out
                    return out

                def ls_faithfulness(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
                    return evaluate_faithfulness(
                        question=inputs["question"],
                        answer=outputs.get("answer", ""),
                        contexts=outputs.get("contexts", []),
                    )

                def ls_context_relevance(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
                    return evaluate_context_relevance(
                        question=inputs["question"],
                        contexts=outputs.get("contexts", []),
                    )

                def ls_answer_correctness(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
                    return evaluate_answer_correctness(
                        question=inputs["question"],
                        answer=outputs.get("answer", ""),
                        expected_answer=reference_outputs.get("expected_answer"),
                    )

                def ls_tool_routing(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
                    return evaluate_tool_routing(
                        tools_used=outputs.get("tools_used", []),
                        expected_tools=reference_outputs.get("expected_tools"),
                    )

                def ls_citation_compliance(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
                    return evaluate_citation_compliance(
                        answer=outputs.get("answer", ""),
                        contexts=outputs.get("contexts", []),
                    )

                ls_res = await aevaluate(
                    ls_target,
                    data=dataset_name,
                    evaluators=[
                        ls_faithfulness,
                        ls_context_relevance,
                        ls_answer_correctness,
                        ls_tool_routing,
                        ls_citation_compliance,
                    ],
                    experiment_prefix=experiment_prefix,
                    metadata={"user_id": user_id, "judge_model": "gemini-2.5-flash"},
                    max_concurrency=2,
                    client=client,
                )

                langsmith_experiment = getattr(ls_res, "experiment_name", None)
                if client and langsmith_experiment:
                    try:
                        proj = client.read_project(project_name=langsmith_experiment)
                        langsmith_url = getattr(proj, "url", None)
                    except Exception:
                        langsmith_url = None

                # Build structured UI breakdown from collected outputs + scores
                for idx, ex in enumerate(examples, start=1):
                    q = ex["question"]
                    out = collected_by_q.get(q)
                    if out is None:
                        out = await _run_adk_agent_once(user_id=user_id, question=q)
                    scored = evaluate_single_example(
                        question=q,
                        answer=out["answer"],
                        contexts=out["contexts"],
                        tools_used=out["tools_used"],
                        expected_answer=ex.get("expected_answer", ""),
                        expected_tools=ex.get("expected_tools", []),
                    )
                    case_results.append(
                        {
                            "id": ex.get("id") or f"case-{idx}",
                            "question": q,
                            "expected_answer": ex.get("expected_answer", ""),
                            "expected_sources": ex.get("expected_sources", []),
                            "expected_tools": ex.get("expected_tools", []),
                            "answer": out["answer"],
                            "tools_used": out["tools_used"],
                            "contexts_count": len(out["contexts"]),
                            "latency_ms": out["latency_ms"],
                            "metrics": scored["metrics"],
                            "overall_score": scored["overall_score"],
                        }
                    )
            except Exception as exc:
                logger.warning("LangSmith aevaluate failed, falling back to local mode: %s", exc)
                langsmith_warning = f"LangSmith upload failed ({str(exc)[:120]}); ran locally instead."
                case_results = await _run_local_cases(user_id=user_id, examples=examples)
        else:
            langsmith_warning = sync_info.get("error") or "Could not sync dataset to LangSmith; ran locally."
            case_results = await _run_local_cases(user_id=user_id, examples=examples)
    else:
        case_results = await _run_local_cases(user_id=user_id, examples=examples)

    run_record = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_name": dataset_name,
        "experiment_name": langsmith_experiment or f"{experiment_prefix}-{run_id}",
        "langsmith_synced": bool(langsmith_experiment),
        "langsmith_url": langsmith_url,
        "langsmith_warning": langsmith_warning,
        "judge_model": (config.GRAPH_EXTRACTION_MODEL or "").strip() or "gemini-2.5-flash",
        "summary": _compute_summary(case_results),
        "cases": case_results,
    }

    user_runs = _EVAL_RUNS.setdefault(user_id, [])
    user_runs.insert(0, run_record)
    del user_runs[20:]
    return run_record


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Run ADK Agentic RAG evaluation.")
    parser.add_argument("--user-id", required=True, help="User email / user_id to evaluate.")
    parser.add_argument("--num-questions", type=int, default=5, help="Synthetic dataset size.")
    parser.add_argument("--dataset-name", default="adk-rag-eval-dataset", help="LangSmith dataset name.")
    args = parser.parse_args()

    examples = generate_synthetic_dataset(user_id=args.user_id, num_questions=args.num_questions)
    result = asyncio.run(
        run_evaluation(
            user_id=args.user_id,
            examples=examples,
            dataset_name=args.dataset_name,
        )
    )
    print(f"Run ID: {result['run_id']} | Overall Score: {result['summary']['overall_score']}")
    print(f"Summary: {result['summary']}")
    if result.get("langsmith_url"):
        print(f"LangSmith Experiment: {result['langsmith_url']}")


if __name__ == "__main__":
    _cli()
