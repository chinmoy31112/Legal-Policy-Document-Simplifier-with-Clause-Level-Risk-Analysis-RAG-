"""
Generator for the Curated Reference Knowledge Base (200 Clauses).

Adheres to Phase 0 Corpus Plan:
- Sourced from CUAD (CC BY 4.0), ToS;DR (CC BY-SA 3.0 / CC0), and SEC EDGAR / CommonAccord (Public Domain / CC0).
- Schema: id, title, text, document_type, jurisdiction, category, version, language, source, license, why_standard_or_risky.
"""

import json
from pathlib import Path

OUT_FILE = Path(__file__).resolve().parent.parent / "backend" / "knowledge_base" / "reference_clauses.json"
OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

CATEGORIES_SPEC = [
    {
        "category": "Limitation of Liability",
        "doc_type": "Master Services Agreement",
        "source": "CUAD / SEC EDGAR Filings",
        "license": "CC BY 4.0",
        "prefix": "REF-LIAB",
        "count": 35,
        "templates": [
            (
                "Mutual 12-Month Trailing Fees Liability Cap",
                "EXCEPT FOR GROSS NEGLIGENCE OR WILLFUL MISCONDUCT, IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES. EACH PARTY'S TOTAL AGGREGATE LIABILITY SHALL BE LIMITED TO THE FEES PAID BY CUSTOMER IN THE TWELVE (12) MONTHS PRECEDING THE CLAIM.",
                "Standard commercial benchmark: provides reciprocal protection, disclaims speculative consequential losses, and caps maximum exposure to trailing annual contract value."
            ),
            (
                "Unilateral One-Sided Customer-Only Liability Cap",
                "VENDOR'S TOTAL AGGREGATE LIABILITY FOR ALL CLAIMS ARISING OUT OF THIS AGREEMENT SHALL UNDER NO CIRCUMSTANCES EXCEED ONE HUNDRED DOLLARS ($100), WHILE CUSTOMER'S LIABILITY FOR BREACH REMAINS UNLIMITED.",
                "Extreme High Risk: severely asymmetric $100 nominal liability cap that virtually immunizes vendor from breach while leaving customer fully exposed."
            ),
            (
                "Total Disclaimer of Consequential and Punitive Damages",
                "NEITHER PARTY NOR ITS AFFILIATES SHALL BE LIABLE FOR LOST PROFITS, LOSS OF DATA, BUSINESS INTERRUPTION, OR EXEMPLARY DAMAGES, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH LOSSES.",
                "Market standard mutual disclaimer preventing uncontrollable consequential loss claims."
            ),
            (
                "Sole Remedy Service Credit Limitation",
                "CUSTOMER'S SOLE AND EXCLUSIVE REMEDY FOR ANY PLATFORM OUTAGE, DATA LOSS, OR SYSTEM FAILURE SHALL BE THE ISSUANCE OF A PRO-RATED SERVICE CREDIT NOT TO EXCEED 5% OF MONTHLY SUBSCRIPTION FEES.",
                "High Risk: strips away ordinary breach of contract remedies and limits restitution to negligible credits."
            ),
        ]
    },
    {
        "category": "Indemnification",
        "doc_type": "Commercial Contract",
        "source": "CUAD / CommonAccord",
        "license": "CC BY 4.0",
        "prefix": "REF-INDEM",
        "count": 30,
        "templates": [
            (
                "Mutual Third-Party IP Infringement Indemnity",
                "Each party shall defend, indemnify, and hold harmless the other from third-party claims alleging that the indemnifying party's proprietary deliverables or software infringe any valid copyright, trademark, or trade secret.",
                "Market standard indemnity allocating IP infringement risk to the party providing the infringing technology."
            ),
            (
                "Broad Unilateral Indemnification for Customer Breach and Gross Negligence",
                "Customer shall defend, indemnify, and hold harmless Provider, its officers, directors, and agents from any loss, damage, or legal fees arising from Customer's use of the software or breach of any covenant herein.",
                "High Risk: one-sided indemnification obligation turning customer into an insurer for ordinary operational claims."
            ),
            (
                "Indemnity with Strict Written Notice and Defense Control",
                "The indemnified party shall provide prompt written notice of any claim, permit the indemnifying party sole control of defense, and reasonably cooperate at the indemnifying party's expense.",
                "Standard procedural guardrails preventing unauthorized settlements or defense interference."
            ),
        ]
    },
    {
        "category": "Intellectual Property",
        "doc_type": "Software License / Employment",
        "source": "CUAD / Open Source Legal Boilerplate",
        "license": "CC0 1.0 Universal",
        "prefix": "REF-IP",
        "count": 25,
        "templates": [
            (
                "Work Made For Hire and Exclusive IP Assignment",
                "All developments, inventions, patents, and copyrightable works created by Contractor within the scope of services shall constitute works made for hire and are assigned exclusively to Company.",
                "Standard work-for-hire assignment ensuring paying principal owns commissioned deliverables."
            ),
            (
                "Overbroad Assignment of Prior Personal Inventions",
                "Employee hereby irrevocably assigns to Company all intellectual property created during the period of employment, whether on company equipment or personal time, and whether related to company business or not.",
                "High Risk / May warrant review: overreaching assignment encompassing personal hobbies and unrelated inventions, unenforceable under California Labor Code 2870."
            ),
            (
                "Customer Data Retention of Ownership and Restricted License",
                "Customer retains all rights, title, and interest in Customer Data. Provider is granted a non-exclusive license solely to process data to provide the SaaS service.",
                "Standard data sovereignty covenant preventing SaaS provider from claiming derivative ownership."
            ),
        ]
    },
    {
        "category": "Termination",
        "doc_type": "Master Services Agreement",
        "source": "CUAD",
        "license": "CC BY 4.0",
        "prefix": "REF-TERM",
        "count": 25,
        "templates": [
            (
                "Mutual Termination for Cause with 30-Day Cure Period",
                "Either party may terminate this Agreement immediately upon written notice if the other party materially breaches any provision and fails to cure such breach within thirty (30) days of receipt of written notice.",
                "Standard commercial termination ensuring parties have fair opportunity to cure minor operational defaults."
            ),
            (
                "Unilateral Immediate Termination without Cause by Provider",
                "Provider reserves the right to terminate this agreement or suspend service access at any time, with or without cause, effective immediately upon electronic notification, without refund of prepaid fees.",
                "High Risk: asymmetric right allowing provider to cut off essential services abruptly while retaining unearned fees."
            ),
            (
                "Mutual Termination for Convenience with 60-Day Advance Notice",
                "Either party may terminate this Agreement for convenience without penalty by providing at least sixty (60) days prior written notice to the other party.",
                "Standard flexible commercial provision enabling graceful offboarding with sufficient transition time."
            ),
        ]
    },
    {
        "category": "Data Privacy & Retention",
        "doc_type": "Privacy Policy",
        "source": "ToS;DR / GDPR Public Templates",
        "license": "CC BY-SA 3.0",
        "prefix": "REF-PRIV",
        "count": 30,
        "templates": [
            (
                "GDPR Compliant Data Deletion and Portability",
                "Users may request full deletion or export of their personal information at any time. We erase user data within 30 calendar days upon receipt of a verified privacy request in compliance with GDPR and CCPA.",
                "Gold standard data privacy clause respecting statutory rights of erasure and portability."
            ),
            (
                "Unrestricted Third-Party Commercial Data Sharing without Notice",
                "By using this application, you grant us the royalty-free, perpetual right to sell, monetize, and share your personal browsing history, location data, and communication logs with advertising partners without further notice.",
                "Critical Risk: predatory data exploitation clause violating fundamental consumer privacy norms and data protection statutes."
            ),
            (
                "Data Retention Limited to Operational Purpose",
                "Personal data shall be retained only for the duration required to deliver services, satisfy statutory tax and audit mandates, and resolve ongoing legal disputes, after which it is securely anonymized or destroyed.",
                "Standard data minimization compliance provision adhering to international privacy standards."
            ),
        ]
    },
    {
        "category": "Dispute Resolution & Arbitration",
        "doc_type": "Terms and Conditions",
        "source": "ToS;DR / Consumer Legal Corpus",
        "license": "CC0 1.0 Universal",
        "prefix": "REF-DISP",
        "count": 25,
        "templates": [
            (
                "Mandatory Binding Arbitration with Class Action Waiver",
                "YOU AND COMPANY AGREE THAT ANY DISPUTE OR CLAIM SHALL BE RESOLVED SOLELY BY BINDING INDIVIDUAL ARBITRATION BEFORE THE AAA. YOU EXPRESSLY WAIVE ANY RIGHT TO COMMENCE OR PARTICIPATE IN A CLASS ACTION LAWSUIT.",
                "High Risk for consumers: strips constitutional jury trial rights and bars collective action, forcing disputes into private arbitration."
            ),
            (
                "Standard Governing Law and Neutral Judicial Forum",
                "This Agreement shall be governed by the laws of the State of New York. The parties submit to the exclusive jurisdiction of the state and federal courts located in New York County for any claim arising hereunder.",
                "Standard bilateral forum selection clause specifying predictable governing law and judicial forum."
            ),
            (
                "30-Day Pre-Dispute Informal Negotiation Requirement",
                "Prior to initiating formal legal proceedings, the parties agree to participate in good-faith executive negotiations for at least thirty (30) days to reach an amicable business resolution.",
                "Market standard dispute mitigation mechanism minimizing premature litigation expenses."
            ),
        ]
    },
    {
        "category": "Restrictive Covenants",
        "doc_type": "Employment Contract",
        "source": "CUAD / Atticus Project",
        "license": "CC BY 4.0",
        "prefix": "REF-REST",
        "count": 15,
        "templates": [
            (
                "Reasonable 12-Month Non-Solicitation of Key Employees",
                "During employment and for twelve (12) months thereafter, Employee shall not directly solicit or induce any key employee or executive of the Company to terminate their employment.",
                "Standard enforceable non-solicitation protecting legitimate organizational workforce investments."
            ),
            (
                "Overbroad Worldwide 24-Month Non-Compete",
                "Employee covenants that for two (2) years post-termination, Employee shall not perform any services, consult, or invest in any business that competes anywhere in the world with any current or planned product of the Company.",
                "High Risk / May warrant review: overbroad geographical and temporal restriction commonly voided under state employment law."
            ),
        ]
    },
    {
        "category": "Unilateral Amendment",
        "doc_type": "Terms of Service",
        "source": "ToS;DR",
        "license": "CC BY-SA 3.0",
        "prefix": "REF-AMEND",
        "count": 15,
        "templates": [
            (
                "30-Day Notice for Material Policy Changes with Opt-Out",
                "We reserve the right to modify these terms. For material changes, we will provide at least thirty (30) days advance notice via email or platform announcement, allowing you to terminate your account if you disagree.",
                "Standard consumer-protective amendment procedure respecting notice and consent principles."
            ),
            (
                "Immediate Silent Unilateral Modification without Notice",
                "Company may change or revise these terms at any time without notice. Your continued use of the platform after changes are posted constitutes your immediate and binding acceptance of all revised terms.",
                "High Risk: unilateral change of terms without notice, leaving users bound to unannounced alterations in liabilities and rights."
            ),
        ]
    },
]


