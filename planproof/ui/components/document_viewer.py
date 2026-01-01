"""
Document viewer component with evidence navigation.

Renders PDF pages as images with bounding box highlighting and page navigation.
"""

import streamlit as st
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import io

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    try:
        from pdf2image import convert_from_path
        PDF2IMAGE_AVAILABLE = True
    except ImportError:
        PDF2IMAGE_AVAILABLE = False

from PIL import Image, ImageDraw


def display_pdf_page(pdf_path: str, page_number: int = 1) -> None:
    """Render a single PDF page as an image."""
    page_image = _render_page(pdf_path, page_number)
    if page_image:
        st.image(page_image)
    else:
        st.warning("Unable to render PDF page.")


def render_document_viewer(
    document_path: str,
    page_number: int = 1,
    bbox: Optional[Dict[str, float]] = None,
    document_id: Optional[int] = None,
    zoom_level: str = "fit-width"
) -> None:
    """
    Render PDF document viewer with optional bounding box highlighting.
    
    Args:
        document_path: Path to PDF file
        page_number: Page number to display (1-indexed)
        bbox: Optional bounding box dict with keys: x, y, width, height (normalized 0-1)
        document_id: Optional document ID for session state
        zoom_level: Zoom level - "fit-width", "fit-height", "actual-size"
    """
    if not Path(document_path).exists():
        st.error(f"Document not found: {document_path}")
        return
    
    # Initialize session state for this document
    viewer_key = f"viewer_{document_id}" if document_id else "viewer_default"
    if viewer_key not in st.session_state:
        st.session_state[viewer_key] = {
            "current_page": page_number,
            "zoom_level": zoom_level
        }
    
    viewer_state = st.session_state[viewer_key]
    
    # Get total pages
    total_pages = _get_page_count(document_path)
    
    if total_pages == 0:
        st.error("Could not read PDF document")
        return
    
    # Page navigation controls
    col1, col2, col3, col4, col5 = st.columns([1, 1, 3, 1, 1])
    
    with col1:
        if st.button("◀ Prev", key=f"{viewer_key}_prev", disabled=viewer_state["current_page"] <= 1):
            viewer_state["current_page"] = max(1, viewer_state["current_page"] - 1)
            st.rerun()
    
    with col2:
        if st.button("Next ▶", key=f"{viewer_key}_next", disabled=viewer_state["current_page"] >= total_pages):
            viewer_state["current_page"] = min(total_pages, viewer_state["current_page"] + 1)
            st.rerun()
    
    with col3:
        new_page = st.number_input(
            "Page",
            min_value=1,
            max_value=total_pages,
            value=viewer_state["current_page"],
            key=f"{viewer_key}_page_input",
            label_visibility="collapsed"
        )
        if new_page != viewer_state["current_page"]:
            viewer_state["current_page"] = new_page
            st.rerun()
        
        st.caption(f"Page {viewer_state['current_page']} of {total_pages}")
    
    with col4:
        zoom_options = ["fit-width", "fit-height", "actual-size"]
        new_zoom = st.selectbox(
            "Zoom",
            zoom_options,
            index=zoom_options.index(viewer_state["zoom_level"]),
            key=f"{viewer_key}_zoom",
            label_visibility="collapsed"
        )
        if new_zoom != viewer_state["zoom_level"]:
            viewer_state["zoom_level"] = new_zoom
            st.rerun()
    
    # Render page
    try:
        page_image = _render_page(
            document_path,
            viewer_state["current_page"],
            bbox if viewer_state["current_page"] == page_number else None,
            viewer_state["zoom_level"]
        )
        
        if page_image:
            st.image(page_image, use_container_width=(viewer_state["zoom_level"] == "fit-width"))
        else:
            st.error("Could not render page")
    
    except Exception as e:
        st.error(f"Error rendering page: {str(e)}")


def _get_page_count(pdf_path: str) -> int:
    """Get total number of pages in PDF."""
    try:
        if PYMUPDF_AVAILABLE:
            doc = fitz.open(pdf_path)
            count = len(doc)
            doc.close()
            return count
        elif PDF2IMAGE_AVAILABLE:
            from pdf2image import pdfinfo_from_path
            info = pdfinfo_from_path(pdf_path)
            return info.get("Pages", 0)
        else:
            return 0
    except Exception:
        return 0


def _render_page(
    pdf_path: str,
    page_number: int,
    bbox: Optional[Dict[str, float]] = None,
    zoom_level: str = "fit-width"
) -> Optional[Image.Image]:
    """
    Render a single PDF page as an image with optional bounding box.
    
    Args:
        pdf_path: Path to PDF file
        page_number: Page number (1-indexed)
        bbox: Optional bounding box dict with keys: x, y, width, height (normalized 0-1)
        zoom_level: Zoom level
    
    Returns:
        PIL Image or None
    """
    try:
        if PYMUPDF_AVAILABLE:
            return _render_page_pymupdf(pdf_path, page_number, bbox, zoom_level)
        elif PDF2IMAGE_AVAILABLE:
            return _render_page_pdf2image(pdf_path, page_number, bbox, zoom_level)
        else:
            return None
    except Exception as e:
        st.error(f"Error rendering page: {str(e)}")
        return None


