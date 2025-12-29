# Contributing to PlanProof

## Development Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up `.env` file with your Azure credentials
5. Run database migrations:
   ```bash
   python scripts/enable_postgis.py
   python scripts/add_content_hash_column.py
   ```

## Code Style

- Follow PEP 8
- Use type hints where possible
- Add docstrings to all public functions
- Keep functions focused and small

## Testing

Before submitting changes:
1. Run smoke tests: `python scripts/smoke_test.py`
2. Test single PDF: `python main.py single-pdf --pdf <test_file>`
3. Verify no regressions in batch processing

## Adding Features

1. **New Fields**: Add to `field_mapper.py` with evidence tracking
2. **New Rules**: Edit `validation_requirements.md`, rebuild catalog
3. **New Document Types**: Update `DOC_TYPE_HINTS` and `DOC_FIELD_OWNERSHIP`

## Commit Messages

Use clear, descriptive commit messages:
- `Add field mapper for site_address extraction`
- `Fix phone number regex to exclude dates`
- `Update LLM gating logic for field ownership`

## Pull Requests

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Update documentation if needed
5. Submit PR with clear description

