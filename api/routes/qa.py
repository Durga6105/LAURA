"""
LAURA - Q&A API

Context-aware follow-up assistant for the completed
NDA analysis.

Users can ask questions about:

- Uploaded NDA
- NDA clauses
- Rule Book validation
- Passed / failed rules
- Risk
- Corrections
- Original validation
- Final validation
- Analysis process
- Generated report
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.routes.analysis import _ANALYSIS_RESULTS
from llm.gemini_client import GeminiClient


router = APIRouter()


# =========================================================
# Request Model
# =========================================================


class QARequest(BaseModel):
    """Follow-up question request."""

    analysis_id: str = Field(
        min_length=1,
    )

    question: str = Field(
        min_length=1,
    )


# =========================================================
# System Prompt
# =========================================================


QA_SYSTEM_PROMPT = """
You are LAURA, an AI assistant for NDA analysis.

You answer questions about the completed LAURA analysis
using ONLY the analysis context provided to you.

The context may contain:

- The uploaded NDA
- Original NDA clauses
- Corrected NDA clauses
- Rule Book validation results
- Original validation summary
- Final validation summary
- Risk information
- Corrections made
- Analysis workflow
- Report information

STRICT RULES:

1. Never invent information about the NDA.
2. Never invent a Rule Book rule.
3. Never invent a correction.
4. Never invent validation results.
5. Use only the supplied analysis context.
6. If information is not available in the context,
   clearly say that it is not available.
7. Do not provide external legal advice.
8. Do not introduce external legal requirements.
9. Answer naturally and clearly.
10. If asked about corrections, use the actual correction
    records.
11. If asked about validation, use the actual validation
    results.
12. If asked about the original NDA, use the original
    clause information.
13. If asked about the corrected NDA, use the corrected
    clause information.
14. If asked about the LAURA process, explain the workflow
    recorded in the context.
15. If the user asks a general question about the uploaded
    NDA, answer from the available NDA context.
16. Do not claim that you performed an action that is not
    present in the supplied context.
17. Do not determine new legal requirements.
18. Do not make assumptions about missing NDA content.

Your goal is to be a useful assistant for the completed
LAURA analysis.
"""


# =========================================================
# Context Builder
# =========================================================


def _build_analysis_context(
    analysis: dict[str, Any],
) -> str:
    """
    Convert the completed analysis into structured text
    for Gemini.

    The context is deliberately built from the actual
    analysis registry so LAURA answers questions about the
    current uploaded NDA rather than acting as a generic
    chatbot.
    """

    context = {
        "document": {
            "file_name": analysis.get(
                "file_name"
            ),
            "original_clauses": analysis.get(
                "original_clauses",
                [],
            ),
            "corrected_clauses": analysis.get(
                "corrected_clauses",
                [],
            ),
        },

        "validation": {
            "original_summary": analysis.get(
                "original_summary",
                {},
            ),
            "final_summary": analysis.get(
                "final_summary",
                {},
            ),
            "validation_results": analysis.get(
                "validation_results",
                [],
            ),
        },

        "corrections": analysis.get(
            "corrections",
            [],
        ),

        "process": analysis.get(
            "process",
            [],
        ),

        "report": {
            "file_name": analysis.get(
                "report_name"
            ),
        },
    }

    return json.dumps(
        context,
        indent=2,
        default=str,
    )


# =========================================================
# Ask LAURA
# =========================================================


@router.post("/ask")
async def ask_question(
    request: QARequest,
):
    """
    Ask an arbitrary follow-up question about the current
    completed NDA analysis.

    Questions may concern the NDA, clauses, Rule Book
    validation, risks, corrections, original/final results,
    analysis process, or report information.
    """

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    # =====================================================
    # Find analysis context
    # =====================================================

    analysis = _ANALYSIS_RESULTS.get(
        request.analysis_id
    )

    if analysis is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Analysis context not found. "
                "Please analyze the NDA again."
            ),
        )

    # =====================================================
    # Build context
    # =====================================================

    analysis_context = _build_analysis_context(
        analysis
    )

    # =====================================================
    # Build Gemini prompt
    # =====================================================

    prompt = f"""
The following is the completed LAURA analysis context
for the user's uploaded NDA.

================ ANALYSIS CONTEXT ================

{analysis_context}

================ END ANALYSIS CONTEXT ==============

USER QUESTION:

{question}

Answer the user's question using ONLY the analysis
context above.

The user may ask ANY question related to:

- the uploaded NDA
- any NDA clause
- the original document
- the corrected document
- Rule Book requirements represented in the validation
  results
- passed rules
- failed rules
- risk
- corrections
- why a correction was made
- original validation
- final validation
- differences between original and corrected content
- the analysis workflow
- the generated report
- what LAURA did during the analysis

Use the most relevant part of the supplied context.

If the question asks for a comparison, compare the
available original and corrected clause information.

If the question asks why a rule failed, use the actual
validation result's reason, evidence, required change,
rule ID, risk, and status when available.

If the question asks what changed, use the actual
correction records and corrected clause information.

If the question asks about the final result, use the
final validation summary.

If the question asks about the original result, use the
original validation summary.

If the question asks about the process, use the recorded
workflow.

If the question asks for information that is not present
in the context, say clearly that the information is not
available in the completed analysis context.

Give a direct, useful answer. Do not invent missing
information and do not provide external legal advice.
"""

    # =====================================================
    # Gemini
    # =====================================================

    try:

        gemini = GeminiClient()

        answer = gemini.generate_text(
            prompt=prompt,
            system_instruction=QA_SYSTEM_PROMPT,
        )

    except RuntimeError as exc:

        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Q&A failed: {exc}",
        ) from exc

    # =====================================================
    # Response
    # =====================================================

    return {
        "status": "success",
        "analysis_id": request.analysis_id,
        "question": question,
        "answer": answer,
    }