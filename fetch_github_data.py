import os
import sys
import json
import logging
import calendar
from datetime import datetime, timezone, timedelta
from github import Auth, Github, GithubException

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def get_month_range(year, month):
    """Get start and end dates for a given month."""
    start_date = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end_date = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end_date = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    return start_date, end_date

def get_week_range(year, month, week):
    """Get start and end dates for a specific week in a month.
    Week numbers are 1-based (1-5).
    """
    if not 1 <= week <= 5:
        raise ValueError("Week must be between 1 and 5")
    
    # Get the first day of the month
    first_day = datetime(year, month, 1, tzinfo=timezone.utc)
    
    # Calculate the start date of the requested week
    # For week 1, it's the 1st of the month
    # For subsequent weeks, add (week_number - 1) * 7 days
    start_date = first_day + timedelta(days=(week - 1) * 7)
    
    # End date is 7 days after start, or end of month, whichever comes first
    potential_end = start_date + timedelta(days=7)
    if month == 12:
        month_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        month_end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    
    end_date = min(potential_end, month_end)
    return start_date, end_date

def get_team_members_from_issues(issues_data):
    """Extract unique team members from issues data."""
    team_members = set()
    
    for issue in issues_data:
        if issue.get('creator'):
            team_members.add(issue['creator'])
        team_members.update(issue.get('assignees', []))
        if issue.get('closed_by'):
            team_members.add(issue['closed_by'])
        
        # Add commenters from the comment_by_author dictionary
        for commenter in issue.get('comments_by_author', {}):
            team_members.add(commenter)
    
    return sorted(list(team_members))

def get_devops_team_members(g, organization_name="SELISEdigitalplatforms"):
    """Fetch members of the DevOps team from GitHub."""
    logger.info("Fetching DevOps team members")
    devops_team_members = []
    try:
        org = g.get_organization(organization_name)
        teams = org.get_teams()
        for team in teams:
            if team.name.lower() == "devops":
                logger.info(f"Found DevOps team: {team.name}")
                members = team.get_members()
                devops_team_members = [member.login for member in members]
                logger.info(f"Found {len(devops_team_members)} DevOps team members")
                break
        if not devops_team_members:
            logger.warning("DevOps team not found in the organization")
    except GithubException as e:
        logger.warning(f"Error fetching DevOps team members: {e}")
    
    return devops_team_members

