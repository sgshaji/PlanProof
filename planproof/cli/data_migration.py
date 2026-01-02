"""
Data migration and consistency checking CLI tool.

Usage:
    python -m planproof.cli.data_migration check
    python -m planproof.cli.data_migration backfill-extractions --since 2024-01-01
    python -m planproof.cli.data_migration recalculate-validations --rule-version v2 --submission-ids all
    python -m planproof.cli.data_migration repair-orphans --dry-run

This tool helps maintain data integrity and enables safe production migrations.
"""

import click
import logging
from datetime import datetime
from typing import List, Dict
from planproof.db import Database, Submission, Document, ChangeSet, Application
from planproof.config import get_settings

LOGGER = logging.getLogger(__name__)


@click.group()
def cli():
    """PlanProof data migration and consistency checking tool."""
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


@cli.command()
def check():
    """
    Run all data consistency checks.

    Validates:
    - parent_submission_id integrity
    - ChangeSet linkages
    - Missing extractions
    - Submission version sequences
    """
    click.echo("🔍 Running PlanProof data consistency checks...\n")

    db = Database()
    issues = []

    # Check 1: Orphaned parent_submission_id references
    click.echo("1️⃣  Checking parent_submission_id integrity...")
    orphaned = _check_orphaned_parents(db)
    if orphaned:
        issues.extend(orphaned)
        click.echo(f"   ❌ Found {len(orphaned)} orphaned parent references", err=True)
        for issue in orphaned[:3]:  # Show first 3
            click.echo(f"      • {issue}", err=True)
        if len(orphaned) > 3:
            click.echo(f"      ... and {len(orphaned) - 3} more", err=True)
    else:
        click.echo("   ✅ All parent references valid")

    # Check 2: ChangeSet consistency
    click.echo("\n2️⃣  Checking ChangeSet linkages...")
    changeset_issues = _check_changeset_consistency(db)
    if changeset_issues:
        issues.extend(changeset_issues)
        click.echo(f"   ❌ Found {len(changeset_issues)} changeset issues", err=True)
        for issue in changeset_issues[:3]:
            click.echo(f"      • {issue}", err=True)
    else:
        click.echo("   ✅ All changesets consistent")

    # Check 3: Missing extractions
    click.echo("\n3️⃣  Checking for documents without extractions...")
    missing_extractions = _check_missing_extractions(db)
    if missing_extractions:
        click.echo(f"   ⚠️  Found {len(missing_extractions)} documents without extractions")
        click.echo(f"      Run 'backfill-extractions' to fix")
    else:
        click.echo("   ✅ All documents have extractions")

    # Check 4: Submission version sequences
    click.echo("\n4️⃣  Checking submission version sequences...")
    version_issues = _check_version_sequences(db)
    if version_issues:
        issues.extend(version_issues)
        click.echo(f"   ❌ Found {len(version_issues)} version sequence issues", err=True)
        for issue in version_issues[:3]:
            click.echo(f"      • {issue}", err=True)
    else:
        click.echo("   ✅ All version sequences valid")

    # Summary
    click.echo("\n" + "=" * 70)
    if issues:
        click.echo(f"❌ FAILED: {len(issues)} data integrity issues found\n", err=True)
        click.echo("💡 Recommended actions:")
        if orphaned:
            click.echo("   • Run: data_migration repair-orphans --dry-run")
        if missing_extractions:
            click.echo("   • Run: data_migration backfill-extractions")
        if version_issues:
            click.echo("   • Manual review required for version sequences")
    else:
        click.echo("✅ PASSED: No data integrity issues found")
        click.echo("   Your database is healthy! 🎉")


