# Praxis Agent — OpenAI review details (v0.1.0)

This file is for the operator. It is **not** in the plugin ZIP: OpenAI
rejects reviewer instructions and credentials in the package. Copy the parts
the portal asks for into **Metadata & Skills → Review information → Review
details**.

The test cases and release notes below are also in `plugin.json`, so the
portal imports them from the ZIP. `check_package.py --review REVIEW.md`
fails when the two copies of a prompt differ.

## 1. Test account (paste into the portal)

| Field | Value |
|---|---|
| Login URL | https://praxis-agent.fly.dev/login |
| Email | `directory-review@lefv.io` |
| Access code | The operator pastes the access credential (`pa_cred_…`) in the portal form. It is never written in a file. |
| Workspace or tenant | None. |
| MFA | None. No emailed code, no SMS, no magic link. |
| Network | Public internet. |

**Sign-in instructions (paste as written):**

1. In ChatGPT, connect the Praxis Agent plugin. ChatGPT registers itself with
   OAuth Dynamic Client Registration and opens the Praxis sign-in page.
2. On https://praxis-agent.fly.dev/login, type the email and the access code
   above. Click **Sign in with code**.
3. The consent page "Connect an AI app to Praxis" names the app and lists
   the nine tools it may use (public law only). Click **Approve**.
4. Do steps 2 and 3 within 10 minutes of step 1. If the window ends, start
   again at step 1.

The account needs no sample data. Praxis reads only public law, and every
test case below works on a new account.

## 2. Positive test cases

| # | Description | Prompt | Tools | Expected behaviour |
|---|---|---|---|---|
| P1 | General public-law question for one state. | Under Virginia law, how long must someone possess land to claim it by adverse possession, and what must they prove? | `ask_praxis` | One call, jurisdiction `VA`. The answer gives the 15-year period of Va. Code § 8.01-236 and the elements (actual, hostile, exclusive, visible, continuous, under a claim of right), with links to the sources. The result starts with the untrusted-content line, ends with the not-legal-advice notice, and has an `answer_ref`. |
| P2 | Case-law search by legal terms and a state filter. | Find Texas cases on the public-policy exception to at-will employment for an employee fired for refusing to commit an illegal act. | `search_case_law` | One call, legal terms, jurisdiction `tx`. Texas opinions (for example *Sabine Pilot Service, Inc. v. Hauck*), each with caption, court, date, CourtListener link, snippet and id. If a live source does not answer, the result says so. It does not say that no case exists. |
| P3 | Official text of one Code of Virginia section. | Show me the current text of Va. Code § 8.01-236. | `get_statute` | The section title and current text, read live from law.lis.virginia.gov, with the official link and the page date. |
| P4 | A FAR section, then rulemaking for its part. | Show the current text of 48 CFR 15.404-4 and the recent Federal Register rulemaking on FAR Part 15. | `get_regulation`, `get_regulation_history` | The text of 48 CFR 15.404-4 with the eCFR link, the last-amended date, the note that eCFR is an unofficial compilation, and the note that 2026 FAR Overhaul class deviations are not shown. Then final and proposed rules for Part 15, newest first, with dates, Federal Register citations, comment status and regulations.gov links. |
| P5 | Rate an earlier answer (the only write tool). Run after P1 in the same chat. | That adverse possession answer was good. Please record a good rating for it. | `report_feedback` | One call: tool `ask_praxis`, rating `good`, the `answer_ref` from P1. Result: "Thank you. Feedback recorded (good) for ask_praxis." A second rating of the same answer gets "Feedback for this answer is already recorded." |

## 3. Negative test cases

Each expected behaviour was checked against the code in `lefv-org/praxis`
(main at `7f8868973`). The evidence column names the source.

