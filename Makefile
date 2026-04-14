.PHONY: test compile smoke

test:
	pytest

compile:
	python3 -m py_compile scripts/*.py

smoke: compile
	python3 scripts/grep_legacy.py --help
	python3 scripts/scan_contract_drift.py --help
	python3 scripts/summarize_impacts.py --help
