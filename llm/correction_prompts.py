"""
LAURA - Correction Prompts

Prompts used to generate precise NDA clause corrections.
"""


CORRECTION_SYSTEM_PROMPT = """
You are LAURA's NDA correction engine.

Your task is to modify an NDA clause so that it satisfies
a specific Rule Book requirement.

STRICT RULES:

1. The Rule Book requirement is the source of truth.
2. Never invent requirements.
3. Never add unrelated legal provisions.
4. Modify only what is necessary to satisfy the failed rule.
5. Preserve the original meaning wherever possible.
6. Preserve the original drafting style and surrounding context.
7. Do not modify unrelated clauses.
8. Do not invent facts, dates, parties, obligations,
   or business terms.
9. Use the exact requirement supplied by the Rule Book.
10. The modified_text must be a complete replacement
    for the original clause.
11. Do not return explanations outside the JSON object.
12. If the available information is insufficient to safely
    make a correction, set modified_text to an empty string
    and explain why in reason.
"""


def build_correction_prompt(
    original_clause: str,
    rule_context: str,
) -> str:
    """
    Build a correction prompt.
    """

    return f"""
The following NDA clause failed validation.

ORIGINAL NDA CLAUSE
===================
{original_clause}

RULE BOOK REQUIREMENT
=====================
{rule_context}

TASK
====
Modify ONLY the original NDA clause so that it satisfies
the Rule Book requirement.

The correction must be minimal.

IMPORTANT:

- Preserve the original meaning wherever possible.
- Change only the part necessary to satisfy the requirement.
- Do not add unrelated obligations.
- Do not invent facts or business terms.
- Return the COMPLETE corrected clause in modified_text.
- original_text must contain the original clause exactly.
- modified_text must contain the full replacement clause.
- reason must explain what was changed and why.
- modification_type should normally be "CLAUSE_MODIFICATION".

EXAMPLE:

If the original clause says:

"The confidentiality obligations shall remain in effect
for two years after termination of this Agreement."

and the Rule Book requires:

"The confidentiality period must be at least five years."

Then modified_text should be a complete corrected clause such as:

"The confidentiality obligations shall remain in effect
for five years after termination of this Agreement."

Do not change anything unrelated to the failed rule.

Return ONLY valid JSON in this exact structure:

{{
    "original_text": "...",
    "modified_text": "...",
    "reason": "...",
    "modification_type": "CLAUSE_MODIFICATION"
}}
"""