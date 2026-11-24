"""
Generate Retrieval Evaluation Dataset with aligned categories.

Produces tests/eval_data/retrieval_set/retrieval_truth.json:
- 35 In-Domain query clauses mapped to acceptable reference IDs in reference_clauses.json.
- 15 Out-of-Domain queries that must return no_reference_found (100% rejection rate).
"""

import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
KB_FILE = ROOT_DIR / "backend" / "knowledge_base" / "reference_clauses.json"
OUT_DIR = ROOT_DIR / "tests" / "eval_data" / "retrieval_set"
OUT_FILE = OUT_DIR / "retrieval_truth.json"

OUT_DIR.mkdir(parents=True, exist_ok=True)

# 35 In-Domain queries covering the exact 8 categories of reference_clauses.json
IN_DOMAIN_QUERIES = [
    # Limitation of Liability (5 queries)
    (
        "In no event shall either party's aggregate liability under this agreement exceed the total fees paid by customer in the preceding 12 months, excluding claims for willful misconduct.",
        "Limitation of Liability",
    ),
    (
        "Vendor's liability under this contract is strictly capped at one hundred dollars ($100), whereas customer shall remain liable for all damages without limit.",
        "Limitation of Liability",
    ),
    (
        "Neither company nor contractor shall be liable for any lost profits, lost revenue, lost savings, or indirect or punitive damages arising out of this agreement.",
        "Limitation of Liability",
    ),
    (
        "The sole and exclusive remedy for customer regarding system downtime or service disruption shall be service credits not exceeding 5% of monthly fees.",
        "Limitation of Liability",
    ),
    (
        "Notwithstanding anything to the contrary, company's total aggregate liability for breach of data covenants shall be capped at fees paid in the past twelve months.",
        "Limitation of Liability",
    ),

    # Indemnification (5 queries)
    (
        "Each party agrees to defend, indemnify, and hold harmless the other party against any third-party claims asserting copyright or patent infringement by deliverables.",
        "Indemnification",
    ),
    (
        "Customer shall indemnify, defend and hold harmless vendor and its affiliates from all claims, damages, liabilities, costs, and attorney fees arising from customer breach.",
        "Indemnification",
    ),
    (
        "The indemnifying party's obligations are conditioned on receiving prompt written notice of the claim and full authority to settle or defend the dispute.",
        "Indemnification",
    ),
    (
        "Supplier indemnifies buyer against all third-party product liability, patent infringement, or regulatory fines resulting from defective hardware components.",
        "Indemnification",
    ),
    (
        "Vendor agrees to indemnify and defend customer against all third-party losses resulting from vendor's gross negligence, intentional fraud, or willful wrongdoing.",
        "Indemnification",
    ),

    # Intellectual Property (5 queries)
    (
        "All inventions, software code, patents, and work products developed under this statement of work are considered works made for hire and owned exclusively by client.",
        "Intellectual Property",
    ),
    (
        "Employee assigns to company all intellectual property, inventions, and ideas developed during employment, whether during business hours or personal time.",
        "Intellectual Property",
    ),
    (
        "Customer retains all title and ownership in customer data uploaded to the cloud service. Vendor receives only a limited license to process data.",
        "Intellectual Property",
    ),
    (
        "Licensor grants licensee a non-exclusive, non-transferable, revocable license to execute the software solely for internal business operations.",
        "Intellectual Property",
    ),
    (
        "Each party shall retain all right, title, and interest in its pre-existing background intellectual property, patents, and confidential proprietary methodologies.",
        "Intellectual Property",
    ),

    # Termination (4 queries)
    (
        "Either party may terminate this agreement for convenience upon providing at least thirty (30) days prior written notice to the other party.",
        "Termination",
    ),
    (
        "Either party may terminate immediately if the other party commits a material breach and fails to cure such breach within thirty days of written notice.",
        "Termination",
    ),
    (
        "Vendor reserves the right to terminate customer account immediately without notice, without cause, and without refund of prepaid fees.",
        "Termination",
    ),
    (
        "Upon termination, vendor shall deliver a complete export of customer data within 30 days and certify destruction of all residual copies.",
        "Termination",
    ),

    # Restrictive Covenants (Confidentiality & Non-Compete) (4 queries)
    (
        "Recipient shall protect disclosing party's confidential information using the same degree of care it uses for its own confidential information, but not less than reasonable care.",
        "Restrictive Covenants",
    ),
    (
        "Confidential proprietary information does not include information that is publicly known through no breach of recipient, or already in recipient's lawful possession.",
        "Restrictive Covenants",
    ),
    (
        "Recipient may disclose confidential information pursuant to a valid subpoena or court order, provided prompt written notice is given to discloser.",
        "Restrictive Covenants",
    ),
    (
        "Employee covenants not to compete or solicit company clients for a period of one year following termination of employment.",
        "Restrictive Covenants",
    ),

    # Dispute Resolution & Arbitration (4 queries)
    (
        "All disputes arising out of this agreement shall be settled through binding arbitration administered by the American Arbitration Association in New York.",
        "Dispute Resolution & Arbitration",
    ),
    (
        "Customer agrees that all disputes shall be resolved on an individual basis and waives any right to bring or participate in any class action lawsuit.",
        "Dispute Resolution & Arbitration",
    ),
    (
        "Prior to commencing formal legal action, senior executives of both parties shall meet in good faith negotiations for thirty (30) days.",
        "Dispute Resolution & Arbitration",
    ),
    (
        "This agreement shall be governed by and construed in accordance with the laws of the State of Delaware, without regard to conflict of law principles.",
        "Dispute Resolution & Arbitration",
    ),

    # Data Privacy & Retention (4 queries)
    (
        "Processor shall implement appropriate technical and organizational measures conforming with GDPR Article 28 to protect personal data against unauthorized processing.",
        "Data Privacy & Retention",
    ),
    (
        "Service provider reserves the unrestricted right to sell, monetize, and transfer user browsing behavior and personal data to third-party advertising partners.",
        "Data Privacy & Retention",
    ),
    (
        "Processor shall notify controller of any confirmed security incident or personal data breach without undue delay and within forty-eight (48) hours.",
        "Data Privacy & Retention",
    ),
    (
        "Company retains user telemetry, device fingerprints, and location data perpetually, even after user account deletion or service cancellation.",
        "Data Privacy & Retention",
    ),

    # Unilateral Amendment (4 queries)
    (
        "Company reserves the right to modify, amend, or revise these terms and conditions at any time in its sole discretion by posting updated terms on the website.",
        "Unilateral Amendment",
    ),
    (
        "Customer's continued use of the service following the posting of amended terms constitutes binding acceptance of all modifications.",
        "Unilateral Amendment",
    ),
    (
        "Provider may unilaterally change service pricing, features, and subscription specifications upon thirty (30) days advance notice to customer.",
        "Unilateral Amendment",
    ),
    (
        "No amendment or modification to this agreement shall be binding unless executed in writing by authorized representatives of both parties.",
        "Unilateral Amendment",
    ),
]

