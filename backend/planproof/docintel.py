"""
Azure Document Intelligence wrapper for document analysis.
"""

from typing import Dict, List, Any, Optional
import logging
import time

from azure.core.exceptions import AzureError, ServiceRequestError, ServiceResponseError

from planproof.config import get_settings


class DocumentIntelligence:
    """Wrapper around Azure Document Intelligence for document analysis."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        """Initialize Document Intelligence client.

        Args:
            endpoint: Azure Document Intelligence endpoint URL
            api_key: Azure Document Intelligence API key
            timeout: Timeout in seconds for operations (default: 300)
        """
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        from azure.core.credentials import AzureKeyCredential
        settings = get_settings()
        endpoint = endpoint or settings.azure_docintel_endpoint
        api_key = api_key or settings.azure_docintel_key

        self.client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(api_key)
        )
        self._settings = settings
        self._logger = logging.getLogger(__name__)
        self._timeout = timeout or 300  # Default 5 minute timeout for document analysis

    def _with_retry(self, operation_name: str, func, *args, **kwargs):
        """Execute a function with exponential backoff retry logic.

        Args:
            operation_name: Name of the operation for logging
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the function call

        Raises:
            RuntimeError: If all retries are exhausted or operation times out
        """
        max_attempts = max(1, self._settings.azure_retry_max_attempts)
        base_delay = max(0.1, self._settings.azure_retry_base_delay_s)
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                return func(*args, **kwargs)
            except ServiceRequestError as exc:
                # Network/connection errors - retriable
                last_error = exc
                error_msg = f"Document Intelligence network error on {operation_name}: {str(exc)}"
                self._logger.warning(error_msg)
                if attempt == max_attempts:
                    raise RuntimeError(f"{error_msg}. Failed after {max_attempts} attempts.") from exc
            except ServiceResponseError as exc:
                # Service errors (500s) - retriable
                last_error = exc
                error_msg = f"Document Intelligence service error on {operation_name}: {str(exc)}"
                self._logger.warning(error_msg)
                if attempt == max_attempts:
                    raise RuntimeError(f"{error_msg}. Failed after {max_attempts} attempts.") from exc
            except AzureError as exc:
                # Other Azure errors - may or may not be retriable
                last_error = exc
                error_msg = f"Document Intelligence Azure error on {operation_name}: {str(exc)}"
                self._logger.warning(error_msg)
                if attempt == max_attempts:
                    raise RuntimeError(f"{error_msg}. Failed after {max_attempts} attempts.") from exc
            except Exception as exc:
                # Unexpected errors - don't retry
                error_msg = f"Unexpected error in Document Intelligence {operation_name}: {str(exc)}"
                self._logger.error(error_msg, exc_info=True)
                raise RuntimeError(error_msg) from exc

            # Calculate delay and sleep before retry
            delay = base_delay * (2 ** (attempt - 1))
            self._logger.warning(
                f"Retrying {operation_name} (attempt {attempt}/{max_attempts}) after {delay}s delay"
            )
            time.sleep(delay)

        # Should not reach here, but just in case
        raise last_error

    def analyze_document(
        self,
        pdf_bytes: bytes,
        model: str = "prebuilt-layout",
        pages: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a document using Document Intelligence with timeout handling.

        Args:
            pdf_bytes: PDF file content as bytes
            model: Model to use (default: "prebuilt-layout")
            pages: Optional list of page ranges to analyze

        Returns:
            Normalized dictionary with:
            - text_blocks: List of text blocks with content and bounding boxes
            - tables: List of tables with cells and content
            - page_anchors: Page number to content mapping
            - metadata: Document metadata (page count, model used, etc.)

        Raises:
            RuntimeError: If analysis fails or times out
        """
        try:
            # Use the correct API signature for azure-ai-documentintelligence 1.0.2
            # body is a required positional argument, content_type goes in headers
            from io import BytesIO
            import threading

            poller = self._with_retry(
                "begin_analyze_document_bytes",
                self.client.begin_analyze_document,
                model_id=model,
                body=BytesIO(pdf_bytes),
                content_type="application/pdf",
                pages=pages,
            )

            # Poll with timeout
            start_time = time.time()
            while not poller.done():
                elapsed = time.time() - start_time
                if elapsed > self._timeout:
                    self._logger.error(f"Document Intelligence analysis timed out after {self._timeout}s")
                    raise RuntimeError(
                        f"Document Intelligence analysis timed out after {self._timeout}s. "
                        f"Consider increasing timeout for large documents or using parallel analysis."
                    )
                time.sleep(1)  # Poll every second

            result = poller.result()
            return self._normalize_result(result, model)

        except RuntimeError:
            # Re-raise RuntimeError from timeout or retry logic
            raise
        except AzureError as e:
            error_msg = f"Document Intelligence analysis failed: {str(e)}"
            self._logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error during document analysis: {str(e)}"
            self._logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e

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

            poller = self._with_retry(
                "begin_analyze_document_url",
                self.client.begin_analyze_document,
                model_id=model,
                analyze_request=AnalyzeDocumentRequest(url_source=document_url),
                pages=pages,
            )
            result = self._with_retry("poll_analyze_document_url", poller.result)
            return self._normalize_result(result, model)
        except AzureError as e:
            raise RuntimeError(f"Document Intelligence analysis failed: {str(e)}") from e

    def analyze_document_parallel(
        self,
        pdf_bytes: bytes,
        model: str = "prebuilt-layout",
        pages_per_batch: int = 5,
        max_workers: int = 4,
        document_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a document by splitting into page ranges and running in parallel.

        When a SAS URL is available, use URL-based requests with page filters to
        avoid re-uploading the full PDF for each batch (network-light, API-side
        fetch). If a URL isn't available, split the PDF into per-range files and
        upload only those bytes (CPU-heavy locally, lower upload volume).

        Args:
            pdf_bytes: PDF file content as bytes
            model: Model to use
            pages_per_batch: Number of pages per analysis request
            max_workers: Number of parallel workers
            document_url: Optional SAS URL for URL-based parallel analysis

        Returns:
            Normalized dictionary merged from all page ranges
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        page_count = self._get_pdf_page_count(pdf_bytes)
        if page_count <= pages_per_batch:
            if document_url:
                return self.analyze_document_url(document_url, model=model)
            return self.analyze_document(pdf_bytes, model=model)

        page_ranges = []
        for start in range(1, page_count + 1, pages_per_batch):
            end = min(start + pages_per_batch - 1, page_count)
            page_ranges.append((start, end))

        results = []
        if document_url:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(
                        self.analyze_document_url,
                        document_url,
                        model,
                        [f"{start}-{end}"]
                    ): (start, end)
                    for start, end in page_ranges
                }
                for future in as_completed(futures):
                    results.append(future.result())
        else:
            split_pdfs = self._split_pdf_by_ranges(pdf_bytes, page_ranges)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self.analyze_document, split_pdf, model): (start, end)
                    for (start, end), split_pdf in zip(page_ranges, split_pdfs)
                }
                for future in as_completed(futures):
                    start, _end = futures[future]
                    result = self._offset_result_pages(future.result(), start - 1)
                    results.append(result)

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

    @staticmethod
    def _split_pdf_by_ranges(
        pdf_bytes: bytes,
        page_ranges: List[tuple]
    ) -> List[bytes]:
        """Split a PDF into per-range PDF byte blobs."""
        from pypdf import PdfReader, PdfWriter
        from io import BytesIO

        reader = PdfReader(BytesIO(pdf_bytes))
        split_bytes = []
        for start, end in page_ranges:
            writer = PdfWriter()
            for page_index in range(start - 1, end):
                writer.add_page(reader.pages[page_index])
            buffer = BytesIO()
            writer.write(buffer)
            split_bytes.append(buffer.getvalue())

        return split_bytes

    @staticmethod
    def _offset_result_pages(result: Dict[str, Any], page_offset: int) -> Dict[str, Any]:
        """Offset page numbers in a normalized result."""
        if page_offset == 0:
            return result
        for block in result.get("text_blocks", []):
            if block.get("page_number"):
                block["page_number"] += page_offset
        for table in result.get("tables", []):
            if table.get("page_number"):
                table["page_number"] += page_offset
        return result

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
