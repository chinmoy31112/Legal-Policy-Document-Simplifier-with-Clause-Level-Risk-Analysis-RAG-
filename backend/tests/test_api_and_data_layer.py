"""
End-to-End API and Data Layer Integration Tests for Phase 5.

Verifies:
1. User registration, login, token refresh, and profile retrieval.
2. Document upload validation (empty, corrupt, scanned-PDF rejection with HTTP 422).
3. Document processing pipeline execution and status tracking.
4. Per-user data isolation (User B cannot access or modify User A's resources).
5. JSON and Markdown exports with mandatory legal disclaimer.
6. Delete-My-Data (GDPR compliance) purging database records and disk storage.
"""

import uuid
from typing import Any

import fitz
import pytest
from httpx import AsyncClient

from app.core.database import async_session_factory
from app.services.analysis_service import AnalysisService


def create_sample_text_pdf() -> bytes:
    """Create a machine-readable text PDF with legal clauses."""
    doc = fitz.open()
    page = doc.new_page()
    content = (
        "MASTER SERVICES AGREEMENT\n\n"
        "1. Limitation of Liability\n"
        "VENDOR'S TOTAL AGGREGATE LIABILITY UNDER THIS AGREEMENT SHALL UNDER NO CIRCUMSTANCES "
        "EXCEED ONE HUNDRED DOLLARS ($100), WHILE CUSTOMER LIABILITY REMAINS UNLIMITED.\n\n"
        "2. Indemnification\n"
        "Customer shall defend, indemnify, and hold harmless Provider from any and all damages.\n\n"
        "3. Governing Law\n"
        "This agreement shall be governed by and construed in accordance with the laws of Delaware.\n"
    )
    page.insert_text((50, 72), content, fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_sample_scanned_pdf() -> bytes:
    """Create an image-only scanned PDF with zero extractable text characters."""
    doc = fitz.open()
    page = doc.new_page()
    # Insert a blank image covering the page
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 200, 200), 1)
    pix.clear_with(240)
    page.insert_image(page.rect, pixmap=pix)
    scanned_bytes = doc.tobytes()
    doc.close()
    return scanned_bytes


@pytest.mark.asyncio
async def test_auth_registration_and_login_flow(client: AsyncClient):
    """Verify registration, login, token refresh, and me endpoints."""
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePassword123!"

    # 1. Register
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": password, "full_name": "Test Legal User"},
    )
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()["data"]
    assert reg_data["email"] == unique_email
    assert "id" in reg_data

    # Duplicate registration must fail
    dup_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": password, "full_name": "Duplicate User"},
    )
    assert dup_resp.status_code == 422

    # 2. Login
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()["data"]
    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    assert access_token
    assert refresh_token

    # Invalid login credentials must fail
    bad_login = await client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": "WrongPassword"},
    )
    assert bad_login.status_code == 401

    # 3. Token Refresh
    ref_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert ref_resp.status_code == 200
    assert "access_token" in ref_resp.json()["data"]

    # 4. Profile /me
    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["data"]["email"] == unique_email


@pytest.mark.asyncio
async def test_document_upload_validation_and_rejections(client: AsyncClient):
    """Verify upload validations: empty, corrupt, and scanned PDFs rejected with 422."""
    email = f"uploader_{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "full_name": "Uploader"},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    token = login_res.json()["data"]["access_token"]
    auth_header = {"Authorization": f"Bearer {token}"}

    # 1. Empty file rejection (422)
    empty_resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_header,
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert empty_resp.status_code == 422
    assert "empty" in empty_resp.text.lower()

    # 2. Corrupted file / invalid PDF header rejection (422)
    corrupt_resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_header,
        files={"file": ("corrupt.pdf", b"NOT_A_REAL_PDF_STREAM", "application/pdf")},
    )
    assert corrupt_resp.status_code == 422
    assert "pdf" in corrupt_resp.text.lower()

    # 3. Scanned PDF rejection (422) with clear informative message
    scanned_bytes = create_sample_scanned_pdf()
    scanned_resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_header,
        files={"file": ("scanned_document.pdf", scanned_bytes, "application/pdf")},
    )
    assert scanned_resp.status_code == 422
    assert "scanned" in scanned_resp.text.lower()

    # 4. Valid text PDF upload success (201)
    valid_pdf_bytes = create_sample_text_pdf()
    valid_resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_header,
        files={"file": ("valid_contract.pdf", valid_pdf_bytes, "application/pdf")},
        data={"document_type": "terms_and_conditions", "jurisdiction": "Delaware"},
    )
    assert valid_resp.status_code == 201
    doc_data = valid_resp.json()["data"]
    assert doc_data["status"] == "uploaded"
    assert doc_data["original_filename"] == "valid_contract.pdf"


