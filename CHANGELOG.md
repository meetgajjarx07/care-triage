# Changelog

All dates are 2026. Versions follow the `version` field in `config/triage.yaml`, which is stamped into `out/run.json` on every run.

## 0.8.0 (2026-10-19)

- Voice of customer: the same sorter pointed at reviews. `data/reviews.csv` holds 104 fictional reviews shaped like a Yotpo export plus Amazon and independent-site rows, with the themes public AlgaeCal reviews actually talk about. `app/voc.py` embeds them with the same model, predicts one of seven themes out of fold (so every shown theme comes from a model that never saw that review), takes the mood from the stars, has the language model write a one-line gist and copy one phrase out of the review (kept only if it really appears in the text), applies the review rules in `config/triage.yaml` (a scan result or a side effect in a negative review goes to a private consultant outreach, other negative reviews get a drafted public reply under 90 words, the rest are counted), and runs the same seven QA rules on every draft.
- `warehouse/bigquery_schema.sql` is one `voice_of_customer` table for emails, reviews and, later, calls and chat; `warehouse/queries.sql` holds the seven queries behind every number on the page, run locally on SQLite over the same rows by `app/voc_sql.py`. The Voice of customer page shows the rising theme, themes by week, the mix, by product, what happened to the bad ones, cancel talk across both channels, and the negative reviews with the model's gist, the drafted public reply and its scorecard. A box says how this would run on the company's stack (Yotpo, Amazon, Talkdesk, Cloud Storage, BigQuery, Looker, Salesforce) and that it is a design, not built here.
- Walkthrough gains a seventh stop, Your reviews. Config version 0.8.0.

## 0.7.0 (2026-10-19)

- The language model now does three jobs, each with a guard (`app/genai.py`), the same shape as the email system this rebuilds: it grades every retrieved paragraph against the email and drops the ones about something else, with the search's best match always kept; if it rejects all of them it rephrases the question once and searches again, and if that also fails the email is marked a content gap (corrective RAG with a guard, because a 3B grader over-rejects); it writes a two-line brief for whoever handles the email and copies the facts out of it, each fact kept only if it appears in the email text; and it writes the draft, from the kept paragraphs only. It still never routes and never grades its own draft.
- `triage.retrieve_graded()` and `triage.make_brief()` are shared by the live path, the API and the batch pipeline. The trace gains `retrieve.crag` and a `brief` stage; results.csv gains `brief_asks`, `brief_check`, `brief_facts`, `crag_kept`, `crag_dropped`. The API `/triage` now runs `triage_email` and returns `brief` and `crag`.
- Step cards show the grading (dropped paragraphs struck through with the model's reason) and the brief; the tags say which steps use generative AI.

## 0.6.0 (2026-10-19)

- Walkthrough page, first in the nav and the default page: the project in six stops in plain words, built from the run. Stop three reuses the Live triage panel (`live.panel`), stop four shows E061's draft with its failed check.
- Pipeline rerun under the 0.6.0 config: predictions, drafts and QA identical to 0.5.0.

## 0.5.0 (2026-10-19)

- Live triage page: paste one email and watch it handled one step at a time, in plain words (what it is about and how sure, which policy, who handles it, a first draft, is it safe, a person decides), each step filling in as it finishes. The engineer's view (timings, model names, probabilities, retrieval ranks, scorecard, sentence support) sits under one expander. Five fresh example emails, none of them in the training set. The page checks Ollama and both models first and says what is missing.
- Overview opens with a plain-language summary of the run above the KPI tiles.
- `app/triage.py`: one email through embed, classify, retrieve, route, draft and check, returning a record shaped like a line of `out/trace.jsonl`, with a progress callback. The Live page uses it; the API's `/triage` does the same work.
- Two more offline tests (`tests/test_triage.py`): record shape without drafting, and that a guarantee claim routes to a consultant and never drafts. 32 tests.

## 0.4.0 (2026-10-18)

- Visual language moved to IBM Carbon conventions with IBM Plex Sans and Plex Mono served from `app/static/fonts`.
- One configuration file, `config/triage.yaml`, now holds the models, classifier settings, confidence band thresholds, retrieval constants, QA limits and the routing rules. `app/config.py` merges it over defaults and validates it. The pipeline, the dashboard and the API read the same object.
- Routing rules are data. `route()` evaluates the YAML top to bottom; behaviour is identical to 0.3.0 and `tests/test_parity.py` replays the last run to prove it.
- New pages: Configuration (status checks, values in force, exports), Model facts (an AI fact sheet built from `models/eval.json` and `out/run.json`), Activity (every review decision, filterable, exportable).
- `app/api.py`: a FastAPI service with `/health`, `/config`, `/emails`, `/emails/{id}`, `/triage` and `/reviews`, so the dashboard is one client of the pipeline rather than the pipeline itself.
- `tests/`: 30 offline tests covering config validation, routing, QA rules, retrieval, API and parity. No Ollama needed.
- `Makefile` with `setup`, `train`, `run`, `eval`, `all`, `app`, `api`, `test`, `lint`, `clean`.
- `docs/`: architecture, runbook and decision records.
- `out/run.json` gains `config_version`, `config_hash` and `routing_rules`; each trace's route stage gains `rule_id`.

## 0.3.0 (2026-10-18)

- Review loop on the Inbox: approve, edit then approve, discard, correct category or sentiment with a reason. Decisions append to `out/reviews.jsonl`. Corrections do not retrain the live model, and the page says so.
- Provenance banner on every draft: which policy sections it was based on, which model wrote it, how long it took.
- Draft QA scorecard: seven deterministic rules taken from the system prompt, three of them critical. A critical fail zeroes the score.
- Sentence support: each draft sentence scored against the retrieved notes and the customer email by embedding similarity, shown as highlighting.
- Confidence bands (high, medium, low) with named escalation reasons.
- Model quality rebuilt on out-of-fold predictions: confusion matrix, per class precision and recall, reliability diagram with expected calibration error, most confident mistakes, a pass/fail check list at the top.
- Overview funnel: received, classified by band, routed by reason, QA result, review status.

## 0.2.0 (2026-10-17)

- Per email trace view: every stage's input, output and timing, a latency waterfall, class probabilities, retrieved chunks with BM25 and dense ranks, the routing rule, the raw JSON record.
- Run log page: run id, timings, library versions, the drafting system prompt, stdout of the last run.
- Retrieval evaluation (`app/eval_retrieval.py`): hit@k and MRR for BM25, dense, hybrid and the boosted pipeline, plus the low-evidence email list.

## 0.1.0 (2026-10-17)

- First end to end pipeline: embed with nomic-embed-text, classify category and sentiment with logistic regression, retrieve policy chunks with BM25 plus dense fusion, route with four rules, draft with llama3.2, check numbers and instruction words against the notes.
- 110 hand written, hand labelled emails and a seven document knowledge base paraphrased from public pages.
- First Streamlit dashboard with Overview, Inbox, Model quality and Knowledge base.
