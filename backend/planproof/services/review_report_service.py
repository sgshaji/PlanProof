"""
Generate PDF reports for completed HIL reviews.
"""

from __future__ import annotations

from io import BytesIO
from typing import Optional
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from planproof.db import (
    Database,
    Run,
    ValidationCheck,
    ReviewDecision,
    Application,
)


def generate_review_report_pdf(run_id: int, db: Optional[Database] = None) -> bytes:
    """
    Generate a PDF review report for a reviewed run.

    Raises:
        ValueError: If the run does not exist or is not reviewed.
    """
    if db is None:
        db = Database()

    session = db.get_session()
    try:
        run = session.query(Run).filter(Run.id == run_id).first()
        if not run:
            raise ValueError("Run not found")
        if run.status != "reviewed":
            raise ValueError("Run has not been reviewed")

        application = None
        if run.application_id:
            application = session.query(Application).filter(
                Application.id == run.application_id
            ).first()

        documents = list(run.documents) if run.documents else []
        if not documents and run.document_id:
            from planproof.db import Document
            document = session.query(Document).filter(Document.id == run.document_id).first()
            if document:
                documents = [document]

        document_ids = [doc.id for doc in documents]
        checks = []
        if document_ids:
            checks = session.query(ValidationCheck).filter(
                ValidationCheck.document_id.in_(document_ids)
            ).all()

        decisions = session.query(ReviewDecision).filter(
            ReviewDecision.run_id == run_id
        ).all()

        decisions_by_check = {decision.validation_check_id: decision for decision in decisions}

        summary = {
            "pass": 0,
            "fail": 0,
            "needs_review": 0,
            "warning": 0,
        }
        for check in checks:
            status = check.status.value if hasattr(check.status, "value") else str(check.status)
            if status == "pass":
                summary["pass"] += 1
            elif status == "fail":
                summary["fail"] += 1
            elif status == "warning":
                summary["warning"] += 1
            else:
                summary["needs_review"] += 1

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()

        elements = []
        elements.append(Paragraph("HIL Review Report", styles["Title"]))
        elements.append(Spacer(1, 12))

        metadata_rows = [
            ["Run ID", str(run.id)],
            ["Status", run.status],
            ["Completed at", run.completed_at.isoformat() if run.completed_at else "N/A"],
            ["Generated at", datetime.utcnow().isoformat()],
            ["Application Ref", application.application_ref if application else "N/A"],
            ["Applicant", application.applicant_name if application else "N/A"],
        ]
        metadata_table = Table(metadata_rows, hAlign="LEFT", colWidths=[120, 360])
        metadata_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        elements.append(metadata_table)
        elements.append(Spacer(1, 16))

        elements.append(Paragraph("Validation Summary", styles["Heading2"]))
        summary_table = Table(
            [
                ["Pass", "Fail", "Warning", "Needs Review"],
                [
                    str(summary["pass"]),
                    str(summary["fail"]),
                    str(summary["warning"]),
                    str(summary["needs_review"]),
                ],
            ],
            hAlign="LEFT",
        )
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ]
            )
        )
        elements.append(summary_table)
        elements.append(Spacer(1, 16))

        elements.append(Paragraph("Review Decisions", styles["Heading2"]))
        if decisions:
            decision_rows = [["Check ID", "Rule", "Decision", "Reviewer", "Comment"]]
            for decision in decisions:
                check = next((c for c in checks if c.id == decision.validation_check_id), None)
                decision_rows.append(
                    [
                        str(decision.validation_check_id),
                        check.rule_id_string if check else "N/A",
                        decision.decision,
                        decision.reviewer_id,
                        decision.comment or "",
                    ]
                )
            decision_table = Table(decision_rows, hAlign="LEFT", colWidths=[60, 110, 70, 120, 180])
            decision_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            elements.append(decision_table)
        else:
            elements.append(Paragraph("No review decisions recorded.", styles["BodyText"]))

        elements.append(Spacer(1, 16))
        elements.append(Paragraph("Findings Overview", styles["Heading2"]))
        if checks:
            finding_rows = [["Check ID", "Rule", "Status", "Severity", "Message", "Decision"]]
            for check in checks:
                status = check.status.value if hasattr(check.status, "value") else str(check.status)
                decision = decisions_by_check.get(check.id)
                message = check.explanation or ""
                finding_rows.append(
                    [
                        str(check.id),
                        check.rule_id_string or str(check.rule_id),
                        status,
                        check.rule.severity if check.rule and check.rule.severity else "info",
                        Paragraph(message, styles["BodyText"]),
                        decision.decision if decision else "N/A",
                    ]
                )
            finding_table = Table(
                finding_rows,
                hAlign="LEFT",
                colWidths=[55, 90, 55, 60, 185, 60],
            )
            finding_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            elements.append(finding_table)
        else:
            elements.append(Paragraph("No findings recorded for this run.", styles["BodyText"]))

        doc.build(elements)
        return buffer.getvalue()
    finally:
        session.close()
