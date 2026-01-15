"""
Report Generator - Creates comprehensive markdown reports from research results.
"""

from typing import Dict, Any
from pathlib import Path
from datetime import datetime
from app.utils.logger import logger
from app.utils.chart_generator import get_chart_generator


class ReportGenerator:
    """Generates comprehensive markdown reports from research results."""
    
    def __init__(self):
        """Initialize the report generator."""
        self.output_dir = Path("reports")
        self.output_dir.mkdir(exist_ok=True)
        self.chart_generator = get_chart_generator()
        logger.info("📝 Initialized ReportGenerator")
    
    def generate_report(self, research_results: Dict[str, Any], synthesis: Dict[str, Any]) -> str:
        """
        Generate a comprehensive markdown report.
        
        Args:
            research_results: Complete research results from orchestrator
            synthesis: Synthesized insights
            
        Returns:
            Path to the generated report file
        """
        company_name = research_results.get("company_name", "Unknown Company")
        ticker = research_results.get("ticker", "")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create filename
        safe_name = company_name.replace(" ", "_").replace(".", "")
        filename = f"{safe_name}_{timestamp}.md"
        output_path = self.output_dir / filename
        
        logger.info(f"📝 Generating report for {company_name}")
        
        # Build report content
        report_content = self._build_report(company_name, ticker, research_results, synthesis)
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"✅ Report generated: {output_path}")
        return str(output_path)
    
    def _create_progress_bar(self, percentage: float, width: int = 20) -> str:
        """Create an ASCII progress bar."""
        filled = int((percentage / 100) * width)
        empty = width - filled
        bar = "█" * filled + "░" * empty
        return f"[{bar}] {percentage:.1f}%"
    
    def _create_sentiment_meter(self, sentiment: float) -> str:
        """
        Create a visual sentiment meter from -1 to +1.
        
        Args:
            sentiment: Sentiment score (-1 to +1)
            
        Returns:
            ASCII art sentiment meter
        """
        # Normalize sentiment to 0-100 scale
        normalized = ((sentiment + 1) / 2) * 100
        position = int(normalized / 10)  # 0-10 position
        
        meter = []
        meter.append("Negative                Neutral                Positive")
        meter.append("    |                      |                      |")
        
        # Create the scale
        scale = "    "
        for i in range(11):
            if i == position:
                scale += "▼"
            else:
                scale += "─"
        meter.append(scale)
        
        # Add the bar
        bar = "    "
        for i in range(11):
            if i < position:
                bar += "█"
            elif i == position:
                bar += "█"
            else:
                bar += "░"
        meter.append(bar)
        
        meter.append(f"   -1.0                  0.0                  +1.0")
        meter.append(f"\n   Current Score: {sentiment:.2f}")
        
        return "\n".join(meter)

    
    def _build_report(self, company_name: str, ticker: str, 
                     research_results: Dict[str, Any], synthesis: Dict[str, Any]) -> str:
        """Build the complete report content."""
        
        report = []
        
        # Header
        report.append(f"# {company_name} - Comprehensive Research Report")
        if ticker:
            report.append(f"**Ticker:** {ticker}")
        
        # Use datetime class directly since we imported it
        from datetime import datetime as dt
        report.append(f"**Generated:** {dt.now().strftime('%B %d, %Y at %I:%M %p')}")
        report.append("\n---\n")
        
        # If we have a full report from the synthesis agent, use it
        if synthesis.get("full_report"):
            report.append(synthesis["full_report"])
            return "\n".join(report)
        
        # Executive Summary
        report.append("## Executive Summary\n")
        report.append(synthesis.get("executive_summary", "No summary available."))
        report.append("\n")
        
        # Key Insights
        report.append("## Key Insights\n")
        for insight in synthesis.get("key_insights", []):
            report.append(f"- {insight}")
        report.append("\n")
        
        # Company Profile
        profile = research_results.get("profile", {})
        if profile:
            # Helper to format values
            def format_val(val, prefix="", suffix=""):
                # Handle TrustedValue objects
                if isinstance(val, dict) and "value" in val:
                    val = val["value"]
                    
                if val is None or val == "null" or val == "None" or val == "N/A":
                    return "N/A"
                return f"{prefix}{val}{suffix}"

            report.append(f"**Fiscal Year:** {format_val(profile.get('fiscal_year'))}")
            report.append(f"**Industry:** {format_val(profile.get('industry', 'N/A'))}")
            report.append(f"**Sector:** {format_val(profile.get('sector', 'N/A'))}")
            report.append(f"**Founded:** {format_val(profile.get('founded', 'N/A'))}")
            report.append(f"**Headquarters:** {format_val(profile.get('headquarters', 'N/A'))}")
            report.append(f"**Employees:** {format_val(profile.get('employees', 'N/A'))}")
            report.append(f"\n**Description:**\n{format_val(profile.get('description', 'N/A'))}\n")
            
            products = profile.get('products', [])
            # Handle TrustedValue list
            if isinstance(products, dict) and "value" in products:
                products = products["value"]
                
            if products and isinstance(products, list):
                report.append("**Key Products/Services:**")
                for product in products:
                    report.append(f"- {product}")
                report.append("\n")
        
        # Financial Performance
        financial = research_results.get("financial", {})
        if financial and not financial.get("error"):
            report.append("## Financial Performance\n")
            
            # Helper to format values
            def format_val(val, prefix="", suffix=""):
                if val is None or val == "null" or val == "None" or val == "N/A":
                    return "N/A"
                return f"{prefix}{val}{suffix}"

            report.append(f"**Fiscal Year:** {format_val(financial.get('fiscal_year'))}")
            report.append(f"**Revenue:** {format_val(financial.get('revenue'), '$', ' Million')}")
            report.append(f"**Net Income:** {format_val(financial.get('net_income'), '$', ' Million')}")
            report.append(f"**Total Assets:** {format_val(financial.get('total_assets'), '$', ' Million')}")
            report.append(f"**Financial Health:** {format_val(financial.get('financial_health'))}\n")
            
            key_metrics = financial.get('key_metrics', {})
            if key_metrics:
                report.append("**Key Metrics:**")
                for metric, value in key_metrics.items():
                    val_str = "N/A" if value is None else str(value)
                    report.append(f"- {metric.replace('_', ' ').title()}: {val_str}")
                report.append("\n")
        
        # News & Market Activity
        news = research_results.get("news", {})
        if news and news.get("total_articles", 0) > 0:
            report.append("## Recent News & Market Activity\n")
            report.append(f"**Total Articles Analyzed:** {news.get('total_articles', 0)}\n")
            
            categories = news.get('categories', {})
            if categories:
                report.append("**News Categories:**")
                for category, count in categories.items():
                    report.append(f"- {category}: {count} articles")
                report.append("\n")
            
            timeline = news.get('timeline', [])
            if timeline:
                report.append("**Major Events:**")
                for event in timeline[:5]:  # Top 5 events
                    title = event.get('title', 'Event')
                    date = event.get('date', 'Unknown')
                    url = event.get('url', '')
                    
                    # Format date nicely if it's not "Unknown"
                    if date and date != 'Unknown':
                        try:
                            from datetime import datetime
                            parsed_date = datetime.strptime(date, '%Y-%m-%d')
                            date = parsed_date.strftime('%B %d, %Y')
                        except:
                            pass  # Keep original format if parsing fails
                    
                    # Create title with link if URL is available
                    if url:
                        title_with_link = f"[{title}]({url})"
                    else:
                        title_with_link = title
                    
                    report.append(f"- **{title_with_link}** ({date})")
                    if event.get('summary'):
                        report.append(f"  {event['summary']}")
                report.append("\n")
        
        # Sentiment Analysis
        sentiment = research_results.get("sentiment", {})
        if sentiment:
            report.append("## Sentiment Analysis\n")
            
            # Generate charts
            try:
                charts = self.chart_generator.generate_sentiment_charts(sentiment, company_name)
            except Exception as e:
                logger.warning(f"Failed to generate charts: {e}")
                charts = {}
            
            # Overall sentiment with visual indicator
            overall = sentiment.get('overall_sentiment', 0)
            trend = sentiment.get('sentiment_trend', 'neutral')
            
            # Sentiment emoji and label
            if overall > 0.3:
                sentiment_emoji = "😊"
                sentiment_label = "Positive"
            elif overall < -0.3:
                sentiment_emoji = "😟"
                sentiment_label = "Negative"
            else:
                sentiment_emoji = "😐"
                sentiment_label = "Neutral"
            
            # Trend arrow
            trend_arrow = "📈" if trend == "positive" else "📉" if trend == "negative" else "➡️"
            
            report.append(f"**Overall Sentiment:** {overall:.2f} {sentiment_emoji} *{sentiment_label}*")
            report.append(f"**Trend:** {trend_arrow} {trend.title()}\n")
            
            # Embed gauge chart
            if 'gauge' in charts:
                report.append(f"![Sentiment Gauge]({charts['gauge']})\n")
            
            # Distribution section
            distribution = sentiment.get('sentiment_distribution', {})
            if distribution:
                total = sum(distribution.values())
                if total > 0:
                    report.append("### Sentiment Distribution\n")
                    
                    # Embed pie chart
                    if 'distribution' in charts:
                        report.append(f"![Sentiment Distribution]({charts['distribution']})\n")
                    
                    # Also show numerical breakdown
                    sentiment_order = ['Positive', 'Neutral', 'Negative']
                    sorted_dist = {k: distribution.get(k, 0) for k in sentiment_order if k in distribution}
                    
                    for label, count in sorted_dist.items():
                        percentage = (count / total) * 100
                        emoji = "🟢" if label == "Positive" else "🟡" if label == "Neutral" else "🔴"
                        report.append(f"- {emoji} **{label}:** {count} articles ({percentage:.1f}%)")
                    report.append("")
            
            # Key themes with sentiment indicators
            themes = sentiment.get('themes', [])
            if themes:
                report.append("\n### Key Themes\n")
                
                # Embed bar chart
                if 'themes' in charts:
                    report.append(f"![Theme Sentiment]({charts['themes']})\n")
                
                # Also list themes
                for theme in themes[:5]:
                    theme_name = theme.get('theme', 'N/A')
                    theme_sentiment = theme.get('sentiment', 0)
                    
                    # Sentiment indicator
                    if theme_sentiment > 0.3:
                        indicator = "🟢"
                    elif theme_sentiment < -0.3:
                        indicator = "🔴"
                    else:
                        indicator = "🟡"
                    
                    report.append(f"- {indicator} **{theme_name}** (sentiment: {theme_sentiment:.2f})")
                report.append("\n")
        
        # Competitive Analysis
        competitive = research_results.get("competitive", {})
        if competitive:
            competitors = competitive.get('competitors', [])
            if competitors:
                report.append("## Competitive Landscape\n")
                report.append("**Main Competitors:**")
                for comp in competitors:
                    report.append(f"\n### {comp.get('name', 'Unknown')}")
                    report.append(f"**Market Position:** {comp.get('market_position', 'N/A')}")
                    
                    strengths = comp.get('strengths', [])
                    if strengths:
                        report.append("**Strengths:**")
                        for strength in strengths:
                            report.append(f"- {strength}")
                    
                    weaknesses = comp.get('weaknesses', [])
                    if weaknesses:
                        report.append("**Weaknesses:**")
                        for weakness in weaknesses:
                            report.append(f"- {weakness}")
                report.append("\n")
            
            # SWOT Analysis
            swot = competitive.get('swot', {})
            if swot:
                report.append("## SWOT Analysis\n")
                
                strengths = swot.get('strengths', [])
                if strengths:
                    report.append("### Strengths")
                    for item in strengths:
                        report.append(f"- {item}")
                    report.append("\n")
                
                weaknesses = swot.get('weaknesses', [])
                if weaknesses:
                    report.append("### Weaknesses")
                    for item in weaknesses:
                        report.append(f"- {item}")
                    report.append("\n")
                
                opportunities = swot.get('opportunities', [])
                if opportunities:
                    report.append("### Opportunities")
                    for item in opportunities:
                        report.append(f"- {item}")
                    report.append("\n")
                
                threats = swot.get('threats', [])
                if threats:
                    report.append("### Threats")
                    for item in threats:
                        report.append(f"- {item}")
                    report.append("\n")
        
        # Investment Analysis
        if synthesis.get("investment_thesis"):
            report.append("## Investment Thesis\n")
            report.append(synthesis.get("investment_thesis"))
            report.append("\n")
        
        # Risk Factors
        risks = synthesis.get("risk_factors", [])
        if risks:
            report.append("## Risk Factors\n")
            for risk in risks:
                report.append(f"- {risk}")
            report.append("\n")
        
        # Opportunities
        opportunities = synthesis.get("opportunities", [])
        if opportunities:
            report.append("## Opportunities\n")
            for opp in opportunities:
                report.append(f"- {opp}")
            report.append("\n")
        
        # Recommendations
        recommendations = synthesis.get("recommendations", [])
        if recommendations:
            report.append("## Recommendations\n")
            for rec in recommendations:
                report.append(f"- {rec}")
            report.append("\n")
        
        # Footer
        report.append("---\n")
        report.append("*This report was generated automatically using AI-powered research agents.*")
        report.append(f"\n*Report ID: {research_results.get('timestamp', 'N/A')}*")
        
        return "\n".join(report)
