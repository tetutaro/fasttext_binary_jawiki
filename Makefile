.PHONY: binary
binary:
	python3 create_fasttext_binary.py

.PHONY: clean
clean:
	@find . -name '*.pyc' -exec rm -f {} +
	@find . -name '*.pyo' -exec rm -f {} +
	@find . -name '*~' -exec rm -f {} +
	@find . -name '__pycache__' -exec rm -fr {} +
	@find . -name '.DS_Store' -exec rm -f {} +
	@rm -rf dist
	@rm -rf build
	@rm -rf $(PACKAGE).egg-info
	@rm -rf .pytest_cache
	@rm -f .coverage
	@rm -rf htmlcov/

.PHONY: test
test:
	python3 -u -m pytest -v --cov

.PHONY: test-html
test-html:
	python3 -u -m pytest -v --cov --cov-report=html
