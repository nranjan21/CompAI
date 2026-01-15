We propose a LangGraph-orchestrated pipeline where specialized agents collaborate to research a company. Each agent is a LangGraph node (a Python function or LLM tool) operating on a shared state object. The StateGraph explicitly defines the workflow: e.g.

START → CompanyDiscovery → [FinancialResearch, NewsResearch, SentimentAnalysis, MarketAnalysis] → Synthesis → END


Each node reads/writes the shared state (a typed dictionary) to pass data and context. For example, one can define a CompanyState TypedDict with fields like company name, industry, summary, etc. Every node returns the updated state, and final results (report sections and citations) are included in this state. LangGraph’s graph-based flow ensures deterministic control, branching (parallel agents) and memory (state updates).

Multi-agent design is critical: by assigning each task to a specialist agent, we handle complexity and parallelize work. Each agent focuses on a domain (e.g. financials, news), and smaller models or calls can run concurrently to speed up the fast mode. Human-in-the-loop and moderation hooks (e.g. LangSmith) can be added to review agent outputs.

1. Company Discovery Agent

Inputs: Company name (text). Possibly additional hints (country, ticker) if provided.

Outputs: A structured company profile (business description, industry/sector, geography, key products/services, management names, ticker symbol if public).

Data Sources: Use web search (e.g. via SerpAPI/Serper) to find the company’s official site, Wikipedia page, LinkedIn or Crunchbase profiles, and news articles. Official filings or directories (EDGAR/Companies House) give legal names. An API like SerpAPI’s web search (which returns structured JSON) can retrieve Google results. We trust official or encyclopedic sources most: e.g. the company’s own “About” page or investor relations, major news profiles, and Wikipedia.

Trust/Contradiction: If search returns multiple entities with similar names, use context (country, industry) to disambiguate. If different sources give conflicting facts (e.g. founding year), prefer official filings or multiple corroborating sources and flag uncertainty. For example, if Crunchbase and Wikipedia differ, we may cite both and lean on the official source.

LLM vs Rule: We use LLMs mainly to summarize unstructured text (like “About us” paragraphs) and generate narrative descriptions. Rule-based or parsing code extracts structured items (locations, industries, stock tickers) from known formats (e.g. HTML parsing of an investor PDF). The agent might call an LLM for free-text inference (e.g. “what sector is company in?”) but rely on deterministic extraction for facts.

Fast vs Deep Mode: In fast mode, query only the top 1–2 sources (e.g. Wikipedia and official site) to quickly fill the profile. In deep mode, probe further: search multiple languages, gather LinkedIn and Crunchbase data, check competitors’ references, and compile a richer history (e.g. mergers, key product lines). More time allows deeper web crawling (e.g. archived press releases).

State/Memory: Outputs of this agent populate state["company_profile"]. This structured object (a TypedDict) might include name, ticker, industry, headquarters, CEO, etc. These fields are then used by downstream agents. The state ensures each piece of data carries its source (e.g. URLs) for later citation.

2. Financial & Regulatory Research Agent

Inputs: Company profile (e.g. ticker or unique ID, industry, headquarters country).

Outputs: Key financial metrics and context, e.g. latest annual revenue, profit, YOY growth, major balance figures, EBITDA, stock price trends, and relevant regulatory items (e.g. recent SEC filings, legal proceedings). These are summarized in text and can also be stored as structured data (tables or dicts).

Data Sources: Primary sources are official financial documents. We download the most recent annual report (10-K for US companies) and quarterly reports (10-Q) from official registries (EDGAR for US, SEDAR for Canada, Companies House for UK) or from aggregator sites like AnnualReports.com. We also use SerpAPI’s Google Finance or Yahoo Finance results for quick market data (market cap, share price). Investor presentations on the company’s website or press releases (e.g. earnings calls) provide insight. Authoritative third-party aggregators (e.g. Yahoo/Google) are used for quick checks but cross-verified.

Trust/Contradiction: We trust audited reports highest. If a number (say revenue) differs between sources, we favor the official report and note the date. Any anomalies (restatements, one-off charges) are flagged for human review or clarified by reading the notes sections. If two sources disagree significantly and neither is clearly authoritative, the agent can include both possibilities in output with sources or ask the LLM to reconcile by context.

LLM vs Rule: We use rule-based extraction (PDF parsers, regex) to pull numeric values from filings where possible, as these are precise. An LLM can parse unstructured text (MD&A sections) to explain why numbers changed. For example, LLM reasoning can interpret management’s discussion to highlight trends or risks. LLMs can also help compute derived ratios (e.g. profit margins) and explain them. Pure calculation (growth %) is done programmatically.

