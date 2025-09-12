"""Analytics Reporter for Xline Trading System.

This module provides comprehensive reporting capabilities for trading analytics,
including performance reports, risk analysis, and visual data representations.

Features:
- Performance report generation
- Risk analysis reports
- Strategy comparison reports
- Real-time dashboard data
- Export capabilities (JSON, CSV)
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from io import StringIO
from typing import Any

from xline.core.analytics.engine import AnalyticsResult
from xline.core.analytics.metrics import (
    PerformanceMetrics,
    RiskMetrics,
    TradeMetrics,
    TradingMetricsCalculator,
)

logger = logging.getLogger(__name__)


@dataclass
class ReportConfig:
    """Configuration for analytics reporting."""
    
    include_charts: bool = True
    export_format: str = 'json'  # 'json', 'csv', 'html'
    date_format: str = '%Y-%m-%d %H:%M:%S'
    decimal_places: int = 4
    include_raw_data: bool = False
    compress_output: bool = False


@dataclass
class PerformanceReport:
    """Performance analysis report."""
    
    strategy_id: str
    period_start: datetime
    period_end: datetime
    trade_metrics: TradeMetrics
    performance_metrics: PerformanceMetrics
    risk_metrics: RiskMetrics
    summary: dict[str, Any]
    recommendations: list[str]
    generated_at: datetime


@dataclass
class PortfolioReport:
    """Portfolio-level report."""
    
    period_start: datetime
    period_end: datetime
    total_strategies: int
    portfolio_metrics: dict[str, Any]
    strategy_reports: list[PerformanceReport]
    correlation_matrix: dict[str, dict[str, float]]
    risk_summary: dict[str, Any]
    generated_at: datetime


class AnalyticsReporter:
    """Advanced analytics reporter for trading system.
    
    Generates comprehensive reports for trading performance analysis,
    risk assessment, and strategic decision making.
    """
    
    def __init__(self, config: ReportConfig | None = None):
        """Initialize analytics reporter.
        
        Args:
            config: Optional reporting configuration
        """
        self.config = config or ReportConfig()
        self.metrics_calculator = TradingMetricsCalculator()
        
        # Report cache
        self._report_cache: dict[str, Any] = {}
        self._cache_timestamps: dict[str, datetime] = {}

    def generate_strategy_report(
        self, 
        strategy_id: str, 
        analytics_result: AnalyticsResult,
        period_start: datetime | None = None,
        period_end: datetime | None = None
    ) -> PerformanceReport:
        """Generate comprehensive strategy performance report.
        
        Args:
            strategy_id: Strategy identifier
            analytics_result: Analytics result data
            period_start: Optional period start date
            period_end: Optional period end date
            
        Returns:
            Performance report for the strategy
        """
        # Set default period
        if period_end is None:
            period_end = datetime.now()
        if period_start is None:
            period_start = period_end - timedelta(days=30)
        
        metrics = analytics_result.metrics
        
        # Extract metrics objects
        trade_metrics = metrics.get('trade_metrics', TradeMetrics())
        performance_metrics = metrics.get('performance_metrics', PerformanceMetrics())
        risk_metrics = metrics.get('risk_metrics', RiskMetrics())
        
        # Generate summary
        summary = self._generate_strategy_summary(
            trade_metrics, performance_metrics, risk_metrics
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            trade_metrics, performance_metrics, risk_metrics
        )
        
        report = PerformanceReport(
            strategy_id=strategy_id,
            period_start=period_start,
            period_end=period_end,
            trade_metrics=trade_metrics,
            performance_metrics=performance_metrics,
            risk_metrics=risk_metrics,
            summary=summary,
            recommendations=recommendations,
            generated_at=datetime.now()
        )
        
        # Cache report
        cache_key = f"{strategy_id}_{period_start}_{period_end}"
        self._report_cache[cache_key] = report
        self._cache_timestamps[cache_key] = datetime.now()
        
        return report

    def generate_portfolio_report(
        self, 
        strategy_results: dict[str, AnalyticsResult],
        period_start: datetime | None = None,
        period_end: datetime | None = None
    ) -> PortfolioReport:
        """Generate comprehensive portfolio report.
        
        Args:
            strategy_results: Dict mapping strategy_id to AnalyticsResult
            period_start: Optional period start date
            period_end: Optional period end date
            
        Returns:
            Portfolio report
        """
        # Set default period
        if period_end is None:
            period_end = datetime.now()
        if period_start is None:
            period_start = period_end - timedelta(days=30)
        
        # Generate individual strategy reports
        strategy_reports = []
        for strategy_id, result in strategy_results.items():
            report = self.generate_strategy_report(
                strategy_id, result, period_start, period_end
            )
            strategy_reports.append(report)
        
        # Calculate portfolio-level metrics
        portfolio_metrics = self._calculate_portfolio_metrics(strategy_reports)
        
        # Calculate correlation matrix
        correlation_matrix = self._calculate_portfolio_correlation(strategy_results)
        
        # Generate risk summary
        risk_summary = self._generate_portfolio_risk_summary(strategy_reports)
        
        return PortfolioReport(
            period_start=period_start,
            period_end=period_end,
            total_strategies=len(strategy_results),
            portfolio_metrics=portfolio_metrics,
            strategy_reports=strategy_reports,
            correlation_matrix=correlation_matrix,
            risk_summary=risk_summary,
            generated_at=datetime.now()
        )

    def export_report(
        self, 
        report: PerformanceReport | PortfolioReport, 
        format_type: str | None = None
    ) -> str:
        """Export report in specified format.
        
        Args:
            report: Report to export
            format_type: Export format ('json', 'csv', 'html')
            
        Returns:
            Exported report as string
        """
        format_type = format_type or self.config.export_format
        
        if format_type == 'json':
            return self._export_json(report)
        elif format_type == 'csv':
            return self._export_csv(report)
        elif format_type == 'html':
            return self._export_html(report)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")

    def get_dashboard_data(
        self, 
        strategy_results: dict[str, AnalyticsResult]
    ) -> dict[str, Any]:
        """Generate data for real-time dashboard.
        
        Args:
            strategy_results: Current strategy analytics results
            
        Returns:
            Dashboard data dictionary
        """
        dashboard_data = {
            'timestamp': datetime.now(),
            'total_strategies': len(strategy_results),
            'strategies': {},
            'portfolio_summary': {},
            'alerts': [],
            'performance_chart_data': [],
            'risk_indicators': {}
        }
        
        # Process each strategy
        total_profit = 0.0
        total_trades = 0
        all_alerts = []
        
        for strategy_id, result in strategy_results.items():
            metrics = result.metrics
            
            # Extract key metrics
            trade_metrics = metrics.get('trade_metrics')
            performance_metrics = metrics.get('performance_metrics')
            
            strategy_data = {
                'total_trades': getattr(trade_metrics, 'total_trades', 0),
                'total_profit': getattr(trade_metrics, 'total_profit', 0.0),
                'win_rate': getattr(trade_metrics, 'win_rate', 0.0),
                'profit_factor': getattr(trade_metrics, 'profit_factor', 0.0),
                'max_drawdown': getattr(performance_metrics, 'max_drawdown', 0.0),
                'sharpe_ratio': getattr(performance_metrics, 'sharpe_ratio', 0.0),
                'last_updated': result.timestamp
            }
            
            dashboard_data['strategies'][strategy_id] = strategy_data
            
            # Aggregate portfolio data
            total_profit += strategy_data['total_profit']
            total_trades += strategy_data['total_trades']
            
            # Collect alerts
            if result.alerts:
                all_alerts.extend(result.alerts)
        
        # Portfolio summary
        dashboard_data['portfolio_summary'] = {
            'total_profit': total_profit,
            'total_trades': total_trades,
            'avg_profit_per_trade': total_profit / max(total_trades, 1),
            'active_strategies': len([
                s for s in dashboard_data['strategies'].values() 
                if s['total_trades'] > 0
            ])
        }
        
        # Recent alerts
        dashboard_data['alerts'] = sorted(
            all_alerts, 
            key=lambda x: x.get('timestamp', datetime.min),
            reverse=True
        )[:10]  # Latest 10 alerts
        
        return dashboard_data

    def _generate_strategy_summary(
        self, 
        trade_metrics: TradeMetrics,
        performance_metrics: PerformanceMetrics,
        risk_metrics: RiskMetrics
    ) -> dict[str, Any]:
        """Generate strategy performance summary.
        
        Args:
            trade_metrics: Trading statistics
            performance_metrics: Performance metrics
            risk_metrics: Risk metrics
            
        Returns:
            Summary dictionary
        """
        return {
            'total_return': performance_metrics.total_return,
            'annualized_return': performance_metrics.annualized_return,
            'max_drawdown': performance_metrics.max_drawdown,
            'sharpe_ratio': performance_metrics.sharpe_ratio,
            'win_rate': trade_metrics.win_rate,
            'profit_factor': trade_metrics.profit_factor,
            'total_trades': trade_metrics.total_trades,
            'avg_trade_profit': trade_metrics.total_profit / max(trade_metrics.total_trades, 1),
            'risk_score': self._calculate_risk_score(performance_metrics, risk_metrics),
            'performance_grade': self._calculate_performance_grade(
                performance_metrics, trade_metrics
            )
        }

    def _generate_recommendations(
        self, 
        trade_metrics: TradeMetrics,
        performance_metrics: PerformanceMetrics,
        risk_metrics: RiskMetrics
    ) -> list[str]:
        """Generate strategy recommendations.
        
        Args:
            trade_metrics: Trading statistics
            performance_metrics: Performance metrics
            risk_metrics: Risk metrics
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Win rate analysis
        if trade_metrics.win_rate < 0.5:
            recommendations.append(
                "Consider improving entry signals - win rate below 50%"
            )
        
        # Risk analysis
        if performance_metrics.max_drawdown < -0.15:
            recommendations.append(
                "High drawdown detected - consider implementing better risk management"
            )
        
        # Performance analysis
        if performance_metrics.sharpe_ratio < 1.0:
            recommendations.append(
                "Low risk-adjusted returns - strategy may need optimization"
            )
        
        # Trade frequency analysis
        if trade_metrics.total_trades < 10:
            recommendations.append(
                "Low trade frequency - consider expanding trading opportunities"
            )
        elif trade_metrics.total_trades > 1000:
            recommendations.append(
                "High trade frequency - monitor transaction costs impact"
            )
        
        # Profit factor analysis
        if trade_metrics.profit_factor < 1.2:
            recommendations.append(
                "Low profit factor - focus on improving trade quality"
            )
        
        if not recommendations:
            recommendations.append("Strategy performance is within acceptable parameters")
        
        return recommendations

    def _calculate_portfolio_metrics(
        self, 
        strategy_reports: list[PerformanceReport]
    ) -> dict[str, Any]:
        """Calculate portfolio-level metrics.
        
        Args:
            strategy_reports: List of strategy reports
            
        Returns:
            Portfolio metrics dictionary
        """
        if not strategy_reports:
            return {}
        
        # Aggregate metrics
        total_profit = sum(r.trade_metrics.total_profit for r in strategy_reports)
        total_trades = sum(r.trade_metrics.total_trades for r in strategy_reports)
        
        # Calculate weighted averages
        weights = [r.trade_metrics.total_trades for r in strategy_reports]
        total_weight = sum(weights) or 1
        
        weighted_win_rate = sum(
            r.trade_metrics.win_rate * w for r, w in zip(strategy_reports, weights)
        ) / total_weight
        
        weighted_sharpe = sum(
            r.performance_metrics.sharpe_ratio * w 
            for r, w in zip(strategy_reports, weights)
        ) / total_weight
        
        # Max drawdown across strategies
        max_drawdown = min(r.performance_metrics.max_drawdown for r in strategy_reports)
        
        return {
            'total_profit': total_profit,
            'total_trades': total_trades,
            'weighted_win_rate': weighted_win_rate,
            'weighted_sharpe_ratio': weighted_sharpe,
            'max_portfolio_drawdown': max_drawdown,
            'strategy_count': len(strategy_reports),
            'profitable_strategies': len([
                r for r in strategy_reports 
                if r.trade_metrics.total_profit > 0
            ])
        }

    def _calculate_portfolio_correlation(
        self, 
        strategy_results: dict[str, AnalyticsResult]
    ) -> dict[str, dict[str, float]]:
        """Calculate strategy correlation matrix.
        
        Args:
            strategy_results: Strategy analytics results
            
        Returns:
            Correlation matrix
        """
        # Extract returns data for correlation calculation
        strategy_returns = {}
        
        for strategy_id, result in strategy_results.items():
            # Simplified: use trade profits as returns proxy
            metrics = result.metrics
            total_trades = metrics.get('total_trades', 0)
            
            if total_trades > 0:
                # Generate synthetic return series based on metrics
                trade_metrics = metrics.get('trade_metrics')
                if trade_metrics:
                    avg_return = getattr(trade_metrics, 'total_profit', 0) / total_trades
                    # Create simple return series (in real implementation, use actual returns)
                    strategy_returns[strategy_id] = [avg_return] * min(total_trades, 100)
        
        # Calculate correlation using metrics calculator
        if len(strategy_returns) > 1:
            return self.metrics_calculator.calculate_strategy_correlation(strategy_returns)
        else:
            return {}

    def _generate_portfolio_risk_summary(
        self, 
        strategy_reports: list[PerformanceReport]
    ) -> dict[str, Any]:
        """Generate portfolio risk summary.
        
        Args:
            strategy_reports: List of strategy reports
            
        Returns:
            Risk summary dictionary
        """
        if not strategy_reports:
            return {}
        
        # Aggregate risk metrics
        drawdowns = [r.performance_metrics.max_drawdown for r in strategy_reports]
        sharpe_ratios = [r.performance_metrics.sharpe_ratio for r in strategy_reports]
        
        return {
            'avg_max_drawdown': sum(drawdowns) / len(drawdowns),
            'worst_drawdown': min(drawdowns),
            'best_drawdown': max(drawdowns),
            'avg_sharpe_ratio': sum(sharpe_ratios) / len(sharpe_ratios),
            'risk_level': self._assess_portfolio_risk_level(strategy_reports),
            'diversification_score': self._calculate_diversification_score(strategy_reports)
        }

    def _calculate_risk_score(
        self, 
        performance_metrics: PerformanceMetrics,
        risk_metrics: RiskMetrics
    ) -> float:
        """Calculate overall risk score.
        
        Args:
            performance_metrics: Performance metrics
            risk_metrics: Risk metrics
            
        Returns:
            Risk score (0-100, lower is better)
        """
        score = 0.0
        
        # Drawdown component (40% weight)
        drawdown_score = min(abs(performance_metrics.max_drawdown) * 100, 50)
        score += drawdown_score * 0.4
        
        # Volatility component (30% weight)
        volatility_score = min(performance_metrics.volatility * 100, 50)
        score += volatility_score * 0.3
        
        # Sharpe ratio component (30% weight, inverted)
        sharpe_score = max(0, 50 - performance_metrics.sharpe_ratio * 10)
        score += sharpe_score * 0.3
        
        return min(score, 100.0)

    def _calculate_performance_grade(
        self, 
        performance_metrics: PerformanceMetrics,
        trade_metrics: TradeMetrics
    ) -> str:
        """Calculate performance grade.
        
        Args:
            performance_metrics: Performance metrics
            trade_metrics: Trade metrics
            
        Returns:
            Performance grade (A-F)
        """
        score = 0
        
        # Sharpe ratio (40 points)
        if performance_metrics.sharpe_ratio > 2.0:
            score += 40
        elif performance_metrics.sharpe_ratio > 1.0:
            score += 30
        elif performance_metrics.sharpe_ratio > 0.5:
            score += 20
        elif performance_metrics.sharpe_ratio > 0:
            score += 10
        
        # Win rate (30 points)
        if trade_metrics.win_rate > 0.6:
            score += 30
        elif trade_metrics.win_rate > 0.5:
            score += 20
        elif trade_metrics.win_rate > 0.4:
            score += 15
        elif trade_metrics.win_rate > 0.3:
            score += 10
        
        # Profit factor (30 points)
        if trade_metrics.profit_factor > 2.0:
            score += 30
        elif trade_metrics.profit_factor > 1.5:
            score += 20
        elif trade_metrics.profit_factor > 1.2:
            score += 15
        elif trade_metrics.profit_factor > 1.0:
            score += 10
        
        # Convert to grade
        if score >= 90:
            return 'A+'
        elif score >= 80:
            return 'A'
        elif score >= 70:
            return 'B'
        elif score >= 60:
            return 'C'
        elif score >= 50:
            return 'D'
        else:
            return 'F'

    def _assess_portfolio_risk_level(
        self, 
        strategy_reports: list[PerformanceReport]
    ) -> str:
        """Assess overall portfolio risk level.
        
        Args:
            strategy_reports: List of strategy reports
            
        Returns:
            Risk level ('Low', 'Medium', 'High', 'Extreme')
        """
        if not strategy_reports:
            return 'Unknown'
        
        avg_drawdown = sum(
            r.performance_metrics.max_drawdown for r in strategy_reports
        ) / len(strategy_reports)
        
        if avg_drawdown > -0.05:
            return 'Low'
        elif avg_drawdown > -0.10:
            return 'Medium'
        elif avg_drawdown > -0.20:
            return 'High'
        else:
            return 'Extreme'

    def _calculate_diversification_score(
        self, 
        strategy_reports: list[PerformanceReport]
    ) -> float:
        """Calculate portfolio diversification score.
        
        Args:
            strategy_reports: List of strategy reports
            
        Returns:
            Diversification score (0-100, higher is better)
        """
        if len(strategy_reports) <= 1:
            return 0.0
        
        # Simple diversification based on strategy count and performance variance
        strategy_count_score = min(len(strategy_reports) * 10, 50)
        
        # Performance variance score
        returns = [r.performance_metrics.total_return for r in strategy_reports]
        if len(returns) > 1:
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            variance_score = min(variance * 100, 50)
        else:
            variance_score = 0
        
        return strategy_count_score + variance_score

    def _export_json(self, report: PerformanceReport | PortfolioReport) -> str:
        """Export report as JSON.
        
        Args:
            report: Report to export
            
        Returns:
            JSON string
        """
        # Convert to dictionary and handle datetime serialization
        report_dict = asdict(report)
        
        # Custom datetime serialization
        def datetime_serializer(obj):
            if isinstance(obj, datetime):
                return obj.strftime(self.config.date_format)
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        return json.dumps(
            report_dict, 
            indent=2, 
            default=datetime_serializer,
            ensure_ascii=False
        )

    def _export_csv(self, report: PerformanceReport | PortfolioReport) -> str:
        """Export report as CSV.
        
        Args:
            report: Report to export
            
        Returns:
            CSV string
        """
        output = StringIO()
        
        if isinstance(report, PerformanceReport):
            # Strategy report CSV
            output.write("Metric,Value\n")
            output.write(f"Strategy ID,{report.strategy_id}\n")
            output.write(f"Period Start,{report.period_start}\n")
            output.write(f"Period End,{report.period_end}\n")
            output.write(f"Total Trades,{report.trade_metrics.total_trades}\n")
            output.write(f"Win Rate,{report.trade_metrics.win_rate:.4f}\n")
            output.write(f"Total Profit,{report.trade_metrics.total_profit:.4f}\n")
            output.write(f"Max Drawdown,{report.performance_metrics.max_drawdown:.4f}\n")
            output.write(f"Sharpe Ratio,{report.performance_metrics.sharpe_ratio:.4f}\n")
            
        elif isinstance(report, PortfolioReport):
            # Portfolio report CSV
            output.write("Strategy,Total Trades,Win Rate,Total Profit,Max Drawdown,Sharpe Ratio\n")
            for strategy_report in report.strategy_reports:
                output.write(
                    f"{strategy_report.strategy_id},"
                    f"{strategy_report.trade_metrics.total_trades},"
                    f"{strategy_report.trade_metrics.win_rate:.4f},"
                    f"{strategy_report.trade_metrics.total_profit:.4f},"
                    f"{strategy_report.performance_metrics.max_drawdown:.4f},"
                    f"{strategy_report.performance_metrics.sharpe_ratio:.4f}\n"
                )
        
        return output.getvalue()

    def _export_html(self, report: PerformanceReport | PortfolioReport) -> str:
        """Export report as HTML.
        
        Args:
            report: Report to export
            
        Returns:
            HTML string
        """
        # Basic HTML template (can be expanded with proper templating)
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Xline Analytics Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                .metric { margin: 10px 0; }
                .header { color: #333; border-bottom: 2px solid #ccc; }
            </style>
        </head>
        <body>
        """
        
        if isinstance(report, PerformanceReport):
            html += f"""
            <h1 class="header">Strategy Performance Report: {report.strategy_id}</h1>
            <p><strong>Period:</strong> {report.period_start} to {report.period_end}</p>
            <p><strong>Generated:</strong> {report.generated_at}</p>
            
            <h2>Trade Metrics</h2>
            <div class="metric">Total Trades: {report.trade_metrics.total_trades}</div>
            <div class="metric">Win Rate: {report.trade_metrics.win_rate:.2%}</div>
            <div class="metric">Total Profit: ${report.trade_metrics.total_profit:.2f}</div>
            
            <h2>Performance Metrics</h2>
            <div class="metric">Total Return: {report.performance_metrics.total_return:.2%}</div>
            <div class="metric">Max Drawdown: {report.performance_metrics.max_drawdown:.2%}</div>
            <div class="metric">Sharpe Ratio: {report.performance_metrics.sharpe_ratio:.2f}</div>
            
            <h2>Recommendations</h2>
            <ul>
            """
            for rec in report.recommendations:
                html += f"<li>{rec}</li>"
            html += "</ul>"
        
        html += """
        </body>
        </html>
        """
        
        return html

    def generate_html_report(self, data: dict[str, Any]) -> str:
        """Generate HTML report from data dictionary.
        
        Args:
            data: Report data dictionary
            
        Returns:
            HTML content as string
        """
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Xline Analytics Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .metric { margin: 10px 0; padding: 10px; background: #f5f5f5; }
                .header { color: #333; border-bottom: 2px solid #ccc; }
            </style>
        </head>
        <body>
            <h1 class="header">Analytics Report</h1>
        """
        
        # Add summary section
        if 'summary' in data:
            html += "<h2>Summary</h2>"
            for key, value in data['summary'].items():
                html += f'<div class="metric"><strong>{key}:</strong> {value}</div>'
        
        # Add trade metrics
        if 'trade_metrics' in data:
            html += "<h2>Trade Metrics</h2>"
            for key, value in data['trade_metrics'].items():
                html += f'<div class="metric"><strong>{key}:</strong> {value}</div>'
        
        # Add timestamp
        if 'timestamp' in data:
            html += f'<p><em>Generated: {data["timestamp"]}</em></p>'
        
        html += """
        </body>
        </html>
        """
        
        return html

    def generate_csv_export(self, data: list[dict[str, Any]]) -> str:
        """Generate CSV export from list of data dictionaries.
        
        Args:
            data: List of data dictionaries
            
        Returns:
            CSV content as string
        """
        if not data:
            return ""
        
        # Get headers from first item
        headers = list(data[0].keys())
        csv_lines = [','.join(headers)]
        
        # Add data rows
        for item in data:
            row = []
            for header in headers:
                value = item.get(header, '')
                row.append(str(value))
            csv_lines.append(','.join(row))
        
        return '\n'.join(csv_lines)

    def save_report(self, content: str, file_path: str) -> str:
        """Save report content to file.
        
        Args:
            content: Report content to save
            file_path: Path to save the file
            
        Returns:
            Path where file was saved
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path

    def generate_pdf_report(self, data: dict[str, Any]) -> bytes:
        """Generate PDF report from data dictionary.
        
        Args:
            data: Report data dictionary
            
        Returns:
            PDF content as bytes
        """
        # This would normally use a PDF library like reportlab
        # For now, return mock PDF content
        html_content = self.generate_html_report(data)
        return html_content.encode('utf-8')

    def format_currency(self, amount: float) -> str:
        """Format currency amount for display.
        
        Args:
            amount: Currency amount
            
        Returns:
            Formatted currency string
        """
        if amount < 0:
            return f"-${abs(amount):,.2f}"
        return f"${amount:,.2f}"

    def calculate_statistics(self, trades: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate statistics from trades data.
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            Statistics dictionary
        """
        if not trades:
            return {}
        
        total_profit = sum(trade.get('profit', 0) for trade in trades)
        total_duration = sum(trade.get('duration', 0) for trade in trades)
        average_duration = total_duration / len(trades) if trades else 0
        
        return {
            'total_profit': total_profit,
            'trade_count': len(trades),
            'average_duration': average_duration,
            'average_profit': total_profit / len(trades) if trades else 0
        }
