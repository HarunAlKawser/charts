import os
import json
import argparse
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

def load_data(file_path):
    """Load the GitHub issue data from a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error loading data: {e}")
        return None

def parse_date(date_str):
    """Parse date string to datetime object."""
    if date_str:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    return None

def create_dataframes(data):
    """Create pandas DataFrames from the GitHub issue data."""
    issues_data = data['issues']
    devops_team_members = data['metadata'].get('devops_team_members', [])  # Get DevOps team members
    
    # Convert issues to DataFrame
    issues_df = pd.DataFrame(issues_data)
    
    # Convert date strings to datetime objects
    issues_df['created_at'] = issues_df['created_at'].apply(parse_date)
    issues_df['closed_at'] = issues_df['closed_at'].apply(parse_date)
    
    # Create a DataFrame for daily activity
    date_range = pd.date_range(
        start=min(issues_df['created_at'].min(), issues_df['created_at'].min()),
        end=max(issues_df['created_at'].max(), 
                issues_df['closed_at'].dropna().max() if not issues_df['closed_at'].dropna().empty else issues_df['created_at'].max()),
        freq='D'
    )
    
    daily_activity = pd.DataFrame({'date': date_range})
    daily_activity['date'] = daily_activity['date'].dt.date
    
    # Count issues created per day
    created_per_day = issues_df.copy()
    created_per_day['date'] = created_per_day['created_at'].dt.date
    created_per_day = created_per_day.groupby('date').size().reset_index(name='issues_created')
    
    # Count issues closed per day
    closed_df = issues_df[~issues_df['closed_at'].isna()].copy()
    if not closed_df.empty:
        closed_df['date'] = closed_df['closed_at'].dt.date
        closed_per_day = closed_df.groupby('date').size().reset_index(name='issues_closed')
    else:
        closed_per_day = pd.DataFrame(columns=['date', 'issues_closed'])
    
    # Merge activity data
    daily_activity = daily_activity.merge(created_per_day, on='date', how='left')
    daily_activity = daily_activity.merge(closed_per_day, on='date', how='left')
    
    # Fill NaN values with 0
    daily_activity = daily_activity.fillna(0)
    
    # Process comments data
    comments_data = []
    active_users_data = []
    
    for date in daily_activity['date']:
        date_str = date.strftime('%Y-%m-%d')
        daily_comments = 0
        active_users = set()
        
        for issue in issues_data:
            issue_date = parse_date(issue['created_at']).date()
            if issue_date == date:
                active_users.add(issue['creator'])
                for assignee in issue.get('assignees', []):
                    active_users.add(assignee)
            
            if issue['closed_at']:
                closed_date = parse_date(issue['closed_at']).date()
                if closed_date == date:
                    active_users.add(issue['creator'])
            
            comments_by_author = issue.get('comments_by_author', {})
            for author, count in comments_by_author.items():
                # Since we don't have comment dates, we'll distribute comments evenly
                # across days between issue creation and closing or current date
                issue_created = parse_date(issue['created_at']).date()
                issue_closed = parse_date(issue['closed_at']).date() if issue['closed_at'] else datetime.now().date()
                
                issue_duration = (issue_closed - issue_created).days + 1
                if issue_duration < 1:
                    issue_duration = 1
                
                # Check if this date is within the issue's timeframe
                if issue_created <= date <= issue_closed:
                    avg_comments_per_day = count / issue_duration
                    daily_comments += avg_comments_per_day
                    active_users.add(author)
        
        comments_data.append({'date': date, 'comments': daily_comments})
        active_users_data.append({'date': date, 'active_users': len(active_users)})
    
    comments_df = pd.DataFrame(comments_data)
    active_users_df = pd.DataFrame(active_users_data)
    
    daily_activity = daily_activity.merge(comments_df, on='date', how='left')
    daily_activity = daily_activity.merge(active_users_df, on='date', how='left')
    daily_activity = daily_activity.fillna(0)
    
    # Create user activity DataFrame
    user_activity = {}
    for issue in issues_data:
        creator = issue['creator']
        if creator not in user_activity:
            user_activity[creator] = {'assigned': 0, 'closed': 0, 'comments': 0}
        
        # Count assignments
        for assignee in issue.get('assignees', []):
            if assignee not in user_activity:
                user_activity[assignee] = {'assigned': 0, 'closed': 0, 'comments': 0}
            user_activity[assignee]['assigned'] += 1
        
        # Count closed issues
        if issue['closed_at']:
            user_activity[creator]['closed'] += 1
        
        # Count comments
        for author, count in issue.get('comments_by_author', {}).items():
            if author not in user_activity:
                user_activity[author] = {'assigned': 0, 'closed': 0, 'comments': 0}
            user_activity[author]['comments'] += count
    
    user_activity_df = pd.DataFrame.from_dict(user_activity, orient='index')
    user_activity_df['user'] = user_activity_df.index
    user_activity_df = user_activity_df.reset_index(drop=True)
    
    # Convert original issues DataFrame for table display
    table_df = issues_df.copy()
    table_df['active_people'] = table_df.apply(
        lambda row: len(set(row.get('assignees', []) + 
                          [row['creator']] + 
                          list(row.get('comments_by_author', {}).keys()))),
        axis=1
    )
    
    # Add devops_team info to user_activity_df
    user_activity_df['is_devops'] = user_activity_df['user'].isin(devops_team_members)
    
    return daily_activity, user_activity_df, table_df, devops_team_members

def filter_data_by_date(daily_activity, user_activity_df, table_df, start_date, end_date):
    """Filter data based on the selected date range."""
    # Convert start_date and end_date to string for JSON serialization if they're date objects
    if hasattr(start_date, 'isoformat'):
        start_date_str = start_date.isoformat()
    else:
        start_date_str = start_date
        
    if hasattr(end_date, 'isoformat'):
        end_date_str = end_date.isoformat()
    else:
        end_date_str = end_date
    
    # Filter daily activity
    filtered_daily = daily_activity[(daily_activity['date'] >= start_date) & 
                                   (daily_activity['date'] <= end_date)].copy()
    
    # Convert date objects to strings in filtered_daily for JSON serialization
    filtered_daily['date'] = filtered_daily['date'].apply(lambda d: d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else d)
    
    # Filter table data
    filtered_table = table_df[
        ((table_df['created_at'].dt.date >= start_date) & 
         (table_df['created_at'].dt.date <= end_date)) |
        ((~table_df['closed_at'].isna()) & 
         (table_df['closed_at'].dt.date >= start_date) & 
         (table_df['closed_at'].dt.date <= end_date))
    ].copy()
    
    # Recalculate user activity based on filtered issues
    new_user_activity = {}
    for _, issue in filtered_table.iterrows():
        creator = issue['creator']
        if creator not in new_user_activity:
            new_user_activity[creator] = {'assigned': 0, 'closed': 0, 'comments': 0}
        
        # Count assignments
        for assignee in issue.get('assignees', []):
            if assignee not in new_user_activity:
                new_user_activity[assignee] = {'assigned': 0, 'closed': 0, 'comments': 0}
            new_user_activity[assignee]['assigned'] += 1
        
        # Count closed issues
        if not pd.isna(issue['closed_at']) and start_date <= issue['closed_at'].date() <= end_date:
            new_user_activity[creator]['closed'] += 1
        
        # Count comments
        for author, count in issue.get('comments_by_author', {}).items():
            if author not in new_user_activity:
                new_user_activity[author] = {'assigned': 0, 'closed': 0, 'comments': 0}
            new_user_activity[author]['comments'] += count
    
    filtered_user_activity = pd.DataFrame.from_dict(new_user_activity, orient='index')
    filtered_user_activity['user'] = filtered_user_activity.index
    filtered_user_activity = filtered_user_activity.reset_index(drop=True)
    
    return filtered_daily, filtered_user_activity, filtered_table

def generate_plotly_charts(daily_activity, user_activity_df):
    """Generate Plotly charts for the report."""
    # Create subplots for line charts
    fig1 = make_subplots(rows=2, cols=2, 
                        subplot_titles=("Issues Created Per Day", "Issues Closed Per Day", 
                                       "Comments Per Day", "Active People Per Day"))
    
    # Add traces for each subplot
    fig1.add_trace(
        go.Scatter(x=daily_activity['date'], y=daily_activity['issues_created'], mode='lines+markers',
                  name='Issues Created', line=dict(color='blue')),
        row=1, col=1
    )
    
    fig1.add_trace(
        go.Scatter(x=daily_activity['date'], y=daily_activity['issues_closed'], mode='lines+markers',
                  name='Issues Closed', line=dict(color='green')),
        row=1, col=2
    )
    
    fig1.add_trace(
        go.Scatter(x=daily_activity['date'], y=daily_activity['comments'], mode='lines+markers',
                  name='Comments', line=dict(color='orange')),
        row=2, col=1
    )
    
    fig1.add_trace(
        go.Scatter(x=daily_activity['date'], y=daily_activity['active_users'], mode='lines+markers',
                  name='Active People', line=dict(color='purple')),
        row=2, col=2
    )
    
    # Update layout for the first figure
    fig1.update_layout(
        height=800,
        autosize=True,  # Enable autosize for responsiveness
        title_text="Daily Activity",
        showlegend=True,  # Show legend
        legend=dict(orientation="h", y=-0.1),  # Place legend at the bottom horizontally
        margin=dict(l=50, r=50, t=100, b=100)  # Adjust margins to accommodate legend
    )
    
    # Define consistent colors for the bar chart categories
    color_map = {
        'assigned': 'rgb(49, 130, 189)',  # Blue
        'closed': 'rgb(50, 171, 96)',     # Green
        'comments': 'rgb(222, 45, 38)'    # Red
    }
    
    # Create a bar chart for user activity
    fig2 = px.bar(
        user_activity_df,
        x='user',
        y=['assigned', 'closed', 'comments'],
        labels={'user': 'User', 'value': 'Count', 'variable': 'Activity Type'},
        title='Activity by User',
        barmode='group',
        height=600,
        color_discrete_map=color_map  # Use our custom color map
    )
    
    fig2.update_layout(
        autosize=True,  # Enable autosize for responsiveness
        xaxis=dict(tickangle=45),
        margin=dict(l=50, r=50, t=100, b=100)  # Adjust margins
    )
    
    # Return HTML with config to make plots responsive
    config = {'responsive': True}
    return fig1.to_html(full_html=False, include_plotlyjs='cdn', config=config), fig2.to_html(full_html=False, include_plotlyjs='cdn', config=config)

def format_date(date_obj):
    """Format date object to string."""
    if isinstance(date_obj, datetime):
        return date_obj.strftime('%Y-%m-%d')
    return str(date_obj) if date_obj else ''

def generate_html_report(data_file_path, output_file_path):
    """Generate an HTML report from the GitHub issue data."""
    data = load_data(data_file_path)
    if not data:
        print("Failed to load data.")
        return
    
    daily_activity, user_activity_df, table_df, devops_team_members = create_dataframes(data)
    
    # Get date range from data
    min_date = min(daily_activity['date'])
    max_date = max(daily_activity['date'])
    
    # Convert dates to string format for HTML
    min_date_str = min_date.strftime('%Y-%m-%d') if hasattr(min_date, 'strftime') else str(min_date)
    max_date_str = max_date.strftime('%Y-%m-%d') if hasattr(max_date, 'strftime') else str(max_date)
    
    # Generate charts
    line_charts_html, bar_chart_html = generate_plotly_charts(daily_activity, user_activity_df)
    
    # Calculate summary statistics
    total_issues = len(table_df)
    open_issues = sum(1 for state in table_df['state'] if state == 'open')
    closed_issues = sum(1 for state in table_df['state'] if state == 'closed')
    total_comments = sum(table_df['comments_count'])
    active_people = len(set([person for people_list in table_df['assignees'] for person in people_list] + 
                          list(table_df['creator']) + 
                          [author for comments_dict in table_df['comments_by_author'] for author in comments_dict.keys()]))
    
    # Format the table DataFrame for display
    formatted_table = []
    for _, row in table_df.iterrows():
        formatted_row = {
            'number': row['number'],
            'title': row['title'],
            'state': row['state'],
            'assignees': ', '.join(row['assignees']) if row['assignees'] else 'None',
            'created_at': format_date(row['created_at']),
            'closed_at': format_date(row['closed_at']) if not pd.isna(row['closed_at']) else 'Not closed',
            'comments_count': row['comments_count'],
            'active_people': row['active_people'],
            'url': row['url']
        }
        formatted_table.append(formatted_row)
    
    # Convert daily activity dates to strings for JSON
    daily_activity_for_json = daily_activity.copy()
    daily_activity_for_json['date'] = daily_activity_for_json['date'].apply(lambda d: d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else d)
    
    # Load JavaScript from external file
    js_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'report.js')
    with open(js_file_path, 'r') as js_file:
        js_content = js_file.read()
        
    # Replace the placeholder with actual data
    original_data_json = json.dumps({
        'daily_activity': daily_activity_for_json.to_dict('records'),
        'user_activity': user_activity_df.to_dict('records'),
        'table_data': formatted_table,
        'summary': {
            'total_issues': total_issues,
            'open_issues': open_issues,
            'closed_issues': closed_issues,
            'total_comments': total_comments,
            'active_people': active_people
        }
    })
    
    js_content = js_content.replace('ORIGINAL_DATA_PLACEHOLDER', original_data_json)
    
    # Create the HTML report
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitHub Issues Report</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.datatables.net/1.11.5/css/dataTables.bootstrap5.min.css">
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.11.5/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/1.11.5/js/dataTables.bootstrap5.min.js"></script>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            padding: 20px;
        }}
        .summary-card {{
            margin-bottom: 20px;
        }}
        .date-selector {{
            margin-bottom: 20px;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 5px;
        }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <h1 class="mb-4 text-center">GitHub Issues Report</h1>
        
        <!-- Date Range Selector -->
        <div class="date-selector">
            <div class="row g-3 align-items-center">
                <div class="col-auto">
                    <h4>Filters</h4>
                </div>
                <div class="col-auto">
                    <label for="start-date" class="col-form-label">Start Date:</label>
                </div>
                <div class="col-auto">
                    <input type="date" id="start-date" class="form-control" value="{min_date_str}">
                </div>
                <div class="col-auto">
                    <label for="end-date" class="col-form-label">End Date:</label>
                </div>
                <div class="col-auto">
                    <input type="date" id="end-date" class="form-control" value="{max_date_str}">
                </div>
                <div class="col-auto">
                    <button id="update-btn" class="btn btn-primary">Update</button>
                </div>
            </div>
        </div>
        <!-- Store DevOps team members in a script tag -->
        <script>
            window.devopsTeamMembers = {json.dumps(devops_team_members)};
        </script>
        
        <!-- Summary Cards -->
        <div class="row" id="summary-cards">
            <div class="col-md-2">
                <div class="card summary-card">
                    <div class="card-body text-center">
                        <h5 class="card-title">Total Issues</h5>
                        <p class="card-text fs-2" id="total-issues">{total_issues}</p>
                    </div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="card summary-card">
                    <div class="card-body text-center">
                        <h5 class="card-title">Open Issues</h5>
                        <p class="card-text fs-2" id="open-issues">{open_issues}</p>
                    </div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="card summary-card">
                    <div class="card-body text-center">
                        <h5 class="card-title">Closed Issues</h5>
                        <p class="card-text fs-2" id="closed-issues">{closed_issues}</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card summary-card">
                    <div class="card-body text-center">
                        <h5 class="card-title">Total Comments</h5>
                        <p class="card-text fs-2" id="total-comments">{total_comments}</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card summary-card">
                    <div class="card-body text-center">
                        <h5 class="card-title">Active People</h5>
                        <p class="card-text fs-2" id="active-people">{active_people}</p>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Charts -->
        <div class="charts mt-4">
            <h3>Activity Charts</h3>
            <div id="line-charts" class="mb-5">
                {line_charts_html}
            </div>
            
            <!-- Move DevOps toggle here, above the bar chart -->
            <div class="mb-3">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="devops-only">
                    <label class="form-check-label" for="devops-only">
                        DevOps Team Only
                    </label>
                </div>
            </div>
            
            <div id="bar-chart" class="mb-5">
                {bar_chart_html}
            </div>
            <!-- User Assignment Table -->
            <div class="table-responsive mb-5">
                <h4>User Assignments Summary</h4>
                <table id="user-assignments-table" class="table table-striped table-hover">
                    <thead>
                        <tr>
                            <th>User</th>
                            <th>Total Assigned</th>
                            <th>Open</th>
                            <th>Closed</th>
                            <th>Completion Rate</th>
                        </tr>
                    </thead>
                    <tbody>
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- Issues Table -->
        <div class="table-responsive mt-4">
            <h3>Issues</h3>
            <table id="issues-table" class="table table-striped table-hover">
                <thead>
                    <tr>
                        <th>Issue ID</th>
                        <th>Issue Title</th>
                        <th>Status</th>
                        <th>Assignee</th>
                        <th>Created Date</th>
                        <th>Closed Date</th>
                        <th>Comments</th>
                        <th>Active People</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(f"<tr><td><a href='{row['url']}' target='_blank'>{row['number']}</a></td><td>{row['title']}</td><td>{row['state']}</td><td>{row['assignees']}</td><td>{row['created_at']}</td><td>{row['closed_at']}</td><td>{row['comments_count']}</td><td>{row['active_people']}</td></tr>" for row in formatted_table)}
                </tbody>
            </table>
        </div>
    </div>
    <script>
        {js_content}
    </script>
</body>
</html>"""
    
    # Write the HTML report to file
    with open(output_file_path, 'w', encoding='utf-8') as file:
        file.write(html_content)
    
    print(f"{output_file_path}")

def main():
    parser = argparse.ArgumentParser(description='Generate HTML report from GitHub issues data.')
    parser.add_argument('--data', '-d', required=True, help='Path to the GitHub issues data JSON file')
    parser.add_argument('--output', '-o', default='github_issues_report.html', help='Output HTML file path')
    args = parser.parse_args()
    
    generate_html_report(args.data, args.output)

if __name__ == '__main__':
    main()