Fast vs Deep Mode: Fast mode might limit analysis to the most recent year and quarter, perhaps only grabbing headline figures (revenue, net income) from summary tables. Deep mode systematically downloads multiple years of reports (e.g. last 3–5 years), compares trends, computes key ratios (ROE, debt/equity), and scans all notes and regulatory filings (e.g. 8-K for recent events). More time allows summarizing tax or legal footnotes for risk.

State/Intermediate: The agent updates state["financials"] with a table or dict of metrics (with timestamps and sources). It can also add textual insights to state["notes"]["financial_notes"]. The state might track a “trust score” for each metric based on source reliability.

3. News & Media Research Agent

Inputs: Company profile (name, ticker).

Outputs: A chronological list of recent key news and events (with date, headline/summary, source). Also a brief narrative of major events (e.g. mergers, earnings surprises, leadership changes, scandals).

Data Sources: Use news aggregation APIs: SerpAPI’s News API can fetch the latest articles from multiple publishers in real-time. We query Google News, Bing News, and specialized financial news (via SerpAPI or APIs like NewsAPI.org). Also directly scrape press release sections of the company site. Priority is given to reputable outlets (e.g. Reuters, Bloomberg, Financial Times). For historical events, old archives (via search) can be used.

Trust/Contradiction: We discard or flag “news” that seems like rumors (low-tier blogs, unverified social posts). If two outlets report different facts, we either note the discrepancy or rely on primary sources. For example, if one source says “CEO resigns” and another denies it, we include both with sources or seek the official statement. We may assign confidence (higher if multiple outlets agree).

LLM vs Rule: Headlines and dates can be extracted by keyword search (rule-based or using the structured results from SerpAPI). Summaries of events and context are generated by the LLM, which can synthesize multiple articles into a coherent brief. The LLM is also used to phrase the significance (“analyst says this is a sign of…”).

Fast vs Deep Mode: Fast mode pulls recent headlines (past 6–12 months) and only the most impactful items. Deep mode extends the timeframe (several years) and deeper analysis of each event. Fast mode might summarize each year’s headlines in bullet form; deep mode writes multi-paragraph narratives.

State/Intermediate: Store state["news"] as a list of records {date, title, source, summary}. Possibly categorize events (financial news, legal news, etc.). The agent can accumulate evidence (e.g. “3 sources reported this executive change”).

4. Social & Public Sentiment Analysis Agent

Inputs: Company profile.

Outputs: An overview of public sentiment: e.g. general tone (positive/negative/neutral), trending topics or concerns, notable public opinion (especially if impacting reputation). It may include a simple sentiment score or index plus example quotes.

Data Sources: Scrape social media and forums. This could include: Twitter/X (public posts about the company), Reddit threads (e.g. r/stocks, r/company-specific forums), and Glassdoor/employee reviews for insights on internal sentiment. Use official APIs or services (Twitter API, Reddit API) or web scraping (via Scraping tools with rotated proxies to respect terms) to collect recent posts. Google Trends can gauge interest spikes. We treat these sources as indicative rather than authoritative.

Trust/Contradiction: Social data is noisy. We give lower trust to single outliers (e.g. a viral negative tweet) and prefer aggregated sentiment. If a sentiment trend conflicts (e.g. one polarized thread vs overall calm), we note the inconsistency. We may weigh sources (e.g. verified accounts vs random users).

LLM vs Rule: Sentiment polarity can be determined by a combination of rule-based sentiment lexicons or specialized sentiment APIs. We can also prompt the LLM to analyze samples (“Given these tweets about X, what is the prevailing sentiment?”). The LLM can summarize qualitative themes (e.g. “customers praise feature Y but worry about service Z”).

Fast vs Deep Mode: Fast mode samples a few recent tweets or posts to infer sentiment. Deep mode collects larger datasets (hundreds of posts), applies an NLP sentiment model (or multiple models), and computes weighted average sentiment. Deep analysis might categorize sentiment by region or demographic (if data allows).

State/Intermediate: Store state["sentiment"] as e.g. an average sentiment score and list of representative quotes (with sources). Also record any notable spikes or trending hashtags.

5. Market & Competitive Analysis Agent

Inputs: Company profile.

Outputs: Description of market position, major competitors, market size or growth trends, and industry outlook. Possibly a list of key competitors or substitute products.

