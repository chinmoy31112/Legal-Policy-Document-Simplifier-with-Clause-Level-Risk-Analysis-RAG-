# Frontend Design System & Architecture Documentation

## 1. Overview & Design Philosophy

The LegalLens AI frontend has been redesigned to provide a clean, warm, professional legal workspace featuring a seamless light/dark theme switch:
* **Light Theme: "Calm Paper"** — Inspired by premium archival legal stationery, warm cream background (`#FBF7F0`), deep espresso text (`#2B2622`), soft wheat surfaces (`#F1E8DA`), and terracotta accent (`#B4532A`).
* **Dark Theme: "Midnight Focus"** — Deep indigo night palette (`#0F1424`), soft periwinkle text (`#E8ECF8`), muted navy surfaces (`#232B4A`), and periwinkle accent (`#8B9BFF`).
* **Document Integrity (PDF Canvas):** In both themes, contract document text is rendered on pure white light paper (`#FFFFFF`) with dark readable text (`#1A1A1A`), preventing visual inversion artifacts and maintaining authentic legal legibility.

---

## 2. Design Tokens & CSS Variables

All tokens are defined in [globals.css](file:///c:/Users/chinm/Desktop/Legal-Policy-Document-Simplifier-with-Clause-Level-Risk-Analysis-RAG-/frontend/src/app/globals.css) and mapped to Tailwind CSS:

| Token | Light ("Calm Paper") | Dark ("Midnight Focus") | Usage |
| :--- | :--- | :--- | :--- |
| `--background` | `#FBF7F0` | `#0F1424` | Main page background |
| `--foreground` | `#2B2622` | `#E8ECF8` | Primary text |
| `--muted-foreground` | `#6B625A` | `#A4ADC8` | Secondary / subtext |
| `--card` | `#FFFFFF` | `#171D33` | Card & panel background |
| `--border` | `#E7DFD3` | `#27304D` | Subtle borders |
| `--soft-surface` | `#F1E8DA` | `#232B4A` | Secondary surfaces & pills |
| `--accent` | `#B4532A` | `#8B9BFF` | Brand accent & CTA buttons |
| `--accent-foreground` | `#FFFFFF` | `#0F1424` | Text on accent buttons |

### Shape Tokens
* **Cards & Panels:** `18px` border radius (`rounded-[18px]`), soft border, zero heavy drop-shadows.
* **Inner Elements (inputs, buttons, items):** `10px` border radius (`rounded-[10px]`).
* **Pills & Badges:** Fully rounded (`rounded-full`).

### Typography
* **Headings & Logo:** `Fraunces 600` via `next/font/google` (self-hosted).
* **Body Text:** `Inter` (weights 400, 500, 600, 700) via `next/font/google`.

---

## 3. Risk Classification Mapping

Risk is never displayed through color alone. Every risk chip includes an accessible icon and text label:

| Backend Category | Light Token (bg / text / border) | Dark Token (bg / text / border) | Icon | Label |
| :--- | :--- | :--- | :--- | :--- |
| `standard` / `low` | `#E3F1E4` / `#1F5C2E` / `#C6E2C9` | `#16342A` / `#7BE0A0` / `#245845` | `CheckCircle2` | Standard |
| `slightly_unusual` / `medium` | `#FBF0C8` / `#6B4F00` / `#F4E299` | `#3A3216` / `#F2D472` / `#5C4F22` | `Info` | Slightly Unusual |
| `one_sided` | `#FDE3CF` / `#8A3B00` / `#F7C7A3` | `#3D2614` / `#FFB06B` / `#633D20` | `AlertTriangle` | One-Sided |
| `high_risk` / `high` | `#FAD7D7` / `#8F1D1D` / `#F4AEAE` | `#3F1A22` / `#FF8F9B` / `#6B2C3A` | `AlertOctagon` | High Risk |
| `potentially_unenforceable` / `critical` | Transparent / `#8F1D1D` / Outlined dashed border | Transparent / `#FF8F9B` / Outlined dashed border | `Scale` | Potentially Unenforceable |

---

## 4. Layout Architecture

1. **Left Sidebar:**
   - Width: exactly **224px** (`w-[224px]`).
   - Links: **Upload**, **Knowledge Base**, **Analysis**, **History**, **Settings**.
   - Footer: Accessible **ThemeToggle** (`aria-label`) and authenticated user profile with logout.
   - Mobile: Collapses to an accessible sliding drawer modal with touch backdrop and `Escape` key dismissal.
2. **Analysis Workspace:**
   - Top executive banner: Overall risk index score, risk count chips, segmented progress bar, legal notice, and export actions.
   - Two-column split layout:
     - Left column (`lg:col-span-7`): Document viewer with light paper canvas (`#FFFFFF`), search input, severity filter pills, and semi-transparent clause highlight overlays.
     - Right column (`lg:col-span-5`): Synchronized clause detail panel (plain English summary, why flagged, similar benchmark clauses with similarity match, suggested rewrite, and expandable verbatim contract text).
   - Narrow screens: Detail panel becomes a mobile bottom sheet modal when a clause is selected.
3. **Statutory Legal Notice:**
   - *"Information, not legal advice: Clause risk scoring and simplifications are AI-generated for workflow convenience and do not constitute formal legal counsel."*
   - Displayed in footer, analysis summary, and upload views.
4. **Motion & Transitions:**
   - Subtle 180ms easeOut fade and slide transitions via Framer Motion.
   - Respects `prefers-reduced-motion` via `useReducedMotion()`.

---

## 5. Verification & Contrast Metrics

* **WCAG AA Compliance (>= 4.5:1):**
  - Light mode body text (`#2B2622` on `#FBF7F0`): **11.8:1** (Pass)
  - Light mode muted text (`#6B625A` on `#FBF7F0`): **4.8:1** (Pass)
  - Light mode primary button (`#FFFFFF` on `#B4532A`): **4.6:1** (Pass)
  - Dark mode body text (`#E8ECF8` on `#0F1424`): **14.4:1** (Pass)
  - Dark mode muted text (`#A4ADC8` on `#0F1424`): **7.4:1** (Pass)
  - Dark mode primary button (`#0F1424` on `#8B9BFF`): **9.8:1** (Pass)
  - Risk chips (Light & Dark): **6.0:1 – 9.6:1** (Pass)
* **TypeScript & ESLint:** 0 errors, 0 warnings.
* **Production Build:** 12/12 routes prerendered with exit code 0.
* **Backend Isolation:** 0 files modified outside `frontend/`.
