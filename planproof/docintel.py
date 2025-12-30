"""
Azure Document Intelligence wrapper for document analysis.
"""

from typing import Dict, List, Any, Optional

from azure.core.exceptions import AzureError

from planproof.config import get_settings


class DocumentIntelligence:
    """Wrapper around Azure Document Intelligence for document analysis."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """Initialize Document Intelligence client."""
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        from azure.core.credentials import AzureKeyCredential
        settings = get_settings()
        endpoint = endpoint or settings.azure_docintel_endpoint
        api_key = api_key or settings.azure_docintel_key

        self.client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(api_key)
        )

    def analyze_document(
        self,
        pdf_bytes: bytes,
        model: str = "prebuilt-layout",
        pages: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a document using Document Intelligence.

        Args:
            pdf_bytes: PDF file content as bytes
            model: Model to use (default: "prebuilt-layout")

        Returns:
            Normalized dictionary with:
            - text_blocks: List of text blocks with content and bounding boxes
            - tables: List of tables with cells and content
            - page_anchors: Page number to content mapping
            - metadata: Document metadata (page count, model used, etc.)
        """
        try:
            # Use the correct API signature for azure-ai-documentintelligence 1.0.2
            # body is a required positional argument, content_type goes in headers
            from io import BytesIO
            
            poller = self.client.begin_analyze_document(
                model_id=model,
                body=BytesIO(pdf_bytes),
                content_type="application/pdf",
                pages=pages
            )
            result = poller.result()
            return self._normalize_result(result, model)

        except AzureError as e:
            raise RuntimeError(f"Document Intelligence analysis failed: {str(e)}") from e

    def analyze_document_url(
        self,
        document_url: str,
        model: str = "prebuilt-layout",
        pages: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a document using a URL source.

        Args:
            document_url: SAS URL for the document
            model: Model to use (default: "prebuilt-layout")
            pages: Optional list of page ranges to analyze

        Returns:
            Normalized dictionary matching analyze_document output
        """
        try:
            from azure.ai.documentintelligence import AnalyzeDocumentRequest

            poller = self.client.begin_analyze_document(
                model_id=model,
                analyze_request=AnalyzeDocumentRequest(url_source=document_url),
                pages=pages
            )
            result = poller.result()
            return self._normalize_result(result, model)
        except AzureError as e:
            raise RuntimeError(f"Document Intelligence analysis failed: {str(e)}") from e

    def analyze_document_parallel(
        self,
        pdf_bytes: bytes,
        model: str = "prebuilt-layout",
        pages_per_batch: int = 5,
        max_workers: int = 4
    ) -> Dict[str, Any]:
        """
        Analyze a document by splitting into page ranges and running in parallel.

        Args:
            pdf_bytes: PDF file content as bytes
            model: Model to use
            pages_per_batch: Number of pages per analysis request
            max_workers: Number of parallel workers

        Returns:
            Normalized dictionary merged from all page ranges
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        page_count = self._get_pdf_page_count(pdf_bytes)
        if page_count <= pages_per_batch:
            return self.analyze_document(pdf_bytes, model=model)

        page_ranges = []
        for start in range(1, page_count + 1, pages_per_batch):
            end = min(start + pages_per_batch - 1, page_count)
            page_ranges.append(f"{start}-{end}")

        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.analyze_document, pdf_bytes, model, [page_range]): page_range
                for page_range in page_ranges
            }
            for future in as_completed(futures):
                results.append(future.result())

        return self._merge_results(results, model, page_count)

    @staticmethod
    def select_model(document_type: Optional[str], default: str = "prebuilt-layout") -> str:
        """
        Select a Doc Intelligence model based on document type.

        Use prebuilt-read for text-heavy documents where layout isn't required.
        """
        if not document_type:
            return default
        text_only_types = {"design_statement", "heritage", "site_notice"}
        if document_type in text_only_types:
            return "prebuilt-read"
        return default

    def _normalize_result(self, result: Any, model: str) -> Dict[str, Any]:
        """Normalize Document Intelligence result into a consistent dictionary."""
        normalized = {
            "text_blocks": [],
            "tables": [],
            "page_anchors": {},
            "metadata": {
                "model": model,
                "page_count": len(result.pages) if result.pages else 0,
                "analyzed_at": None  # Will be set by caller if needed
            }
        }

        if result.paragraphs:
            for para in result.paragraphs:
                if para.content:
                    normalized["text_blocks"].append({
                        "content": para.content,
                        "page_number": para.bounding_regions[0].page_number if para.bounding_regions else None,
                        "bounding_box": self._extract_bounding_box(para.bounding_regions[0]) if para.bounding_regions else None,
                        "role": getattr(para, "role", None)
                    })

        if result.tables:
            for table in result.tables:
                table_data = {
                    "row_count": table.row_count,
                    "column_count": table.column_count,
                    "cells": [],
                    "page_number": table.bounding_regions[0].page_number if table.bounding_regions else None,
                    "bounding_box": self._extract_bounding_box(table.bounding_regions[0]) if table.bounding_regions else None
                }

                if table.cells:
                    for cell in table.cells:
                        table_data["cells"].append({
                            "row_index": cell.row_index,
                            "column_index": cell.column_index,
                            "content": cell.content or "",
                            "kind": getattr(cell, "kind", None)
                        })

                normalized["tables"].append(table_data)

        for page_num in range(1, normalized["metadata"]["page_count"] + 1):
            page_text_blocks = [
                block for block in normalized["text_blocks"]
                if block["page_number"] == page_num
            ]
            page_tables = [
                table for table in normalized["tables"]
                if table["page_number"] == page_num
            ]
            normalized["page_anchors"][page_num] = {
                "text_blocks": page_text_blocks,
                "tables": page_tables
            }

        return normalized

    @staticmethod
    def _merge_results(
        results: List[Dict[str, Any]],
        model: str,
        page_count: int
    ) -> Dict[str, Any]:
        """Merge normalized results from parallel page ranges."""
        merged = {
            "text_blocks": [],
            "tables": [],
            "page_anchors": {},
            "metadata": {
                "model": model,
                "page_count": page_count,
                "analyzed_at": None
            }
        }

        for result in results:
            merged["text_blocks"].extend(result.get("text_blocks", []))
            merged["tables"].extend(result.get("tables", []))

        for page_num in range(1, page_count + 1):
            page_text_blocks = [
                block for block in merged["text_blocks"]
                if block.get("page_number") == page_num
            ]
            page_tables = [
                table for table in merged["tables"]
                if table.get("page_number") == page_num
            ]
            merged["page_anchors"][page_num] = {
                "text_blocks": page_text_blocks,
                "tables": page_tables
            }

        return merged

    @staticmethod
    def _get_pdf_page_count(pdf_bytes: bytes) -> int:
        """Get PDF page count using pypdf."""
        from pypdf import PdfReader
        from io import BytesIO

        reader = PdfReader(BytesIO(pdf_bytes))
        return len(reader.pages)

    def _extract_bounding_box(self, bounding_region) -> Optional[Dict[str, float]]:
        """Extract bounding box coordinates from a bounding region."""
        if not bounding_region or not hasattr(bounding_region, "polygon"):
            return None

        polygon = bounding_region.polygon
        if not polygon or len(polygon) < 4:
            return None

        # Extract x, y coordinates (assuming polygon is a list of points)
        # Format: [x1, y1, x2, y2, x3, y3, x4, y4]
        if len(polygon) >= 8:
            return {
                "x1": polygon[0],
                "y1": polygon[1],
                "x2": polygon[2],
                "y2": polygon[3],
                "x3": polygon[4],
                "y3": polygon[5],
                "x4": polygon[6],
                "y4": polygon[7]
            }
        return None

    def get_text_by_page(self, analysis_result: Dict[str, Any], page_number: int) -> str:
        """
        Extract all text from a specific page.

        Args:
            analysis_result: Result from analyze_document()
            page_number: Page number (1-indexed)

        Returns:
            Combined text content from the page
        """
        if page_number not in analysis_result["page_anchors"]:
            return ""

        page_data = analysis_result["page_anchors"][page_number]
        text_parts = []

        # Add text blocks
        for block in page_data["text_blocks"]:
            if block["content"]:
                text_parts.append(block["content"])

        # Add table content
        for table in page_data["tables"]:
            for cell in table["cells"]:
                if cell["content"]:
                    text_parts.append(cell["content"])

        return "\n".join(text_parts)
