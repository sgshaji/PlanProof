from pathlib import Path
from planproof.rules.catalog import write_rule_catalog_json

if __name__ == "__main__":
    md = Path("validation_requirements.md")
    if not md.exists():
        print(f"ERROR: {md} not found. Please create it first.")
        exit(1)
    
    out = Path("artefacts/rule_catalog.json")
    payload = write_rule_catalog_json(md, out)
    print(f"OK: Wrote {payload['rule_count']} rules to {out}")