def _check_orphaned_parents(db: Database) -> List[str]:
    """Check for submissions with invalid parent_submission_id."""
    session = db.get_session()
    issues = []

    try:
        submissions = session.query(Submission).filter(
            Submission.parent_submission_id.isnot(None)
        ).all()

        for sub in submissions:
            parent = session.query(Submission).filter(
                Submission.id == sub.parent_submission_id
            ).first()

            if not parent:
                issues.append(
                    f"Submission {sub.id} (v{sub.submission_version}) "
                    f"has invalid parent_submission_id={sub.parent_submission_id}"
                )
            elif parent.planning_case_id != sub.planning_case_id:
                issues.append(
                    f"Submission {sub.id} parent {sub.parent_submission_id} "
                    f"belongs to different application (cross-app reference)"
                )
    finally:
        session.close()

    return issues


def _check_changeset_consistency(db: Database) -> List[str]:
    """Check ChangeSet.parent_submission_id matches Submission.parent_submission_id."""
    session = db.get_session()
    issues = []

    try:
        changesets = session.query(ChangeSet).all()

        for cs in changesets:
            submission = session.query(Submission).filter(
                Submission.id == cs.submission_id
            ).first()

            if not submission:
                issues.append(f"ChangeSet {cs.id} references missing submission {cs.submission_id}")
            elif submission.parent_submission_id != cs.parent_submission_id:
                issues.append(
                    f"ChangeSet {cs.id} parent mismatch: "
                    f"ChangeSet={cs.parent_submission_id}, Submission={submission.parent_submission_id}"
                )
    finally:
        session.close()

    return issues


def _check_missing_extractions(db: Database) -> List[int]:
    """Find documents without extraction artefacts."""
    session = db.get_session()
    missing = []

    try:
        from planproof.db import Artefact

        documents = session.query(Document).all()
        for doc in documents:
            extraction_artefact = session.query(Artefact).filter(
                Artefact.document_id == doc.id,
                Artefact.artefact_type == "extraction"
            ).first()

            if not extraction_artefact:
                missing.append(doc.id)
    finally:
        session.close()

    return missing


def _check_version_sequences(db: Database) -> List[str]:
    """Check submission version sequences are correct (V0, V1, V2, ...)."""
    session = db.get_session()
    issues = []

    try:
        applications = session.query(Application).all()

        for app in applications:
            submissions = session.query(Submission).filter(
                Submission.planning_case_id == app.id
            ).order_by(Submission.created_at).all()

            if not submissions:
                continue

            versions = [sub.submission_version for sub in submissions]
            expected = [f"V{i}" for i in range(len(submissions))]

            if versions != expected:
                issues.append(
                    f"Application {app.application_ref} has version sequence {versions}, "
                    f"expected {expected}"
                )
    finally:
        session.close()

    return issues


@cli.command()
@click.option('--dry-run', is_flag=True, help='Preview changes without applying them')
def repair_orphans(dry_run):
    """
    Repair orphaned submissions by setting parent_submission_id=NULL.

    This command finds submissions with invalid parent_submission_id references
    and nullifies them to prevent FK constraint errors.
    """
    db = Database()
    orphaned = _check_orphaned_parents(db)

    if not orphaned:
        click.echo("✅ No orphaned submissions found. Database is healthy!")
        return

    click.echo(f"Found {len(orphaned)} orphaned submissions:\n")
    for issue in orphaned:
        click.echo(f"  • {issue}")

    if dry_run:
        click.echo("\n🔍 DRY RUN - No changes will be made")
        click.echo("Run without --dry-run to apply fixes")
        return

    click.echo()
    if not click.confirm("Apply fixes? This will set parent_submission_id=NULL for orphaned submissions"):
        click.echo("Aborted.")
        return

    # Apply fixes
    session = db.get_session()
    try:
        fixed_count = 0
        submissions = session.query(Submission).filter(
            Submission.parent_submission_id.isnot(None)
        ).all()

        for sub in submissions:
            parent = session.query(Submission).filter(
                Submission.id == sub.parent_submission_id
            ).first()

            if not parent or parent.planning_case_id != sub.planning_case_id:
                sub.parent_submission_id = None
                fixed_count += 1
                LOGGER.info(f"Fixed submission {sub.id}")

        session.commit()
        click.echo(f"\n✅ Fixed {fixed_count} orphaned submissions")
    except Exception as e:
        session.rollback()
        click.echo(f"\n❌ Error: {e}", err=True)
    finally:
        session.close()


