"""
Financial Research Agent - LangGraph Node Implementation

Gathers and analyzes financial data from annual reports with explicit reasoning
for report selection, contradiction detection, and trust scoring.
"""

from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
import re

from app.core.state_schema import CompanyResearchState, TrustedValue, Source, FinancialData
from app.core.reasoning_chain import ReasoningChain
from app.core.trust_scorer import get_trust_scorer
from app.core.mode_config import get_config_value
from app.core.llm_manager import get_llm_manager
from app.utils.web_scraper import get_web_scraper
from app.utils.pdf_parser import get_pdf_parser
from app.utils.logger import logger
from app.utils.retry_utils import retry_on_failure
from app.utils.text_chunker import TextChunker, chunk_and_summarize


def financial_research_node(state: CompanyResearchState) -> CompanyResearchState:
    """
    Financial Research LangGraph node.
    
    Workflow:
    1. Search for annual report with reasoning
    2. Download latest report (with logic for selection)
    3. Parse financial statements  
    4. Extract and analyze metrics with LLM
    5. Detect contradictions and anomal

ies
    6. Score trust based on source quality
    
    Args:
        state: Current research state
        
    Returns:
        Updated state with financial_data populated
    """
    logger.info("🚀 Starting FinancialResearchNode")
    
    # Initialize
    reasoning = ReasoningChain("FinancialResearchAgent")
    web_scraper = get_web_scraper()
    pdf_parser = get_pdf_parser()
    llm_manager = get_llm_manager()
    trust_scorer = get_trust_scorer()
    
    # Get configuration
    mode = state.get("mode", "fast")
    years_back = get_config_value(mode, "financial_years_back", 1)
    detailed_analysis = get_config_value(mode, "financial_detailed_analysis", False)
    max_sections = get_config_value(mode, "financial_max_sections", 3)
    
    company_name = state["company_name"]
    ticker = state.get("ticker")
    
    # Create reports directory
    reports_dir = Path("annual_reports")
    reports_dir.mkdir(exist_ok=True)
    
    try:
        # Step 1: Find annual report
        logger.info(f"🔍 Searching for {company_name} annual report")
        
        search_query = f"{company_name} site:annualreports.com"
        search_results = web_scraper.search_google(search_query, num_results=5)
        
        if not search_results:
            reasoning.add_step(
                decision="Skip financial research",
                rationale="No annual reports found in search results",
                alternatives_considered=["Try alternative sites", "Skip entirely"],
                chosen_option="Skip entirely",
                confidence=1.0
            )
            return {
                "errors": ["Could not find annual report"],
                "reasoning_chains": {"financial": reasoning.to_list()},
                "completed_nodes": ["financial"]
            }
        
        # Find the company page
        reports_url = None
        for result in search_results:
            url = result.get('url', '')
            if 'annualreports.com' in url and company_name.lower().replace(' ', '') in url.lower():
                reports_url = url
                break
        
        if not reports_url and search_results:
            reports_url = search_results[0].get('url')
        
        reasoning.add_source_selection(
            data_type="annual report page",
            sources_considered=[r['url'] for r in search_results[:3]],
            chosen_source=reports_url,
            rationale="Selected annualreports.com page matching company name" if reports_url else "Used first search result",
            confidence=0.85
        )
        
        logger.info(f"✅ Found annual reports page: {reports_url}")
        
        # Step 2: Download latest report
        logger.info("📥 Downloading latest annual report")
        
        # Check for existing PDF
        safe_name = company_name.replace(' ', '_').replace('.', '').replace(',', '')
        timestamp = datetime.now().strftime("%Y%m%d")
        pdf_filename = f"{safe_name}_annual_report_{timestamp}.pdf"
        pdf_path = reports_dir / pdf_filename
        
        # If today's PDF exists, use it
        if pdf_path.exists():
            logger.info(f"♻️ Using existing PDF: {pdf_path.name}")
            reasoning.add_step(
                decision="Reuse existing PDF",
                rationale=f"PDF from today already exists at {pdf_path}",
                alternatives_considered=["Download fresh copy", "Use existing"],
                chosen_option="Use existing to save time",
                confidence=1.0
            )
        else:
            # Check for recent PDFs
            existing_pdfs = list(reports_dir.glob(f"{safe_name}_annual_report_*.pdf"))
            
            if existing_pdfs:
                most_recent = max(existing_pdfs, key=lambda p: p.stat().st_mtime)
                import time
                age_days = (time.time() - most_recent.stat().st_mtime) / (24 * 3600)
                
                if age_days < 7:
                    pdf_path = most_recent
                    logger.info(f"♻️ Reusing existing PDF ({age_days:.1f} days old): {most_recent.name}")
                    
                    reasoning.add_step(
                        decision="Reuse recent PDF",
                        rationale=f"PDF is only {age_days:.1f} days old, within acceptable freshness threshold",
                        alternatives_considered=["Download fresh copy", "Use existing"],
                        chosen_option="Use existing (<7 days old)",
                        confidence=0.95
                    )
                else:
                    logger.info(f"PDF is {age_days:.1f} days old, downloading fresh copy")
            
            if not pdf_path.exists():
                soup = web_scraper.fetch_and_parse(reports_url)
                if not soup:
                    return {
                        "errors": ["Could not access annual reports page"],
                        "reasoning_chains": {"financial": reasoning.to_list()},
                        "completed_nodes": ["financial"]
                    }
                
                # Strategy 1: Look for "Most Recent" section with redirect links
                most_recent_link = None
                
                for header in soup.find_all(['h2', 'h3', 'div', 'span']):
                    header_text = header.get_text(strip=True).lower()
                    if 'most recent' in header_text:
                        parent = header.parent
                        if parent:
                            links = parent.find_all('a', href=True)
                            for link in links:
                                href = link['href']
                                if '/click/' in href.lower() or href.endswith('.pdf'):
                                    most_recent_link = {
                                        'url': href if href.startswith('http') else f"https://www.annualreports.com{href}",
                                        'text': link.get_text(strip=True),
                                        'is_redirect': '/click/' in href.lower()
                                    }
                                    break
                        if most_recent_link:
                            break
                
                # Strategy 2: Collect all PDF links and sort by year
                pdf_links = []
                
                if not most_recent_link:
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        if href.endswith('.pdf') or 'pdf' in href.lower():
                            link_text = link.get_text(strip=True)
                            
                            # Extract year
                            year_match = re.search(r'20\d{2}', href + ' ' + link_text)
                            year = int(year_match.group()) if year_match else 0
                            
                            pdf_links.append({
                                'url': href if href.startswith('http') else f"https://www.annualreports.com{href}",
                                'text': link_text,
                                'year': year
                            })
                    
                    # Sort by year
                    pdf_links.sort(key=lambda x: x['year'], reverse=True)
                    
                    if pdf_links:
                        most_recent_link = pdf_links[0]
                
                # Reasoning: Report selection
                if most_recent_link:
                    alternatives = [most_recent_link.get('text', 'Selected report')]
                    if pdf_links:
                        alternatives.extend([p['text'] for p in pdf_links[1:min(3, len(pdf_links))]])
                    
                    reasoning.add_step(
                        decision="Select annual report",
                        rationale=f"Selected report: '{most_recent_link.get('text')}'. "
                                  f"Prioritized redirect links or latest year ({most_recent_link.get('year', 'N/A')})",
                        alternatives_considered=alternatives,
                        chosen_option=most_recent_link.get('text', 'Selected report'),
                        confidence=0.9 if most_recent_link.get('is_redirect') else 0.8
                    )
                    
                    # Download
                    pdf_url = most_recent_link['url']
                    logger.info(f"📥 Downloading: {most_recent_link['text']} from {pdf_url}")
                    
                    success = web_scraper.download_file(pdf_url, str(pdf_path))
                    if not success:
                        return {
                            "errors": ["Failed to download PDF"],
                            "reasoning_chains": {"financial": reasoning.to_list()},
                            "completed_nodes": ["financial"]
                        }
                    
                    logger.info(f"✅ Downloaded to {pdf_path}")
                else:
                    return {
                        "errors": ["No PDF reports found"],
                        "reasoning_chains": {"financial": reasoning.to_list()},
                        "completed_nodes": ["financial"]
                    }
        
        # Step 3: Parse PDF
        logger.info("📄 Parsing financial statements")
        
        full_text = pdf_parser.extract_text(str(pdf_path))
        if not full_text:
            return {
                "errors": ["Could not extract text from PDF"],
                "reasoning_chains": {"financial": reasoning.to_list()},
                "completed_nodes": ["financial"]
            }
        
        logger.info(f"Extracted {len(full_text)} characters from PDF")
        
        # Extract financial sections
        section_markers = [
            "consolidated statements of income",
            "consolidated statements of operations",
            "consolidated balance sheets",
            "consolidated statements of cash flows",
            "financial highlights",
            "selected financial data",
            "income statements",
            "balance sheets"
        ]
        
        financial_sections = []
        for marker in section_markers[:max_sections]:
            section_text = pdf_parser.extract_section(str(pdf_path), marker)
            if section_text:
                financial_sections.append({
                    'section': marker,
                    'text': section_text[:10000]
                })
        
        reasoning.add_step(
            decision=f"Extract {len(financial_sections)} financial sections",
            rationale=f"Found {len(financial_sections)} out of {len(section_markers[:max_sections])} target sections",
            alternatives_considered=["Parse all sections", f"Parse top {max_sections} sections"],
            chosen_option=f"Parse top {max_sections} sections based on {mode} mode",
            confidence=0.85
        )
        
        # Step 4: Analyze with LLM
        logger.info("🤖 Analyzing financial data with LLM")
        
        # Build context
        context_parts = []
        for section in financial_sections:
            context_parts.append(f"## {section['section'].title()}\n{section['text']}")
        
        if not financial_sections:
            context_parts.append(full_text[:50000])
        
        full_context = '\n\n'.join(context_parts)
        
        # Check if chunking needed
        chunker = TextChunker(max_tokens=30000, overlap_tokens=1000)
        estimated_tokens = chunker.estimate_tokens(full_context)
        
        logger.info(f"Financial data: {estimated_tokens} estimated tokens")
        
        if estimated_tokens > 30000:
            logger.info("Using chunking strategy for large financial data")
            context = chunk_and_summarize(
                full_context,
                llm_manager,
                topic=f"{company_name} annual report financial sections"
            )
            
            reasoning.add_step(
                decision="Use chunking for large document",
                rationale=f"Document has {estimated_tokens} tokens, exceeds LLM context limit",
                alternatives_considered=["Truncate", "Chunk and summarize"],
                chosen_option="Chunk and summarize to preserve details",
                confidence=0.9
            )
        else:
            context = full_context
        
        # LLM prompt for extraction
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

        result = llm_manager.generate(prompt, temperature=0.3, max_tokens=1500)
        
        if not result.get("success"):
            return {
                "errors": [f"LLM analysis failed: {result.get('error')}"],
                "reasoning_chains": {"financial": reasoning.to_list()},
                "completed_nodes": ["financial"]
            }
        
        response_text = result.get("text", "")
        
        # Parse JSON
        try:
            import json
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            elif "JSON:" in response_text:
                response_text = response_text.split("JSON:")[1].strip()
            
            # Remove trailing text
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
            
            # Check for anomalies
            anomalies = []
            
            # 1. Growth rate anomalies
            if financial_metrics.get('growth_rates'):
                gr = financial_metrics['growth_rates']
                if gr.get('revenue_growth') is not None:
                    rev_growth = float(gr['revenue_growth'])
                    if abs(rev_growth) > 1.0:  # >100% growth
                        anomalies.append({
                            "type": "unusual_growth",
                            "metric": "revenue_growth",
                            "value": rev_growth,
                            "severity": "high",
                            "note": f"Revenue growth of {rev_growth*100:.1f}% is unusually high."
                        })
                
                if gr.get('earnings_growth') is not None:
                    earn_growth = float(gr['earnings_growth'])
                    if abs(earn_growth) > 2.0:  # >200% growth/decline
                        anomalies.append({
                            "type": "unusual_growth",
                            "metric": "earnings_growth",
                            "value": earn_growth,
                            "severity": "medium",
                            "note": f"Earnings growth of {earn_growth*100:.1f}% is highly volatile."
                        })

            # 2. Margin anomalies
            if financial_metrics.get('key_metrics'):
                km = financial_metrics['key_metrics']
                if km.get('net_margin') is not None:
                    net_margin = float(km['net_margin'])
                    if net_margin < -0.2:  # >20% loss
                        anomalies.append({
                            "type": "negative_margin",
                            "metric": "net_margin",
                            "value": net_margin,
                            "severity": "medium",
                            "note": f"Significant negative net margin ({net_margin*100:.1f}%)."
                        })
            
            if anomalies:
                reasoning.add_step(
                    decision="Flag financial anomalies",
                    rationale=f"Detected {len(anomalies)} anomalies in financial data for further review",
                    alternatives_considered=["Ignore outliers", "Flag as warnings"],
                    chosen_option="Flag and store as structured anomalies",
                    confidence=0.8
                )
            
            reasoning.add_step(
                decision="LLM extraction successful",
                rationale=f"Extracted financial metrics for FY {financial_metrics.get('fiscal_year', 'N/A')}",
                alternatives_considered=["Rule-based extraction", "LLM extraction"],
                chosen_option="LLM extraction for flexibility",
                confidence=0.85
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}\nResponse: {response_text[:500]}")
            return {
                "errors": [f"Failed to parse financial data: {e}"],
                "reasoning_chains": {"financial": reasoning.to_list()},
                "completed_nodes": ["financial"]
            }
        
        # Step 5: Build TrustedValue structures
        source = Source(
            url=reports_url,
            title=f"{company_name} Annual Report",
            source_type="filing",
            access_date=datetime.now().isoformat(),
            page_numbers=None,
            trust_score=trust_scorer.score_source(reports_url, "filing")
        )
        
        # Build financial data with trust scores
        financial_data: FinancialData = {
            "pdf_path": str(pdf_path),
            "anomalies": anomalies if 'anomalies' in locals() else []
        }
        
        for key, value in financial_metrics.items():
            if value is not None and key != "key_metrics" and key != "growth_rates":
                financial_data[key] = TrustedValue(
                    value=value,
                    sources=[source],
                    trust_score=source["trust_score"],
                    reasoning=None
                )
        
        # Add key_metrics and growth_rates to financial_data
        if financial_metrics.get("key_metrics"):
            financial_data["key_metrics"] = {
                k: TrustedValue(value=v, sources=[source], trust_score=source["trust_score"], reasoning=None)
                for k, v in financial_metrics["key_metrics"].items() if v is not None
            }
            
        if financial_metrics.get("growth_rates"):
            financial_data["growth_rates"] = {
                k: TrustedValue(value=v, sources=[source], trust_score=source["trust_score"], reasoning=None)
                for k, v in financial_metrics["growth_rates"].items() if v is not None
            }
        
        logger.info(f"✅ Financial research completed with trust score {source['trust_score']:.2f}")
        logger.info(f"📊 Reasoning steps: {len(reasoning.steps)}, Avg confidence: {reasoning.get_average_confidence():.2f}")
        
        return {
            "financial_data": financial_data,
            "reasoning_chains": {"financial": reasoning.to_list()},
            "sources": {"financial": [source]},
            "trust_scores": {"financial": source["trust_score"]},
            "warnings": [a['note'] for a in anomalies] if 'anomalies' in locals() else [],
            "completed_nodes": ["financial"]
        }
        
    except Exception as e:
        logger.exception("💥 FinancialResearchNode failed")
        return {
            "errors": [f"FinancialResearchNode error: {str(e)}"],
            "reasoning_chains": {"financial": ReasoningChain("FinancialResearchAgent").to_list()},
            "completed_nodes": ["financial"]
        }
