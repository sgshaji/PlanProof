"""
Diagnostic script to analyze a run and show what went wrong.
"""
import sys
import json
from pathlib import Path

def diagnose_run(run_id):
    """Diagnose issues with a specific run."""
    run_dir = Path(f"./runs/{run_id}")
    
    if not run_dir.exists():
        print(f"❌ Run {run_id} directory not found")
        return
    
    print(f"🔍 Diagnosing Run {run_id}")
    print("=" * 60)
    
    # Check inputs
    inputs_dir = run_dir / "inputs"
    outputs_dir = run_dir / "outputs"
    
    if inputs_dir.exists():
        input_files = list(inputs_dir.glob("*.pdf"))
        print(f"\n📁 Input Files ({len(input_files)}):")
        for f in input_files:
            print(f"   - {f.name} ({f.stat().st_size / 1024:.1f} KB)")
    
    # Check outputs
    if outputs_dir.exists():
        extraction_files = list(outputs_dir.glob("extraction_*.json"))
        validation_files = list(outputs_dir.glob("validation_*.json"))
        error_files = list(outputs_dir.glob("error_*.txt"))
        llm_files = list(outputs_dir.glob("llm_*.json"))
        
        print(f"\n📊 Output Files:")
        print(f"   - Extractions: {len(extraction_files)}")
        print(f"   - Validations: {len(validation_files)}")
        print(f"   - Errors: {len(error_files)}")
        print(f"   - LLM Notes: {len(llm_files)}")
        
        # Check for missing validations
        if len(extraction_files) > len(validation_files):
            print(f"\n⚠️  ISSUE FOUND: {len(extraction_files) - len(validation_files)} validation(s) missing!")
            extraction_ids = {f.stem.split('_')[1] for f in extraction_files}
            validation_ids = {f.stem.split('_')[1] for f in validation_files}
            missing_ids = extraction_ids - validation_ids
            print(f"   Missing validation for document IDs: {', '.join(missing_ids)}")
        
        # Show error details
        if error_files:
            print(f"\n❌ Errors Found:")
            for error_file in error_files:
                print(f"\n   📄 {error_file.name}:")
                with open(error_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Show first 500 chars of error
                    lines = content.split('\n')
                    for line in lines[:15]:  # First 15 lines
                        print(f"      {line}")
                    if len(lines) > 15:
                        print(f"      ... ({len(lines) - 15} more lines)")
        
        # Check summary
        summary_file = outputs_dir / "summary.json"
        if summary_file.exists():
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary = json.load(f)
            print(f"\n📋 Summary:")
            print(f"   Status: {summary.get('status', 'unknown')}")
            print(f"   Total: {summary.get('summary', {}).get('total_documents', 0)}")
            print(f"   Processed: {summary.get('summary', {}).get('processed', 0)}")
            print(f"   Errors: {summary.get('summary', {}).get('errors', 0)}")
            print(f"   LLM Calls: {summary.get('llm_calls_per_run', 0)}")
    
    print("\n" + "=" * 60)
    print("✅ Diagnosis complete")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python diagnose_run.py <run_id>")
        sys.exit(1)
    
    run_id = sys.argv[1]
    diagnose_run(run_id)
