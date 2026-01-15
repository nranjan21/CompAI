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
from app.utils.cache_manager import get_cache_manager


def _extract_year_from_text(text: str) ->Optional[int]:
    """
    Extract year from text (URL, link text, etc.).
    
    Looks for patterns like: 2025, FY2025, 2025.pdf, etc.
    Returns the most recent valid year found.
    """
    import re
    from datetime import datetime
    
    # Find all 4-digit numbers that could be years
    year_patterns = re.findall(r'20\d{2}', text)
    
    if not year_patterns:
        return None
    
    # Convert to integers and filter valid years (2000-2030)
    current_year = datetime.now().year
    valid_years = [int(y) for y in year_patterns if 2000 <= int(y) <= current_year + 5]
    
    if not valid_years:
        return None
    
    # Return the most recent year
    return max(valid_years)


def _verify_company_url_match(url: str, company_name: str, expanded_names: List[str], llm_manager) -> float:
    """
    Score how well a URL slug matches the company name.
    
    Returns a score from 0.0 to 1.0, where:
    - 1.0 = Perfect match
    - 0.7-0.9 = Good match (abbreviation or variation)
    - 0.3-0.6 = Possible match (similar name)
    - 0.0-0.2 = Poor match (different company)
    
    Uses LLM to handle abbreviations and variations.
    """
    # Extract company slug from URL
    if '/Company/' not in url:
        return 0.0
    
    slug = url.split('/Company/')[-1].split('/')[0].split('?')[0]
    slug_readable = slug.replace('-', ' ').replace('_', ' ')
    
    # Quick check: exact match
    for name in [company_name] + expanded_names:
        name_normalized = name.lower().replace(' ', '').replace(',', '').replace('.', '')
        slug_normalized = slug.lower().replace('-', '').replace('_', '')
        
        # Exact match after normalization
        if name_normalized == slug_normalized:
            return 1.0
        
        # Check if slug is fully contained in name (e.g., "tatagroup" in "tata-consultancy-services")
        if len(slug_normalized) > 5 and slug_normalized in name_normalized:
            return 0.95
    
    # LLM scoring for ambiguous cases
    prompt = f"""Score how well the company slug "{slug_readable}" matches the company "{company_name}".

Consider:
- Is it the SAME company? (Score: 90-100)
- Is it a subsidiary or division? (Score: 70-85)
- Is it a similar/related company? (Score: 30-60)
- Is it a completely different company? (Score: 0-20)

Examples:
- "tata consultancy services ltd" vs "TCS" → Score: 95 (abbreviation)
- "tcs group holding plc" vs "TCS" → Score: 60 (similar abbreviation, different company)
- "microsoft corporation" vs "Microsoft" → Score: 100 (exact match)
- "apple inc" vs "Microsoft" → Score: 0 (different company)

Return ONLY a number from 0-100.

Score:"""
    
    try:
        result = llm_manager.generate(prompt, temperature=0.1, max_tokens=10)
        response = result.get("text", "0").strip()
        
        # Extract number
        import re
        score_match = re.search(r'\d+', response)
        if score_match:
            score = int(score_match.group())
            # Normalize to 0.0-1.0
            return min(100, max(0, score)) / 100.0
        else:
            return 0.5  # Default to uncertain
    except:
        # If LLM fails, use conservative heuristic
        # Check for substring match
        if any(name.lower() in slug_readable.lower() for name in [company_name] + expanded_names):
            return 0.6
        return 0.3


def _expand_company_name(company_name: str, ticker: Optional[str], llm_manager) -> List[str]:
    """
    Expand company name to include potential variations.
    Uses LLM to generate full company name from abbreviations.
    
    Args:
        company_name: Original company name (might be abbreviation)
        ticker: Stock ticker symbol (optional)
        llm_manager: LLM manager instance
        
    Returns:
        List of company name variations to try
    """
    variations = [company_name]
    
    # If company name is short (likely an abbreviation), use LLM to expand
    if len(company_name.split()) <= 1 and len(company_name) <= 5:
        prompt = f"""What is the full official company name for "{company_name}"?
{f"Stock ticker: {ticker}" if ticker else ""}

Provide ONLY the full official company name, nothing else.
Example: "AMD" -> "Advanced Micro Devices, Inc."

Full company name:"""
        
        try:
            result = llm_manager.generate(prompt, temperature=0.1, max_tokens=50)
            if result.get("success"):
                full_name = result.get("text", "").strip()
                # Clean up response
                full_name = full_name.replace('"', '').replace("'", "").strip()
                if full_name and full_name.lower() != company_name.lower():
                    variations.append(full_name)
                    logger.info(f"💡 Expanded '{company_name}' to '{full_name}'")
        except Exception as e:
            logger.warning(f"Could not expand company name: {e}")
    
    # Add ticker as variation if available
    if ticker and ticker not in variations:
        variations.append(ticker)
    
    return variations


