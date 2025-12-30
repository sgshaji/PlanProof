"""
Unit tests for Phase 4: Certificates & Fees Extraction
"""
import pytest
from planproof.pipeline.field_mapper import (
    detect_certificate_type,
    detect_signatures,
    extract_fee_amount,
    detect_fee_exemption
)


def _make_block(text, page=1, idx=0):
    """Helper to create a text block"""
    return {
        "content": text,
        "text": text,
        "page": page,
        "page_number": page,
        "index": idx,
        "bounding_box": {"x": 0, "y": 0, "width": 100, "height": 10}
    }


class TestCertificateDetection:
    """Test ownership certificate type detection"""
    
    def test_certificate_a_sole_owner(self):
        blocks = [_make_block("I certify that I am the sole owner of the land")]
        cert_type, src, conf = detect_certificate_type(blocks)
        assert cert_type == "A"
        assert conf >= 0.7
    
    def test_certificate_a_explicit(self):
        blocks = [_make_block("Certificate A - Ownership: Sole owner of all the land")]
        cert_type, src, conf = detect_certificate_type(blocks)
        assert cert_type == "A"
        assert conf >= 0.9  # Higher confidence with explicit "certificate" mention
    
    def test_certificate_b_notice_given(self):
        blocks = [_make_block("Certificate B: Notice has been given to other owners")]
        cert_type, src, conf = detect_certificate_type(blocks)
        assert cert_type == "B"
        assert conf >= 0.9
    
    def test_certificate_b_some_land(self):
        blocks = [_make_block("I own some of the land but not all")]
        cert_type, src, conf = detect_certificate_type(blocks)
        assert cert_type == "B"
        assert conf >= 0.7
    
    def test_certificate_c_unknown_owner(self):
        blocks = [_make_block("Certificate C: Unable to issue certificate, unknown owner")]
        cert_type, src, conf = detect_certificate_type(blocks)
        assert cert_type == "C"
        assert conf >= 0.9
    
    def test_certificate_d_agricultural(self):
        blocks = [_make_block("Certificate D - Agricultural holding: Agricultural tenant present")]
        cert_type, src, conf = detect_certificate_type(blocks)
        assert cert_type == "D"
        assert conf >= 0.9
    
    def test_no_certificate(self):
        blocks = [_make_block("This is a planning application with no certificate information")]
        cert_type, src, conf = detect_certificate_type(blocks)
        assert cert_type is None
        assert conf == 0.0


class TestSignatureDetection:
    """Test signature presence detection"""
    
    def test_signed_with_certify(self):
        blocks = [
            _make_block("Applicant signature: "),
            _make_block("I hereby certify that this information is correct")
        ]
        sigs = detect_signatures(blocks)
        assert len(sigs) >= 1
        # Should detect signature with "certify" as signed
        signed_sigs = [s for s in sigs if s["is_signed"]]
        assert len(signed_sigs) >= 1
        assert signed_sigs[0]["confidence"] >= 0.7
    
    def test_signed_with_name(self):
        blocks = [_make_block("Signed by: John Smith")]
        sigs = detect_signatures(blocks)
        assert len(sigs) >= 1
        assert sigs[0]["is_signed"] == True
        assert sigs[0]["confidence"] >= 0.8
    
    def test_signed_with_date(self):
        blocks = [
            _make_block("Signature: "),
            _make_block("Date: 15/01/2025")
        ]
        sigs = detect_signatures(blocks)
        assert len(sigs) >= 1
        # Should detect signature with date as signed
        signed_sigs = [s for s in sigs if s["is_signed"]]
        assert len(signed_sigs) >= 1
    
    def test_unsigned_signature_field(self):
        blocks = [_make_block("Signature:")]
        sigs = detect_signatures(blocks)
        # Unsigned signature fields might be detected with low is_signed=False
        # or might not be detected at all (depends on heuristic)
        # Just check we don't get high confidence signed result
        if sigs:
            signed_sigs = [s for s in sigs if s["is_signed"]]
            if signed_sigs:
                assert signed_sigs[0]["confidence"] < 0.6  # Low confidence for unsigned
    
    def test_applicant_signature_type(self):
        blocks = [_make_block("Applicant signature: I hereby certify")]
        sigs = detect_signatures(blocks)
        assert len(sigs) >= 1
        assert sigs[0]["type"] == "applicant"
    
    def test_agent_signature_type(self):
        blocks = [_make_block("Agent signature: Signed on behalf")]
        sigs = detect_signatures(blocks)
        assert len(sigs) >= 1
        assert sigs[0]["type"] == "agent"
    
    def test_multiple_signatures(self):
        blocks = [
            _make_block("Applicant signature: John Smith"),
            _make_block("Agent signature: Jane Doe")
        ]
        sigs = detect_signatures(blocks)
        assert len(sigs) >= 2
        types = [s["type"] for s in sigs]
        assert "applicant" in types
        assert "agent" in types