def _render_page_pymupdf(
    pdf_path: str,
    page_number: int,
    bbox: Optional[Dict[str, float]] = None,
    zoom_level: str = "fit-width"
) -> Optional[Image.Image]:
    """Render page using PyMuPDF."""
    doc = fitz.open(pdf_path)
    
    if page_number < 1 or page_number > len(doc):
        doc.close()
        return None
    
    page = doc[page_number - 1]  # 0-indexed
    
    # Set zoom/DPI
    zoom_map = {
        "fit-width": 2.0,
        "fit-height": 2.0,
        "actual-size": 1.5
    }
    zoom = zoom_map.get(zoom_level, 2.0)
    mat = fitz.Matrix(zoom, zoom)
    
    # Render page to pixmap
    pix = page.get_pixmap(matrix=mat)
    
    # Convert to PIL Image
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    
    doc.close()
    
    # Draw bounding box if provided
    if bbox:
        img = _draw_bbox(img, bbox)
    
    return img


def _render_page_pdf2image(
    pdf_path: str,
    page_number: int,
    bbox: Optional[Dict[str, float]] = None,
    zoom_level: str = "fit-width"
) -> Optional[Image.Image]:
    """Render page using pdf2image."""
    from pdf2image import convert_from_path
    
    # Set DPI based on zoom
    dpi_map = {
        "fit-width": 200,
        "fit-height": 200,
        "actual-size": 150
    }
    dpi = dpi_map.get(zoom_level, 200)
    
    # Convert single page
    images = convert_from_path(
        pdf_path,
        dpi=dpi,
        first_page=page_number,
        last_page=page_number
    )
    
    if not images:
        return None
    
    img = images[0]
    
    # Draw bounding box if provided
    if bbox:
        img = _draw_bbox(img, bbox)
    
    return img


def _draw_bbox(img: Image.Image, bbox: Dict[str, float]) -> Image.Image:
    """
    Draw bounding box on image.
    
    Args:
        img: PIL Image
        bbox: Dict with keys: x, y, width, height (normalized 0-1 or absolute pixels)
    
    Returns:
        Image with bounding box drawn
    """
    draw = ImageDraw.Draw(img)
    
    width, height = img.size
    
    # Check if bbox is normalized (0-1) or absolute
    x = bbox.get("x", 0)
    y = bbox.get("y", 0)
    w = bbox.get("width", 0)
    h = bbox.get("height", 0)
    
    # If values are between 0 and 1, treat as normalized
    if x <= 1 and y <= 1 and w <= 1 and h <= 1:
        x = x * width
        y = y * height
        w = w * width
        h = h * height
    
    # Draw rectangle
    left = x
    top = y
    right = x + w
    bottom = y + h
    
    # Draw bounding box with highlight
    draw.rectangle(
        [left, top, right, bottom],
        outline="red",
        width=3
    )
    
    # Draw semi-transparent overlay
    overlay = Image.new("RGBA", img.size, (255, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle(
        [left, top, right, bottom],
        fill=(255, 255, 0, 50)  # Yellow with transparency
    )
    
    # Composite overlay onto image
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay)
    img = img.convert("RGB")
    
    return img


def render_evidence_link(
    evidence: Dict[str, Any],
    document_path: str,
    document_id: int,
    label: str = "View Evidence"
) -> None:
    """
    Render a clickable evidence link that opens the document viewer.
    
    Args:
        evidence: Evidence dict with page, bbox, snippet
        document_path: Path to PDF file
        document_id: Document ID
        label: Button label
    """
    page = evidence.get("page", 1)
    bbox = evidence.get("bbox", None)
    snippet = evidence.get("snippet", "")
    
    # Create expander for evidence
    with st.expander(f"📄 {label} (Page {page})"):
        if snippet:
            st.code(snippet, language="text")
        
        if st.button(f"Open Document at Page {page}", key=f"evidence_{document_id}_{page}"):
            # Store viewer state to open at specific page
            viewer_key = f"viewer_{document_id}"
            if viewer_key not in st.session_state:
                st.session_state[viewer_key] = {}
            st.session_state[viewer_key]["current_page"] = page
            st.session_state[viewer_key]["zoom_level"] = "fit-width"
            st.session_state["show_viewer"] = True
            st.session_state["viewer_document_path"] = document_path
            st.session_state["viewer_document_id"] = document_id
            st.session_state["viewer_page"] = page
            st.session_state["viewer_bbox"] = bbox
            st.rerun()


def check_pdf_library() -> Tuple[bool, str]:
    """
    Check if PDF rendering library is available.
    
    Returns:
        (available, library_name)
    """
    if PYMUPDF_AVAILABLE:
        return True, "PyMuPDF"
    elif PDF2IMAGE_AVAILABLE:
        return True, "pdf2image"
    else:
        return False, "None"
