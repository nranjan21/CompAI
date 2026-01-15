"""
Quick test to verify report generation is working.
"""

import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.synthesis.insight_synthesizer import InsightSynthesizer
from app.reporting.report_generator import ReportGenerator


def test_report_generation():
    """Test report generation with sample data."""
    print("\n" + "="*80)
    print("Testing Report Generation")
    print("="*80)
    
    # Sample research results
    research_results = {
        "company_name": "Test Company Inc",
        "ticker": "TEST",
        "timestamp": "2026-01-12T23:00:00",
        "profile": {
            "company_name": "Test Company Inc",
            "industry": "Technology",
            "sector": "Software",
            "founded": "2010",
            "headquarters": "San Francisco, CA",
            "employees": 5000,
            "description": "A leading technology company",
            "products": ["Product A", "Product B"]
        },
        "financial": {
            "fiscal_year": "2024",
            "revenue": 1000,
            "net_income": 200,
            "total_assets": 5000,
            "financial_health": "Strong",
            "key_metrics": {
                "gross_margin": 0.65,
                "operating_margin": 0.25
            }
        },
        "news": {
            "total_articles": 5,
            "categories": {"Product Launch": 2, "Financial Results": 3},
            "timeline": [
                {"title": "New Product Launch", "date": "2026-01-10", "summary": "Company launched new product"}
            ]
        },
        "sentiment": {
            "overall_sentiment": 0.7,
            "sentiment_trend": "positive",
            "sentiment_distribution": {"Positive": 4, "Neutral": 1, "Negative": 0},
            "themes": [
                {"theme": "Innovation", "sentiment": 0.8}
            ]
        },
        "competitive": {
            "competitors": [
                {"name": "Competitor A", "market_position": "Strong Player"}
            ],
            "swot": {
                "strengths": ["Strong brand", "Innovation"],
                "weaknesses": ["High costs"],
                "opportunities": ["Market expansion"],
                "threats": ["Competition"]
            }
        }
    }
    
    # Test InsightSynthesizer
    print("\n1. Testing InsightSynthesizer...")
    synthesizer = InsightSynthesizer()
    synthesis = synthesizer.synthesize(research_results)
    
    print(f"   ✅ Executive Summary: {synthesis.get('executive_summary', 'N/A')[:100]}...")
    print(f"   ✅ Key Insights: {len(synthesis.get('key_insights', []))} insights")
    print(f"   ✅ Recommendations: {len(synthesis.get('recommendations', []))} recommendations")
    
    # Test ReportGenerator
    print("\n2. Testing ReportGenerator...")
    report_gen = ReportGenerator()
    report_path = report_gen.generate_report(research_results, synthesis)
    
    print(f"   ✅ Report generated: {report_path}")
    
    # Check file exists and has content
    from pathlib import Path
    report_file = Path(report_path)
    if report_file.exists():
        file_size = report_file.stat().st_size
        print(f"   ✅ File size: {file_size} bytes")
        
        # Read first few lines
        with open(report_file, 'r', encoding='utf-8') as f:
            first_lines = [f.readline().strip() for _ in range(5)]
        
        print("\n   First few lines of report:")
        for line in first_lines:
            if line:
                print(f"   {line}")
        
        print("\n✅ Report generation test PASSED!")
        return True
    else:
        print("\n❌ Report file not found!")
        return False


if __name__ == "__main__":
    test_report_generation()
