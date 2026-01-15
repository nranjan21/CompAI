
import sys
import os
import logging

# Add project root to path
sys.path.append(os.getcwd())

from agents.financial_research_agent import FinancialResearchAgent
from utils.logger import setup_logger

# Setup logging
logger = setup_logger("verification")

def verify():
    print("Starting verification for FinancialResearchAgent...")
    agent = FinancialResearchAgent()
    
    company = "Amazon.com Inc"
    print(f"Researching {company}...")
    
    result = agent.research(company)
    
    print("\n--- Research Result ---")
    if result.success:
        print("✅ Research Successful")
        data = result.data
        print(f"Revenue Trend: {data.get('revenue_trend')}")
        
        sources = result.sources
        print("\nSources:")
        found_ar = False
        for s in sources:
            # Check for dict or object access compatibility just in case sources are dicts which they are in the agent code
            if isinstance(s, dict):
                 src = s.get('source')
                 url = s.get('url')
            else:
                 src = getattr(s, 'source', '')
                 url = getattr(s, 'url', '')

            print(f"- {src}: {url}")
            if "annualreports.com" in str(url) or "Report PDF" in str(src):
                found_ar = True
        
        if found_ar:
            print("\n✅ Successfully found annual report link!")
        else:
            print("\n❌ Did NOT find annual report link from annualreports.com")
            
        if 'annual_report_text' in data: # Note: this key might be inside the internal data structure, check agent
            # Actually research puts analysis in 'data', but the raw data was passed to _analyze_financials.
            # The agent doesn't explicitly modify 'data' to include raw text unless _analyze_financials includes it.
            # Let's check _analyze_financials in agent.
            pass
            
    else:
        print("❌ Research Failed")
        print(result.get('errors'))

if __name__ == "__main__":
    verify()
