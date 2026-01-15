"""
Financial Research Agent - Gathers financial data from annual reports.

Workflow:
1. Search annualreports.com for company
2. Download latest annual report PDF
3. Parse financial statements
4. Extract key financial metrics
5. Use LLM to analyze financial health
"""

from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import re
from app.agents.base_agent import BaseAgent
from app.utils.web_scraper import get_web_scraper
from app.utils.pdf_parser import get_pdf_parser
from app.utils.logger import logger
from app.utils.retry_utils import retry_on_failure


class FinancialResearchAgent(BaseAgent):
    """Agent for gathering and analyzing financial data from annual reports."""
    
    def __init__(self):
        """Initialize the financial research agent."""
        super().__init__(name="FinancialResearchAgent", use_cache=True)
        self.web_scraper = get_web_scraper()
        self.pdf_parser = get_pdf_parser()
        self.total_steps = 5
        
        # Create annual reports directory
        self.reports_dir = Path("annual_reports")
        self.reports_dir.mkdir(exist_ok=True)
    
    @retry_on_failure()
    def _find_annual_report(self, company_name: str) -> Optional[str]:
        """Find annual report on annualreports.com."""
        self._log_step(f"Searching for {company_name} annual report")
        
        # Search annualreports.com
        search_query = f"{company_name} site:annualreports.com"
        search_results = self.web_scraper.search_google(search_query, num_results=5)
        
        if not search_results:
            self._add_error("Could not find annual report")
            return None
        
        # Find the company page
        for result in search_results:
            url = result.get('url', '')
            if 'annualreports.com' in url and company_name.lower().replace(' ', '') in url.lower():
                logger.info(f"Found annual reports page: {url}")
                return url
        
        # If no exact match, use first result
        if search_results:
            return search_results[0].get('url')
        
        return None
    
    @retry_on_failure()
    def _download_latest_report(self, company_name: str, reports_url: str) -> Optional[str]:
        """Download the latest annual report PDF or reuse existing one."""
        
        # First, check if we have a recent PDF for this company
        safe_name = company_name.replace(' ', '_').replace('.', '')
        timestamp = datetime.now().strftime("%Y%m%d")
        pdf_filename = f"{safe_name}_annual_report_{timestamp}.pdf"
        pdf_path = self.reports_dir / pdf_filename
        
        # If today's PDF already exists, use it immediately
        if pdf_path.exists():
            logger.info(f"♻️ Using today's PDF: {pdf_path.name}")
            return str(pdf_path)
        
        # Check for any existing PDFs for this company (from previous days)
        existing_pdfs = list(self.reports_dir.glob(f"{safe_name}_annual_report_*.pdf"))
        
        if existing_pdfs:
            # Get most recent PDF
            most_recent = max(existing_pdfs, key=lambda p: p.stat().st_mtime)
            
            # Check age (reuse if less than 7 days old)
            import time
            age_days = (time.time() - most_recent.stat().st_mtime) / (24 * 3600)
            
            if age_days < 7:
                logger.info(f"♻️ Reusing existing PDF ({age_days:.1f} days old): {most_recent.name}")
                return str(most_recent)
            else:
                logger.info(f"PDF is {age_days:.1f} days old, downloading fresh copy")
        
        # No recent PDF found, proceed with download
        self._log_step("Downloading latest annual report")
        
        # Fetch the company's annual reports page
        soup = self.web_scraper.fetch_and_parse(reports_url)
        if soup is None:
            self._add_error("Could not access annual reports page")
            return None
        
        # Strategy 1: Look for "Most Recent Annual Report" section with redirect links
        most_recent_link = None
        
        # Find headers/sections indicating "Most Recent"
        for header in soup.find_all(['h2', 'h3', 'div', 'span']):
            header_text = header.get_text(strip=True).lower()
            if 'most recent' in header_text:
                # Look for links near this header (redirect or PDF links)
                parent = header.parent
                if parent:
                    links = parent.find_all('a', href=True)
                    for link in links:
                        href = link['href']
                        # Prioritize redirect links (pattern: /Click/xxxxx)
                        if '/click/' in href.lower() or href.endswith('.pdf'):
                            most_recent_link = {
                                'url': href if href.startswith('http') else f"https://www.annualreports.com{href}",
                                'text': link.get_text(strip=True),
                                'is_redirect': '/click/' in href.lower()
                            }
                            logger.info(f"Found 'Most Recent' link: {most_recent_link['text']} ({most_recent_link['url']})")
                            break
                if most_recent_link:
                    break
        
        # Strategy 2: If no "Most Recent" section, collect all PDF links and sort by year
        pdf_links = []
        
        if not most_recent_link:
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.endswith('.pdf') or 'pdf' in href.lower():
                    link_text = link.get_text(strip=True)
                    
                    # Extract year from link text or href
                    year_match = re.search(r'20\d{2}', href + ' ' + link_text)
                    year = int(year_match.group()) if year_match else 0
                    
                    pdf_links.append({
                        'url': href if href.startswith('http') else f"https://www.annualreports.com{href}",
                        'text': link_text,
                        'year': year
                    })
            
            # Sort by year descending (highest/latest first)
            pdf_links.sort(key=lambda x: x['year'], reverse=True)
            
            if pdf_links:
                most_recent_link = pdf_links[0]
                logger.info(f"Selected archived PDF (year {most_recent_link['year']}): {most_recent_link['text']}")
            else:
                self._add_error("No PDF reports found")
                return None
        
        # Download the selected PDF
        pdf_url = most_recent_link['url']
        logger.info(f"Downloading report: {most_recent_link['text']} from {pdf_url}")
        
        # Download PDF
        safe_name = company_name.replace(' ', '_').replace('.', '')
        timestamp = datetime.now().strftime("%Y%m%d")
        pdf_filename = f"{safe_name}_annual_report_{timestamp}.pdf"
        pdf_path = self.reports_dir / pdf_filename
        
        try:
            success = self.web_scraper.download_file(pdf_url, str(pdf_path))
            if success:
                logger.info(f"Downloaded report to {pdf_path}")
                return str(pdf_path)
            else:
                self._add_error("Failed to download PDF")
                return None
        except Exception as e:
            self._add_error(f"Error downloading PDF: {e}")
            return None
    
    @retry_on_failure()
    def _parse_financial_data(self, pdf_path: str) -> Dict[str, Any]:
        """Parse financial data from PDF."""
        self._log_step("Parsing financial statements")
        
        try:
            # Extract text from PDF
            full_text = self.pdf_parser.extract_text(pdf_path)
            
            if not full_text:
                self._add_error("Could not extract text from PDF")
                return {}
            
            logger.info(f"Extracted {len(full_text)} characters from PDF")
            
            # Extract key sections (look for common financial statement headers)
            financial_sections = []
            
            # Common section headers in annual reports (including variants for 10-K)
            section_markers = [
                "consolidated statements of income",
                "consolidated statements of operations",
                "consolidated balance sheets",
                "consolidated statements of cash flows",
                "financial highlights",
                "selected financial data",
                "condensed consolidated statements of income",
                "condensed consolidated balance sheets",
                "income statements",
                "balance sheets"
            ]
            
            for marker in section_markers:
                section_text = self.pdf_parser.extract_section(pdf_path, marker)
                if section_text:
                    # Increase limit to 10000 chars to ensure tables are captured
                    financial_sections.append({
                        'section': marker,
                        'text': section_text[:10000]
                    })
            
            return {
                'full_text': full_text[:50000],  # First 50k chars
                'sections': financial_sections,
                'pdf_path': pdf_path
            }
        except Exception as e:
            self._add_error(f"Error parsing PDF: {e}")
            return {}
    
    def _analyze_financials(self, financial_data: Dict[str, Any], company_name: str) -> Dict[str, Any]:
        """Use LLM to analyze financial data with smart chunking."""
        self._log_step("Analyzing financial data with LLM")
        
        if not financial_data:
            return self._get_default_financial_data()
        
        # Import chunking utility
        from app.utils.text_chunker import TextChunker, chunk_and_summarize
        
        # Build context from financial sections
        context_parts = []
        
        # Add sections if available
        for section in financial_data.get('sections', []):
            context_parts.append(f"## {section['section'].title()}\n{section['text']}")
        
        # If no sections found, use full text
        if not financial_data.get('sections'):
            context_parts.append(financial_data.get('full_text', '')[:50000])
        
        full_context = '\n\n'.join(context_parts)
        
        # Check if we need chunking - Increased limit to 30000 for modern LLMs to preserve data
        chunker = TextChunker(max_tokens=30000, overlap_tokens=1000)
        estimated_tokens = chunker.estimate_tokens(full_context)
        
        logger.info(f"Financial data: {estimated_tokens} estimated tokens")
        
        # If content is extremely large, use chunking with hierarchical summarization
        if estimated_tokens > 30000:
            logger.info("Using chunking strategy for large financial data")
            summarized_context = chunk_and_summarize(
                full_context, 
                self.llm_manager,
                topic=f"{company_name} annual report financial sections"
            )
            context = summarized_context
        else:
            context = full_context
        
        # Build final prompt for financial extraction
        prompt = f"""Analyze the following financial information for {company_name} and extract key metrics.

{context}

Extract the following financial information in JSON format:

{{
  "fiscal_year": "Most recent fiscal year (e.g., 2024)",
  "revenue": "Total revenue in millions (number only, e.g., 637959)",
  "net_income": "Net income in millions (number only)",
  "total_assets": "Total assets in millions (number only)",
  "total_liabilities": "Total liabilities in millions (number only)",
  "key_metrics": {{
    "gross_margin": "Gross profit margin as decimal (e.g., 0.45)",
    "operating_margin": "Operating margin as decimal",
    "net_margin": "Net profit margin as decimal",
    "roe": "Return on equity as decimal",
    "debt_to_equity": "Debt to equity ratio"
  }},
  "financial_health": "Brief assessment in one word (Strong/Moderate/Weak)",
  "growth_rates": {{
    "revenue_growth": "YoY revenue growth as decimal (e.g., 0.15 for 15%)",
    "earnings_growth": "YoY earnings growth as decimal"
  }},
  "risks": ["Key risk 1", "Key risk 2", "Key risk 3"]
}}

IMPORTANT:
- For revenue, net_income, assets: provide ONLY the number in millions (no symbols, no text)
- For margins and ratios: provide as decimal (e.g., 0.45 for 45%)
- If a value is not found, use null (not "N/A" or "None")
- Return ONLY valid JSON, no additional text

JSON:"""

        result = self.llm_manager.generate(prompt, temperature=0.3, max_tokens=1500)
        
        if result.get("success"):
            response_text = result.get("text", "")
            
            try:
                import json
                # Extract JSON from response
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()
                elif "JSON:" in response_text:
                    response_text = response_text.split("JSON:")[1].strip()
                
                # Remove any trailing text after the JSON
                if response_text.startswith('{'):
                    brace_count = 0
                    end_pos = 0
                    for i, char in enumerate(response_text):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_pos = i + 1
                                break
                    if end_pos > 0:
                        response_text = response_text[:end_pos]
                
                financial_metrics = json.loads(response_text)
                financial_metrics['pdf_path'] = financial_data.get('pdf_path')
                
                logger.info(f"✅ Extracted financial data: Revenue ${financial_metrics.get('revenue', 'N/A')}M")
                return financial_metrics
            except Exception as e:
                logger.error(f"Error parsing LLM response: {e}")
                logger.error(f"Response was: {response_text[:500]}")
                return self._get_default_financial_data()
        else:
            logger.warning("LLM failed to analyze financial data")
            return self._get_default_financial_data()
    
    def _get_default_financial_data(self) -> Dict[str, Any]:
        """Return default financial data structure."""
        return {
            "fiscal_year": "N/A",
            "revenue": "N/A",
            "net_income": "N/A",
            "total_assets": "N/A",
            "total_liabilities": "N/A",
            "key_metrics": {},
            "financial_health": "N/A",
            "growth_rates": {},
            "risks": []
        }
    
    def execute(self, company_name: str, ticker: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute financial research workflow.
        
        Args:
            company_name: Name of the company
            ticker: Optional stock ticker (not used with annualreports.com)
            
        Returns:
            Dictionary with financial data
        """
        # Step 1: Find annual report
        reports_url = self._find_annual_report(company_name)
        if not reports_url:
            return self._get_default_financial_data()
        
        # Step 2: Download latest report
        pdf_path = self._download_latest_report(company_name, reports_url)
        if not pdf_path:
            return self._get_default_financial_data()
        
        # Step 3: Parse financial data
        financial_data = self._parse_financial_data(pdf_path)
        
        # Step 4: Analyze with LLM
        analysis = self._analyze_financials(financial_data, company_name)
        
        return analysis