def _search_annual_report_with_retry(
    company_name: str,
    ticker: Optional[str],
    web_scraper,
    llm_manager,
    reasoning: ReasoningChain
) -> Optional[str]:
    """
    Search for annual report page with multiple retry strategies.
    
    Returns:
        URL of the company's annual reports page, or None if not found
    """
    logger.info(f"🔍 Searching for {company_name} annual report")
    
    # Get company name variations
    name_variations = _expand_company_name(company_name, ticker, llm_manager)
    
    # Strategy 1: Search for company landing page WITH VERIFICATION AND SCORING
    for name_var in name_variations:
        search_query = f"{name_var} site:annualreports.com/Company"
        logger.info(f"🔍 Attempt with query: {search_query}")
        search_results = web_scraper.search_google(search_query, num_results=10)
        
        if search_results:
            # Score and rank URLs
            scored_urls = []
            for result in search_results:
                url = result.get('url', '')
                if 'annualreports.com/Company/' in url:
                    # Score company match
                    match_score = _verify_company_url_match(url, company_name, name_variations, llm_manager)
                    
                    if match_score >= 0.5:  # Only consider scores >= 50%
                        scored_urls.append({
                            'url': url,
                            'score': match_score
                        })
                        logger.info(f"✅ Company match score {match_score:.2f}: {url}")
                    else:
                        logger.info(f"⚠️ Low match score {match_score:.2f}, skipping: {url}")
            
            if scored_urls:
                # Sort by score (highest first)
                scored_urls.sort(key=lambda x: x['score'], reverse=True)
                
                # Select highest-scoring URL
                best_match = scored_urls[0]
                selected_url = best_match['url']
                
                reasoning.add_step(
                    decision="Found and verified company annual reports page with scoring",
                    rationale=f"Found {len(search_results)} URLs, scored {len(scored_urls)} as potential matches. "
                              f"Selected '{selected_url}' with match score {best_match['score']:.2f}",
                    alternatives_considered=[f"{s['url']} (score: {s['score']:.2f})" for s in scored_urls[:3]],
                    chosen_option=f"{selected_url} (score: {best_match['score']:.2f})",
                    confidence=best_match['score']
                )
                return selected_url
    
    # Strategy 2: Broader search without /Company/ restriction
    logger.info("🔄 Retrying with broader search")
    for name_var in name_variations:
        search_query = f"{name_var} site:annualreports.com"
        search_results = web_scraper.search_google(search_query, num_results=10)
        
        if not search_results:
            continue
        
        # Score and rank URLs
        scored_urls = []
        for result in search_results:
            url = result.get('url', '')
            title = result.get('title', '').lower()
            score = 0
            
            # Prioritize company pages over direct PDF archives
            if '/Company/' in url:
                score += 100
            elif '/HostedData/' in url or '.pdf' in url.lower():
                score -= 50  # Penalize direct PDF links
            
            # Check if company name/ticker appears in URL
            url_lower = url.lower()
            # Create URL-friendly version of name
            name_slug = name_var.lower().replace(' ', '-').replace(',', '').replace('.', '')
            if name_slug in url_lower or (ticker and ticker.lower() in url_lower):
                score += 50
            
            # Check title relevance
            if name_var.lower() in title or (ticker and ticker.lower() in title):
                score += 25
            
            scored_urls.append({
                'url': url,
                'score': score,
                'title': title
            })
        
        # Sort by score
        scored_urls.sort(key=lambda x: x['score'], reverse=True)
        
        if scored_urls and scored_urls[0]['score'] > 0:
            selected_url = scored_urls[0]['url']
            reasoning.add_step(
                decision="Selected annual report page from broader search",
                rationale=f"Top result scored {scored_urls[0]['score']} points. "
                          f"Prioritized '/Company/' URLs over archive PDFs.",
                alternatives_considered=[r['url'] for r in scored_urls[:3]],
                chosen_option=selected_url,
                confidence=0.75 if '/Company/' in selected_url else 0.6
            )
            return selected_url
    
    # Strategy 3: Use ticker if available
    if ticker:
        logger.info(f"🔄 Final attempt using ticker: {ticker}")
        search_query = f"{ticker} annual report site:annualreports.com"
        search_results = web_scraper.search_google(search_query, num_results=5)
        
        if search_results:
            # Try to find company page
            for result in search_results:
                url = result.get('url', '')
                if '/Company/' in url:
                    reasoning.add_step(
                        decision="Found via ticker search",
                        rationale=f"Used ticker '{ticker}' as fallback search",
                        alternatives_considered=["Give up", "Try ticker"],
                        chosen_option="Ticker search successful",
                        confidence=0.7
                    )
                    return url
            
            # If no company page, use first result
            first_url = search_results[0].get('url')
            reasoning.add_step(
                decision="Use first result from ticker search",
                rationale="No ideal matches found, using first result as last resort",
                alternatives_considered=["Skip financial research", "Use first result"],
                chosen_option="Use first result",
                confidence=0.5
            )
            return first_url
    
    # Strategy 4: Broader web search with confidence validation
    logger.info("🔄 Final fallback: broader web search with validation")
    for name_var in name_variations:
        search_query = f'"{name_var}" annual report 2024 OR 2023 filetype:pdf'
        logger.info(f"🔍 Broader search: {search_query}")
        search_results = web_scraper.search_google(search_query, num_results=10)
        
        if not search_results:
            continue
        
        # Validate each result with confidence scoring
        validated_urls = []
        for result in search_results:
            url = result.get('url', '')
            title = result.get('title', '').lower()
            snippet = result.get('snippet', '').lower()
            
            confidence = 0.0
            checks_passed = []
            
            # Check 1: Is it a PDF?
            if url.lower().endswith('.pdf'):
                confidence += 0.3
                checks_passed.append("PDF file")
            
            # Check 2: Company name in URL or title
            name_lower = name_var.lower()
            if name_lower in url.lower() or name_lower in title:
                confidence += 0.25
                checks_passed.append("Name match")
            
            # Check 3: Ticker in URL or title
            if ticker and ticker.lower() in (url.lower() + title):
                confidence += 0.2
                checks_passed.append("Ticker match")
            
            # Check 4: Contains "annual report" or similar keywords
            keywords = ['annual report', 'form 10-k', '10k', 'annual filing']
            if any(kw in title or kw in snippet for kw in keywords):
                confidence += 0.15
                checks_passed.append("Annual report keywords")
            
            # Check 5: Recent year in title/URL
            if any(year in (url + title) for year in ['2024', '2023', '2025']):
                confidence += 0.1
                checks_passed.append("Recent year")
            
            # Only consider URLs with confidence > 0.5
            if confidence > 0.5:
                validated_urls.append({
                    'url': url,
                    'confidence': confidence,
                    'checks': checks_passed,
                    'title': title
                })
        
        # Sort by confidence
        validated_urls.sort(key=lambda x: x['confidence'], reverse=True)
        
        if validated_urls:
            best_match = validated_urls[0]
            reasoning.add_step(
                decision="Found annual report via broader web search",
                rationale=f"Confidence: {best_match['confidence']:.2f}. "
                          f"Passed checks: {', '.join(best_match['checks'])}",
                alternatives_considered=[v['url'] for v in validated_urls[:3]],
                chosen_option=best_match['url'],
                confidence=best_match['confidence']
            )
            logger.info(f"✅ Validated URL with confidence {best_match['confidence']:.2f}")
            return best_match['url']
    
    # No results found
    reasoning.add_step(
        decision="Skip financial research",
        rationale="No annual reports found after trying multiple search strategies including broader web search",
        alternatives_considered=["Try alternative sites", "Skip entirely"],
        chosen_option="Skip entirely",
        confidence=1.0
    )
    return None


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
    
    # Initialize components
    web_scraper = get_web_scraper()
    pdf_parser = get_pdf_parser()
    llm_manager = get_llm_manager()
    trust_scorer = get_trust_scorer()
    cache_manager = get_cache_manager()
    
    company_name = state["company_name"]
    ticker = state.get("ticker")
    mode = state.get("mode", "fast")
    
    # Step 0: Check cache
    cache_key = f"financial_research_{company_name.lower().replace(' ', '_')}_{mode}"
    cached_result = cache_manager.get(cache_key, ttl_hours=24)
    if cached_result:
        logger.info(f"✅ Cache hit for {company_name} financial research")
        # Ensure we update completing node status while returning cached data
        cached_result["completed_nodes"] = ["financial"]
        return cached_result
    
    # Initialize reasoning
    reasoning = ReasoningChain("FinancialResearchAgent")
    
    # Get configuration
    years_back = get_config_value(mode, "financial_years_back", 1)
    detailed_analysis = get_config_value(mode, "financial_detailed_analysis", False)
    max_sections = get_config_value(mode, "financial_max_sections", 3)
    
    company_name = state["company_name"]
    ticker = state.get("ticker")
    
    # Create reports directory
    reports_dir = Path("annual_reports")
    reports_dir.mkdir(exist_ok=True)
    
    try:
        # Step 1: Find annual report with retry logic
        reports_url = _search_annual_report_with_retry(
            company_name=company_name,
            ticker=ticker,
            web_scraper=web_scraper,
            llm_manager=llm_manager,
            reasoning=reasoning
        )
        
        if not reports_url:
            return {
                "errors": ["Could not find annual report after multiple attempts"],
                "reasoning_chains": {"financial": reasoning.to_list()},
                "completed_nodes": ["financial"]
            }
        
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
                
                
                # IMPROVED STRATEGY: Prioritize "Most Recent" section, then scan archives
                most_recent_reports = []
                archived_reports = []
                
                # First, specifically look for "Most Recent" section
                for header in soup.find_all(['h2', 'h3', 'h4', 'div', 'span']):
                    header_text = header.get_text(strip=True).lower()
                    if 'most recent' in header_text:
                        # Found "Most Recent" section, get parent container
                        parent = header.parent
                        if parent:
                            # Look for all links in this section
                            for link in parent.find_all('a', href=True):
                                href = link['href']
                                link_text = link.get_text(strip=True)
                                
                                # Most Recent links are often redirect links or view buttons
                                if '/click/' in href.lower() or 'view' in link_text.lower() or href.endswith('.pdf'):
                                    year = _extract_year_from_text(href + ' ' + link_text + ' ' + header_text)
                                    full_url = href if href.startswith('http') else f"https://www.annualreports.com{href}"
                                    
                                    # Check if it's in the current reports directory (not archive)
                                    is_current = '/AnnualReports/PDF/' in full_url
                                    is_redirect = '/click/' in href.lower()
                                    
                                    most_recent_reports.append({
                                        'url': full_url,
                                        'text': link_text if link_text else 'Most Recent Annual Report',
                                        'year': year if year else datetime.now().year,  # Assume current year if not found
                                        'is_redirect': is_redirect,
                                        'is_current': is_current,
                                        'source': 'most_recent_section'
                                    })
                                    logger.info(f"📌 Found in Most Recent section: {link_text} (year: {year}, redirect: {is_redirect})")
                
                # Then, collect ALL other PDF links from archive
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    link_text = link.get_text(strip=True)
                    
                    # Check if it's a report link
                    is_report = (
                        href.endswith('.pdf') or 
                        'pdf' in href.lower() or \
                        '/click/' in href.lower() or
                        'annual' in link_text.lower()
                    )
                    
                    if is_report:
                        # Skip if we already added it from Most Recent section
                        full_url = href if href.startswith('http') else f"https://www.annualreports.com{href}"
                        if any(r['url'] == full_url for r in most_recent_reports):
                            continue
                        
                        # Extract year from URL and link text
                        year = _extract_year_from_text(href + ' ' + link_text)
                        
                        is_redirect = '/click/' in href.lower()
                        is_current = '/AnnualReports/PDF/' in full_url
                        
                        archived_reports.append({
                            'url': full_url,
                            'text': link_text if link_text else 'Annual Report',
                            'year': year if year else 0,
                            'is_redirect': is_redirect,
                            'is_current': is_current,
                            'source': 'archive'
                        })
                
                # Combine with priority: Most Recent first, then archived
                all_reports = most_recent_reports + archived_reports
                
                if not all_reports:
                    return {
                        "errors": ["No PDF reports found on company page"],
                        "reasoning_chains": {"financial": reasoning.to_list()},
                        "completed_nodes": ["financial"]
                    }
                
                # Sort by: (1) source (most_recent first), (2) is_current (non-archive first), (3) year (highest first), (4) is_redirect
                all_reports.sort(
                    key=lambda x: (
                        x['source'] == 'most_recent_section',  # Most Recent section first
                        x['is_current'],  # Current reports (/PDF/) before archived
                        x['year'] if x['year'] else 0,  # Highest year
                        x['is_redirect']  # Redirect links (often most recent)
                    ),
                    reverse=True
                )
                
                # Select the latest report
                selected_report = all_reports[0]
                
                # Validate year
                current_year = datetime.now().year
                report_year = selected_report['year']
                
                # Create alternatives list for reasoning
                alternatives = [f"{r['text']} (Year: {r['year'] if r['year'] else 'Unknown'}, Source: {r['source']})" 
                               for r in all_reports[:min(5, len(all_reports))]]
                
                # Add warnings if report is old
                age_warning = None
                if report_year == 0:
                    age_warning = "Could not extract year from report. Proceeding with best guess."
                elif current_year - report_year > 2:
                    age_warning = f"Latest report is from {report_year}, which is {current_year - report_year} years old."
                elif report_year > current_year:
                    age_warning = f"Report year ({report_year}) is in the future - may be a fiscal year designation."
                
                # Reasoning: Report selection with year validation
                reasoning.add_step(
                    decision="Select latest annual report with year validation",
                    rationale=f"Found {len(all_reports)} reports. Selected '{selected_report['text']}' "
                              f"from year {selected_report['year'] if selected_report['year'] else 'Unknown'}. "
                              f"{age_warning if age_warning else 'Year is recent and valid.'}",
                    alternatives_considered=alternatives,
                    chosen_option=f"{selected_report['text']} (Year: {selected_report['year']})",
                    confidence=0.95 if selected_report['year'] >= current_year - 1 else 0.75
                )
                
                # Log year validation results
                logger.info(f"📊 Found {len(all_reports)} reports. Years: {[r['year'] for r in all_reports[:5]]}")
                logger.info(f"✅ Selected: {selected_report['text']} (Year: {selected_report['year']})")
                if age_warning:
                    logger.warning(f"⚠️ {age_warning}")
                
                # Download
                pdf_url = selected_report['url']
                logger.info(f"📥 Downloading: {selected_report['text']} from {pdf_url}")
                
                success = web_scraper.download_file(pdf_url, str(pdf_path))
                if not success:
                    return {
                        "errors": ["Failed to download PDF"],
                        "reasoning_chains": {"financial": reasoning.to_list()},
                        "completed_nodes": ["financial"]
                    }
                
                logger.info(f"✅ Downloaded to {pdf_path}")
        
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

