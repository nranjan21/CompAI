"""
Chart Generator - Creates visual charts for reports using matplotlib.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path
from typing import Dict, Any, List
from app.utils.logger import logger


class ChartGenerator:
    """Generates visual charts for research reports."""
    
    def __init__(self):
        """Initialize the chart generator."""
        self.output_dir = Path("reports/charts")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set matplotlib style
        plt.style.use('seaborn-v0_8-darkgrid')
        plt.rcParams['font.size'] = 11
        plt.rcParams['font.family'] = 'sans-serif'
        
        # Color palette
        self.colors = {
            'positive': '#10B981',  # Green
            'neutral': '#F59E0B',   # Yellow/Orange
            'negative': '#EF4444',  # Red
            'primary': '#6366F1',   # Indigo
            'background': '#F9FAFB'
        }
        
        logger.info("📊 Initialized ChartGenerator")
    
    def generate_sentiment_charts(self, sentiment_data: Dict[str, Any], company_name: str) -> Dict[str, str]:
        """
        Generate all sentiment-related charts.
        
        Args:
            sentiment_data: Sentiment analysis results
            company_name: Company name for file naming
            
        Returns:
            Dictionary with chart types and their file paths
        """
        charts = {}
        safe_name = company_name.replace(' ', '_').replace('.', '')
        
        try:
            # 1. Sentiment Distribution Pie Chart
            distribution = sentiment_data.get('sentiment_distribution', {})
            if distribution:
                charts['distribution'] = self._create_pie_chart(
                    distribution, safe_name
                )
            
            # 2. Sentiment Gauge
            overall = sentiment_data.get('overall_sentiment', 0)
            if overall is not None:
                charts['gauge'] = self._create_gauge_chart(
                    overall, safe_name
                )
            
            # 3. Theme Sentiment Bar Chart
            themes = sentiment_data.get('themes', [])
            if themes:
                charts['themes'] = self._create_bar_chart(
                    themes[:5], safe_name
                )
            
            logger.info(f"✅ Generated {len(charts)} charts for {company_name}")
            
        except Exception as e:
            logger.error(f"Error generating charts: {e}", exc_info=True)
        
        return charts
    
    def _create_pie_chart(self, distribution: Dict[str, int], company_name: str) -> str:
        """Create a pie chart for sentiment distribution."""
        labels = []
        values = []
        colors = []
        
        # Sort by sentiment type
        sentiment_order = ['Positive', 'Neutral', 'Negative']
        for label in sentiment_order:
            if label in distribution:
                labels.append(label)
                values.append(distribution[label])
                colors.append(self.colors[label.lower()])
        
        # Create figure
        fig, ax = plt.subplots(figsize=(8, 6), facecolor='white')
        
        # Create pie chart
        wedges, texts, autotexts = ax.pie(
            values,
            labels=labels,
            colors=colors,
            autopct='%1.1f%%',
            startangle=90,
            textprops={'fontsize': 12, 'weight': 'bold'}
        )
        
        # Enhance text
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(11)
        
        ax.set_title('Sentiment Distribution', fontsize=14, weight='bold', pad=20)
        
        # Save
        chart_path = self.output_dir / f"{company_name}_sentiment_pie.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return str(chart_path)
    
    def _create_gauge_chart(self, sentiment: float, company_name: str) -> str:
        """Create a gauge chart for overall sentiment."""
        fig, ax = plt.subplots(figsize=(8, 5), facecolor='white', subplot_kw={'projection': 'polar'})
        
        # Normalize sentiment from -1,1 to 0,180 degrees
        normalized = ((sentiment + 1) / 2) * 180
        
        # Create gauge background (semicircle)
        theta = np.linspace(0, np.pi, 100)
        
        # Color zones
        zone_size = len(theta) // 3
        
        # Negative zone (red)
        ax.fill_between(
            theta[:zone_size], 0, 1,
            color=self.colors['negative'], alpha=0.3
        )
        
        # Neutral zone (yellow)
        ax.fill_between(
            theta[zone_size:2*zone_size], 0, 1,
            color=self.colors['neutral'], alpha=0.3
        )
        
        # Positive zone (green)
        ax.fill_between(
            theta[2*zone_size:], 0, 1,
            color=self.colors['positive'], alpha=0.3
        )
        
        # Draw pointer
        pointer_angle = np.radians(normalized)
        ax.arrow(
            pointer_angle, 0, 0, 0.8,
            width=0.05, head_width=0.15, head_length=0.1,
            fc='black', ec='black', linewidth=2
        )
        
        # Add sentiment value in center
        ax.text(
            np.pi/2, -0.3, f'{sentiment:.2f}',
            ha='center', va='center',
            fontsize=24, weight='bold'
        )
        
        # Labels
        ax.text(0, 1.15, 'Negative', ha='right', fontsize=10, weight='bold')
        ax.text(np.pi/2, 1.15, 'Neutral', ha='center', fontsize=10, weight='bold')
        ax.text(np.pi, 1.15, 'Positive', ha='left', fontsize=10, weight='bold')
        
        # Remove grid and ticks
        ax.set_ylim(0, 1.2)
        ax.set_theta_direction(-1)
        ax.set_theta_offset(np.pi)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines['polar'].set_visible(False)
        
        ax.set_title('Overall Sentiment Score', fontsize=14, weight='bold', pad=20)
        
        # Save
        chart_path = self.output_dir / f"{company_name}_sentiment_gauge.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return str(chart_path)
    
    def _create_bar_chart(self, themes: List[Dict[str, Any]], company_name: str) -> str:
        """Create a horizontal bar chart for theme sentiments."""
        theme_names = [t.get('theme', 'Unknown')[:30] for t in themes]  # Truncate long names
        sentiments = [t.get('sentiment', 0) for t in themes]
        
        # Color bars based on sentiment
        colors = [
            self.colors['positive'] if s > 0.3 else
            self.colors['negative'] if s < -0.3 else
            self.colors['neutral']
            for s in sentiments
        ]
        
        # Create figure with extra space for legend
        fig, ax = plt.subplots(figsize=(10, 6), facecolor='white')
        
        # Create horizontal bar chart
        y_pos = np.arange(len(theme_names))
        bars = ax.barh(y_pos, sentiments, color=colors, alpha=0.8, edgecolor='black', linewidth=0.5)
        
        # Customize
        ax.set_yticks(y_pos)
        ax.set_yticklabels(theme_names, fontsize=10)
        ax.set_xlabel('Sentiment Score', fontsize=11, weight='bold')
        ax.set_title('Key Themes Sentiment', fontsize=14, weight='bold', pad=20)
        ax.axvline(x=0, color='black', linestyle='-', linewidth=1)
        ax.set_xlim(-1, 1.2)  # Extended to make room for labels
        
        # Add value labels on bars
        for i, (bar, sentiment) in enumerate(zip(bars, sentiments)):
            width = bar.get_width()
            label_x = width + (0.05 if width > 0 else -0.05)
            ax.text(
                label_x, bar.get_y() + bar.get_height()/2,
                f'{sentiment:.2f}',
                ha='left' if width > 0 else 'right',
                va='center',
                fontsize=9,
                weight='bold'
            )
        
        # Add legend outside plot area (upper right, outside)
        positive_patch = mpatches.Patch(color=self.colors['positive'], label='Positive (>0.3)')
        neutral_patch = mpatches.Patch(color=self.colors['neutral'], label='Neutral')
        negative_patch = mpatches.Patch(color=self.colors['negative'], label='Negative (<-0.3)')
        ax.legend(
            handles=[positive_patch, neutral_patch, negative_patch],
            loc='upper left',
            bbox_to_anchor=(1.02, 1),
            frameon=True,
            fancybox=True,
            shadow=True
        )
        
        # Adjust layout to prevent legend cutoff
        plt.tight_layout()
        
        # Save
        chart_path = self.output_dir / f"{company_name}_themes_bar.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return str(chart_path)


def get_chart_generator():
    """Get a singleton instance of ChartGenerator."""
    return ChartGenerator()
