PYTHON ?= python
APP_DIR = backend
FRONTEND = frontend/app.py

.PHONY: bootstrap backend frontend sample test lint compile report zip

bootstrap:
	$(PYTHON) scripts/bootstrap.py

backend:
	uvicorn backend.app.main:app --reload --port 8000

frontend:
	streamlit run $(FRONTEND)

sample:
	$(PYTHON) scripts/run_sample_case.py --sample remediation_tender

test:
	pytest -q

compile:
	$(PYTHON) -m compileall backend frontend scripts tests

report:
	$(PYTHON) scripts/generate_report.py

zip:
	cd .. && zip -r RemedAI_submission.zip RemedAI \
		-x "RemedAI/runtime/*" \
		-x "RemedAI/**/__pycache__/*" \
		-x "RemedAI/.pytest_cache/*" \
		-x "RemedAI/.mypy_cache/*" \
		-x "RemedAI/.ruff_cache/*" \
		-x "RemedAI/.env"
