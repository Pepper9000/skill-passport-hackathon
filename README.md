# Skill Passport

Skill Passport builds an evidence-backed skills profile from public GitHub work and a resume PDF. AI may propose citations, but deterministic checks decide which citations are verified. Levels show evidence of use in the candidate's code, not how well a skill is used.

## Run locally (Windows)

Start the backend in one PowerShell terminal:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

HTTPS to GitHub uses the Windows certificate store (via `truststore`), so it also works behind antivirus or proxy software that intercepts HTTPS. Note that `--reload` restarts the server whenever a backend file changes, which cancels any passport being generated at that moment.

Always activate this `backend\.venv` before installing or running; packages installed into another Python (or the old `.venv` in the project root) won't be seen by the server. Check with `python -c "import httpx, truststore"`.

`backend/.env` must contain `GITHUB_TOKEN` and `GEMINI_MODEL`; `GEMINI_API_KEY` is optional because passport generation falls back to extracted document skill mentions when AI proposals are unavailable. The fallback never verifies skills or invents repository evidence. The GitHub token remains required in production for repository ingestion and applicant ownership checks; without it those required workflows would be rate-limited or unavailable. Gemini-backed growth/interview features may be unavailable without the key. Set `APP_ENV=development` explicitly for local use. Production full-access recruiters use individual named keys in `RECRUITER_ACCOUNTS` (a JSON object with distinct secrets of at least 32 characters). An optional shared read-only recruiter sign-in can be enabled separately with `PRESET_RECRUITER_PASSWORD`; see Preset sign-ins below. The deprecated single `RECRUITER_KEY` is accepted only in local development. Marking a review records the recruiter's name in the review-request audit trail. `FRONTEND_ORIGINS` is a comma-separated allowlist of exact frontend origins; it defaults to `http://localhost:5173`, so add the current Vercel origin when deploying. A trailing slash is normalized, but wildcard origins are rejected. Debug endpoints are disabled unless `ALLOW_DEBUG_ENDPOINTS=true` is explicitly set. Passport creation returns an owner access token that the creating browser tab keeps in session storage; it is required for job polling, review requests and passport re-checks. The API rejects request bodies larger than 26 MB before multipart parsing; configure the deployment's reverse proxy or hosting platform with a matching or smaller request-body limit. The existing `.env` is ignored by Git; do not replace it with `.env.example`. The current Gemini model setting is `gemini-flash-latest`.