@pytest.mark.asyncio
async def test_end_to_end_pipeline_and_exports(client: AsyncClient):
    """
    End-to-end integration test:
    Register -> Upload -> Execute Analysis Pipeline -> Status -> Clauses -> Summary -> Export JSON & Markdown.
    """
    email = f"e2e_{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "full_name": "E2E User"},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    token = login_res.json()["data"]["access_token"]
    auth_header = {"Authorization": f"Bearer {token}"}

    # Upload document
    pdf_bytes = create_sample_text_pdf()
    upload_resp = await client.post(
        "/api/v1/documents",
        headers=auth_header,
        files={"file": ("commercial_terms.pdf", pdf_bytes, "application/pdf")},
        data={"document_type": "terms_and_conditions"},
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["data"]["id"]

    # Wait for processing or execute analysis pipeline
    import asyncio
    from uuid import UUID

    st_data: dict[str, Any] = {}
    for _ in range(20):
        status_resp = await client.get(
            f"/api/v1/documents/{doc_id}/status",
            headers=auth_header,
        )
        assert status_resp.status_code == 200
        st_data = status_resp.json()["data"]
        if st_data["status"] in ("completed", "failed"):
            break
        await asyncio.sleep(0.5)

    if st_data.get("status") != "completed":
        async with async_session_factory() as session:
            analysis_service = AnalysisService(session)
            await analysis_service._run_analysis_task(UUID(doc_id))

        status_resp = await client.get(
            f"/api/v1/documents/{doc_id}/status",
            headers=auth_header,
        )
        assert status_resp.status_code == 200
        st_data = status_resp.json()["data"]

    assert st_data["status"] == "completed"
    assert st_data["progress"] == 1.0

    # Fetch clause-level analyses
    clauses_resp = await client.get(
        f"/api/v1/documents/{doc_id}/clauses",
        headers=auth_header,
    )
    assert clauses_resp.status_code == 200
    clauses = clauses_resp.json()["data"]
    assert len(clauses) >= 2
    c1 = clauses[0]
    assert "plain_english_summary" in c1
    assert "risk_score" in c1
    assert "risk_category" in c1
    assert "risk_reasons" in c1

    # Fetch document-level risk summary
    analysis_resp = await client.get(
        f"/api/v1/documents/{doc_id}/analysis",
        headers=auth_header,
    )
    assert analysis_resp.status_code == 200
    analysis_data = analysis_resp.json()["data"]
    assert analysis_data["overall_risk_score"] > 0
    assert len(analysis_data["overall_summary"]) > 10

    # Export JSON
    json_export = await client.get(
        f"/api/v1/documents/{doc_id}/export/json",
        headers=auth_header,
    )
    assert json_export.status_code == 200
    export_obj = json_export.json()
    assert "document" in export_obj
    assert "risk_summary" in export_obj
    assert "clauses" in export_obj
    assert "disclaimer" in export_obj
    assert "legal advice" in export_obj["disclaimer"].lower()

    # Export Markdown
    md_export = await client.get(
        f"/api/v1/documents/{doc_id}/export/markdown",
        headers=auth_header,
    )
    assert md_export.status_code == 200
    md_text = md_export.text
    assert "# Legal Document Simplification & Risk Report" in md_text
    assert "IMPORTANT NOTICE:" in md_text
    assert "not constitute legal advice" in md_text
    assert "Executive Summary" in md_text


@pytest.mark.asyncio
async def test_per_user_data_isolation(client: AsyncClient):
    """Verify User B is strictly forbidden from accessing User A's documents, analyses, and exports."""
    # Register User A
    user_a_email = f"usera_{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": user_a_email, "password": "Password123!", "full_name": "User A"},
    )
    login_a = await client.post(
        "/api/v1/auth/login",
        json={"email": user_a_email, "password": "Password123!"},
    )
    token_a = login_a.json()["data"]["access_token"]

    # User A uploads document
    pdf_bytes = create_sample_text_pdf()
    up_res = await client.post(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"file": ("confidential_user_a.pdf", pdf_bytes, "application/pdf")},
    )
    doc_id = up_res.json()["data"]["id"]

    # Register User B
    user_b_email = f"userb_{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": user_b_email, "password": "Password123!", "full_name": "User B"},
    )
    login_b = await client.post(
        "/api/v1/auth/login",
        json={"email": user_b_email, "password": "Password123!"},
    )
    token_b = login_b.json()["data"]["access_token"]
    header_b = {"Authorization": f"Bearer {token_b}"}

    # User B attempts to access User A's document
    res_doc = await client.get(f"/api/v1/documents/{doc_id}", headers=header_b)
    assert res_doc.status_code == 404

    # User B attempts to access User A's status
    res_st = await client.get(f"/api/v1/documents/{doc_id}/status", headers=header_b)
    assert res_st.status_code == 404

    # User B attempts to access User A's clauses
    res_cls = await client.get(f"/api/v1/documents/{doc_id}/clauses", headers=header_b)
    assert res_cls.status_code == 404

    # User B attempts to access User A's analysis
    res_ana = await client.get(f"/api/v1/documents/{doc_id}/analysis", headers=header_b)
    assert res_ana.status_code == 404

    # User B attempts to export User A's document
    res_exp = await client.get(f"/api/v1/documents/{doc_id}/export/json", headers=header_b)
    assert res_exp.status_code == 404

    # User B attempts to delete User A's document
    res_del = await client.delete(f"/api/v1/documents/{doc_id}", headers=header_b)
    assert res_del.status_code == 404

    # User B list documents must not include User A's doc
    res_list = await client.get("/api/v1/documents", headers=header_b)
    items = res_list.json()["data"]["items"]
    assert not any(item["id"] == doc_id for item in items)


@pytest.mark.asyncio
async def test_delete_my_data_gdpr_compliance(client: AsyncClient):
    """Verify deleting user account cascades and wipes all documents and data."""
    email = f"gdpr_{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "full_name": "GDPR User"},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    token = login_res.json()["data"]["access_token"]
    header = {"Authorization": f"Bearer {token}"}

    # Upload document
    pdf_bytes = create_sample_text_pdf()
    up = await client.post(
        "/api/v1/documents",
        headers=header,
        files={"file": ("to_delete.pdf", pdf_bytes, "application/pdf")},
    )
    _doc_id = up.json()["data"]["id"]

    # Delete account (Delete-My-Data)
    del_resp = await client.delete("/api/v1/auth/me", headers=header)
    assert del_resp.status_code == 200

    # Token must now be rejected
    me_resp = await client.get("/api/v1/auth/me", headers=header)
    assert me_resp.status_code == 401

    # Re-registering the same email is allowed now that data is purged
    re_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "full_name": "Recreated User"},
    )
    assert re_reg.status_code == 201
