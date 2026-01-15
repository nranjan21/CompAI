# Deep Research Agent for Company Analysis

An autonomous AI system that gathers, analyzes, and synthesizes publicly available information about companies to generate comprehensive investment research reports.

## 🎯 Overview

This Deep Research Agent is a **Proof of Concept (POC)** that demonstrates:

- **Research Depth**: Multi-source data collection across financial, news, social, and competitive domains
- **Structured Thinking**: Organized multi-agent architecture with specialized research modules
- **Judgment in Source Selection**: Prioritizes official sources and flags contradictions
- **Clear Synthesis**: Connects insights across domains to surface non-obvious observations
- **Cross-Source Reasoning**: Analyzes relationships between financial trends, sentiment, and market dynamics

## 🏗️ Architecture

The system uses a **Multi-Agent Research Architecture**:

```
User Input → Orchestrator Agent
                    ↓
    ┌───────┬───────┬───────┬───────┬───────┐
    ↓       ↓       ↓       ↓       ↓       ↓
 Profile Financial News Sentiment Competitive
  Agent   Agent    Agent   Agent    Agent
    │       │       │       │       │       │
    └───────┴───────┴───────┴───────┴───────┘
                    ↓
          Synthesis Engine
                    ↓
          Report Generator
                    ↓
          Markdown Report
```

### Key Components

1. **Company Profile Agent** - Discovers and validates company identity, extracts basic profile
2. **Financial Research Agent** - Analyzes SEC filings, revenue trends, balance sheet
3. **News Intelligence Agent** - Categorizes major events from news coverage
4. **Sentiment Analysis Agent** - Analyzes customer, employee, and investor sentiment from social media
5. **Competitive Intelligence Agent** - Maps competitive landscape and positioning
6. **Synthesis Engine** - Generates cross-domain insights and identifies contradictions
7. **Report Generator** - Creates structured markdown reports

## 🚀 Features

### Free LLM Fallback Chain ✨

The system uses **5 free LLM providers** with automatic fallback:

1. **Google Gemini 1.5 Flash** (15 RPM free tier)
2. **Groq** (fast inference, Llama 3.1 70B)
3. **Hugging Face Inference API** (various models)
4. **Together AI** (free trial credits)
5. **Cohere** (100 calls/min free tier)

If one API fails or hits rate limits, the system automatically retries with the next provider.

### Data Sources (All Free)

- **Financial**: SEC EDGAR API (official regulatory filings)
- **News**: Google News RSS feeds
- **Social Sentiment**: Reddit API, HackerNews Algolia API
- **Company Info**: Wikipedia, web scraping

## 📦 Installation

### Prerequisites

- Python 3.8+
- API keys for at least one LLM provider (see Setup below)

### Setup

1. **Clone or navigate to the project**:
   ```bash
   cd d:\Coding\Projects_2026\CompAI
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API keys**:
   - Copy `.env.example` to `.env`
   - Add your API keys:

   ```bash
   # At minimum, add ONE of these:
   GOOGLE_API_KEY=your_gemini_api_key_here
   GROQ_API_KEY=your_groq_api_key_here
   HUGGINGFACE_API_KEY=your_hf_api_key_here
   TOGETHER_API_KEY=your_together_api_key_here
   COHERE_API_KEY=your_cohere_api_key_here

   # Optional but recommended:
   REDDIT_CLIENT_ID=your_reddit_client_id
   REDDIT_CLIENT_SECRET=your_reddit_client_secret
   ```

### Getting API Keys (Free Tiers)

- **Google Gemini**: https://makersuite.google.com/app/apikey
- **Groq**: https://console.groq.com/keys
- **Hugging Face**: https://huggingface.co/settings/tokens
- **Together AI**: https://api.together.xyz/
- **Cohere**: https://dashboard.cohere.com/api-keys
- **Reddit**: https://www.reddit.com/prefs/apps

## 💻 Usage

### Basic Usage

```bash
python main.py --company "Apple Inc" --ticker AAPL
```

### Examples

```bash
# Public company with ticker
python main.py --company "Tesla" --ticker TSLA

# Private company (no ticker)
python main.py --company "Stripe"

