# Reference Knowledge Base Corpus Plan

## 1. Overview & Objectives
To ensure the LLM never judges risk in a vacuum (Rule 1: "Retrieval before reasoning"), the application indexes a curated reference knowledge base of **150 to 300 benchmark clauses** spanning standard commercial contracts, technology agreements, consumer policies, and employment instruments.

Each reference clause serves as a factual anchor. During retrieval, high-similarity clauses are fetched and provided to Gemini to ground the risk classification, highlight one-sided language, and inform the balanced rewrite.

---

## 2. Approved Sources & Licensing Verification

All reference clauses are sourced exclusively from open, commercially usable, and legally vetted datasets:

| Source | Description | Dominant Document Types | License | License Compliance Verification |
| :--- | :--- | :--- | :--- | :--- |
| **CUAD (Contract Understanding Atticus Dataset)** | Curated by the Atticus Project; 500+ commercial contracts annotated by legal experts across 41 categories. | Master Service Agreements, NDAs, Software Licenses, Commercial Leases, Employment. | **CC BY 4.0** | Permitted for commercial use with attribution. Attribution recorded in `source` and `license` fields. |
| **ToS;DR (Terms of Service; Didn't Read)** | Community-driven repository analyzing consumer Terms of Service and Privacy Policies with standardized point ratings. | Consumer Terms of Service, Privacy Policies, End User License Agreements (EULAs). | **CC BY-SA 3.0 / CC0** | Open data; points and clause excerpts attributed to ToS;DR project. |
| **SEC EDGAR Public Filings & CommonAccord** | Public corporate agreements filed with the US Securities and Exchange Commission; open-source legal text templates. | B2B Commercial Contracts, SaaS Agreements, Vendor Agreements, Joint Ventures. | **Public Domain / CC0** | Government public filings / open commons legal boilerplate. Zero copyright restrictions. |

---

## 3. Target Distribution & Category Breakdown (200 Clauses Target)

The initial reference corpus targets **200 expertly curated clauses** distributed across 8 core legal categories and 5 document types:

```
Total Clauses: 200
├── Limitation of Liability & Disclaimers: 35 clauses (15 Standard, 20 High-Risk / One-Sided)
├── Indemnification & Defense: 30 clauses (15 Standard Mutual, 15 Unilateral / Extreme)
├── Intellectual Property & Work-for-Hire: 25 clauses (10 Standard, 15 Overreaching Assignments)
├── Termination & Post-Termination: 25 clauses (15 Standard Mutual, 10 Unilateral / Penalties)
├── Data Privacy, Retention & Tracking: 30 clauses (15 GDPR/CCPA Compliant, 15 Silent / Unrestricted Sharing)
├── Dispute Resolution, Arbitration & Class Action Waiver: 25 clauses (10 Standard Forum, 15 Mandatory Arbitration / Class Waivers)
├── Non-Compete, Non-Solicit & Restrictive Covenants: 15 clauses (5 Narrow/Reasonable, 10 Overbroad / Unreasonable)
└── Unilateral Amendment & Notice: 15 clauses (5 Reasonable Notice, 10 Silent Modification without Notice)
```

---

## 4. Reference Clause Schema

Every reference clause record conforms to the following strict Pydantic / SQLAlchemy schema:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ReferenceClause",
  "type": "object",
  "required": [
    "id",
    "title",
    "text",
    "document_type",
    "jurisdiction",
    "category",
    "version",
    "language",
    "source",
    "license",
    "why_standard_or_risky"
  ],
  "properties": {
    "id": {
      "type": "string",
      "description": "Unique identifier, slugified with category and sequence.",
      "examples": ["REF-LIAB-001", "REF-PRIV-014"]
    },
    "title": {
      "type": "string",
      "description": "Concise human-readable name of the clause."
    },
    "text": {
      "type": "string",
      "description": "Verbatim benchmark legal clause text."
    },
    "document_type": {
      "type": "string",
      "enum": [
        "Terms and Conditions",
        "Privacy Policy",
        "Employment Contract",
        "Non-Disclosure Agreement",
        "Master Services Agreement",
        "Commercial Lease",
        "Software License / EULA"
      ]
    },
    "jurisdiction": {
      "type": "string",
      "description": "Legal jurisdiction or governing standard.",
      "default": "General / US Common Law"
    },
    "category": {
      "type": "string",
      "enum": [
        "Limitation of Liability",
        "Indemnification",
        "Intellectual Property",
        "Termination",
        "Data Privacy & Retention",
        "Dispute Resolution & Arbitration",
        "Restrictive Covenants",
        "Unilateral Amendment",
        "Confidentiality",
        "Payment & Fees"
      ]
    },
    "version": {
      "type": "string",
      "default": "1.0.0"
    },
    "language": {
      "type": "string",
      "default": "en"
    },
    "source": {
      "type": "string",
      "description": "Provenance dataset or public filing citation."
    },
    "license": {
      "type": "string",
      "description": "Exact copyright license applying to the benchmark text."
    },
    "why_standard_or_risky": {
      "type": "string",
      "description": "Expert legal rationale detailing why this language represents a safe market baseline or creates dangerous, one-sided liabilities for the executing party."
    }
  }
}
```

### Example Curated Reference Record
```json
{
  "id": "REF-LIAB-001",
  "title": "Mutual Direct Damages Cap with Consequential Waiver",
  "text": "IN NO EVENT SHALL EITHER PARTY BE LIABLE TO THE OTHER FOR ANY INDIRECT, INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOSS OF PROFITS, ARISING OUT OF OR IN CONNECTION WITH THIS AGREEMENT. EACH PARTY'S TOTAL AGGREGATE LIABILITY UNDER THIS AGREEMENT SHALL BE LIMITED TO THE TOTAL FEES PAID OR PAYABLE BY CUSTOMER IN THE TWELVE (12) MONTHS PRECEDING THE CLAIM.",
  "document_type": "Master Services Agreement",
  "jurisdiction": "General / US Common Law",
  "category": "Limitation of Liability",
  "version": "1.0.0",
  "language": "en",
  "source": "CUAD / SEC EDGAR Filings",
  "license": "CC BY 4.0",
  "why_standard_or_risky": "Standard commercial baseline: ensures mutual protection by disclaiming indirect/consequential damages and capping aggregate direct liabilities to 12 months trailing fees, preventing catastrophic uncapped exposure for either party."
}
```

---

## 5. Ingestion & Quality Control Protocol
1. **Deduplication:** Hashed via SHA-256 to ensure no identical clauses exist in the reference corpus.
2. **Embedding Generation:** Embedded using Google GenAI `gemini-embedding-2` with dimension registered directly alongside vector records.
3. **Idempotence:** CLI ingestion script (`python -m cli.ingest_kb`) updates existing clauses if text is unchanged, or re-embeds only modified items.