Data Sources: Industry and competitor data come from market research reports, trade publications, and financial news. We search via SerpAPI or web for industry reports (if free) or summaries (e.g. “Market share [Company] vs competitors”). Tools like Google Trends or sector classification APIs can identify peers. We also parse SEC filings or investor presentations for competitor mentions. Financial data (for peers) via Yahoo Finance/SerpAPI can quantify relative size.

Trust/Contradiction: Different sources may list different sets of competitors or market sizes. We triangulate (e.g. if multiple analysts cite the same top 5 competitors, adopt that). If numbers differ (e.g. market size), note ranges and source date. Official statements (“#1 in Asia-Pacific market”) are taken seriously but cross-checked against third-party data.

LLM vs Rule: Extracting competitor names or market figures can be rule-based (pattern matching on lists). However, explaining industry dynamics (“growing segment”, “threat from X technology”) is done by an LLM synthesizing multiple descriptions. An LLM can also reason about how macro trends (e.g. rising interest rates) affect the market.

Fast vs Deep Mode: Fast mode may list only the top 3–5 competitors (based on market cap or revenue) and a brief statement of the company’s niche. Deep mode compiles a more exhaustive competitor list, notes any niche markets, and summarizes analyst reports on the industry outlook.

State/Intermediate: Populate state["market"] with competitors (list[str]), and maybe a short narrative of market trends. Include any quantitative market figures found (with sources).

6. Insight Synthesis & Report Generation Agent

Inputs: All accumulated state fields: company profile, financials, news events, sentiment data, market analysis.

Outputs: A unified Markdown report with the required sections (Executive Summary, Company Overview, Business & Industry Analysis, Financial Highlights, Key News & Events, Public/Social Sentiment, Opportunities & Risks, Analyst Notes). Each section synthesizes the relevant data with citations.

Data Sources: This agent uses the structured outputs of the previous agents (plus their source annotations). It should also have any remaining text from source docs that were stored if needed for quotes.

Process: We prompt GPT-4 (or another LLM) in a structured way. For example, we might feed it a prompt template like:

“You are an expert financial analyst. Based on the following collected information, write a structured research report. Include an executive summary and the sections listed. Use the provided data in each section and cite sources. Data: Company: {company_summary}. Financials: {financial_table or highlights}. News: {bullet points of events}. Sentiment: {overview}. Competitors: {list}. Then produce the report with sections.”

This is analogous to the SynthesisNode example that prompted an LLM with reasoning and search results to create a report. The LLM’s output is the final report.

LLM vs Rule: The bulk of text generation is by the LLM (GPT-4), which must organize information logically and write narrative. Rule-based post-processing can enforce formatting (Markdown headings) and append properly formatted citations (e.g. ensure each claim is followed by our collected source tokens). The agent can iterate: if it generates a draft, a follow-up pass can check for missing sections or citations.

Fast vs Deep Mode: In fast mode, the synthesis agent might use a smaller “thinking” chain (just one prompt) and produce a concise report (brief paragraphs, a few bullet lists). In deep mode, it might break the task into multiple prompts (one per section) to allow deeper reasoning and review each section, resulting in a more detailed report (longer analysis, more citations). Deep mode may also include a final pass cross-checking facts across sections.

State/Output: The final report (as Markdown text) is stored in state["report"]. The agent should format headings for the required sections and include citations of the form 【source†Lx-Ly】 based on the sources saved earlier.

Multi-Agent Communication & Orchestration

LangGraph Workflow: We build a StateGraph where each node is one of the above agents (as a function or LangChain agent). The graph explicitly defines the flow and data dependencies. For example:

CompanyDiscovery reads state["company_name"] and writes state["company_profile"].

Once done, control flows concurrently to FinancialResearch, NewsResearch, SentimentAnalysis, and MarketAnalysis (multiple outgoing edges).

Each of those nodes runs in parallel or sequence (depending on implementation). When all done, edges lead to Synthesis.

Finally, Synthesis produces state["report"] and ends.
This explicit graph ensures precise sequencing and parallelism.

State Passing: All communication is via the shared state. For example, the NewsResearch agent can read state["company_profile"]["name"] and state["company_profile"]["ticker"] to know what to search for. Each node updates the state (e.g. adding entries to state["notes"] or state["report_sections"]).

Memory & Caching: LangGraph’s persistent memory (if used) can cache results across runs (e.g. save past company data to avoid re-scraping). The shared state acts as short-term memory for this workflow. LangGraph even allows “long-term memory” APIs, but for this POC we assume each run is stateless beyond the state graph.

Fault Tolerance: If one agent fails (e.g. news API timeout), the graph can continue with defaults or partial info. LangGraph supports retry logic and validation, so we can moderate or rerun steps as needed.

Source Attribution & Trust Scoring

Citations: Every piece of information gathered is tagged with its source (URL, document title, and if possible page numbers). For example, when FinancialResearch extracts revenue, it records the exact filing and page. These references are stored alongside the data in state. In the final report, the Synthesis agent is prompted to insert these as 【source†Lx-Ly】 citations. Because we’re using structured state, it’s straightforward to include the correct snippet references in the prompt or with postprocessing. (SerpAPI results and scraped text inherently include source links, which can be output by tools.)

Annotation: In addition to citations, we may annotate trust/confidence. For example, state["financials"]["revenue"].trust = 0.9 if from SEC, or 0.6 if from a blog. The synthesis prompt can instruct the LLM to “flag or re-check items with low confidence”. We might format uncertain claims with qualifiers (“According to one source…”).

Trust Scoring: We define a simple trust hierarchy: official filings and well-known news = high trust; niche blogs and social = low trust. When aggregating conflicting data (e.g. two profit figures), we weight by trust score: majority opinion wins, or highest-trust source wins. The system can compute a confidence metric (e.g. average trust of sources supporting a claim) and include that as a note if needed.

Evaluation: LangGraph facilitates validation checks. For critical fields, we can add nodes that verify values (e.g. cross-check revenue from two sources). LangSmith/Master can review steps. We can embed simple rule checks in nodes: e.g. “if YOY growth > 1000%, double-check for errors.” If anomalies appear, the LLM can be asked to re-examine the data.

Fast vs Deep Modes

Fast Mode (~2–5 min): The graph runs with time/resource constraints. Agents use “light” strategies: e.g. limit web searches to top 3 results, sample social data from the last month only, and use cached or summary data where possible. The Synthesis agent uses a single streamlined prompt to generate a brief report. Parallel execution (where possible) is maximized to save time. The emphasis is on key highlights rather than exhaustiveness.

Deep Mode (~30–45 min): Agents take more thorough paths. For example, FinancialResearch might download multiple years of SEC filings; NewsResearch collects a larger news history; SentimentAnalysis processes many more posts; and the LLM is allowed multi-stage prompting for rigorous analysis. We can perform iterative loops (e.g. “refine competitor list after initial pass”). Human-approved fact-checking steps (using LangGraph’s moderation) can be added in deep mode for critical claims. The output is more detailed and sources are exhaustively cited.

Trade-offs: Fast mode accepts slightly higher error risk or lower coverage. For instance, a figure from last year’s report may serve in place of fully updated numbers. In deep mode, we insist on double-checks. However, even in deep mode we prioritize synthesis over raw data: the report should read like an analyst summary, not a data dump.

Final Report Structure

The Insight Synthesis agent produces a Markdown report with these sections:

Executive Summary: A concise overview of major findings (mission, key metrics, trends, and conclusion).

Company Overview: Business description, industry/sector, geography, products/services, leadership. (Draw on CompanyDiscovery output.)

Business & Industry Analysis: Market context, industry trends, and competitive positioning. (Uses Market/Competitive data.)

Financial Highlights: High-level financial metrics (revenue, profit, growth rates, stock performance) with comparative context. (Uses Financial data.)

Key News & Events: Chronological list of major recent events (with dates) and their implications.

Public & Social Sentiment Overview: Summary of public perception (positive/negative) and notable sentiment drivers.

Opportunities & Risks: Analyst interpretation of opportunities (e.g. market growth areas) and risks (e.g. debt levels, regulatory challenges).

Key Observations / Analyst Notes: Additional insights, unanswered questions, and any caveats (e.g. data gaps or contradictory info).

Each section will weave in citations (【source†Lx-Ly】) from the collected data. For example, the Executive Summary might state: “Company X’s revenue was $2B last year【FinancialReport†L45-L47】 and it operates in the growing Y industry【IndustryReport†L10-L13】, but public sentiment is cautious【SocialMedia}….”.

References

Throughout, we leverage LangGraph’s explicit workflow. LangGraph’s design (nodes, edges, state) ensures clarity and reproducibility. Its support for multi-agent flows and stateful memory is ideal for this complex research task. SerpAPI (and similar tools) provide reliable structured web search and news data. Source attribution is built into each agent. By emphasizing synthesis and using trusted sources first, this architecture delivers a comprehensive, clear research report while respecting the fast/deep mode constraints.