# Run agents sequentially instead of parallel
python main.py --company "Microsoft" --ticker MSFT --no-parallel
```

### Output

The agent will:
1. ✅ Gather data from all research modules
2. 🧠 Synthesize cross-domain insights
3. 📝 Generate a comprehensive markdown report

Reports are saved to `./reports/` with timestamp.

## 📄 Report Structure

Generated reports include:

1. **Executive Summary** - 3-4 sentence overview
2. **Company Overview** - Business description, industry, management
3. **Business & Industry Analysis** - Competitive positioning, market dynamics
4. **Financial Highlights** - Revenue trends, profitability, balance sheet strength
5. **Key News & Events** - Major events categorized and analyzed
6. **Public & Social Sentiment Overview** - Customer, employee, investor sentiment
7. **Opportunities & Risks** - Investment thesis elements
8. **Key Observations / Analyst Notes** - Cross-domain insights and non-obvious patterns
9. **Research Methodology & Source Notes** - Transparency and sources

## 🎓 Key Design Principles

### 1. **Synthesis Over Collection**

The core value is in **connecting insights**, not just aggregating data. The Synthesis Engine:
- Identifies contradictions (e.g., "positive financials but negative sentiment")
- Surfaces patterns (e.g., "revenue growth slowing while customer complaints rising")
- Provides context and interpretation

### 2. **Source Prioritization**

Sources are categorized by trust level:
- **Primary**: SEC filings, official company sources
- **Secondary**: Major news outlets, Wikipedia
- **Tertiary**: Social media (used for sentiment only)

### 3. **Graceful Degradation**

If data sources fail, the agent:
- Continues with available sources
- Notes limitations explicitly in report
- Never fabricates data

### 4. **Explainability**

The agent explains:
- How conclusions were reached
- Source credibility assessment
- How contradictions were handled

## 🗂️ Project Structure

```
CompAI/
├── main.py                 # Entry point
├── config.py              # Configuration management
├── llm_manager.py         # LLM fallback chain manager
├── requirements.txt       # Dependencies
├── .env.example          # Environment template
│
├── agents/               # Research agent modules
│   ├── base_agent.py
│   ├── company_profile_agent.py
│   ├── financial_research_agent.py
│   ├── news_intelligence_agent.py
│   ├── sentiment_analysis_agent.py
│   ├── competitive_intelligence_agent.py
│   └── orchestrator.py
│
├── synthesis/            # Insight synthesis
│   └── insight_synthesizer.py
│
├── reporting/            # Report generation
│   └── report_generator.py
│
├── utils/               # Utilities
│   ├── logger.py
│   ├── web_scraper.py
│   ├── cache_manager.py
│   └── pdf_parser.py
│
├── cache/              # Cached research data
├── reports/            # Generated reports
└── logs/               # Application logs
```

## ⚙️ Configuration

Edit `.env` to customize:

```bash
# Research parameters
RESEARCH_TIME_HORIZON_MONTHS=12
MAX_NEWS_ARTICLES=50
MAX_SOCIAL_POSTS=100

# System settings
LOG_LEVEL=INFO
ENABLE_CACHING=true
CACHE_DIR=./cache
OUTPUT_DIR=./reports
```

## 🧪 Testing

Run the agent on a well-known public company to verify functionality:

```bash
python main.py --company "Apple Inc" --ticker AAPL
```

Expected behavior:
- ✅ All agents execute successfully
- ✅ Report generated with all sections
- ✅ Sources properly cited
- ✅ At least 2-3 cross-domain insights in "Key Observations"

## 📊 Example Use Cases

- **Investment Research**: Quickly assess company for due diligence
- **Competitive Analysis**: Understand market positioning
- **Risk Assessment**: Identify red flags and concerns
- **Sentiment Monitoring**: Track public perception

## ⚠️ Limitations (POC Scope)

- **Financial Precision**: High-level interpretation, not accounting-grade accuracy
- **Real-time Data**: Point-in-time research, not live monitoring  
- **Non-English Sources**: Limited support
- **Private Companies**: Reduced data availability
- **Paywall Content**: Excluded from analysis
- **Rate Limits**: May require caching and slower execution

## 🔮 Future Enhancements

Potential improvements beyond POC:

- Multi-language support
- PDF OCR for quarterly reports
- Time-series financial analysis
- Automated fact-checking
- Webhook notifications
- REST API interface
- Web UI dashboard

## 🤝 Contributing

This is a POC demonstration. For production use:

1. Add comprehensive error handling
2. Implement rate limit management
3. Add authentication for API access
4. Create unit and integration tests
5. Add data validation and sanitization
6. Implement audit logging

## 📝 License

This is a proof-of-concept project for demonstration purposes.

## 🙋 Support

For issues or questions:
1. Check logs in `./logs/`
2. Verify API keys in `.env`
3. Ensure dependencies are installed
4. Review error messages for specific failures

---

**Built with**: Python, Google Gemini, Groq, HuggingFace, Together AI, Cohere, and other free APIs

**Purpose**: Demonstrate autonomous research capabilities and structured synthesis of unstructured information
