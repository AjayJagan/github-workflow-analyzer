from typing import List, Dict
from analyzer import WorkflowStats


class DashboardGenerator:
    def __init__(self, title: str = "GitHub Workflow Performance Dashboard"):
        self.title = title
    
    def generate_charts(self, stats: List[WorkflowStats], repo_summary: Dict, trends: Dict, patterns: Dict) -> Dict[str, str]:
        """Generate simplified charts focusing on actionable workflows."""
        charts = {}
        
        # 1. Top Problematic Workflows - What needs to be fixed
        charts['top_workflows'] = self._create_top_problematic_workflows_chart(stats)
        
        # 2. Repository Scorecard - Performance Grades
        charts['repository_scorecard'] = self._create_repository_scorecard(repo_summary)
        
        return charts
    
    def _create_top_problematic_workflows_chart(self, stats: List[WorkflowStats]) -> str:
        """Create a simple list of top problematic workflows that need attention."""
        if not stats:
            return "<p>No workflow data available</p>"
        
        # Filter to problematic workflows and take top 20
        problematic_workflows = [s for s in stats if s.optimization_priority in ['critical', 'high']]
        top_workflows = problematic_workflows[:20]
        
        if not top_workflows:
            return """
            <div style="font-family: 'Segoe UI', Arial, sans-serif; background: white; padding: 25px; border-radius: 10px; border: 1px solid #ddd; text-align: center;">
                <h3 style="color: #4caf50; margin-bottom: 15px;">
                    <i class="fas fa-check-circle" style="margin-right: 10px;"></i>
                    All Workflows Optimized!
                </h3>
                <p style="color: #666; margin: 0;">No critical or high priority workflow issues found. Your CI/CD is well optimized!</p>
            </div>
            """
        
        html_content = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; background: white; padding: 25px; border-radius: 10px; border: 1px solid #ddd;">
            <h3 style="margin-top: 0; color: #151515; border-bottom: 2px solid #c9190b; padding-bottom: 15px; display: flex; align-items: center;">
                <i class="fas fa-exclamation-triangle" style="color: #c9190b; margin-right: 10px;"></i>
                Top Problematic Workflows
            </h3>
            <div style="margin-bottom: 20px; padding: 15px; background: #fdf2d0; border-left: 4px solid #f0ab00; border-radius: 4px;">
                <strong>Found {len(problematic_workflows)} workflows needing attention.</strong> 
                These workflows are either slow (>10min) and frequent (PR/Push triggered) or extremely slow (>15min).
            </div>
            <div style="max-height: 600px; overflow-y: auto; padding-right: 10px; scrollbar-width: thin; scrollbar-color: #e0e0e0 transparent;">
        """
        
        for i, workflow in enumerate(top_workflows, 1):
            repo_name = workflow.repository.split('/')[-1]
            
            # Determine priority styling (OpenShift colors)
            if workflow.optimization_priority == 'critical':
                priority_color = "#c9190b"  # OpenShift danger color
                priority_bg = "#faeae8"     # Light danger background
                priority_icon = "🔴"
                priority_label = "CRITICAL"
            else:  # high
                priority_color = "#f0ab00"  # OpenShift warning color
                priority_bg = "#fdf2d0"     # Light warning background
                priority_icon = "🟠"
                priority_label = "HIGH"
            
            # Calculate daily impact
            daily_impact = workflow.avg_duration_minutes * workflow.frequency_score
            
            html_content += f"""
            <div style="margin-bottom: 15px; padding: 15px; background: {priority_bg}; border-left: 4px solid {priority_color}; border-radius: 6px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div style="flex: 1;">
                        <div style="display: flex; align-items: center; margin-bottom: 8px;">
                            <span style="font-size: 1.1em; margin-right: 8px;">{priority_icon}</span>
                            <span style="background: {priority_color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75em; font-weight: bold; margin-right: 10px;">
                                #{i} {priority_label}
                            </span>
                            <strong style="color: #333; font-size: 1.1em;">{repo_name}</strong>
                        </div>
                        <div style="color: #333; font-size: 1.05em; font-weight: 500; margin-bottom: 6px;">
                            {workflow.workflow_name}
                        </div>
                        <div style="color: #666; font-size: 0.9em; margin-bottom: 8px;">
                            <strong>Duration:</strong> {workflow.avg_duration_minutes:.1f} minutes • 
                            <strong>Frequency:</strong> {workflow.frequency_score:.1f} runs/day
                        </div>
                        <div style="color: #666; font-size: 0.85em;">
                            <strong>Repository:</strong> {workflow.repository}
                        </div>
                    </div>
                    <div style="text-align: right; margin-left: 15px;">
                        <div style="background: {priority_color}; color: white; padding: 6px 10px; border-radius: 4px; font-size: 0.9em; font-weight: bold; margin-bottom: 4px;">
                            {workflow.avg_duration_minutes:.1f}m
                        </div>
                        <div style="font-size: 0.7em; color: #666;">avg duration</div>
                    </div>
                </div>
            </div>
            """
        
        html_content += """
            </div>
        </div>
        """
        
        return html_content

    def _create_repository_scorecard(self, repo_summary: Dict) -> str:
        """Create a repository scorecard showing performance grades for each repository."""
        if not repo_summary:
            return "<p>No repository data available</p>"
        
        html_content = """
        <div style="font-family: 'Segoe UI', Arial, sans-serif; background: white; padding: 25px; border-radius: 10px; border: 1px solid #ddd;">
            <h3 style="margin-top: 0; color: #151515; border-bottom: 2px solid #06c; padding-bottom: 15px; display: flex; align-items: center;">
                <i class="fas fa-trophy" style="color: #06c; margin-right: 10px;"></i>
                Repository Performance Scorecard
            </h3>
            <div style="max-height: 400px; overflow-y: auto; padding-right: 10px; scrollbar-width: thin; scrollbar-color: #e0e0e0 transparent;">
        """
        
        # Sort repositories by percentage of problematic workflows, then by count (most problematic first)
        def sort_key(item):
            repo_name, data = item
            total = data['total_workflows']
            problematic = data['problematic_workflows']
            percentage = (problematic / total * 100) if total > 0 else 0
            return (-percentage, -problematic)  # Negative for descending order
        
        sorted_repos = sorted(repo_summary.items(), key=sort_key)
        
        for repo_name, data in sorted_repos:
            total_workflows = data['total_workflows']
            problematic_workflows = data['problematic_workflows']
            short_name = repo_name.split('/')[-1]
            
            # Calculate percentage
            percentage = (problematic_workflows / total_workflows * 100) if total_workflows > 0 else 0
            
            # Determine color based on problem severity
            if percentage >= 50:
                severity_color = "#c9190b"  # OpenShift danger red
                severity_bg = "#faeae8"
                severity_label = "HIGH RISK"
            elif percentage >= 25:
                severity_color = "#f0ab00"  # OpenShift warning yellow
                severity_bg = "#fdf2d0"
                severity_label = "NEEDS ATTENTION"
            elif percentage > 0:
                severity_color = "#6a6e73"  # OpenShift gray
                severity_bg = "#f0f0f0"
                severity_label = "MINOR ISSUES"
            else:
                severity_color = "#3e8635"  # OpenShift success green
                severity_bg = "#f3faf2"
                severity_label = "HEALTHY"
            
            html_content += f"""
            <div style="margin-bottom: 15px; padding: 15px; background: {severity_bg}; border-radius: 6px; border: 1px solid #e9ecef; border-left: 4px solid {severity_color};">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="flex: 1;">
                        <div style="display: flex; align-items: center; margin-bottom: 5px;">
                            <h4 style="margin: 0; color: #151515; font-size: 1.1em; margin-right: 10px;">{short_name}</h4>
                            <span style="background: {severity_color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.7em; font-weight: bold;">
                                {severity_label}
                            </span>
                        </div>
                        <div style="color: #6a6e73; font-size: 0.85em; margin-top: 2px;">{repo_name}</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 1.4em; font-weight: bold; color: {severity_color}; margin-bottom: 2px;">
                            {percentage:.0f}%
                        </div>
                        <div style="font-size: 0.9em; color: #151515; font-weight: 500;">
                            {problematic_workflows} / {total_workflows}
                        </div>
                        <div style="font-size: 0.75em; color: #6a6e73;">problems / total</div>
                    </div>
                </div>
            </div>
            """
        
        html_content += """
            </div>
        </div>
        """
        
        return html_content
    
    def generate_summary_stats(self, stats: List[WorkflowStats], repo_summary: Dict, trends: Dict) -> Dict:
        """Generate summary statistics for the dashboard."""
        from datetime import datetime
        
        total_workflows = len(stats)
        problematic_workflows = len([s for s in stats if s.optimization_priority in ['critical', 'high']])
        
        avg_duration = sum(s.avg_duration_minutes for s in stats) / len(stats) if stats else 0
        total_runs = sum(s.total_runs for s in stats)
        
        return {
            'total_workflows': total_workflows,
            'problematic_workflows': problematic_workflows,
            'total_repositories': len(repo_summary),
            'avg_duration_minutes': round(avg_duration, 1),
            'total_runs_analyzed': total_runs,
            'analysis_period_days': 15,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        }