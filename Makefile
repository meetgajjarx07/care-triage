# Care Triage: local pipeline, dashboard, API and tests. Everything runs on this machine.
PY ?= python
EMBED := $(shell $(PY) -c "import sys; sys.path.insert(0,'app'); from config import CFG; print(CFG['models']['embed'])")
DRAFT := $(shell $(PY) -c "import sys; sys.path.insert(0,'app'); from config import CFG; print(CFG['models']['draft'])")

.PHONY: setup train run voc eval all app api test lint clean

setup:            ## install Python deps and pull both Ollama models
	pip install -r requirements.txt
	ollama pull $(EMBED)
	ollama pull $(DRAFT)

train:            ## fit classifiers, write models/metrics.json and models/eval.json (~1 min)
	$(PY) app/classify.py --llm

run:              ## run every email through the pipeline, write out/ (~12 min, drafts locally)
	$(PY) app/pipeline.py

voc:              ## the same sorter over data/reviews.csv -> out/voc_* (~10 min, drafts public replies locally)
	$(PY) app/voc.py

eval:             ## retrieval hit@k / MRR -> models/retrieval_eval.json (seconds)
	$(PY) app/eval_retrieval.py

all: train run voc eval

app:              ## the dashboard
	streamlit run app/dashboard.py

api:              ## the service, docs at http://localhost:8000/docs
	uvicorn api:app --app-dir app --port 8000 --reload

test:             ## offline test suite, no Ollama needed
	$(PY) -m pytest -q tests

lint:
	@if command -v ruff >/dev/null 2>&1; then ruff check app tests; \
	elif $(PY) -c "import pyflakes" 2>/dev/null; then $(PY) -m pyflakes app tests; \
	else echo "no linter installed (pip install ruff)"; fi

clean:            ## reset the review log and caches; models/ and out/ runs are kept
	rm -f out/reviews.jsonl
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
