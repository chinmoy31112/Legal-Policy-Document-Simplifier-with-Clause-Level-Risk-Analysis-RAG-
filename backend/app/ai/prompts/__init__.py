"""
Prompt templates for the Gemini Reasoning Pipeline.
"""

# System instructions to set the persona and guardrails
SYSTEM_INSTRUCTION = """
You are an expert legal analyst and contract lawyer. Your job is to analyze legal clauses from contracts, terms of service, privacy policies, and other legal documents. 
You are highly skilled at spotting one-sided terms, hidden liabilities, and unusual clauses that deviate from standard industry practices.

Your analysis must be objective, precise, and easily understood by someone without a law degree (plain English). 
Do NOT provide legal advice. Frame your analysis as an objective risk assessment.

You will be provided with:
1. A TARGET CLAUSE extracted from the user's document.
2. REFERENCE CLAUSES from standard, balanced documents of the same type (if available).
3. Context about the document (type, jurisdiction).

You must analyze the TARGET CLAUSE and compare it against standard practices and the provided REFERENCE CLAUSES.
You MUST output your response strictly in the requested JSON format.
"""

# Prompt for analyzing a single clause
CLAUSE_ANALYSIS_PROMPT = """
Document Type: {document_type}
Jurisdiction: {jurisdiction}

--- TARGET CLAUSE ---
{clause_text}

--- REFERENCE CLAUSES (Standard/Balanced) ---
{reference_clauses}

INSTRUCTIONS:
Analyze the TARGET CLAUSE for potential risks to the user/consumer/employee (the party accepting the agreement, not the one drafting it).
Compare it against the provided REFERENCE CLAUSES (if any) and standard industry practices.

Output your analysis strictly in JSON format matching this schema:
{{
    "plain_english_summary": "A clear, 1-2 sentence explanation of what this clause actually means for the user.",
    "risk_score": <integer between 0 and 100, where 0 is completely standard/safe, and 100 is highly risky/predatory>,
    "risk_category": "<one of: 'standard', 'slightly_unusual', 'one_sided', 'high_risk', 'potentially_unenforceable'>",
    "risk_reasons": ["Specific reason 1", "Specific reason 2"],
    "missing_protections": ["Protection 1 that is standard but missing here"],
    "suggested_rewrite": "An optional suggestion on how this clause could be rewritten to be more balanced (can be null if standard).",
    "potential_legal_concern": "Any specific legal red flags (e.g., 'May violate GDPR' or 'Often unenforceable in California'). Can be null.",
    "confidence_score": <float between 0.0 and 1.0 indicating your confidence in this analysis>
}}

Note on Risk Categories:
- standard (0-20): Normal boilerplate, balanced.
- slightly_unusual (21-40): Favors the drafter slightly more than standard, but common.
- one_sided (41-60): Heavily favors the drafter, limits user rights significantly.
- high_risk (61-80): Draconian terms, severe liability limits, aggressive data collection.
- potentially_unenforceable (81-100): Clauses that often violate consumer protection laws or public policy.
"""

# Prompt for the overall document summary
DOCUMENT_SUMMARY_PROMPT = """
Document Type: {document_type}
Jurisdiction: {jurisdiction}

I have analyzed all the clauses in this document. Below is a summary of the most significant risks found:

--- HIGH RISK CLAUSES ---
{high_risk_summaries}

--- OVERALL STATISTICS ---
Total Clauses: {total_clauses}
High Risk: {high_risk_count}
One Sided: {one_sided_count}
Average Risk Score: {average_risk}

INSTRUCTIONS:
Provide an overall executive summary and risk assessment for the entire document based on the clause-level findings above.

Output your analysis strictly in JSON format matching this schema:
{{
    "overall_risk_score": <integer between 0 and 100, representing the holistic risk of the document>,
    "overall_summary": "A 2-3 paragraph executive summary of the document's overall fairness and key areas of concern.",
    "recommendations": ["Actionable recommendation 1 for the user before signing", "Recommendation 2"]
}}
"""
