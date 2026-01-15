"""
PDF Parser utility for extracting text and metadata from PDF files.
Uses PyMuPDF (fitz) for robust PDF processing.
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Optional, List, Dict, Any
from app.utils.logger import logger


class PDFParser:
    """PDF parsing utility for extracting text and metadata."""
    
    def __init__(self):
        """Initialize PDF parser."""
        pass
    
    def extract_text(self, pdf_path: str) -> Optional[str]:
        """
        Extract all text from a PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text or None if failed
        """
        try:
            logger.debug(f"📄 Extracting text from {pdf_path}")
            
            doc = fitz.open(pdf_path)
            text = ""
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text += page.get_text()
            
            doc.close()
            
            logger.info(f"✅ Extracted {len(text)} characters from {pdf_path}")
            return text
        except Exception as e:
            logger.warning(f"⚠️ Error extracting text from {pdf_path}: {e}")
            return None
    
    def extract_text_by_page(self, pdf_path: str) -> Optional[List[str]]:
        """
        Extract text from each page separately.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of text per page or None if failed
        """
        try:
            logger.debug(f"📄 Extracting text by page from {pdf_path}")
            
            doc = fitz.open(pdf_path)
            pages = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                pages.append(page.get_text())
            
            doc.close()
            
            logger.info(f"✅ Extracted text from {len(pages)} pages")
            return pages
        except Exception as e:
            logger.warning(f"⚠️ Error extracting text by page from {pdf_path}: {e}")
            return None
    
    def extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract PDF metadata.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary of metadata
        """
        try:
            doc = fitz.open(pdf_path)
            metadata = doc.metadata
            
            # Add additional info
            metadata['page_count'] = len(doc)
            metadata['file_size'] = Path(pdf_path).stat().st_size
            
            doc.close()
            
            return metadata
        except Exception as e:
            logger.warning(f"⚠️ Error extracting metadata from {pdf_path}: {e}")
            return {}
    
    def extract_tables(self, pdf_path: str) -> List[List[List[str]]]:
        """
        Extract tables from PDF (basic implementation).
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of tables (each table is a list of rows)
        """
        # Note: This is a basic implementation
        # For production use, consider using libraries like tabula-py or camelot
        try:
            doc = fitz.open(pdf_path)
            tables = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Try to find tables by looking for structured text
                blocks = page.get_text("blocks")
                
                # This is a simplified approach
                # In practice, table detection is complex
                for block in blocks:
                    text = block[4]  # Text content
                    # Simple heuristic: multiple tabs or whitespace = potential table
                    if '\t' in text or '  ' in text:
                        rows = [line.split() for line in text.split('\n') if line.strip()]
                        if len(rows) > 1:
                            tables.append(rows)
            
            doc.close()
            
            return tables
        except Exception as e:
            logger.warning(f"⚠️ Error extracting tables from {pdf_path}: {e}")
            return []
    
    def search_text(self, pdf_path: str, search_term: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """
        Search for text in PDF and return matches with page numbers.
        
        Args:
            pdf_path: Path to PDF file
            search_term: Text to search for
            case_sensitive: Whether search is case-sensitive
            
        Returns:
            List of matches with page numbers and context
        """
        try:
            doc = fitz.open(pdf_path)
            matches = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                # Search in page text
                search_text = text if case_sensitive else text.lower()
                term = search_term if case_sensitive else search_term.lower()
                
                if term in search_text:
                    # Find all occurrences
                    start = 0
                    while True:
                        pos = search_text.find(term, start)
                        if pos == -1:
                            break
                        
                        # Get context (50 chars before and after)
                        context_start = max(0, pos - 50)
                        context_end = min(len(text), pos + len(search_term) + 50)
                        context = text[context_start:context_end]
                        
                        matches.append({
                            'page': page_num + 1,
                            'position': pos,
                            'context': context
                        })
                        
                        start = pos + 1
            
            doc.close()
            
            return matches
        except Exception as e:
            logger.warning(f"⚠️ Error searching in {pdf_path}: {e}")
            return []
    
    def extract_section(self, pdf_path: str, start_marker: str, end_marker: Optional[str] = None) -> Optional[str]:
        """
        Extract a specific section from PDF between markers.
        Improved to find the most relevant occurrence (e.g. not the Table of Contents).
        """
        try:
            text = self.extract_text(pdf_path)
            if text is None:
                return None
            
            # Find all occurrences of start marker
            import re
            # Use case-insensitive search for markers
            matches = [m.start() for m in re.finditer(re.escape(start_marker), text, re.IGNORECASE)]
            
            if not matches:
                logger.warning(f"⚠️ Start marker '{start_marker}' not found")
                return None
            
            # Heuristic: The real financial statement usually has many numbers following it.
            # TOC or cross-references usually have text or single page numbers.
            best_pos = matches[0]
            max_numbers = -1
            
            for pos in matches:
                # Check next 1000 characters for number density
                context = text[pos:pos+1000]
                num_count = len(re.findall(r'\d+', context))
                if num_count > max_numbers:
                    max_numbers = num_count
                    best_pos = pos
            
            start_pos = best_pos
            logger.info(f"📍 Found best match for '{start_marker}' at pos {start_pos} (num_density: {max_numbers})")
            
            # Find end marker if specified
            if end_marker:
                end_pos = text.find(end_marker, start_pos + len(start_marker))
                if end_pos == -1:
                    logger.warning(f"⚠️ End marker '{end_marker}' not found")
                    return text[start_pos:]
                return text[start_pos:end_pos]
            else:
                return text[start_pos:]
        except Exception as e:
            logger.warning(f"⚠️ Error extracting section from {pdf_path}: {e}")
            return None


# Global PDF parser instance
pdf_parser = None

def get_pdf_parser() -> PDFParser:
    """Get or create global PDF parser instance."""
    global pdf_parser
    if pdf_parser is None:
        pdf_parser = PDFParser()
    return pdf_parser