OUT_OF_DOMAIN_QUERIES = [
    "To bake a classic sourdough loaf, combine 500 grams of bread flour with 350 grams of warm water and 100 grams of active starter, folding every 30 minutes.",
    "The home team rallied in the ninth inning with a bases-loaded double into deep right field, scoring three runs to secure the championship victory.",
    "A strong low-pressure cold front will sweep across the midwestern plains on Thursday, bringing wind gusts up to 55 miles per hour and freezing precipitation.",
    "def quicksort(arr): return arr if len(arr) <= 1 else quicksort([x for x in arr[1:] if x < arr[0]]) + [arr[0]] + quicksort([x for x in arr[1:] if x >= arr[0]])",
    "Two roads diverged in a yellow wood, and sorry I could not travel both and be one traveler, long I stood and looked down one as far as I could.",
    "Photosynthesis occurs within the chloroplasts of plant cells, converting sunlight, water, and carbon dioxide into glucose and oxygen through light reactions.",
    "The spaceship entered the atmosphere of Kepler-452b, thrusters firing to decelerate through the turbulent nitrogen-rich troposphere.",
    "Heat two tablespoons of extra virgin olive oil in a stainless steel skillet over medium heat, add minced garlic and saute until golden brown and fragrant.",
    "The concert began with an energetic acoustic guitar solo followed by heavy percussion and synchronized brass instruments in 4/4 meter.",
    "Initialize the convolutional neural network with He normal weights, applying batch normalization and dropout after each residual layer to prevent overfitting.",
    "The golden retriever puppy bounded across the grassy meadow chasing colorful autumn leaves caught in the brisk afternoon breeze.",
    "Install the latest graphics driver from the official manufacturer website, then restart your workstation and verify hardware acceleration in settings.",
    "Pour freshly ground Arabica coffee into the French press, pour boiling water at 94 degrees Celsius, stir gently, and let steep for exactly four minutes.",
    "Jupiter is the largest planet in our solar system, with an orbital radius of approximately 5.2 astronomical units and a prominent Great Red Spot.",
    "The museum exhibit showcases ancient Roman pottery and bronze currency uncovered during archaeological excavations in southern Italy.",
]


def generate_fixtures():
    ref_data = json.loads(KB_FILE.read_text(encoding="utf-8"))
    category_to_ids: dict[str, list[str]] = {}
    for item in ref_data:
        cat = item["category"]
        category_to_ids.setdefault(cat, []).append(item["id"])

    eval_items = []

    for idx, (text, cat) in enumerate(IN_DOMAIN_QUERIES, start=1):
        matching_ids = category_to_ids.get(cat, [])
        eval_items.append({
            "query_id": f"QUERY-IN-{idx:03d}",
            "query_text": text,
            "expected_category": cat,
            "acceptable_reference_ids": matching_ids,
            "is_out_of_domain": False,
        })

    for idx, text in enumerate(OUT_OF_DOMAIN_QUERIES, start=1):
        eval_items.append({
            "query_id": f"QUERY-OOD-{idx:03d}",
            "query_text": text,
            "expected_category": None,
            "acceptable_reference_ids": [],
            "is_out_of_domain": True,
        })

    OUT_FILE.write_text(json.dumps(eval_items, indent=2), encoding="utf-8")
    print(f"Generated {len(eval_items)} retrieval evaluation samples ({len(IN_DOMAIN_QUERIES)} in-domain, {len(OUT_OF_DOMAIN_QUERIES)} out-of-domain) to {OUT_FILE}")


if __name__ == "__main__":
    generate_fixtures()
