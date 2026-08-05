# Knowledge Base Reference Data

This directory contains pre-built reference clause data for the knowledge base.

## Structure

Each JSON file contains standard/fair clauses for a specific document type:

- `privacy_policy.json` — Standard privacy policy clauses
- `terms_of_service.json` — Standard terms of service clauses  
- `employment_contract.json` — Standard employment contract clauses
- `rental_agreement.json` — Standard rental agreement clauses
- `loan_agreement.json` — Standard loan agreement clauses
- `eula.json` — Standard end-user license agreement clauses

## Format

Each JSON file follows this structure:

```json
{
  "document_type": "privacy_policy",
  "title": "Standard Privacy Policy Clauses",
  "jurisdiction": "general",
  "version": "1.0",
  "clauses": [
    {
      "clause_number": "1",
      "title": "Data Collection",
      "content": "We collect personal information...",
      "category": "data_collection"
    }
  ]
}
```

## Ingestion

Use the CLI command to ingest these into the knowledge base:

```bash
python -m cli.kb_ingest --source ./knowledge_base/standard_clauses/ --type privacy_policy
```
