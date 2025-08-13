import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
from typing import List, Dict
from datetime import datetime
from analyzer import WorkflowStats


class DashboardGenerator:
    def __init__(self, title: str = "GitHub Workflow Performance Dashboard"):
        self.title = title
        self.colors = {
            'primary': '#1f77b4',
            'secondary': '#ff7f0e',
            'success': '#2ca02c',
            'warning': '#d62728',
            'info': '#9467bd',
            'background': '#f8f9fa'
        }
    
    def generate_charts(self, stats: List[WorkflowStats], repo_summary: Dict, trends: Dict, patterns: Dict) -> Dict[str, str]:
        """Generate all dashboard charts and return HTML strings."""
        charts = {}
        
        # 1. Workflow Duration vs Frequency Scatter Plot
        charts['duration_frequency'] = self._create_duration_frequency_chart(stats)
        
        # 2. Repository Summary Bar Chart
        charts['repository_summary'] = self._create_repository_summary_chart(repo_summary)
        
        # 3. Top Problematic Workflows
        charts['top_workflows'] = self._create_top_workflows_chart(stats[:10])
        
        # 4. Daily Trends Line Chart
        charts['daily_trends'] = self._create_daily_trends_chart(trends)
        
        # 5. Trigger Events Pie Chart
        charts['trigger_events'] = self._create_trigger_events_chart(patterns)
        
        # 6. Hourly Patterns Heatmap
        charts['hourly_patterns'] = self._create_hourly_patterns_chart(patterns)
        
        # 7. Duration Distribution Histogram
        charts['duration_distribution'] = self._create_duration_distribution_chart(stats)
        
        # 8. Performance Impact Overview
        charts['performance_impact'] = self._create_performance_impact_chart(stats)
        
        return charts
    
    def _create_duration_frequency_chart(self, stats: List[WorkflowStats]) -> str:
        """Create an intuitive scatter plot showing workflow performance with clear problematic zones."""
        
        if not stats:
            return "<p>No workflow data available</p>"
        
        durations = [s.avg_duration_minutes for s in stats]
        frequencies = [s.frequency_score for s in stats]
        workflow_names = [f"{s.repository.split('/')[-1]}: {s.workflow_name[:20]}..." for s in stats]
        
        # Categorize workflows by priority zones
        colors = []
        symbols = []
        sizes = []
        
        for s in stats:
            if s.avg_duration_minutes >= 10 and s.frequency_score >= 1:
                colors.append('#d32f2f')  # Red - Critical (frequent + slow)
                symbols.append('diamond')
                sizes.append(12)
            elif s.avg_duration_minutes >= 10:
                colors.append('#ff9800')  # Orange - High priority (slow but infrequent)
                symbols.append('triangle-up')
                sizes.append(10)
            elif s.frequency_score >= 2:
                colors.append('#ffc107')  # Yellow - Medium priority (fast but very frequent)
                symbols.append('circle')
                sizes.append(8)
            else:
                colors.append('#4caf50')  # Green - Low priority
                symbols.append('circle')
                sizes.append(6)
        
        fig = go.Figure()
        
        # Add scatter plot
        fig.add_trace(go.Scatter(
            x=frequencies,
            y=durations,
            mode='markers',
            marker=dict(
                color=colors,
                symbol=symbols,
                size=sizes,
                line=dict(width=1, color='white')
            ),
            text=workflow_names,
            hovertemplate='<b>%{text}</b><br>' +
                         'Frequency: %{x:.1f} runs/day<br>' +
                         'Duration: %{y:.1f} minutes<br>' +
                         '<extra></extra>',
            name='Workflows'
        ))
        
        # Add threshold lines
        max_freq = max(frequencies) if frequencies else 5
        max_duration = max(durations) if durations else 30
        
        # Vertical line at 1 run/day frequency threshold
        fig.add_vline(x=1, line_dash="dash", line_color="gray", opacity=0.5,
                     annotation_text="High Frequency", annotation_position="top")
        
        # Horizontal line at 10 minutes duration threshold
        fig.add_hline(y=10, line_dash="dash", line_color="gray", opacity=0.5,
                     annotation_text="Slow Execution", annotation_position="right")
        
        # Add colored background zones
        fig.add_shape(
            type="rect",
            x0=1, y0=10, x1=max_freq * 1.1, y1=max_duration * 1.1,
            fillcolor="rgba(211, 47, 47, 0.1)",
            line=dict(width=0),
            layer="below"
        )
        
        # Add zone labels
        fig.add_annotation(
            x=max_freq * 0.8, y=max_duration * 0.9,
            text="<b>🚨 CRITICAL ZONE</b><br>Frequent + Slow",
            showarrow=False,
            bgcolor="rgba(211, 47, 47, 0.8)",
            bordercolor="white",
            borderwidth=1,
            font=dict(color="white", size=10)
        )
        
        fig.update_layout(
            title="Workflow Performance Matrix - Focus on Red Diamond Zone",
            xaxis_title="Frequency (runs per day)",
            yaxis_title="Average Duration (minutes)",
            template="plotly_white",
            height=500,
            showlegend=False,
            xaxis=dict(range=[0, max_freq * 1.1]),
            yaxis=dict(range=[0, max_duration * 1.1])
        )
        
        return fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    def _create_repository_summary_chart(self, repo_summary: Dict) -> str:
        """Create repository summary bar chart."""
        repos = list(repo_summary.keys())
        total_workflows = [repo_summary[repo]['total_workflows'] for repo in repos]
        problematic_workflows = [repo_summary[repo]['problematic_workflows'] for repo in repos]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Total Workflows',
            x=[repo.split('/')[-1] for repo in repos],
            y=total_workflows,
            marker_color=self.colors['primary']
        ))
        
        fig.add_trace(go.Bar(
            name='Problematic Workflows',
            x=[repo.split('/')[-1] for repo in repos],
            y=problematic_workflows,
            marker_color=self.colors['warning']
        ))
        
        fig.update_layout(
            title="Workflow Analysis by Repository",
            xaxis_title="Repository",
            yaxis_title="Number of Workflows",
            barmode='group',
            template="plotly_white",
            height=400
        )
        
        return fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    def _create_top_workflows_chart(self, top_stats: List[WorkflowStats]) -> str:
        """Create horizontal bar chart of top problematic workflows."""
        if not top_stats:
            return "<p>No data available</p>"
        
        fig = go.Figure()
        
        y_labels = [f"{stat.repository.split('/')[-1]}: {stat.workflow_name[:30]}" for stat in top_stats]
        
        fig.add_trace(go.Bar(
            x=[stat.combined_score for stat in top_stats],
            y=y_labels,
            orientation='h',
            marker_color=[self.colors['warning'] if stat.combined_score > 10 else self.colors['secondary'] for stat in top_stats],
            text=[f"{stat.avg_duration_minutes:.1f}m ({stat.total_runs} runs)" for stat in top_stats],
            textposition="inside"
        ))
        
        fig.update_layout(
            title="Top 10 Problematic Workflows",
            xaxis_title="Combined Impact Score",
            yaxis_title="Workflow",
            template="plotly_white",
            height=600,
            margin=dict(l=200)
        )
        
        return fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    def _create_daily_trends_chart(self, trends: Dict) -> str:
        """Create daily trends line chart."""
        daily_data = trends.get('daily_trends', [])
        if not daily_data:
            return "<p>No trend data available</p>"
        
        dates = [data['date'] for data in daily_data]
        runs_count = [data['runs_count'] for data in daily_data]
        avg_duration = [data['avg_duration_minutes'] for data in daily_data]
        
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig.add_trace(
            go.Scatter(x=dates, y=runs_count, name="Daily Runs", 
                      line=dict(color=self.colors['primary'])),
            secondary_y=False,
        )
        
        fig.add_trace(
            go.Scatter(x=dates, y=avg_duration, name="Avg Duration", 
                      line=dict(color=self.colors['secondary'])),
            secondary_y=True,
        )
        
        fig.update_xaxes(title_text="Date")
        fig.update_yaxes(title_text="Number of Runs", secondary_y=False)
        fig.update_yaxes(title_text="Average Duration (minutes)", secondary_y=True)
        
        fig.update_layout(
            title="Daily Workflow Trends",
            template="plotly_white",
            height=400
        )
        
        return fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    def _create_trigger_events_chart(self, patterns: Dict) -> str:
        """Create pie chart of trigger events."""
        trigger_events = patterns.get('trigger_events', {})
        if not trigger_events:
            return "<p>No trigger event data available</p>"
        
        fig = go.Figure(data=[go.Pie(
            labels=list(trigger_events.keys()),
            values=list(trigger_events.values()),
            hole=.3
        )])
        
        fig.update_layout(
            title="Workflow Trigger Events Distribution",
            template="plotly_white",
            height=400
        )
        
        return fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    def _create_hourly_patterns_chart(self, patterns: Dict) -> str:
        """Create heatmap of hourly patterns."""
        hourly_data = patterns.get('hourly_patterns', {})
        if not hourly_data:
            return "<p>No hourly pattern data available</p>"
        
        hours = list(range(24))
        durations = [hourly_data.get(hour, 0) for hour in hours]
        
        fig = go.Figure(data=go.Heatmap(
            z=[durations],
            x=hours,
            y=['Average Duration'],
            colorscale='RdYlBu_r',
            hoverongaps=False
        ))
        
        fig.update_layout(
            title="Workflow Duration by Hour of Day",
            xaxis_title="Hour of Day",
            template="plotly_white",
            height=200
        )
        
        return fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    def _create_duration_distribution_chart(self, stats: List[WorkflowStats]) -> str:
        """Create histogram of duration distribution."""
        durations = [stat.avg_duration_minutes for stat in stats]
        
        fig = go.Figure(data=[go.Histogram(
            x=durations,
            nbinsx=20,
            marker_color=self.colors['info'],
            opacity=0.7
        )])
        
        fig.add_vline(x=10, line_dash="dash", line_color="red", 
                     annotation_text="Threshold")
        
        fig.update_layout(
            title="Workflow Duration Distribution",
            xaxis_title="Average Duration (minutes)",
            yaxis_title="Number of Workflows",
            template="plotly_white",
            height=400
        )
        
        return fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    def _create_performance_impact_chart(self, stats: List[WorkflowStats]) -> str:
        """Create a clean, scalable chart showing performance impact by workflow categories."""
        
        if not stats:
            return "<p>No workflow data available</p>"
        
        # Categorize workflows and calculate total time impact
        categories = {
            'Critical': {'count': 0, 'total_time': 0, 'color': '#d32f2f', 'desc': 'Frequent + Slow (≥10min, ≥1/day)'},
            'High': {'count': 0, 'total_time': 0, 'color': '#ff9800', 'desc': 'Slow but Infrequent (≥10min)'},
            'Medium': {'count': 0, 'total_time': 0, 'color': '#ffc107', 'desc': 'Fast but Very Frequent (≥2/day)'},
            'Low': {'count': 0, 'total_time': 0, 'color': '#4caf50', 'desc': 'Fast and Infrequent'}
        }
        
        critical_workflows = []
        
        for s in stats:
            # Calculate daily time impact (frequency * duration)
            daily_impact = s.frequency_score * s.avg_duration_minutes
            
            if s.avg_duration_minutes >= 10 and s.frequency_score >= 1:
                categories['Critical']['count'] += 1
                categories['Critical']['total_time'] += daily_impact
                critical_workflows.append((s, daily_impact))
            elif s.avg_duration_minutes >= 10:
                categories['High']['count'] += 1
                categories['High']['total_time'] += daily_impact
            elif s.frequency_score >= 2:
                categories['Medium']['count'] += 1
                categories['Medium']['total_time'] += daily_impact
            else:
                categories['Low']['count'] += 1
                categories['Low']['total_time'] += daily_impact
        
        # Sort critical workflows by impact and take top 15 for visualization
        critical_workflows.sort(key=lambda x: x[1], reverse=True)
        top_critical = critical_workflows[:15]
        
        # Create a cleaner, single focused chart
        fig = go.Figure()
        
        # Main chart: Category impact with dual y-axis
        cat_names = list(categories.keys())
        time_impacts = [categories[cat]['total_time'] for cat in cat_names]
        counts = [categories[cat]['count'] for cat in cat_names]
        colors = [categories[cat]['color'] for cat in cat_names]
        
        # Bar chart showing time impact
        fig.add_trace(go.Bar(
            x=cat_names,
            y=time_impacts,
            name='Daily Time Impact (min)',
            marker_color=colors,
            text=[f"{t:.0f}m<br>({c} workflows)" for t, c in zip(time_impacts, counts)],
            textposition="outside",
            hovertemplate='<b>%{x}</b><br>' +
                         'Daily Impact: %{y:.0f} minutes<br>' +
                         'Workflow Count: %{customdata}<br>' +
                         '<extra></extra>',
            customdata=counts
        ))
        
        # Calculate potential savings
        total_critical_time = categories['Critical']['total_time']
        total_workflows = len(stats)
        critical_percentage = (categories['Critical']['count'] / total_workflows * 100) if total_workflows > 0 else 0
        
        # Add efficiency metrics as annotations
        annotations = []
        
        if total_critical_time > 0:
            # Main savings annotation
            annotations.append(dict(
                text=f"<b>💰 Optimization ROI</b><br>" +
                     f"<span style='color: #d32f2f; font-size: 1.2em;'>{total_critical_time:.0f} min/day</span> from critical workflows<br>" +
                     f"Weekly: <b>{total_critical_time * 7:.0f} min</b> | Monthly: <b>{total_critical_time * 30/60:.1f} hours</b><br>" +
                     f"<small>{categories['Critical']['count']} workflows ({critical_percentage:.1f}% of total)</small>",
                xref="paper", yref="paper",
                x=0.98, y=0.98,
                showarrow=False,
                bgcolor="rgba(255, 243, 224, 0.9)",
                bordercolor="#ff9800",
                borderwidth=2,
                font=dict(size=12),
                align="left",
                xanchor="right",
                yanchor="top"
            ))
        
        # Add workflow breakdown if there are critical workflows
        if top_critical:
            breakdown_text = "<b>🎯 Top Critical Workflows:</b><br>"
            for i, (workflow, impact) in enumerate(top_critical[:5]):
                repo_name = workflow.repository.split('/')[-1]
                breakdown_text += f"{i+1}. {repo_name}: {workflow.workflow_name[:20]}... ({impact:.1f}m/day)<br>"
            
            if len(critical_workflows) > 5:
                breakdown_text += f"<small>...and {len(critical_workflows) - 5} more critical workflows</small>"
            
            annotations.append(dict(
                text=breakdown_text,
                xref="paper", yref="paper",
                x=0.02, y=0.98,
                showarrow=False,
                bgcolor="rgba(255, 235, 238, 0.9)",
                bordercolor="#d32f2f",
                borderwidth=1,
                font=dict(size=10),
                align="left",
                xanchor="left",
                yanchor="top"
            ))
        
        fig.update_layout(
            title=dict(
                text="Performance Impact by Priority Category",
                font=dict(size=16),
                x=0.5
            ),
            xaxis_title="Priority Category",
            yaxis_title="Daily Time Impact (minutes)",
            template="plotly_white",
            height=500,
            showlegend=False,
            annotations=annotations,
            margin=dict(t=60, b=40, l=50, r=50)
        )
        
        # Add category descriptions as x-axis labels with hover info
        fig.update_traces(
            hovertemplate='<b>%{x} Priority</b><br>' +
                         'Daily Impact: %{y:.0f} minutes<br>' +
                         'Workflow Count: %{customdata}<br>' +
                         '<extra></extra>'
        )
        
        return fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    def generate_summary_stats(self, stats: List[WorkflowStats], repo_summary: Dict, trends: Dict) -> Dict:
        """Generate summary statistics for the dashboard."""
        total_workflows = len(stats)
        problematic_workflows = len([s for s in stats if s.combined_score > 5])
        
        avg_duration = sum(s.avg_duration_minutes for s in stats) / len(stats) if stats else 0
        total_runs = sum(s.total_runs for s in stats)
        
        return {
            'total_workflows': total_workflows,
            'problematic_workflows': problematic_workflows,
            'total_repositories': len(repo_summary),
            'avg_duration_minutes': round(avg_duration, 1),
            'total_runs_analyzed': total_runs,
            'analysis_period_days': trends.get('total_analysis_days', 15),
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        }