# GitHub Workflow Performance Analyzer

Automated analysis of GitHub Actions workflows with GitHub Pages dashboard deployment.

## Overview

This tool automatically analyzes your organization's GitHub Actions workflows and generates a performance dashboard deployed to GitHub Pages. It identifies slow, frequent workflows that are consuming the most CI/CD resources and provides actionable insights for optimization.

## Features

- **Automated Analysis**: Runs every 15 days via GitHub Actions
- **Interactive Dashboard**: Beautiful charts and performance metrics
- **Smart Prioritization**: Identifies workflows >10min + frequent (≥1/day) as critical
- **Performance Insights**: Shows daily time impact and optimization potential
- **GitHub Pages**: Zero-maintenance dashboard hosting

## Quick Setup

1. **Fork/Copy this repository** to your organization

2. **Create a Personal Access Token (PAT)**:
   - Go to GitHub Settings > Developer settings > Personal access tokens > Tokens (classic)
   - Click "Generate new token" 
   - Select scopes: `repo`, `read:org`, `actions:read`
   - Copy the generated token

3. **Add the token as a repository secret**:
   - Go to your repository Settings > Secrets and variables > Actions
   - Click "New repository secret"
   - Name: `WORKFLOW_ANALYZER_TOKEN`
   - Value: Paste your PAT token

4. **Enable GitHub Pages**:
   - Go to Settings > Pages
   - Source: "GitHub Actions"

5. **Run the analysis**:
   - Go to Actions tab
   - Select "Workflow Performance Analysis"
   - Click "Run workflow" for immediate analysis

That's it! The dashboard will be available at: `https://[your-org].github.io/[repo-name]/`

## What It Analyzes

### Critical Workflows (Priority)
- **PR workflows >10 minutes** - Directly block developer productivity
- **Push to main workflows >10 minutes** - Block deployment pipeline
- These workflows have maximum impact on team velocity

### High Priority
- **PR workflows >5 minutes** - Create developer friction
- **Push to main >5 minutes** - Delay releases  
- **Any workflow >15 minutes** - Extremely slow regardless of trigger

### Medium Priority
- **Fast PR/Push workflows** - Good but could be faster
- **Background workflows >10 minutes** - Slow but don't block developers
- **High-frequency workflows** - Resource consumption concerns

### Low Priority
- **Fast background workflows** - No immediate optimization needed

## Dashboard Features

### Performance Matrix
Visual scatter plot showing all workflows by duration vs frequency with clear critical zones.

### Performance Impact Analysis
Shows daily time consumption by category with optimization potential calculations.

### Repository Summary
Breakdown of problematic workflows per repository.

### Top Workflows
Ranked list of most impactful workflows to optimize first.

### Filtering & Details
Interactive filtering by repository, duration, and frequency in the Workflows tab.

## Configuration

The analysis runs with these defaults:
- **Analysis Period**: 15 days
- **Duration Threshold**: 10 minutes
- **Schedule**: 1st and 15th of each month at 6 AM UTC

To modify the schedule, edit `.github/workflows/workflow-analysis.yml`:

```yaml
on:
  schedule:
    - cron: '0 6 1,15 * *'  # Modify this line
```

## Permissions

### GitHub Action Permissions (already configured):
- `contents: read` - Read repository code
- `pages: write` - Deploy to GitHub Pages  
- `id-token: write` - GitHub Pages deployment

### Personal Access Token Scopes (required):
- `repo` - Access to repository data and workflows
- `read:org` - Read organization repositories  
- `actions:read` - Read workflow run data

**Note**: The default `GITHUB_TOKEN` has insufficient permissions for organization-wide analysis, so a Personal Access Token is required.

## Repository Structure

```
├── .github/workflows/
│   └── workflow-analysis.yml    # GitHub Action workflow
├── src/                         # Core analysis modules
│   ├── analyzer.py             # Workflow analysis logic
│   ├── dashboard.py            # Chart generation
│   └── github_client.py        # GitHub API integration
├── templates/
│   └── dashboard.html          # Dashboard HTML template
├── action_analyzer.py          # Main script for GitHub Actions
├── requirements.txt            # Python dependencies
├── .gitignore                  # Ignore unnecessary files
└── README.md                   # This setup guide
```

## Local Development (Optional)

If you want to test locally before deploying:

```bash
# Clone the repository
git clone <your-repo-url>
cd workflow-analyzer-tool

# Install dependencies
pip install -r requirements.txt

# Set GitHub token
export GITHUB_TOKEN='your_token_here'

# Run analysis
python action_analyzer.py
```

**Note**: The `output/` directory will contain the generated dashboard files.

## Manual Execution

To run analysis manually:

1. Go to the Actions tab in your repository
2. Select "Workflow Performance Analysis"
3. Click "Run workflow"
4. Wait for completion (~5-10 minutes)
5. Visit your GitHub Pages URL

## Understanding the Results

### Key Metrics to Focus On:
1. **Critical Workflows**: Red diamonds in performance matrix
2. **Daily Time Impact**: Total minutes consumed by workflow categories  
3. **Optimization Potential**: Estimated time savings from fixing critical workflows
4. **Top Offenders**: Specific workflows with highest impact scores

### Optimization Strategies:
- **Caching**: Add dependency caching for critical workflows
- **Parallelization**: Split long workflows into parallel jobs
- **Trigger Optimization**: Review if all triggers are necessary
- **Resource Scaling**: Use larger runners for compute-heavy tasks

## Contributing

This tool is designed to be organization-specific. Common customizations:

- Modify analysis thresholds in `action_analyzer.py`
- Customize dashboard styling in `templates/dashboard.html`
- Adjust repository discovery logic in `src/github_client.py`

## License

MIT License - See LICENSE file for details.

---

**Ready to optimize your CI/CD performance? Set it up and let the automation handle the rest!**