@cli.command()
@click.option('--since', help='Backfill documents created after this date (YYYY-MM-DD)')
@click.option('--dry-run', is_flag=True, help='Preview without making changes')
def backfill_extractions(since, dry_run):
    """
    Re-extract documents that are missing extractions.

    Useful after Document Intelligence model updates or extraction failures.
    """
    db = Database()
    missing_doc_ids = _check_missing_extractions(db)

    if since:
        # Filter by date
        since_date = datetime.strptime(since, '%Y-%m-%d')
        session = db.get_session()
        try:
            filtered_docs = session.query(Document).filter(
                Document.id.in_(missing_doc_ids),
                Document.uploaded_at >= since_date
            ).all()
            missing_doc_ids = [d.id for d in filtered_docs]
        finally:
            session.close()

    if not missing_doc_ids:
        click.echo("✅ No documents need backfilling")
        return

    click.echo(f"Found {len(missing_doc_ids)} documents to backfill")

    if dry_run:
        click.echo("\n🔍 DRY RUN - would process these document IDs:")
        for doc_id in missing_doc_ids[:10]:
            click.echo(f"  • Document {doc_id}")
        if len(missing_doc_ids) > 10:
            click.echo(f"  ... and {len(missing_doc_ids) - 10} more")
        return

    click.echo("\n⚠️  This will download PDFs and run Document Intelligence extraction")
    click.echo(f"Estimated cost: ~${len(missing_doc_ids) * 0.10:.2f} (Azure charges)")

    if not click.confirm("Proceed with backfill?"):
        click.echo("Aborted.")
        return

    # Import here to avoid circular dependencies
    from planproof.storage import StorageClient
    from planproof.docintel import DocumentIntelligence
    from planproof.pipeline.extract import extract_from_pdf_bytes

    storage = StorageClient()
    docintel = DocumentIntelligence()

    # Process each document
    with click.progressbar(missing_doc_ids, label='Backfilling') as docs:
        success_count = 0
        error_count = 0

        for doc_id in docs:
            try:
                _backfill_single_document(doc_id, db, storage, docintel)
                success_count += 1
            except Exception as e:
                LOGGER.error(f"Failed to backfill document {doc_id}: {e}")
                error_count += 1

    click.echo(f"\n✅ Backfill complete: {success_count} success, {error_count} errors")


def _backfill_single_document(doc_id: int, db: Database, storage, docintel):
    """Backfill extraction for a single document."""
    session = db.get_session()
    try:
        doc = session.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise ValueError(f"Document {doc_id} not found")

        # Download PDF from blob storage
        pdf_bytes = storage.download_blob(doc.blob_uri)

        # Extract
        ingested = {
            "document_id": doc.id,
            "submission_id": doc.submission_id,
            "application_id": doc.application_id
        }

        from planproof.pipeline.extract import extract_from_pdf_bytes

        extraction = extract_from_pdf_bytes(
            pdf_bytes,
            ingested,
            docintel=docintel,
            storage_client=storage,
            db=db,
            write_to_tables=True
        )

        # Save extraction artefact
        extraction_blob = f"backfill/extraction_{doc_id}.json"
        extraction_url = storage.write_json_blob("artefacts", extraction_blob, extraction, overwrite=True)

        db.create_artefact_record(
            document_id=doc_id,
            artefact_type="extraction",
            blob_uri=extraction_url,
            metadata={"backfilled": True, "backfilled_at": datetime.now().isoformat()}
        )

        LOGGER.info(f"Backfilled extraction for document {doc_id}")
    finally:
        session.close()


if __name__ == '__main__':
    cli()