Extract the following financial information in JSON format. Provide the most recent data as top-level fields AND include historical data for the last 3 years if available.

{{
  "fiscal_year": "Most recent fiscal year (e.g., 2024)",
  "revenue": "Total revenue in millions for most recent year",
  "net_income": "Net income in millions for most recent year",
  "total_assets": "Total assets in millions for most recent year",
  "total_liabilities": "Total liabilities in millions for most recent year",
  "key_metrics": {{
    "gross_margin": "Gross margin as decimal",
    "operating_margin": "Operating margin as decimal",
    "net_margin": "Net margin as decimal",
    "roe": "ROE as decimal",
    "debt_to_equity": "Debt to equity ratio"
  }},
  "growth_rates": {{
    "revenue_growth": "YoY revenue growth as decimal",
    "earnings_growth": "YoY earnings growth as decimal"
  }},
  "historical_data": [
    {{
      "fiscal_year": 2024,
      "revenue": 637959,
      "net_income": 20000,
      "total_assets": 450000,
      "total_liabilities": 200000
    }},
    {{
      "fiscal_year": 2023,
      "revenue": 611000,
      "net_income": 18000,
      "total_assets": 440000,
      "total_liabilities": 210000
    }}
  ],
  "financial_health": "Brief assessment (Strong/Moderate/Weak)",
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
        
        # Add historical data if present
        if financial_metrics.get("historical_data"):
            financial_data["historical_data"] = financial_metrics["historical_data"]
        
        logger.info(f"✅ Financial research completed with trust score {source['trust_score']:.2f}")
        logger.info(f"📊 Reasoning steps: {len(reasoning.steps)}, Avg confidence: {reasoning.get_average_confidence():.2f}")
        
        result_state = {
            "financial_data": financial_data,
            "reasoning_chains": {"financial": reasoning.to_list()},
            "sources": {"financial": [source]},
            "trust_scores": {"financial": source["trust_score"]},
            "warnings": [a['note'] for a in anomalies] if 'anomalies' in locals() else [],
            "completed_nodes": ["financial"]
        }
        
        # Save to cache
        cache_manager.set(cache_key, result_state)
        
        return result_state
        
    except Exception as e:
        logger.exception("💥 FinancialResearchNode failed")
        return {
            "errors": [f"FinancialResearchNode error: {str(e)}"],
            "reasoning_chains": {"financial": ReasoningChain("FinancialResearchAgent").to_list()},
            "completed_nodes": ["financial"]
        }
