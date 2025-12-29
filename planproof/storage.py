"""
Azure Blob Storage helpers for PDF uploads and JSON artefact storage.
"""

import os
from typing import Optional, List
from pathlib import Path
from datetime import datetime
from azure.storage.blob import BlobServiceClient, BlobClient
from azure.core.exceptions import AzureError

from planproof.config import get_settings


class StorageClient:
    """Client for Azure Blob Storage operations."""

    def __init__(self, connection_string: Optional[str] = None):
        """Initialize storage client."""
        settings = get_settings()
        conn_str = connection_string or settings.azure_storage_connection_string
        self.client = BlobServiceClient.from_connection_string(conn_str)
        self.inbox_container = settings.azure_storage_container_inbox
        self.artefacts_container = settings.azure_storage_container_artefacts
        self.logs_container = settings.azure_storage_container_logs

    def upload_pdf(self, pdf_path: str, blob_name: Optional[str] = None) -> str:
        """
        Upload a PDF file to the inbox container.

        Args:
            pdf_path: Local path to the PDF file
            blob_name: Optional custom blob name. If not provided, uses filename with timestamp.

        Returns:
            Blob URI (stable identifier for the uploaded file)
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        if not path.suffix.lower() == ".pdf":
            raise ValueError(f"File must be a PDF: {pdf_path}")

        # Generate blob name if not provided
        if blob_name is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            blob_name = f"{path.stem}_{timestamp}{path.suffix}"

        # Ensure blob name doesn't start with /
        blob_name = blob_name.lstrip("/")

        blob_client = self.client.get_blob_client(
            container=self.inbox_container,
            blob=blob_name
        )

        with open(pdf_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)

        return self.get_blob_uri(self.inbox_container, blob_name)

    def upload_pdf_bytes(self, pdf_bytes: bytes, blob_name: str) -> str:
        """
        Upload PDF bytes directly to the inbox container.

        Args:
            pdf_bytes: PDF file content as bytes
            blob_name: Blob name (should include .pdf extension)

        Returns:
            Blob URI
        """
        blob_name = blob_name.lstrip("/")
        blob_client = self.client.get_blob_client(
            container=self.inbox_container,
            blob=blob_name
        )
        blob_client.upload_blob(pdf_bytes, overwrite=True)
        return self.get_blob_uri(self.inbox_container, blob_name)

    def write_artefact(self, artefact_data: dict, artefact_name: str) -> str:
        """
        Write a JSON artefact to the artefacts container.

        Args:
            artefact_data: Dictionary to serialize as JSON
            artefact_name: Name for the artefact blob (should include .json extension)

        Returns:
            Blob URI
        """
        import json

        blob_name = artefact_name.lstrip("/")
        blob_client = self.client.get_blob_client(
            container=self.artefacts_container,
            blob=blob_name
        )

        json_bytes = json.dumps(artefact_data, indent=2, ensure_ascii=False).encode("utf-8")
        blob_client.upload_blob(json_bytes, overwrite=True, content_settings={"content_type": "application/json"})

        return self.get_blob_uri(self.artefacts_container, blob_name)

    def list_blobs(self, container: str, prefix: Optional[str] = None) -> List[str]:
        """
        List blob names in a container, optionally filtered by prefix.

        Args:
            container: Container name (inbox, artefacts, or logs)
            prefix: Optional prefix to filter blob names

        Returns:
            List of blob names (not URIs)
        """
        container_client = self.client.get_container_client(container)
        blobs = container_client.list_blobs(name_starts_with=prefix)
        return [blob.name for blob in blobs]

    def get_blob_uri(self, container: str, blob_name: str) -> str:
        """
        Generate a stable blob URI.

        Args:
            container: Container name
            blob_name: Blob name

        Returns:
            Stable URI in format: azure://{account}/{container}/{blob_name}
        """
        account_name = self.client.account_name
        # Remove leading slash if present
        blob_name = blob_name.lstrip("/")
        return f"azure://{account_name}/{container}/{blob_name}"

    def download_blob(self, container: str, blob_name: str) -> bytes:
        """
        Download a blob as bytes.

        Args:
            container: Container name
            blob_name: Blob name

        Returns:
            Blob content as bytes
        """
        blob_client = self.client.get_blob_client(container=container, blob=blob_name)
        return blob_client.download_blob().readall()

    def blob_exists(self, container: str, blob_name: str) -> bool:
        """
        Check if a blob exists.

        Args:
            container: Container name
            blob_name: Blob name

        Returns:
            True if blob exists, False otherwise
        """
        blob_client = self.client.get_blob_client(container=container, blob=blob_name)
        try:
            blob_client.get_blob_properties()
            return True
        except AzureError:
            return False

