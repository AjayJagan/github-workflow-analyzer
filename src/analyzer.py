from typing import List, Dict
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass
from github_client import WorkflowRun


@dataclass
class WorkflowStats:
    workflow_name: str
    repository: str
    total_runs: int
    avg_duration_minutes: float
    max_duration_minutes: float
    min_duration_minutes: float
    success_rate: float
    frequency_score: float
    trigger_events: List[str]
    recent_runs: List[WorkflowRun]
    # New trigger analysis fields
    is_pr_triggered: bool = False
    is_push_triggered: bool = False
    is_high_frequency_trigger: bool = False
    trigger_frequency_score: float = 0.0
    optimization_priority: str = "low"


class WorkflowAnalyzer:
    def __init__(self, duration_threshold_minutes: int = 10):
        self.duration_threshold_minutes = duration_threshold_minutes
    
    def analyze_workflows(self, runs: List[WorkflowRun]) -> List[WorkflowStats]:
        """Analyze workflow runs and return statistics."""
        # Group runs by workflow and repository
        workflow_groups = defaultdict(list)
        
        for run in runs:
            key = (run.repository, run.workflow_name)
            workflow_groups[key].append(run)
        
        stats = []
        
        for (repo, workflow_name), workflow_runs in workflow_groups.items():
            if len(workflow_runs) == 0:
                continue
            
            # Calculate statistics
            durations_minutes = [r.duration_seconds / 60 for r in workflow_runs]
            avg_duration = sum(durations_minutes) / len(durations_minutes)
            max_duration = max(durations_minutes)
            min_duration = min(durations_minutes)
            
            # Calculate frequency score (runs per day)
            days_span = self._calculate_days_span(workflow_runs)
            frequency_score = len(workflow_runs) / max(days_span, 1)
            
            # Analyze triggers from workflow content
            trigger_analysis = self._analyze_workflow_triggers(workflow_runs)
            
            # Enhanced frequency score based on trigger analysis
            enhanced_frequency_score = frequency_score
            if trigger_analysis['is_pr_triggered'] or trigger_analysis['is_push_triggered']:
                enhanced_frequency_score *= 1.5  # Boost score for PR/push triggered workflows
            
            # Determine optimization priority
            optimization_priority = self._determine_optimization_priority(
                avg_duration, enhanced_frequency_score, trigger_analysis
            )
            
            # Get trigger events
            events = list(set(r.event for r in workflow_runs))
            
            # Sort runs by recency
            recent_runs = sorted(workflow_runs, key=lambda x: x.created_at, reverse=True)[:10]
            
            workflow_stat = WorkflowStats(
                workflow_name=workflow_name,
                repository=repo,
                total_runs=len(workflow_runs),
                avg_duration_minutes=avg_duration,
                max_duration_minutes=max_duration,
                min_duration_minutes=min_duration,
                success_rate=100.0,  # We only analyze successful runs
                frequency_score=enhanced_frequency_score,
                trigger_events=events,
                recent_runs=recent_runs,
                is_pr_triggered=trigger_analysis['is_pr_triggered'],
                is_push_triggered=trigger_analysis['is_push_triggered'],
                is_high_frequency_trigger=trigger_analysis['is_high_frequency_trigger'],
                trigger_frequency_score=trigger_analysis['trigger_frequency_score'],
                optimization_priority=optimization_priority
            )
            
            stats.append(workflow_stat)
        
        # Sort by priority (critical > high > medium > low), then by duration (longest first within same priority)
        def sort_key(workflow):
            priority_order = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
            priority_score = priority_order.get(workflow.optimization_priority, 0)
            # Return negative priority so higher priority comes first, positive duration so longer comes first
            return (-priority_score, -workflow.avg_duration_minutes)
        
        return sorted(stats, key=sort_key)
    
    def get_repository_summary(self, stats: List[WorkflowStats]) -> Dict[str, Dict]:
        """Get summary statistics by repository."""
        repo_stats = defaultdict(lambda: {
            'total_workflows': 0,
            'problematic_workflows': 0,
            'avg_duration': 0,
            'total_runs': 0,
            'workflows': []
        })
        
        for stat in stats:
            repo = stat.repository
            repo_stats[repo]['total_workflows'] += 1
            repo_stats[repo]['total_runs'] += stat.total_runs
            repo_stats[repo]['workflows'].append(stat)
            
            if (
                # Most impactful: Frequent (PR/Push) workflows that are slow (>10min)
                ((stat.is_pr_triggered or stat.is_push_triggered) and stat.avg_duration_minutes > 10) or
                # Also include: Frequent workflows that are moderately slow (>5min)
                ((stat.is_pr_triggered or stat.is_push_triggered) and stat.avg_duration_minutes > 5) or
                # Also include: Extremely slow workflows regardless of trigger (>15min)
                stat.avg_duration_minutes > 15
            ):
                repo_stats[repo]['problematic_workflows'] += 1
        
        # Calculate average durations
        for repo, data in repo_stats.items():
            if data['workflows']:
                data['avg_duration'] = sum(w.avg_duration_minutes for w in data['workflows']) / len(data['workflows'])
        
        return dict(repo_stats)
    
    def get_trend_analysis(self, runs: List[WorkflowRun], days: int = 15) -> Dict:
        """Analyze trends over time (kept for backward compatibility)."""
        return {
            'daily_trends': [],
            'total_analysis_days': days,
            'total_runs': len(runs),
            'total_workflows': len(set(r.workflow_name for r in runs)) if runs else 0
        }
    
    def get_workflow_patterns(self, stats: List[WorkflowStats]) -> Dict:
        """Analyze patterns in workflow triggers and timing (kept for backward compatibility)."""
        return {
            'trigger_events': {},
            'hourly_patterns': {},
            'peak_hours': []
        }
    
    def _calculate_days_span(self, runs: List[WorkflowRun]) -> int:
        """Calculate the number of days spanned by the workflow runs."""
        if not runs:
            return 1
        
        dates = [r.created_at.date() for r in runs]
        min_date = min(dates)
        max_date = max(dates)
        
        return max((max_date - min_date).days, 1)
    
    def _analyze_workflow_triggers(self, runs: List[WorkflowRun]) -> Dict[str, any]:
        """Analyze triggers from workflow runs."""
        if not runs:
            return {
                'is_pr_triggered': False,
                'is_push_triggered': False,
                'is_high_frequency_trigger': False,
                'trigger_frequency_score': 0.0
            }
        
        # Get trigger analysis from the first run (should be consistent across runs)
        first_run = runs[0]
        if hasattr(first_run, 'trigger_analysis') and first_run.trigger_analysis:
            analysis = first_run.trigger_analysis.copy()
        else:
            # Fallback to event-based analysis
            events = [run.event for run in runs]
            analysis = {
                'is_pr_triggered': any('pull_request' in event for event in events),
                'is_push_triggered': any('push' in event for event in events),
                'trigger_frequency_score': 0
            }
            
            if analysis['is_pr_triggered']:
                analysis['trigger_frequency_score'] += 3
            if analysis['is_push_triggered']:
                analysis['trigger_frequency_score'] += 2
        
        # Determine if it's high frequency based on trigger analysis and run count
        analysis['is_high_frequency_trigger'] = (
            analysis.get('trigger_frequency_score', 0) >= 3 or  # PR/Push triggered
            len(runs) > 10  # More than 10 runs in analysis period
        )
        
        return analysis
    
    def _determine_optimization_priority(self, avg_duration: float, frequency_score: float, trigger_analysis: Dict) -> str:
        """
        Determine optimization priority based on the most impactful workflows:
        - Frequently run workflows (PR/Push triggered) that take >10 minutes
        - Focus on workflows that directly impact developer productivity
        """
        
        is_pr_triggered = trigger_analysis.get('is_pr_triggered', False)
        is_push_triggered = trigger_analysis.get('is_push_triggered', False)
        is_frequent = is_pr_triggered or is_push_triggered  # These run frequently
        
        # CRITICAL: Most impactful workflows - frequent (PR/Push) + slow (>10min)
        # These directly block developers and deployments
        if is_frequent and avg_duration > 10:
            return "critical"
        
        # HIGH: Either frequent workflows that are moderately slow (>5min)
        # OR very slow workflows regardless of frequency (>15min)
        if is_frequent and avg_duration > 5:
            return "high"
        if avg_duration > 15:  # Extremely slow workflows impact CI/CD resources
            return "high"
        
        # MEDIUM: Frequent workflows that could be optimized further
        # OR background workflows that are slow but don't block developers
        if is_frequent:  # Fast PR/Push workflows - still worth optimizing
            return "medium"
        if avg_duration > 10:  # Slow background workflows (nightly builds, etc.)
            return "medium"
        
        # LOW: Everything else
        return "low"