from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
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
    duration_score: float
    combined_score: float
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
            
            # Calculate duration score (how much it exceeds threshold)
            duration_score = max(0, avg_duration - self.duration_threshold_minutes)
            
            # Enhanced combined score for prioritization
            # PR/Push triggered workflows get higher priority if they're slow
            trigger_multiplier = 1.0
            if trigger_analysis['is_pr_triggered'] and avg_duration > self.duration_threshold_minutes:
                trigger_multiplier = 1.3  # High priority for slow PR workflows
            elif trigger_analysis['is_push_triggered'] and avg_duration > self.duration_threshold_minutes:
                trigger_multiplier = 1.2  # Medium-high priority for slow push workflows
            
            combined_score = ((duration_score * 0.6) + (enhanced_frequency_score * 0.4)) * trigger_multiplier
            
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
                duration_score=duration_score,
                combined_score=combined_score,
                trigger_events=events,
                recent_runs=recent_runs,
                is_pr_triggered=trigger_analysis['is_pr_triggered'],
                is_push_triggered=trigger_analysis['is_push_triggered'],
                is_high_frequency_trigger=trigger_analysis['is_high_frequency_trigger'],
                trigger_frequency_score=trigger_analysis['trigger_frequency_score'],
                optimization_priority=optimization_priority
            )
            
            stats.append(workflow_stat)
        
        # Sort by combined score (highest impact workflows first)
        return sorted(stats, key=lambda x: x.combined_score, reverse=True)
    
    def filter_problematic_workflows(self, stats: List[WorkflowStats]) -> List[WorkflowStats]:
        """Filter workflows that exceed duration or frequency thresholds."""
        return [
            stat for stat in stats
            if stat.avg_duration_minutes > self.duration_threshold_minutes
            or stat.frequency_score > 5  # More than 5 runs per day
        ]
    
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
            
            if (stat.avg_duration_minutes > self.duration_threshold_minutes or 
                stat.frequency_score > 5):  # More than 5 runs per day
                repo_stats[repo]['problematic_workflows'] += 1
        
        # Calculate average durations
        for repo, data in repo_stats.items():
            if data['workflows']:
                data['avg_duration'] = sum(w.avg_duration_minutes for w in data['workflows']) / len(data['workflows'])
        
        return dict(repo_stats)
    
    def get_trend_analysis(self, runs: List[WorkflowRun], days: int = 15) -> Dict:
        """Analyze trends over time."""
        # Group runs by day
        daily_runs = defaultdict(list)
        daily_durations = defaultdict(list)
        
        for run in runs:
            day = run.created_at.date()
            daily_runs[day].append(run)
            daily_durations[day].append(run.duration_seconds / 60)
        
        # Calculate daily statistics
        trend_data = []
        for day in sorted(daily_runs.keys()):
            avg_duration = sum(daily_durations[day]) / len(daily_durations[day])
            trend_data.append({
                'date': day.isoformat(),
                'runs_count': len(daily_runs[day]),
                'avg_duration_minutes': avg_duration,
                'max_duration_minutes': max(daily_durations[day]),
                'workflows': len(set(r.workflow_name for r in daily_runs[day]))
            })
        
        return {
            'daily_trends': trend_data,
            'total_analysis_days': days,
            'total_runs': len(runs),
            'total_workflows': len(set(r.workflow_name for r in runs))
        }
    
    def _calculate_days_span(self, runs: List[WorkflowRun]) -> int:
        """Calculate the number of days spanned by the workflow runs."""
        if not runs:
            return 1
        
        dates = [r.created_at.date() for r in runs]
        min_date = min(dates)
        max_date = max(dates)
        
        return max((max_date - min_date).days, 1)
    
    def get_workflow_patterns(self, stats: List[WorkflowStats]) -> Dict:
        """Analyze patterns in workflow triggers and timing."""
        event_patterns = Counter()
        hourly_patterns = defaultdict(list)
        
        for stat in stats:
            for run in stat.recent_runs:
                event_patterns[run.event] += 1
                hour = run.created_at.hour
                hourly_patterns[hour].append(run.duration_seconds / 60)
        
        # Calculate average duration by hour
        hourly_avg = {}
        for hour, durations in hourly_patterns.items():
            hourly_avg[hour] = sum(durations) / len(durations)
        
        return {
            'trigger_events': dict(event_patterns),
            'hourly_patterns': hourly_avg,
            'peak_hours': sorted(hourly_avg.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
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
        """Determine optimization priority based on duration, frequency, and triggers."""
        
        # Critical: PR-triggered workflows that are slow
        if (trigger_analysis.get('is_pr_triggered', False) and 
            avg_duration > self.duration_threshold_minutes * 2):
            return "critical"
        
        # High: Any PR/Push triggered workflow over threshold, or very frequent workflows
        if ((trigger_analysis.get('is_pr_triggered', False) or trigger_analysis.get('is_push_triggered', False)) and
            avg_duration > self.duration_threshold_minutes):
            return "high"
        
        # High: Very frequent workflows regardless of trigger
        if frequency_score > 10:  # More than 10 runs per day
            return "high"
        
        # Medium: Workflows over duration threshold
        if avg_duration > self.duration_threshold_minutes:
            return "medium"
        
        # Medium: Moderately frequent workflows
        if frequency_score > 5:  # More than 5 runs per day
            return "medium"
        
        return "low"