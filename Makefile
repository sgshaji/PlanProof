.PHONY: fmt lint test cov

fmt:
	black tests scripts

lint:
	ruff check tests scripts

test:
	pytest

cov:
	pytest --cov=planproof.pipeline.field_mapper --cov=planproof.pipeline.validate --cov=planproof.pipeline.llm_gate --cov-report=term-missing --cov-fail-under=80
