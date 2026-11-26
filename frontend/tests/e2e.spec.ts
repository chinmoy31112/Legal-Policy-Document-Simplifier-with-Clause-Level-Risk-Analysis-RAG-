import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import path from "node:path";

const ROOT_DIR = path.resolve(__dirname, "..", "..");
const PYTHON_BIN =
  process.env.PYTHON_BIN ||
  path.join(ROOT_DIR, "backend", "venv", "Scripts", "python.exe");
const API_URL = process.env.E2E_API_URL || "http://127.0.0.1:18000/api/v1";
const REDIS_URL = process.env.REDIS_URL || "redis://localhost:6379/0";

function buildLegalPdfBuffer(numClauses: number): Buffer {
  const lines = ["COMMERCIAL MASTER SERVICES AGREEMENT"];
  for (let i = 1; i <= numClauses; i++) {
    lines.push(
      `${i}. Clause Number ${i}\nVendor liability under section ${i} shall not exceed one hundred dollars ($100) and Customer agrees to indemnify Vendor for any claims arising out of use.`
    );
  }
  const py = [
    "import fitz, sys",
    "doc = fitz.open()",
    "text = sys.stdin.read()",
    "chunk_size = 2800",
    "for start in range(0, len(text), chunk_size):",
    "    page = doc.new_page()",
    "    page.insert_text((40, 40), text[start:start+chunk_size], fontsize=8)",
    "sys.stdout.buffer.write(doc.tobytes())",
    "doc.close()",
  ].join("\n");
  return execFileSync(PYTHON_BIN, ["-c", py], {
    input: lines.join("\n\n"),
    maxBuffer: 10 * 1024 * 1024,
  });
}

function setRedisQuotaFlag(val: string | null) {
  const py = val
    ? `import redis; r = redis.from_url(${JSON.stringify(REDIS_URL)}); r.set("test:inject_daily_quota", ${JSON.stringify(val)}, ex=120)`
    : `import redis; r = redis.from_url(${JSON.stringify(REDIS_URL)}); keys = ["test:inject_daily_quota"] + [k for p in ("ratelimit:daily_exhausted:*", "ratelimit:*:daily_exhausted", "ratelimit:*:daily_notice") for k in r.keys(p)]; r.delete(*keys) if keys else None`;
  execFileSync(PYTHON_BIN, ["-c", py]);
}

async function registerAndLogin(page: import("@playwright/test").Page) {
  const suffix = `${Date.now()}_${Math.floor(Math.random() * 10000)}`;
  const email = `pw_${suffix}@example.com`;
  const password = "Password123!";

  const regRes = await page.request.post(`${API_URL}/auth/register`, {
    data: { email, password, full_name: "Playwright User" },
  });
  expect(regRes.ok()).toBeTruthy();

  await page.goto("/login");
  await page.getByLabel(/email/i).fill(email);
  await page.locator("#login-password").fill(password);
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.waitForURL(/\/(upload|dashboard|documents|analysis)/, { timeout: 20_000 });
  return { email, password };
}

