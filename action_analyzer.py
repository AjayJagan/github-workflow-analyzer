#!/usr/bin/env python3
"""
GitHub Workflow Analyzer for GitHub Actions

Simplified version designed to run as a GitHub Action.
Analyzes workflows for the current organization and generates a GitHub Pages dashboard.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from github_client import GitHubClient
from analyzer import WorkflowAnalyzer
from dashboard import DashboardGenerator


def get_target_org():
    """Get the target GitHub organization to analyze."""
    # First check if TARGET_ORG is explicitly set (from workflow input)
    target_org = os.getenv('TARGET_ORG')
    if target_org:
        return target_org
    
    # Fallback to current repository's organization
    github_repo = os.getenv('GITHUB_REPOSITORY', '')
    if '/' in github_repo:
        return github_repo.split('/')[0]
    
    # Default fallback
    return 'opendatahub-io'


def main():
    """Main function for GitHub Action execution."""
    print("🚀 Starting GitHub Workflow Analysis...")
    
    # Configuration
    ANALYSIS_DAYS = 15
    DURATION_THRESHOLD = 10  # Flag workflows >10 minutes as slow
    OUTPUT_PATH = Path('output/index.html')  # GitHub Pages expects index.html
    
    # Get GitHub token from environment
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("❌ GITHUB_TOKEN not found in environment")
        sys.exit(1)
    
    # Get target organization to analyze
    org = get_target_org()
    if not org:
        print("❌ Could not determine target GitHub organization")
        sys.exit(1)
    
    print(f"🔍 Analyzing organization: {org}")
    
    try:
        # Initialize components
        github_client = GitHubClient(github_token)
        analyzer = WorkflowAnalyzer(DURATION_THRESHOLD)
        dashboard_gen = DashboardGenerator(f"{org} - Workflow Performance Dashboard")
        
        # Discover repositories in the organization
        print("🔎 Discovering repositories...")
        repos = github_client.get_organization_repositories(org, '*')
        
        # Safety limit for GitHub Actions
        MAX_REPOS = 300
        if len(repos) > MAX_REPOS:
            print(f"⚠️  Found {len(repos)} repositories, limiting to {MAX_REPOS} for performance")
            repos = repos[:MAX_REPOS]
        
        print(f"📊 Analyzing {len(repos)} repositories...")
        
        # Collect workflow runs
        all_runs = []
        for i, repo in enumerate(repos, 1):
            print(f"[{i}/{len(repos)}] Analyzing {repo}...")
            try:
                runs = github_client.get_all_repository_runs(repo, ANALYSIS_DAYS)
                all_runs.extend(runs)
                print(f"  ✓ Found {len(runs)} workflow runs")
            except Exception as e:
                print(f"  ✗ Error: {e}")
        
        if not all_runs:
            print("❌ No workflow runs found")
            sys.exit(1)
        
        print(f"📈 Analyzing {len(all_runs)} total workflow runs...")
        
        # Perform analysis
        stats = analyzer.analyze_workflows(all_runs)
        repo_summary = analyzer.get_repository_summary(stats)
        trends = analyzer.get_trend_analysis(all_runs, ANALYSIS_DAYS)
        patterns = analyzer.get_workflow_patterns(stats)
        
        # Generate dashboard
        print("🎨 Generating dashboard...")
        charts = dashboard_gen.generate_charts(stats, repo_summary, trends, patterns)
        summary = dashboard_gen.generate_summary_stats(stats, repo_summary, trends)
        
        # Render HTML template
        template_dir = Path(__file__).parent / 'templates'
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template('dashboard.html')
        
        max_score = max([s.combined_score for s in stats]) if stats else 1
        repositories = list(set(s.repository for s in stats))
        
        html_content = template.render(
            title=f"{org} - Workflow Performance Dashboard",
            charts=charts,
            summary=summary,
            workflows=stats,
            repositories=repositories,
            max_score=max_score
        )
        
        # Save output for GitHub Pages
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Print summary
        print(f"\n🎉 Analysis Complete!")
        print(f"📊 Total Workflows: {len(stats)}")
        print(f"🏢 Repositories: {len(repo_summary)}")
        print(f"🔥 Problematic Workflows: {len([s for s in stats if s.combined_score > 5])}")
        print(f"📁 Dashboard saved to: {OUTPUT_PATH}")
        
        # Display top problematic workflows
        problematic = [s for s in stats if s.combined_score > 5]
        if problematic:
            print(f"\n🚨 Top 5 Problematic Workflows:")
            for i, workflow in enumerate(sorted(problematic, key=lambda x: x.combined_score, reverse=True)[:5], 1):
                print(f"  {i}. {workflow.repository}: {workflow.workflow_name}")
                print(f"     Duration: {workflow.avg_duration_minutes:.1f}min, Frequency: {workflow.frequency_score:.1f}/day")
        
        print(f"\n🌐 Dashboard will be available at: https://{org.lower()}.github.io/workflow-performance/")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
