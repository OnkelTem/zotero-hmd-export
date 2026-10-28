.PHONY: dev lint test clean

.venv:
	python3 -m venv .venv
	.venv/bin/pip install -e .

dev: .venv
	@echo "Run: source .venv/bin/activate"

lint:
	.venv/bin/python -m py_compile zotero_hmd_export/*.py

test:
	.venv/bin/python -m unittest discover -s tests -v

clean:
	rm -rf .venv
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