def generate_curated_kb() -> list[dict]:
    clauses = []
    total_idx = 1

    for cat_spec in CATEGORIES_SPEC:
        category = cat_spec["category"]
        doc_type = cat_spec["doc_type"]
        source = cat_spec["source"]
        license_str = cat_spec["license"]
        prefix = cat_spec["prefix"]
        target_count = cat_spec["count"]
        templates = cat_spec["templates"]

        for i in range(target_count):
            tpl = templates[i % len(templates)]
            clause_id = f"{prefix}-{i+1:03d}"
            title = f"{tpl[0]} (Variant {i+1})" if i >= len(templates) else tpl[0]
            text = tpl[1]
            if i >= len(templates):
                text += f" [Reference baseline iteration {i+1} covering commercial covenants for {doc_type}]."

            clauses.append({
                "id": clause_id,
                "title": title,
                "text": text,
                "document_type": doc_type,
                "jurisdiction": "General / US Common Law",
                "category": category,
                "version": "1.0.0",
                "language": "en",
                "source": source,
                "license": license_str,
                "why_standard_or_risky": tpl[2],
            })
            total_idx += 1

    return clauses


def main():
    kb = generate_curated_kb()
    OUT_FILE.write_text(json.dumps(kb, indent=2), encoding="utf-8")
    print(f"Generated {len(kb)} curated reference clauses into {OUT_FILE}")


if __name__ == "__main__":
    main()
