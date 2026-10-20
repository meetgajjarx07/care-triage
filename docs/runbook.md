# Runbook

How I operate the demo. Everything here is a laptop command or a click in the dashboard. There is no server to page and nothing sends email on its own.

## Daily

1. `make app`, open Overview. The Needs attention table lists consultant calls, QA fails and low confidence emails that nobody has reviewed yet.
2. Work the queue from the Inbox. For a draft: read the email, read the draft with sentence support switched on, read the QA scorecard. Approve, edit then approve, or discard. For a consultant call there is no draft; the retrieved policy is what the consultant should have open.
3. When the model got the category or sentiment wrong, open Correct the prediction, set the right value and give a one line reason. The correction is logged. It does not change the live model, and the page says so.
4. Decisions go to `out/reviews.jsonl`. The Activity page shows all of them and exports the file.
5. To show someone the whole project in a few minutes, open the Walkthrough and press Next through the six stops.
6. For a new email that is not in the run, use Live triage: paste it, press the button, read the result the same way. It needs Ollama running with both models; the page says which one is missing. Its decisions land in the same review log with a `LIVE-` id.

## Weekly: retrain with the new labels

Corrections are the labels the next model should learn from.

1. Export the review log from the Activity page, or read `out/reviews.jsonl` directly. Records with `action: correct` carry `id`, `field`, `old`, `new`.
2. Apply them to `data/emails.csv`: for each correction, set that row's `category` or `sentiment` column to `new`. Keep a copy of the previous CSV next to it with the date in the filename. (In this demo that is a short pandas script; in the bank version it was a scheduled job.)
3. Back up the current models and outputs before anything is overwritten:
   ```
   RUN=$(python -c "import json;print(json.load(open('out/run.json'))['run_id'])")
   mkdir -p archive/$RUN && cp -R models out archive/$RUN/
   ```
4. `make all`. Training takes about a minute, the pipeline about twelve (the grading and the briefs are one small model call per paragraph and per email), retrieval evaluation seconds. Set `genai.crag: false` or `genai.brief: false` in the config for a two-minute run without them.
5. Open Model quality and read the Checks table first. Compare out-of-fold accuracy, the worst class recall and the critical QA fail count with the archived run. If a check that passed last week fails now, restore `models/` from the archive and look at which rows changed label before trying again.
6. Note the new run id and config hash from the Run log page.

## When a Configuration status check is red

| Check | Cause | Fix |
|---|---|---|
| Ollama reachable | the Ollama app is not running | start Ollama, reload the page |
| Embedding or drafting model present | model not pulled on this machine | `ollama pull nomic-embed-text` or `ollama pull llama3.2` (names are in `config/triage.yaml`) |
| Dense index matches the knowledge base | a file in `kb/` changed since the index was built | nothing to do by hand, the next `Retriever()` rebuilds it; rerun `make run` so results match the new text |
| Last run age | `out/run.json` is older than `monitoring.run_age_days_max` | `make run` |
| Config hash matches last run | `config/triage.yaml` was edited after the last run | `make run` so the numbers on screen match the settings |
| Critical QA fail rate | more than the configured share of drafts failed a critical rule | read the failures on the Inbox QA fails view before touching thresholds; usually the knowledge base is missing a fact the model then invents |

## Changing a routing rule or a threshold safely

1. Edit `config/triage.yaml`. Rules are evaluated top to bottom and the first match wins, so order matters. `body_regex` is case insensitive.
2. `make test`. `tests/test_config.py` rejects bands out of order, duplicate rule ids and unknown actions. `tests/test_parity.py` replays the last run through the rules; if you changed a rule on purpose this test will fail on the rows that now route differently, which is the list of emails to spot check.
3. `make run`, then compare the Overview funnel with the archived run. The Routed step shows the count per reason.
4. The config hash in the footer and on the Run log page changes with every edit, so a screenshot can always be traced to its settings.

## Rollback

Each archived folder under `archive/<run id>/` holds `models/` and `out/` as they were. To go back:

```
cp -R archive/run-20261018-183709/models/. models/
cp -R archive/run-20261018-183709/out/. out/
```

Restart the dashboard and the API so they drop their caches. The review log is append only and is not part of a rollback; keep it.

## Known limits

- 110 labelled emails. Out-of-fold category accuracy is 73% and the worst classes (safety concern, positive feedback) are under 60% recall. More labels is the fix, not a bigger model.
- Drafting takes about 1.4 seconds per email on this laptop and is the only stage that can state something false. Every draft is read by a person. There is no auto send and no plan for one.
- Retrieval is evaluated against a proxy label (the document a category lives in), not per email relevance judgements. The numbers are directional.
- The whole thing is single machine, single process. The API holds models in memory and is not designed for concurrent writers to the review log.
- No fine-tuning anywhere. Both language models are used as pulled from Ollama.

## Reviews

`python app/voc.py` runs the review set (about ten minutes with the local model; `--no-llm` for themes and rules only, in seconds) and writes `out/voc_results.csv`, `out/voc_trace.jsonl` and `out/voc_run.json`. The Voice of customer page and Walkthrough stop 6 read those. `scripts/make_reviews.py` regenerates `data/reviews.csv` if the fictional set is edited.
