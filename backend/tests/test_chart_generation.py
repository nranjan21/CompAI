"""
Test chart generation functionality.
"""

import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.utils.chart_generator import ChartGenerator


def test_chart_generation():
    """Test generating sentiment charts."""
    print("\n" + "="*80)
    print("Testing Chart Generation")
    print("="*80)
    
    # Sample sentiment data
    sentiment_data = {
        'overall_sentiment': 0.22,
        'sentiment_trend': 'neutral',
        'sentiment_distribution': {
            'Positive': 12,
            'Neutral': 2,
            'Negative': 5
        },
        'themes': [
            {'theme': 'Investments', 'sentiment': 0.65},
            {'theme': 'Job Cuts', 'sentiment': -0.65},
            {'theme': 'FTC Settlement', 'sentiment': -0.65},
            {'theme': 'Product Launch', 'sentiment': 0.70},
            {'theme': 'New Devices', 'sentiment': 0.70}
        ]
    }
    
    # Create chart generator
    generator = ChartGenerator()
    
    # Generate charts
    print("\n📊 Generating charts...")
    charts = generator.generate_sentiment_charts(sentiment_data, "Amazon")
    
    # Check results
    print(f"\n✅ Generated {len(charts)} charts:")
    for chart_type, path in charts.items():
        file_path = Path(path)
        if file_path.exists():
            size_kb = file_path.stat().st_size / 1024
            print(f"  - {chart_type}: {path} ({size_kb:.1f} KB)")
        else:
            print(f"  - {chart_type}: ❌ File not found!")
    
    print("\n" + "="*80)
    print("✅ Chart generation test completed!")
    print("="*80)
    print(f"\nCheck the charts in: {generator.output_dir}")
    
    return True


if __name__ == "__main__":
    test_chart_generation()