| # | Prompt | Why Praxis must not do it all | Expected safe behaviour | Evidence |
|---|---|---|---|---|
| N1 | My client Jane Roe, 62, of 14 Elm Street, Richmond, was fired by Acme Widgets LLC after she refused to falsify safety logs. Will she win a wrongful-discharge suit? | The prompt has a person's private facts and asks for an outcome. | The model leaves the personal details out of the tool arguments (each tool description says they are not needed). Praxis describes only the general law (Virginia's public-policy exception to at-will employment). It does not apply the law to Jane Roe, predict the outcome or say what to do. The answer ends with the not-legal-advice notice. The name, address and company are not legal words, so they are not sent to the live case-law source. | `sidecar/src/praxis/orchestrator.py` `PUBLIC_LAW_ONLY_INSTRUCTION`; `sidecar/src/praxis/public_egress_terms.py`; `apps/core/lib/core/research_agent/notice.ex` |
| N2 | What does 9VAC25-210 of the Virginia Administrative Code require for a wetlands permit? | Praxis does not cover state administrative codes. | The model says Praxis does not cover state administrative codes. `get_regulation` answers "That is not a CFR citation…"; `get_statute` answers that only the Code of Virginia is supported. No text is shown as coming from Praxis. | `apps/praxis_web/lib/praxis_web/public_agent/tools.ex` (`get_regulation` not-supported branch, `not_supported/0`, tool descriptions); server instructions in `public_agent_mcp_controller.ex` |
| N3 | My employer gave me a severance agreement today. Should I sign it, or will I lose my discrimination claim? | It asks for legal advice on the user's own matter. | Praxis says it can describe only the general law, then gives general information on releases of discrimination claims in severance agreements. It does not say whether to sign. The answer ends with "Answers are AI-assisted, may be incomplete, and are not legal advice." | `orchestrator.py` `PUBLIC_LAW_ONLY_INSTRUCTION` ("If the question asks for that, say you can describe only the general law, then describe it"); `notice.ex`; `answer.ex` `render/1` appends the notice to every answer |

## 4. Release notes (v0.1.0)

First release. One remote MCP server, `https://praxis-agent.fly.dev/mcp/agent`
(streamable HTTP, OAuth with Dynamic Client Registration), with nine tools:
`ask_praxis`, `search_case_law`, `get_opinion`, `get_statute` (Code of
Virginia), `get_regulation`, `search_regulations`, `get_regulation_history`,
`get_regulation_comments` and `report_feedback`. One skill,
`public-law-research`, tells the model which tool fits which question.

## 5. Demo video shot list (about 2 minutes)

Record in ChatGPT with developer mode on, signed in as the test account. Show
the tool-call panel for each call. Upload the video where the reviewer can
open it without signing in, then put its URL in the portal (or in
`plugin.json` at `extensions.com.openai.review.demo_recording_url`).

| Time | Show |
|---|---|
| 0:00–0:15 | ChatGPT plugin directory or developer-mode connector list: Praxis Agent, its icon and its description. |
| 0:15–0:35 | Connect: the Praxis sign-in page, email and access code, the consent page with the nine tools, **Approve**, back in ChatGPT. |
| 0:35–0:55 | P1: the adverse-possession question. Show the `ask_praxis` call, the source links, and the not-legal-advice notice. Click one link. |
| 0:55–1:10 | P2: the Texas case search. Show the opinion list and open one CourtListener link. |
| 1:10–1:20 | P3: `get_statute` for Va. Code § 8.01-236, with the official link. |
| 1:20–1:40 | P4: `get_regulation` and `get_regulation_history` for 48 CFR 15.404-4. |
| 1:40–1:50 | P5: `report_feedback`; show the confirmation. |
| 1:50–2:10 | N1 and N3: show that Praxis gives the general law only, with the notice. N2: show "not covered". |

Record it once on desktop and check one prompt on the ChatGPT mobile app.
OpenAI asks that plugins work on both.

## 6. Portal steps that are not in the ZIP

1. **Domain verification.** The portal gives a token. Serve it as plain text
   at `https://praxis-agent.fly.dev/.well-known/openai-apps-challenge`. This
   route does not exist yet (it answers 404 on 2026-10-20).
2. **Demo URL.** Not in `plugin.json` yet; required before submission.
3. **Listing URLs.** `https://praxis-agent.fly.dev/support` and
   `https://praxis-agent.fly.dev/terms` must answer 200 before submission
   (both answered 404 on 2026-10-20). The portal checks that each URL is
   reachable and names the same publisher (CCL Consulting LLC).
4. **Developer identity.** The listing's developer name comes from the
   verified identity chosen at upload, not from `developerName`. Verify CCL
   Consulting LLC in the OpenAI organization settings first.