def main():
    # Create data directory if it doesn't exist
    logger.info("Creating data directory if it doesn't exist")
    os.makedirs("data", exist_ok=True)

    # Get input for month and year
    current_date = datetime.now()
    if len(sys.argv) >= 3:
        year = int(sys.argv[1])
        month = int(sys.argv[2])
    else:
        year = current_date.year
        month = current_date.month

    # Get optional week parameter and repository name
    week = None
    repo_name = "HarunAlKawser/charts"
    
    # Check for remaining arguments
    remaining_args = sys.argv[3:] if len(sys.argv) >= 3 else []
    
    for arg in remaining_args:
        # If argument can be converted to an integer between 1-5, it's a week
        try:
            potential_week = int(arg)
            if 1 <= potential_week <= 5:
                week = potential_week
                continue
        except ValueError:
            pass
        
        # If it contains a slash, assume it's a repo name
        if '/' in arg:
            repo_name = arg

    logger.info("Fetching data for %s %d%s from repository %s", 
                calendar.month_name[month], year,
                f" week {week}" if week else "",
                repo_name)

    # Authentication using environment variable
    logger.info("Checking for GitHub token")
    MY_GITHUB_TOKEN = os.getenv("MY_GITHUB_TOKEN")
    if not MY_GITHUB_TOKEN:
        logger.error("MY_GITHUB_TOKEN environment variable not set")
        sys.exit(1)

    g = None
    try:
        logger.info("Authenticating with GitHub")
        auth = Auth.Token(MY_GITHUB_TOKEN)
        g = Github(auth=auth)
        user = g.get_user()
        logger.info("Successfully authenticated as: %s", user.login)

        logger.info("Fetching repository information for %s", repo_name)
        repo = g.get_repo(repo_name)
        logger.info("Processing repository: %s", repo.full_name)

        # Get organization name from repository
        organization_name = repo_name.split('/')[0]
        
        # Get DevOps team members
        devops_team_members = get_devops_team_members(g, organization_name)

        # Get date range based on whether week is specified
        if week:
            start_date, end_date = get_week_range(year, month, week)
        else:
            start_date, end_date = get_month_range(year, month)
            
        logger.info("Analyzing data from %s to %s", start_date, end_date)

        # Collect issues data
        logger.info("Fetching issues data")
        issues_data = []
        
        # Get all issues that were active during the given period
        issues = repo.get_issues(state='all', since=start_date)
        
        for issue in issues:
            # Skip issues created after the end date
            if issue.created_at >= end_date:
                continue
            
            # Create a comment tracker by author
            comment_by_author = {}
            
            # Get comments for this issue
            logger.info("Fetching comments for issue #%d", issue.number)
            try:
                comments = issue.get_comments()
                for comment in comments:
                    commenter = comment.user.login if comment.user else 'unknown'
                    
                    # Track comment counts by author
                    if commenter in comment_by_author:
                        comment_by_author[commenter] += 1
                    else:
                        comment_by_author[commenter] = 1
            except GithubException as e:
                logger.warning("Error fetching comments for issue #%d: %s", 
                             issue.number, str(e))
            
            # Create the issue data structure with only essential information
            issue_data = {
                'number': issue.number,
                'title': issue.title,
                'created_at': issue.created_at.isoformat(),
                'closed_at': issue.closed_at.isoformat() if issue.closed_at else None,
                'creator': issue.user.login if issue.user else None,
                'assignees': [assignee.login for assignee in issue.assignees],
                'state': issue.state,
                'comments_count': issue.comments,
                'comments_by_author': comment_by_author,
                'url': issue.html_url
            }
            issues_data.append(issue_data)

        # Get team members for summary
        team_members = get_team_members_from_issues(issues_data)
        
        # Collect simple repository-wide statistics
        total_issues = len(issues_data)
        open_issues = sum(1 for issue in issues_data if issue['state'] == 'open')
        closed_issues = sum(1 for issue in issues_data if issue['state'] == 'closed')
        total_comments = sum(issue['comments_count'] for issue in issues_data)
        
        # Create the final data structure - simplified
        github_data = {
            'metadata': {
                'repository': repo.full_name,
                'period_start': start_date.isoformat(),
                'period_end': end_date.isoformat(),
                'year': year,
                'month': month,
                'month_name': calendar.month_name[month],
                'generated_at': datetime.now().isoformat(),
                'devops_team_members': devops_team_members  # Add DevOps team members
            },
            'summary': {
                'total_issues': total_issues,
                'open_issues': open_issues,
                'closed_issues': closed_issues,
                'total_comments': total_comments,
                'team_members': team_members,
                'devops_team_members': devops_team_members
            },
            'issues': issues_data
        }

        # Update output filename to include week if specified
        output_filename = f"data/github_data_{repo.name}_{year}_{month:02d}"
        if week:
            output_filename += f"_week{week}"
        output_filename += ".json"
        
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(github_data, f, indent=2)
            
        logger.info("Data collection completed successfully. JSON file saved to %s", output_filename)
        
        # Print a special format that's easy to grep
        print(f"OUTPUT_FILE: {output_filename}")
        
        logger.info("Found %d issues (%d open, %d closed) with %d comments", 
                    total_issues, open_issues, closed_issues, total_comments)
        logger.info("Found %d DevOps team members", len(devops_team_members))

    except GithubException as ge:
        logger.error("GitHub API error: %s", str(ge), exc_info=True)
        sys.exit(1)
    except (IOError, OSError) as io_err:
        logger.error("File operation error: %s", str(io_err), exc_info=True)
        sys.exit(1)
    except (ValueError, KeyError) as val_err:
        logger.error("Data validation error: %s", str(val_err), exc_info=True)
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: %s", str(e), exc_info=True)
        sys.exit(1)
    finally:
        if g:
            logger.info("Closing GitHub connection")
            g.close()

if __name__ == "__main__":
    main()