Certificates are optional: upload up to five PDF, PNG or JPEG files (10 MB each, 25 MB total with the resume). Text PDFs are extracted locally; scanned PDF pages and images are processed by local Tesseract OCR on the backend, and no original certificate file is retained after the generation job. Install the [Tesseract executable](https://tesseract-ocr.github.io/tessdoc/Installation.html) on the backend host and make sure `tesseract` is on `PATH` (for local Windows development, install Tesseract and reopen the terminal; on Debian/Ubuntu hosts, install the `tesseract-ocr` package). No Google Cloud API, billing account or credentials are needed for OCR. Scanned certificate PDFs are limited to 10 OCR pages each. You can select several files at once or add more in a later selection; selected files are listed so you can remove one before submitting.

**Deployment boundary:** the backend stores passports and job status in SQLite and runs generation in the web process after returning the request. Deploy one backend instance with a persistent disk for the database and cache. If that process restarts during generation, the job is marked failed and the user must retry; uploaded PDFs are not retained for automatic recovery. Do not scale this setup across ephemeral or independent instances. Reliable horizontal scaling needs a separate durable worker queue and shared persistent storage, designed so raw resumes are not retained longer than necessary. Keep the current five-job limit until production metrics justify changing it.

The ownership check confirms that the applicant can post a one-time code from the GitHub account used for the passport. It does not establish the applicant’s real-world identity.

Start the frontend in a second PowerShell terminal:

```powershell
cd frontend
npm install
npm run dev
```

Production frontend builds require `VITE_API_BASE_URL` to be set to the HTTPS base URL of the deployed backend (for example, in the Vercel project’s Environment Variables). Set Vercel’s root directory to `frontend`, build command to `npm run build`, and output directory to `dist`. The localhost default applies only to Vite development; a production build without this setting reports a configuration error instead of sending API calls to the visitor’s own computer. After changing this variable, redeploy the frontend so Vite rebuilds the bundle.

For Railway, set the backend service root directory to `backend` and start command to `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Mount one persistent volume and set `DATA_DIR` to its mount path. Set `APP_ENV=production`, a valid `GITHUB_TOKEN`, optional `GEMINI_API_KEY`, `RECRUITER_ACCOUNTS` (a JSON object of individually named 32+ character secrets), and `FRONTEND_ORIGINS` to the exact deployed frontend origin. Restart the backend after configuration changes. Configure `VITE_API_BASE_URL` on Vercel to the reachable HTTPS backend origin, then rebuild the frontend. `/health` checks process health; `/ready` checks storage. Both must succeed before release.

## Screens and API

- Create Passport: <http://localhost:5173/>
- Student Passport: <http://localhost:5173/passport/{passport-id}>
- Recruiter view: <http://localhost:5173/recruiter/{passport-id}>
- Recruiter evidence review (all signals, evidence records, review requests): <http://localhost:5173/recruiter/{passport-id}/evidence>
- Placement Cell: <http://localhost:5173/placement>
- FastAPI docs: <http://localhost:8000/docs>
- Liveness check: <http://localhost:8000/health>
- Readiness check (database and required production integrations): <http://localhost:8000/ready>

Recruiter cohort list endpoints return at most 50 passports by default and support `limit` (1–100) and `offset` query parameters. The Placement Cell loads more on demand; its current CSV export covers the passports loaded in the page.


## Reading a passport

- **Levels** (evidence of use, not ability): **Unverified**, mentioned on the resume or a certificate with no evidence in the analysed files; **Used**, listed in a dependency or config file the candidate committed to; **Applied**, used in source code they committed to, with exact lines cited; **Demonstrated**, applied and exercised by a test the candidate committed to that targets that code (by file name or import). A citation counts only if git blame shows the candidate last changed at least one of its lines (unknown blame counts), and only one where they wrote at least half can make a skill Demonstrated.
- **Skill Evidence Depth (pilot).** A separate, deterministic summary of cited code patterns for SQL, Python, React, FastAPI, Docker, Git, Unit Testing and scikit-learn. It does not change evidence levels or role matching and is not a proficiency rating. A score appears only when at least 60% of the applicable rubric weight and three competencies can be assessed; the panel shows citations and sample coverage. Other skills do not have a depth analyzer yet.
- **Coverage.** Evidence comes from a sample: up to 5 repositories, 6 source files each, and about 8,000 lines sent to the AI step. The one-line summary ("Analysed 5 repositories · 28 of 168 source files · about 6,400 lines") expands to show what wasn't read and why. "Not found" means not found in the analysed files, not that the candidate lacks the skill.
- **Evidence packet (recruiter view).** Each requirement row is collapsed to its status, attribution and a one-line summary. Clicking it shows four parts:
  - **What supports it:** Met / Partial / Not found, plus up to 2 evidence links, code first.
  - **Attribution:** High, Medium or Low, for how clearly the cited work traces to the candidate (not their ability). A thin or one-day history, a bulk upload, backdated history, AI chat text or a one-line copy match caps it at Medium; an earlier-source match on the skill caps it at Low; too little history to judge shows "Low (limited history)".
  - **What's uncertain:** short lines such as "Only one citation" or an advisory warning.
  - **What to ask next:** the interview-kit question, or a template question when there isn't one.

  It is computed deterministically, with no extra AI calls.
- **Evidence record (recruiter evidence page and badge):** the commit, path, lines, SHA-256 of the cited lines, retrieval time, verifier version, checks and the rules that set the level.
- **Students** see every citation that wasn't counted, with links to their lines and the earlier source, and can **Request review**. They don't see the advisory signals or their thresholds. A review request never changes levels; a recruiter marks it reviewed.

## Recruiter sign-in and interview kit

Recruiter sign-in exchanges a configured account name and key at `POST /auth/recruiter/login` for an 8-hour server-validated session token, never a locally guessed role. Expired or revoked sessions require sign-in again. The preset student sign-in is browser-local UI state, not persistent authentication: private passport access still depends on the token held in the creating browser's session storage. Keep that tab/session available for private actions and re-checks. Local development can use `RECRUITER_KEY`; production must configure individually named `RECRUITER_ACCOUNTS` or explicitly enable the shared read-only account. On upgrade, startup removes only passports registered by the retired backend fixture seeder and their associated records. Ordinary user passports are preserved.

The Create Passport form accepts one optional public Gist URL in addition to public repositories. It must be a `gist.github.com` URL belonging to the submitted GitHub account. The server reads supported source files from the Gist's current revision and only includes them as authored code evidence when the latest revision is attributable to that account. Gists remain separate from repository count; they do not supply Git history, dependency/config evidence, or known blame data.

On a recruiter view, **Interview kit** (header button, or scroll down) shows the private interview workspace:

1. **Generate interview set.** The set picks job-critical requirements whose attribution needs a look first, then must-haves below their required level, then strong evidence. It makes one Gemini call. Each question appears beside its cited code, with the focus lines highlighted, and has passed a check against that file and those lines. A requirement with no code citation becomes a recruiter-led discussion.
2. **Show answer guidance** reveals the points a good answer covers. A modification question may include a five-minute code-change task; nothing is run on the server.
3. Record **Explained well / Partly explained / Couldn't explain** and an optional note per question. The summary ("Interview check: 3 of 5 questions explained well · 1 not yet assessed") is computed from the saved outcomes.

Sets are saved: reopening the page never generates new questions, and **Generate another set** starts a separate one. Each recruiter sees only their own sets. After a Re-check, questions about citations that changed are marked outdated.

**Outcomes move levels on recruiter pages.**

- **Steps:** Explained well **+1**, Partly explained **−1**, Couldn't explain **−2**.
- **Which answer counts:** each skill takes its worst answer in the newest interview set that assessed it, from any recruiter.
- **Limits:** levels stay between Unverified and Demonstrated (Unit Testing: Applied). A skill with no counted evidence never rises above Unverified.
- **Where it shows:** the role match, the Placement Cell ranking and the requirement rows use the adjusted level. Each moved level is tagged, e.g. "Interview −1 · evidence: Applied", and the header also shows the match from evidence alone when it differs.
- **Unchanged:** the student passport, the downloadable credential and the stored evidence keep the level from the code checks. Changing an outcome recalculates immediately.

## Regenerate all passports

After changing verification rules, rebuild every stored passport with a fresh GitHub read. This is the same as pressing Re-check on each one, and it reuses each passport's stored resume and certificate mentions. From the project root:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\recheck_all.py
```

It prints one line per passport (username, requirements met before → after, and rejected and excluded claim counts). A passport that fails, for example on a GitHub rate limit, is reported and left unchanged. Each passport makes live GitHub and Gemini calls, so expect about a minute per passport.

## Authorship checks

Student views exclude recruiter-only identity signals, evaluation details and answer guides. Recruiters use authenticated review endpoints. Citations matched to an earlier public source are excluded only when two cited lines match another owner's file and its first commit predates the candidate file by more than a day. Missing source dates remain warnings for human review, not automatic accusations. Unknown evidence means "not found in the analysed files", never that a candidate lacks a skill.

## Tests

From the project root:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests -q
cd frontend
npm test
npm run build
```

Automated tests use isolated fixtures and mocked external APIs. Parser-only fictional PDFs live under `backend/tests/fixtures/resumes/`; they are never seeded or offered in the application. Real-browser testing must use a local backend and authorized account ownership proof.

## Preset sign-ins

The sign-in screen offers `student@university.edu` / `student2026` and `recruiter@techcorp.com` / `recruiter2026`. The student selection is browser-local UI state, not persistent authentication, and does not grant ownership of another student's passport. Private actions still require the token issued to the creating browser session.

The shared recruiter sign-in is disabled until an operator explicitly sets `PRESET_RECRUITER_PASSWORD=recruiter2026` on the backend. It reads real submissions and is read-only: no evidence changes, evidence requests, interviews or re-checks. The displayed shared password is not private. Enable it only when sharing candidate records with anyone who has those credentials is intended. Named `RECRUITER_ACCOUNTS` remain the full-access option. No sample passports are created.
