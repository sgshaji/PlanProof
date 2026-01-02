import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  IconButton,
  Typography,
  CircularProgress,
  Alert,
  Tooltip,
  Paper,
} from '@mui/material';
import {
  Close,
  NavigateBefore,
  NavigateNext,
  ZoomIn,
  ZoomOut,
  FindInPage,
} from '@mui/icons-material';

interface Evidence {
  page: number;
  snippet: string;
  evidence_key?: string;
  confidence?: number;
  bbox?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

interface DocumentViewerProps {
  open: boolean;
  onClose: () => void;
  documentId?: number;
  documentName?: string;
  initialPage?: number;
  evidence?: Evidence;
  runId?: number;
}

const DocumentViewer: React.FC<DocumentViewerProps> = ({
  open,
  onClose,
  documentId,
  documentName,
  initialPage = 1,
  evidence,
  runId,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [documentUrl, setDocumentUrl] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [scale, setScale] = useState(1.0);

  useEffect(() => {
    if (open && documentId) {
      loadDocument();
    }
  }, [open, documentId]);

  useEffect(() => {
    if (initialPage) {
      setCurrentPage(initialPage);
    }
  }, [initialPage]);

  const loadDocument = async () => {
    setLoading(true);
    setError(null);

    try {
      // TODO: Call API endpoint to get SAS URL for document
      // For now, show placeholder
      setError('Document viewer integration pending - blob SAS URL endpoint needed');
      setLoading(false);
    } catch (err: any) {
      console.error('Failed to load document:', err);
      setError(err.message || 'Failed to load document');
      setLoading(false);
    }
  };

  const handleZoomIn = () => {
    setScale((prev) => Math.min(prev + 0.25, 3.0));
  };

  const handleZoomOut = () => {
    setScale((prev) => Math.max(prev - 0.25, 0.5));
  };

  const handlePreviousPage = () => {
    setCurrentPage((prev) => Math.max(prev - 1, 1));
  };

  const handleNextPage = () => {
    if (numPages) {
      setCurrentPage((prev) => Math.min(prev + 1, numPages));
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: {
          height: '90vh',
          maxHeight: '90vh',
        },
      }}
    >
      <DialogTitle sx={{ pb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box>
            <Typography variant="h6">{documentName || `Document ${documentId}`}</Typography>
            {evidence && (
              <Typography variant="caption" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
                <FindInPage fontSize="small" />
                Evidence: {evidence.snippet?.substring(0, 60)}...
              </Typography>
            )}
          </Box>
          <IconButton onClick={onClose} size="small">
            <Close />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent dividers sx={{ p: 0, display: 'flex', flexDirection: 'column' }}>
        {/* Toolbar */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            p: 1,
            borderBottom: '1px solid',
            borderColor: 'divider',
            backgroundColor: 'grey.50',
          }}
        >
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <Tooltip title="Previous page">
              <span>
                <IconButton onClick={handlePreviousPage} disabled={currentPage <= 1} size="small">
                  <NavigateBefore />
                </IconButton>
              </span>
            </Tooltip>
            <Typography variant="body2">
              Page {currentPage} {numPages && `of ${numPages}`}
            </Typography>
            <Tooltip title="Next page">
              <span>
                <IconButton onClick={handleNextPage} disabled={!numPages || currentPage >= numPages} size="small">
                  <NavigateNext />
                </IconButton>
              </span>
            </Tooltip>
          </Box>

          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title="Zoom out">
              <IconButton onClick={handleZoomOut} size="small" disabled={scale <= 0.5}>
                <ZoomOut />
              </IconButton>
            </Tooltip>
            <Typography variant="body2" sx={{ minWidth: 50, textAlign: 'center', lineHeight: '32px' }}>
              {(scale * 100).toFixed(0)}%
            </Typography>
            <Tooltip title="Zoom in">
              <IconButton onClick={handleZoomIn} size="small" disabled={scale >= 3.0}>
                <ZoomIn />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {/* Document Display Area */}
        <Box
          sx={{
            flexGrow: 1,
            overflow: 'auto',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'grey.200',
            p: 2,
          }}
        >
          {loading && (
            <Box sx={{ textAlign: 'center' }}>
              <CircularProgress />
              <Typography variant="body2" sx={{ mt: 2 }}>
                Loading document...
              </Typography>
            </Box>
          )}

          {error && (
            <Alert severity="warning" sx={{ maxWidth: 600 }}>
              <Typography variant="body2" gutterBottom>
                {error}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                To enable document viewing, implement the /api/v1/documents/{'{'}{'{'}documentId{'}'}{'}'}
/sas-url endpoint that returns a temporary SAS URL for blob access.
              </Typography>
            </Alert>
          )}

          {!loading && !error && documentUrl && (
            <Paper elevation={3} sx={{ transform: `scale(${scale})`, transformOrigin: 'center' }}>
              {/* PDF rendering would go here using react-pdf or similar */}
              <Box sx={{ width: 600, height: 800, bgcolor: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Typography color="text.secondary">PDF Canvas (Page {currentPage})</Typography>
              </Box>
              
              {/* Evidence highlighting overlay */}
              {evidence && evidence.bbox && currentPage === evidence.page && (
                <Box
                  sx={{
                    position: 'absolute',
                    left: `${evidence.bbox.x}px`,
                    top: `${evidence.bbox.y}px`,
                    width: `${evidence.bbox.width}px`,
                    height: `${evidence.bbox.height}px`,
                    border: '2px solid',
                    borderColor: 'warning.main',
                    backgroundColor: 'rgba(255, 165, 0, 0.2)',
                    pointerEvents: 'none',
                  }}
                />
              )}
            </Paper>
          )}
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default DocumentViewer;
