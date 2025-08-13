import os
import requests
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class WorkflowRun:
    id: int
    name: str
    status: str
    conclusion: str
    duration_seconds: int
    created_at: datetime
    updated_at: datetime
    repository: str
    workflow_name: str
    event: str
    branch: str
    workflow_content: Optional[str] = None
    trigger_analysis: Optional[Dict] = None


class GitHubClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv('GITHUB_TOKEN')
        if not self.token:
            raise ValueError("GitHub token is required. Set GITHUB_TOKEN environment variable.")
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'workflow-analyzer-tool'
        })
        self.base_url = 'https://api.github.com'
    
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Dict:
        """Make authenticated request to GitHub API with rate limit handling."""
        response = self.session.get(url, params=params)
        
        # Handle rate limiting
        if response.status_code == 403 and 'rate limit' in response.text.lower():
            reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
            sleep_time = max(reset_time - int(time.time()), 0) + 1
            print(f"Rate limit exceeded. Sleeping for {sleep_time} seconds...")
            time.sleep(sleep_time)
            response = self.session.get(url, params=params)
        
        response.raise_for_status()
        return response.json()
    
    def get_repository_workflows(self, repo: str) -> List[Dict]:
        """Get all workflows for a repository."""
        url = f"{self.base_url}/repos/{repo}/actions/workflows"
        data = self._make_request(url)
        return [w for w in data['workflows'] if w['state'] == 'active']
    
    def get_workflow_runs(self, repo: str, workflow_id: int, days: int = 15) -> List[WorkflowRun]:
        """Get workflow runs for the last N days."""
        url = f"{self.base_url}/repos/{repo}/actions/workflows/{workflow_id}/runs"
        
        since = (datetime.now() - timedelta(days=days)).isoformat()
        params = {
            'status': 'completed',
            'per_page': 100,
            'created': f'>{since}'
        }
        
        runs = []
        page = 1
        
        while True:
            params['page'] = page
            data = self._make_request(url, params)
            
            if not data['workflow_runs']:
                break
                
            for run in data['workflow_runs']:
                if run['conclusion'] == 'success':
                    created_at = datetime.fromisoformat(run['created_at'].replace('Z', '+00:00'))
                    updated_at = datetime.fromisoformat(run['updated_at'].replace('Z', '+00:00'))
                    duration = int((updated_at - created_at).total_seconds())
                    
                    runs.append(WorkflowRun(
                        id=run['id'],
                        name=run['name'],
                        status=run['status'],
                        conclusion=run['conclusion'],
                        duration_seconds=duration,
                        created_at=created_at,
                        updated_at=updated_at,
                        repository=repo,
                        workflow_name=run['name'],
                        event=run['event'],
                        branch=run['head_branch'] or 'unknown'
                    ))
            
            # Check if there are more pages
            if len(data['workflow_runs']) < 100:
                break
            page += 1
            
            # Safety limit
            if page > 10:
                break
        
        return runs
    
    def get_organization_repositories(self, org: str, repo_filter: str = "*") -> List[str]:
        """Get all repositories for an organization."""
        url = f"{self.base_url}/orgs/{org}/repos"
        repos = []
        page = 1
        
        print(f"Discovering repositories in organization: {org}")
        
        while True:
            params = {
                'type': 'all',
                'per_page': 100,
                'page': page
            }
            
            try:
                data = self._make_request(url, params)
                
                if not data:
                    break
                
                for repo in data:
                    # Skip archived repositories by default
                    if not repo.get('archived', False):
                        repo_name = repo['full_name']
                        
                        # Apply filter if not "*"
                        if repo_filter == "*" or repo_filter in repo_name:
                            repos.append(repo_name)
                
                # Check if there are more pages
                if len(data) < 100:
                    break
                page += 1
                
                # Safety limit to prevent infinite loops
                if page > 50:
                    print(f"Warning: Stopped at page {page} to prevent excessive API calls")
                    break
                    
            except Exception as e:
                print(f"Error fetching repositories for org {org}: {e}")
                break
        
        print(f"Found {len(repos)} repositories in {org}")
        return repos
    
    def get_workflow_file_content(self, repo: str, workflow_id: int) -> Optional[str]:
        """Get the workflow file content to analyze triggers."""
        try:
            # First get workflow details to find the path
            workflow_url = f"{self.base_url}/repos/{repo}/actions/workflows/{workflow_id}"
            workflow_data = self._make_request(workflow_url)
            
            workflow_path = workflow_data.get('path', '')
            if not workflow_path:
                return None
            
            # Get the file content
            file_url = f"{self.base_url}/repos/{repo}/contents/{workflow_path}"
            file_data = self._make_request(file_url)
            
            if file_data.get('content'):
                import base64
                content = base64.b64decode(file_data['content']).decode('utf-8')
                return content
                
        except Exception as e:
            # Silently fail for workflow content - not critical
            pass
        
        return None
    
    def get_all_repository_runs(self, repo: str, days: int = 15) -> List[WorkflowRun]:
        """Get all workflow runs for a repository."""
        workflows = self.get_repository_workflows(repo)
        all_runs = []
        
        print(f"Analyzing {len(workflows)} workflows in {repo}...")
        
        for workflow in workflows:
            print(f"  Fetching runs for workflow: {workflow['name']}")
            runs = self.get_workflow_runs(repo, workflow['id'], days)
            
            # Get workflow file content to analyze triggers
            workflow_content = self.get_workflow_file_content(repo, workflow['id'])
            
            # Enhance runs with trigger analysis
            for run in runs:
                run.workflow_content = workflow_content
                run.trigger_analysis = self._analyze_workflow_triggers(workflow_content)
            
            all_runs.extend(runs)
            
            # Small delay to be respectful to the API
            time.sleep(0.1)
        
        return all_runs
    
    def _analyze_workflow_triggers(self, content: Optional[str]) -> Dict[str, any]:
        """Analyze workflow file content to determine trigger patterns."""
        analysis = {
            'is_pr_triggered': False,
            'is_push_triggered': False,
            'is_schedule_triggered': False,
            'is_manual_triggered': False,
            'trigger_frequency_score': 0,
            'raw_triggers': []
        }
        
        if not content:
            return analysis
        
        try:
            import yaml
            workflow_data = yaml.safe_load(content)
            
            if 'on' in workflow_data:
                triggers = workflow_data['on']
                
                # Handle different trigger formats
                if isinstance(triggers, str):
                    triggers = [triggers]
                elif isinstance(triggers, dict):
                    triggers = list(triggers.keys())
                elif isinstance(triggers, list):
                    pass  # Already a list
                else:
                    triggers = []
                
                analysis['raw_triggers'] = triggers
                
                # Analyze trigger types and assign frequency scores
                for trigger in triggers:
                    if 'pull_request' in str(trigger).lower():
                        analysis['is_pr_triggered'] = True
                        analysis['trigger_frequency_score'] += 3  # High frequency
                    
                    if 'push' in str(trigger).lower():
                        analysis['is_push_triggered'] = True
                        analysis['trigger_frequency_score'] += 2  # Medium-high frequency
                    
                    if 'schedule' in str(trigger).lower():
                        analysis['is_schedule_triggered'] = True
                        analysis['trigger_frequency_score'] += 1  # Low-medium frequency
                    
                    if 'workflow_dispatch' in str(trigger).lower():
                        analysis['is_manual_triggered'] = True
                        # No frequency score for manual triggers
                
        except Exception as e:
            # If YAML parsing fails, fall back to text analysis
            content_lower = content.lower()
            if 'pull_request' in content_lower:
                analysis['is_pr_triggered'] = True
                analysis['trigger_frequency_score'] += 3
            if 'push' in content_lower:
                analysis['is_push_triggered'] = True
                analysis['trigger_frequency_score'] += 2
            if 'schedule' in content_lower:
                analysis['is_schedule_triggered'] = True
                analysis['trigger_frequency_score'] += 1
        
        return analysis