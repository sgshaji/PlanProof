"""Tests for document labeller."""

import pytest

from research.synthetic.labeller import DocumentLabeller


class TestDocumentLabeller:
    def test_add_and_query(self, tmp_path):
        label_file = str(tmp_path / "labels.json")
        labeller = DocumentLabeller(label_file)

        labeller.add_real("doc_1", submission_id=1)
        labeller.add_synthetic("doc_2", "conflicting", submission_id=-1)

        assert labeller.is_synthetic("doc_2") is True
        assert labeller.is_synthetic("doc_1") is False
        assert labeller.is_synthetic("doc_99") is False

    def test_get_ids(self, tmp_path):
        label_file = str(tmp_path / "labels.json")
        labeller = DocumentLabeller(label_file)

        labeller.add_real("r1", 1)
        labeller.add_real("r2", 2)
        labeller.add_synthetic("s1", "standard", -1)

        assert set(labeller.get_real_ids()) == {"r1", "r2"}
        assert labeller.get_synthetic_ids() == ["s1"]

    def test_save_and_load(self, tmp_path):
        label_file = str(tmp_path / "labels.json")
        labeller = DocumentLabeller(label_file)
        labeller.add_real("doc_1", 1, notes="Test doc")
        labeller.add_synthetic("doc_2", "incomplete", -1)
        labeller.save()

        # Reload
        labeller2 = DocumentLabeller(label_file)
        assert len(labeller2.labels) == 2
        assert labeller2.labels["doc_1"].source == "bcc_real"
        assert labeller2.labels["doc_1"].notes == "Test doc"
        assert labeller2.labels["doc_2"].variation == "incomplete"

    def test_summary(self, tmp_path):
        label_file = str(tmp_path / "labels.json")
        labeller = DocumentLabeller(label_file)
        labeller.add_real("r1", 1)
        labeller.add_synthetic("s1", "standard", -1)
        labeller.add_synthetic("s2", "conflicting", -2)

        summary = labeller.summary()
        assert summary["total"] == 3
        assert summary["real"] == 1
        assert summary["synthetic"] == 2
        assert summary["by_variation"]["standard"] == 1
        assert summary["by_variation"]["conflicting"] == 1