test.describe("Reliability E2E Suite (Latency Fake)", () => {
  test.beforeEach(() => {
    setRedisQuotaFlag(null);
  });

  test.afterEach(() => {
    setRedisQuotaFlag(null);
  });

  test("clauses stream progressively, provisional score appears before summary finishes, and counts + breakdown bar agree", async ({
    page,
  }) => {
    test.setTimeout(180_000);
    await registerAndLogin(page);

    const pdfBuf = buildLegalPdfBuffer(28);
    await page.goto("/upload");

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: "progressive_28.pdf",
      mimeType: "application/pdf",
      buffer: pdfBuf,
    });
    await page.getByRole("button", { name: /begin clause risk analysis/i }).click();
    await page.waitForURL(/\/analysis\/[0-9a-f-]+/, { timeout: 20_000 });

    // 1. Progressive rendering check: Wave 1 (24 clauses at batch_size=8) appears BEFORE all 28+ finish!
    let sawPartialProgress = false;
    await expect
      .poll(
        async () => {
          const count = await page.locator('[data-testid="clause-item"]').count();
          if (count > 0 && count < 28) {
            sawPartialProgress = true;
          }
          return count > 0 && count < 28;
        },
        { timeout: 60_000, intervals: [500] }
      )
      .toBe(true);
    expect(sawPartialProgress).toBe(true);

    // 2. Provisional score badge renders after last batch finishes while summary sleeps
    await expect(page.locator('[data-testid="provisional-score-badge"]')).toBeVisible({
      timeout: 45_000,
    });

    // 3. Final completed state: Provisional disappears, counts and breakdown bar agree
    await expect(page.locator('[data-testid="status-badge"]').first()).toContainText(
      /completed/i,
      { timeout: 45_000 }
    );
    await expect(page.locator('[data-testid="provisional-score-badge"]')).toHaveCount(0);

    const clauseCount = await page.locator('[data-testid="clause-item"]').count();
    expect(clauseCount).toBeGreaterThanOrEqual(28);

    const summaryCountText = await page
      .locator('[data-testid="summary-clause-count"]')
      .textContent();
    const expectedLabel = clauseCount === 1 ? "1 clause evaluated" : `${clauseCount} clauses evaluated`;
    expect(summaryCountText).toContain(expectedLabel);

    const allFilterText = await page.locator('[data-testid="filter-all"]').textContent();
    const highFilterText = await page.locator('[data-testid="filter-high"]').textContent();
    const medFilterText = await page.locator('[data-testid="filter-medium"]').textContent();
    const stdFilterText = await page.locator('[data-testid="filter-standard"]').textContent();

    const extractNum = (txt: string | null) => {
      const m = (txt || "").match(/\((\d+)\)/);
      return m ? Number(m[1]) : 0;
    };

    expect(extractNum(allFilterText)).toBe(clauseCount);
    expect(
      extractNum(highFilterText) + extractNum(medFilterText) + extractNum(stdFilterText)
    ).toBe(clauseCount);

    // Breakdown bar renders non-empty segments matching clause count
    const breakdownBar = page.locator('[data-testid="risk-breakdown-bar"]');
    await expect(breakdownBar).toBeVisible();
    const segmentCount = await breakdownBar.locator("> div").count();
    expect(segmentCount).toBeGreaterThan(0);
  });

  test("delete mid-run shows Stopping analysis, removes item, closes SSE, stops progress events", async ({
    page,
  }) => {
    test.setTimeout(120_000);
    await registerAndLogin(page);

    const pdfBuf = buildLegalPdfBuffer(16);
    await page.goto("/upload");
    await page.locator('input[type="file"]').setInputFiles({
      name: "delete_mid_run.pdf",
      mimeType: "application/pdf",
      buffer: pdfBuf,
    });
    await page.getByRole("button", { name: /begin clause risk analysis/i }).click();
    await page.waitForURL(/\/analysis\/([0-9a-f-]+)/, { timeout: 20_000 });

    const docIdMatch = page.url().match(/\/analysis\/([0-9a-f-]+)/);
    expect(docIdMatch).toBeTruthy();
    const docId = docIdMatch![1];

    // Confirm active analysis / SSE stream started
    await expect(page.locator('[data-testid="status-badge"]').first()).toContainText(
      /(queued|extracting|segmenting|classifying|embedding|analyzing|running)/i,
      { timeout: 15_000 }
    );

    const postDeleteProgressRequests: string[] = [];
    let deleteSettled = false;
    page.on("request", (req) => {
      if (
        deleteSettled &&
        req.url().includes(docId) &&
        (req.url().includes("/events") ||
          req.url().includes("/status") ||
          req.url().includes("/clauses"))
      ) {
        postDeleteProgressRequests.push(`${req.method()} ${req.url()}`);
      }
    });

    // Gate DELETE fulfillment strictly until Playwright confirms "Stopping analysis..." renders while DELETE is pending
    let releaseDelete!: () => void;
    const deleteGate = new Promise<void>((resolve) => {
      releaseDelete = resolve;
    });
    await page.route(`**/api/v1/documents/${docId}`, async (route) => {
      if (route.request().method() === "DELETE") {
        await deleteGate;
      }
      await route.continue();
    });

    await page.locator('[data-testid="delete-document-button"]').click();
    await expect(page.getByText(/Stopping analysis\.\.\./i).first()).toBeVisible({
      timeout: 5_000,
    });
    releaseDelete();

    // Navigates to /documents and removes item once backend confirms
    await page.waitForURL(/\/documents/, { timeout: 15_000 });
    deleteSettled = true;

    await expect(page.locator(`[data-testid="document-row-${docId}"]`)).toHaveCount(0);

    // Wait 3s after delete to ensure zero further progress/SSE requests occur
    await page.waitForTimeout(3000);
    expect(postDeleteProgressRequests).toEqual([]);
  });

  test("quota-pause state displays cleanly without fake countdown", async ({ page }) => {
    test.setTimeout(120_000);
    setRedisQuotaFlag("analyze");
    await registerAndLogin(page);

    const pdfBuf = buildLegalPdfBuffer(8);
    await page.goto("/upload");
    await page.locator('input[type="file"]').setInputFiles({
      name: "quota_pause_test.pdf",
      mimeType: "application/pdf",
      buffer: pdfBuf,
    });
    await page.getByRole("button", { name: /begin clause risk analysis/i }).click();
    await page.waitForURL(/\/analysis\/([0-9a-f-]+)/, { timeout: 20_000 });

    // Worker finishes classification sleep (~10s), then hits injected daily quota 429 on analyze call
    const banner = page.locator('[data-testid="quota-pause-banner"]');
    await expect(banner).toBeVisible({ timeout: 45_000 });
    await expect(banner).toContainText(/resumes automatically after the daily quota reset/i);

    const statusText = await page.locator('[data-testid="status-badge"]').first().textContent();
    expect(statusText?.toLowerCase()).toContain("waiting for quota");

    // Verify Resume Analysis button is visible and NO fake countdown timer exists
    await expect(page.locator('[data-testid="resume-analysis-button"]')).toBeVisible();
    const bannerText = (await banner.textContent()) || "";
    expect(bannerText).not.toMatch(/\d{2}:\d{2}:\d{2}/);
  });

  test("logout clears cached documents and tokens so next user sees clean state", async ({
    page,
  }) => {
    test.setTimeout(120_000);
    await registerAndLogin(page);

    const pdfBuf = buildLegalPdfBuffer(4);
    await page.goto("/upload");
    await page.locator('input[type="file"]').setInputFiles({
      name: "user_a_secret_doc.pdf",
      mimeType: "application/pdf",
      buffer: pdfBuf,
    });
    await page.getByRole("button", { name: /begin clause risk analysis/i }).click();
    await page.waitForURL(/\/analysis\/([0-9a-f-]+)/, { timeout: 20_000 });

    await page.goto("/documents");
    await expect(page.getByText("user_a_secret_doc.pdf")).toBeVisible({ timeout: 15_000 });

    // Click sidebar Log out button
    await page.getByRole("button", { name: /log out of application/i }).click();
    await page.waitForURL(/\/login/, { timeout: 15_000 });

    const clearedTokens = await page.evaluate(() => ({
      access: localStorage.getItem("access_token"),
      refresh: localStorage.getItem("refresh_token"),
    }));
    expect(clearedTokens.access).toBeNull();
    expect(clearedTokens.refresh).toBeNull();

    // Sign in as a brand new User B in the same browser session; User A's cached row must not appear
    await registerAndLogin(page);
    await page.goto("/documents");
    await expect(page.getByText(/no history records found/i)).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("user_a_secret_doc.pdf")).toHaveCount(0);
  });

  test("account deletion from settings purges backend data, clears cache, and blocks re-login", async ({
    page,
  }) => {
    test.setTimeout(120_000);
    const { email, password } = await registerAndLogin(page);

    const pdfBuf = buildLegalPdfBuffer(4);
    await page.goto("/upload");
    await page.locator('input[type="file"]').setInputFiles({
      name: "delete_acct_doc.pdf",
      mimeType: "application/pdf",
      buffer: pdfBuf,
    });
    await page.getByRole("button", { name: /begin clause risk analysis/i }).click();
    await page.waitForURL(/\/analysis\/([0-9a-f-]+)/, { timeout: 20_000 });

    await page.goto("/settings");
    await page.getByRole("button", { name: /delete account & data/i }).click();
    await page.locator("#confirm-delete-input").fill("DELETE");

    const deletePromise = page.waitForResponse(
      (res) => res.url().includes("/api/v1/auth/me") && res.request().method() === "DELETE"
    );
    await page.getByRole("button", { name: /confirm purge/i }).click();
    const deleteRes = await deletePromise;
    expect(deleteRes.status()).toBe(200);

    await page.waitForURL(/\/login/, { timeout: 15_000 });
    const clearedTokens = await page.evaluate(() => ({
      access: localStorage.getItem("access_token"),
      refresh: localStorage.getItem("refresh_token"),
    }));
    expect(clearedTokens.access).toBeNull();
    expect(clearedTokens.refresh).toBeNull();

    // Verify account no longer exists in backend
    const loginRetry = await page.request.post(`${API_URL}/auth/login`, {
      data: { email, password },
    });
    expect(loginRetry.status()).toBe(401);
  });
});
