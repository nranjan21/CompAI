"""
Deep Research Agent - CLI Entry Point
"""

import argparse
import sys
import os
from pathlib import Path

# Add the current directory to sys.path to allow imports from 'app'
# Assuming run from the 'backend' folder
sys.path.append(os.getcwd())

from app.agents.orchestrator import OrchestratorAgent
from app.synthesis.insight_synthesizer import InsightSynthesizer
from app.reporting.report_generator import ReportGenerator
from app.utils.logger import logger
from app.core.config import config
from app.core.llm_manager import get_llm_manager

def main():
    """Main entry point for the Deep Research Agent CLI."""
    
    parser = argparse.ArgumentParser(
        description="Deep Research Agent for Company Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_cli.py --company "Apple Inc" --ticker AAPL
  python run_cli.py --company "Tesla" --ticker TSLA --no-parallel
  python run_cli.py --company "Stripe"
        """
    )
    
    parser.add_argument("--company", type=str, required=True, help="Company name to research")
    parser.add_argument("--ticker", type=str, default=None, help="Stock ticker symbol")
    parser.add_argument("--no-parallel", action="store_true", help="Run agents sequentially")
    parser.add_argument("--mode", type=str, choices=["fast", "deep"], default="fast", help="Research mode (fast or deep)")
    parser.add_argument("--output", type=str, default=None, help="Custom output directory")
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("🚀 DEEP RESEARCH AGENT - Company Analysis System")
    print("="*70)
    print(f"\n📊 Target Company: {args.company}")
    if args.ticker:
        print(f"💹 Ticker Symbol: {args.ticker}")
    
    # Check available LLM providers
    available_providers = config.get_available_llm_providers()
    if not available_providers:
        logger.error("\n❌ No LLM API keys configured!")
        sys.exit(1)
    
    try:
        # Initialize components
        orchestrator = OrchestratorAgent()
        synthesizer = InsightSynthesizer()
        report_generator = ReportGenerator()
        
        # Step 1: Conduct research
        logger.info("🔎 Phase 1: Research Collection")
        research_results = orchestrator.conduct_research(
            company_name=args.company,
            ticker=args.ticker,
            mode=args.mode,
            parallel=not args.no_parallel
        )
        
        # Step 2: Synthesize insights
        logger.info("\n🧠 Phase 2: Insight Synthesis")
        synthesis = synthesizer.synthesize(research_results)
        
        # Step 3: Generate report
        logger.info("\n📝 Phase 3: Report Generation")
        report_path = report_generator.generate_report(research_results, synthesis)
        
        print("\n" + "="*70)
        print("✅ RESEARCH COMPLETED SUCCESSFULLY")
        print("="*70)
        print(f"\n📄 Report saved to: {report_path}")
        
        # Display LLM usage stats
        llm = get_llm_manager()
        stats = llm.get_usage_stats()
        
        print("📊 LLM Provider Usage:")
        for provider, stat in stats.items():
            if stat['calls'] > 0 or stat['failures'] > 0:
                print(f"   {provider.value}: {stat['calls']} calls, {stat['failures']} failures")
        
        print("\n" + "="*70 + "\n")
        
    except KeyboardInterrupt:
        logger.warning("\n\n⚠️  Research interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n\n❌ Research failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
