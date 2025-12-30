# Contributing to PlanProof

Thank you for your interest in contributing to PlanProof! This guide will help you get started with contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Adding New Features](#adding-new-features)
- [Documentation](#documentation)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of experience level, background, or identity.

### Expected Behavior

- Be respectful and professional
- Provide constructive feedback
- Focus on what is best for the project
- Show empathy towards other community members

### Unacceptable Behavior

- Harassment or discriminatory language
- Trolling or insulting comments
- Public or private harassment
- Publishing others' private information

---

## Getting Started

### Prerequisites

- Python 3.11 or 3.12
- Git
- PostgreSQL 13+ with PostGIS
- Azure account (for testing with real services)

### Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR-USERNAME/planproof.git
cd planproof

# Add upstream remote
git remote add upstream https://github.com/original-org/planproof.git
```

### Setup Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install development dependencies
make install-dev

# Setup database
make db-init

# Run tests to verify setup
make test
```

---

## Development Workflow

### 1. Create a Branch

```bash
# Sync with upstream
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feature/my-awesome-feature
```

**Branch Naming Convention**:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions/improvements

### 2. Make Changes

```bash
# Make your changes
# Run formatters and linters
make format
make lint

# Run tests
make test

# Run all checks
make check
```

### 3. Commit Changes

We follow [Conventional Commits](https://www.conventionalcommits.org/) specification:

```bash
# Format: <type>(<scope>): <description>

# Examples:
git commit -m "feat(validation): add new spatial validation rule"
git commit -m "fix(ui): correct evidence badge rendering"
git commit -m "docs(readme): update installation instructions"
git commit -m "test(pipeline): add integration tests for extract phase"
```

**Types**:
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation only
- `style` - Code style (formatting, missing semicolons, etc.)
- `refactor` - Code refactoring
- `test` - Adding/updating tests
- `chore` - Maintenance tasks

### 4. Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/my-awesome-feature

# Create Pull Request on GitHub
# Fill out the PR template with details
```

---

## Coding Standards

### Python Style Guide

We follow PEP 8 with some modifications:

- **Line Length**: 100 characters
- **Formatter**: Black
- **Linter**: Ruff
- **Type Checker**: MyPy

```bash
# Format code
make format

# Check linting
make lint
```

### Code Structure

```python
"""
Module docstring explaining purpose.

Example:
    from planproof.pipeline import validate
    result = validate.run_validation(rule, fields)
"""

import standard_library
import third_party
import local_modules


def function_name(param1: str, param2: int) -> dict:
    """
    Function docstring in Google style.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Dictionary containing result data
        
    Raises:
        ValueError: If param1 is empty
    """
    if not param1:
        raise ValueError("param1 cannot be empty")
    
    return {"result": param2}


class ClassName:
    """Class docstring explaining purpose."""
    
    def __init__(self, name: str):
        """Initialize the class."""
        self.name = name
    
    def method_name(self) -> None:
        """Method docstring."""
        pass
```

### Imports Organization

```python
# Standard library imports
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

# Third-party imports
import streamlit as st
from sqlalchemy import Column, Integer, String

# Local application imports
from planproof.db import Database
from planproof.pipeline import validate
```

### Naming Conventions

- **Variables/Functions**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private methods**: `_leading_underscore`
- **Files**: `snake_case.py`

### Type Hints

Use type hints for function parameters and return values:

```python
from typing import Dict, List, Optional

def process_field(
    field_name: str,
    field_value: Optional[str],
    confidence: float
) -> Dict[str, any]:
    """Process an extracted field."""
    return {
        "name": field_name,
        "value": field_value,
        "confidence": confidence
    }
```

---

## Testing Guidelines

### Test Structure

```
tests/
├── unit/           # Fast, isolated tests
├── integration/    # End-to-end tests
└── fixtures/       # Test data
```

### Writing Tests

```python
import pytest
from planproof.pipeline import validate


class TestValidation:
    """Test validation logic."""
    
    def test_spatial_validation_pass(self):
        """Test spatial validation with valid data."""
        rule = {"rule_id": "SPATIAL-01", "config": {"min_setback": 1.0}}
        fields = {"setback": 2.0}
        
        result = validate.validate_spatial(rule, fields)
        
        assert result["status"] == "pass"
    
    def test_spatial_validation_fail(self):
        """Test spatial validation with invalid data."""
        rule = {"rule_id": "SPATIAL-01", "config": {"min_setback": 1.0}}
        fields = {"setback": 0.5}
        
        result = validate.validate_spatial(rule, fields)
        
        assert result["status"] == "fail"


@pytest.mark.integration
class TestPipeline:
    """Integration tests for full pipeline."""
    
    def test_full_pipeline(self, test_db):
        """Test complete pipeline execution."""
        # Test implementation
        pass
```

### Running Tests

```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests
make test-integration

# With coverage
make coverage

# Specific test
pytest tests/unit/test_validate.py::TestValidation::test_spatial_validation_pass
```

### Test Coverage

- Aim for **80%+ coverage** for new code
- 100% coverage required for critical validation logic
- Integration tests should cover main user workflows

---

## Pull Request Process

### Before Submitting

1. ✅ Run all tests: `make test`
2. ✅ Check linting: `make lint`
3. ✅ Format code: `make format`
4. ✅ Update documentation if needed
5. ✅ Add tests for new functionality
6. ✅ Update CHANGELOG.md (if applicable)

### PR Template

When creating a PR, include:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] All tests passing

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings generated
```

### Review Process

1. **Automated Checks**: CI/CD runs tests and linting
2. **Code Review**: At least one maintainer reviews
3. **Feedback**: Address comments and suggestions
4. **Approval**: Maintainer approves PR
5. **Merge**: Squash and merge to main

---

## Adding New Features

### Adding a New Business Rule

1. **Update Rule Catalog** (`artefacts/rule_catalog.json`):

```json
{
  "rule_id": "NEW-01",
  "name": "New Rule Name",
  "category": "CUSTOM",
  "severity": "error",
  "message": "Rule failure message",
  "description": "Detailed description",
  "config": {
    "threshold": 10,
    "required_docs": ["site_plan"]
  }
}
```

2. **Implement Validator** (`planproof/pipeline/validate.py`):

```python
def _validate_custom(rule: Rule, extracted_fields: Dict, documents: List, db) -> ValidationCheck:
    """
    Validate custom rule.
    
    Args:
        rule: Rule configuration from catalog
        extracted_fields: Dictionary of extracted fields
        documents: List of associated documents
        db: Database session
        
    Returns:
        ValidationCheck with pass/fail status and evidence
    """
    threshold = rule.config.get("threshold", 10)
    field_value = extracted_fields.get("custom_field")
    
    if field_value is None:
        return ValidationCheck(
            rule_id=rule.rule_id,
            status="warning",
            message="Field not found",
            evidence={}
        )
    
    if field_value > threshold:
        return ValidationCheck(
            rule_id=rule.rule_id,
            status="fail",
            message=f"Value {field_value} exceeds threshold {threshold}",
            evidence={"value": field_value, "threshold": threshold}
        )
    
    return ValidationCheck(
        rule_id=rule.rule_id,
        status="pass",
        message="Validation passed",
        evidence={"value": field_value}
    )
```

3. **Register Validator**:

```python
VALIDATORS = {
    "CUSTOM": _validate_custom,
    # ... existing validators
}
```

4. **Add Tests**:

```python
def test_custom_validation():
    """Test custom validation rule."""
    rule = Rule(rule_id="NEW-01", category="CUSTOM", config={"threshold": 10})
    fields = {"custom_field": 15}
    
    result = _validate_custom(rule, fields, [], None)
    
    assert result.status == "fail"
```

### Adding a New UI Page

1. **Create Page File** (`planproof/ui/pages/my_page.py`):

```python
import streamlit as st


def render():
    """Render my new page."""
    st.title("My New Page")
    
    st.write("Content goes here")
```

2. **Register in Navigation** (`planproof/ui/main.py`):

```python
pages = {
    "Upload": upload.render,
    "My Page": my_page.render,  # Add here
    # ... existing pages
}
```

---

## Documentation

### Code Documentation

- Add docstrings to all public functions and classes
- Use Google-style docstrings
- Include examples for complex functions

### README Updates

- Update README.md if adding user-facing features
- Keep examples up-to-date
- Update feature list

### API Documentation

- Document new API endpoints in `docs/API.md`
- Include request/response examples
- Document error cases

---

## Getting Help

- **Issues**: Check existing issues or create a new one
- **Discussions**: Use GitHub Discussions for questions
- **Email**: team@planproof.com

---

## Recognition

Contributors will be recognized in:
- GitHub contributors page
- CHANGELOG.md for significant contributions
- Project documentation

Thank you for contributing to PlanProof! 🎉