class TestFeeExtraction:
    """Test fee amount extraction"""
    
    def test_fee_with_pound_prefix(self):
        blocks = [_make_block("Planning fee: £462.00")]
        amount, src, conf = extract_fee_amount(blocks)
        assert amount == 462.00
        assert conf >= 0.9
    
    def test_fee_with_pound_suffix(self):
        blocks = [_make_block("Payment of 250.00 £ required")]
        amount, src, conf = extract_fee_amount(blocks)
        assert amount == 250.00
        assert conf >= 0.7
    
    def test_fee_with_comma_thousands(self):
        blocks = [_make_block("Fee: £1,250.50")]
        amount, src, conf = extract_fee_amount(blocks)
        assert amount == 1250.50
        assert conf >= 0.9
    
    def test_fee_gbp_suffix(self):
        blocks = [_make_block("Total charge: 500 GBP")]
        amount, src, conf = extract_fee_amount(blocks)
        assert amount == 500.00
        assert conf >= 0.7
    
    def test_fee_without_pence(self):
        blocks = [_make_block("Planning fee: £150")]
        amount, src, conf = extract_fee_amount(blocks)
        assert amount == 150.00
        assert conf >= 0.9
    
    def test_fee_sanity_check_too_small(self):
        blocks = [_make_block("Fee: £25")]
        amount, src, conf = extract_fee_amount(blocks)
        # Should fail sanity check (< £50)
        assert amount is None
    
    def test_fee_sanity_check_too_large(self):
        blocks = [_make_block("Fee: £100,000")]
        amount, src, conf = extract_fee_amount(blocks)
        # Should fail sanity check (> £50,000)
        assert amount is None
    
    def test_no_fee_without_context(self):
        blocks = [_make_block("The price is £250")]
        amount, src, conf = extract_fee_amount(blocks)
        # Should not extract without "fee", "payment", "charge", "cost" context
        assert amount is None


class TestFeeExemption:
    """Test fee exemption detection"""
    
    def test_fee_exempt(self):
        blocks = [_make_block("This application is fee exempt")]
        is_exempt, src, conf = detect_fee_exemption(blocks)
        assert is_exempt == True
        assert conf >= 0.9
    
    def test_fee_exemption(self):
        blocks = [_make_block("Fee exemption claimed under Section X")]
        is_exempt, src, conf = detect_fee_exemption(blocks)
        assert is_exempt == True
        assert conf >= 0.9
    
    def test_no_fee_payable(self):
        blocks = [_make_block("No fee payable for this application type")]
        is_exempt, src, conf = detect_fee_exemption(blocks)
        assert is_exempt == True
        assert conf >= 0.7
    
    def test_prior_approval_no_fee(self):
        blocks = [_make_block("Prior approval application - no fee required")]
        is_exempt, src, conf = detect_fee_exemption(blocks)
        assert is_exempt == True
        assert conf >= 0.7
    
    def test_no_exemption(self):
        blocks = [_make_block("This is a standard planning application")]
        is_exempt, src, conf = detect_fee_exemption(blocks)
        assert is_exempt == False
        assert conf == 0.0


class TestIntegratedCertificatesAndFees:
    """Test realistic certificate and fee scenarios"""
    
    def test_full_application_with_certificate_a(self):
        blocks = [
            _make_block("Certificate A - Ownership"),
            _make_block("I certify that I am the sole owner"),
            _make_block("Applicant signature: John Smith"),
            _make_block("Date: 15/01/2025"),
            _make_block("Planning fee: £462.00")
        ]
        
        # Certificate
        cert_type, _, _ = detect_certificate_type(blocks)
        assert cert_type == "A"
        
        # Signature
        sigs = detect_signatures(blocks)
        assert len(sigs) >= 1
        assert any(s["is_signed"] for s in sigs)
        
        # Fee
        amount, _, _ = extract_fee_amount(blocks)
        assert amount == 462.00
        
        # No exemption
        is_exempt, _, _ = detect_fee_exemption(blocks)
        assert is_exempt == False
    
    def test_prior_approval_with_exemption(self):
        blocks = [
            _make_block("Prior approval application"),
            _make_block("Certificate B: Notice given to owners"),
            _make_block("I hereby certify this application"),
            _make_block("No fee required for prior approval")
        ]
        
        # Certificate
        cert_type, _, _ = detect_certificate_type(blocks)
        assert cert_type == "B"
        
        # Signature
        sigs = detect_signatures(blocks)
        assert len(sigs) >= 1
        
        # Exemption
        is_exempt, _, _ = detect_fee_exemption(blocks)
        assert is_exempt == True
