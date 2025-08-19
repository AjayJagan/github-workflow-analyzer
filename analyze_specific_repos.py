#!/usr/bin/env python3
"""
GitHub Workflow Analyzer for specific repositories

Modified version to analyze only specific repositories instead of entire organization.
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


def main():
    """Main function for analyzing specific repositories."""
    print("Starting GitHub Workflow Analysis for Specific Repositories...")
    
    # Configuration
    ANALYSIS_DAYS = 15
    DURATION_THRESHOLD = 10  # Flag workflows >10 minutes as slow
    OUTPUT_PATH = Path('output/dashboard.html')
    
    # Specific repositories to analyze (modify this list)
    SPECIFIC_REPOS = [
        # Add your repositories here, for example:
        "opendatahub-io/odh-dashboard",
        "opendatahub-io/notebooks", 
        "opendatahub-io/opendatahub-operator"
    ]
    
    if not SPECIFIC_REPOS:
        print("ERROR: No repositories specified. Please add repositories to the SPECIFIC_REPOS list.")
        print("Example: SPECIFIC_REPOS = ['org/repo1', 'org/repo2']")
        sys.exit(1)
    
    # Get GitHub token from environment
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("ERROR: GITHUB_TOKEN not found in environment")
        sys.exit(1)
    
    print(f"Analyzing {len(SPECIFIC_REPOS)} specific repositories...")
    for repo in SPECIFIC_REPOS:
        print(f"  - {repo}")
    
    try:
        # Initialize components
        github_client = GitHubClient(github_token)
        analyzer = WorkflowAnalyzer(DURATION_THRESHOLD)
        dashboard_gen = DashboardGenerator("Specific Repositories - Workflow Performance Dashboard")
        
        # Collect workflow runs from specific repositories
        all_runs = []
        for i, repo in enumerate(SPECIFIC_REPOS, 1):
            print(f"[{i}/{len(SPECIFIC_REPOS)}] Analyzing {repo}...")
            try:
                runs = github_client.get_all_repository_runs(repo, ANALYSIS_DAYS)
                all_runs.extend(runs)
                print(f"  Found {len(runs)} workflow runs")
            except Exception as e:
                print(f"  Error: {e}")
        
        if not all_runs:
            print("ERROR: No workflow runs found")
            sys.exit(1)
        
        print(f"\nAnalyzing {len(all_runs)} total workflow runs...")
        
        # Perform analysis
        stats = analyzer.analyze_workflows(all_runs)
        repo_summary = analyzer.get_repository_summary(stats)
        
        # Generate dashboard
        print("Generating dashboard...")
        charts = dashboard_gen.generate_charts(stats, repo_summary, {}, {})
        summary = dashboard_gen.generate_summary_stats(stats, repo_summary, {})
        
        # Render HTML template
        template_dir = Path(__file__).parent / 'templates'
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template('dashboard.html')
        
        repositories = list(set(s.repository for s in stats))
        
        html_content = template.render(
            title="Specific Repositories - Workflow Performance Dashboard",
            charts=charts,
            summary=summary,
            workflows=stats,
            repositories=repositories
        )
        
        # Save output
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Copy images directory for logo
        import shutil
        images_src = Path(__file__).parent / 'images'
        images_dst = OUTPUT_PATH.parent / 'images'
        if images_src.exists():
            if images_dst.exists():
                shutil.rmtree(images_dst)
            shutil.copytree(images_src, images_dst)
            print(f"Copied images to {images_dst}")
        
        print(f"Dashboard generated successfully: {OUTPUT_PATH}")
        print("Open the dashboard in your browser to view the results.")
        
    except Exception as e:
        print(f"ERROR: Error during analysis: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
