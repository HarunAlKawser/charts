// Initialize DataTable
$(document).ready(function() {
    $('#issues-table').DataTable({
        order: [[0, 'desc']],
        paging: false,
        pageLength: -1
    });
    
    // Store the original data
    window.originalData = ORIGINAL_DATA_PLACEHOLDER;
    
    // Initialize user assignments table with all data
    updateUserAssignmentsTable(window.originalData.user_activity);
    
    // Handle date range update
    $('#update-btn').click(function() {
        updateDataWithDateRange();
    });
    
    // Add DevOps toggle handler
    $('#devops-only').change(function() {
        const devopsOnly = $(this).is(':checked');
        updateBarChart(devopsOnly);
    });
});

function updateDataWithDateRange() {
    const startDate = $('#start-date').val();
    const endDate = $('#end-date').val();
    const devopsOnly = $('#devops-only').is(':checked');
    
    if (!startDate || !endDate) {
        alert('Please select both start and end dates.');
        return;
    }
    
    // Filter the original data based on the selected date range
    filterDataByDateRange(startDate, endDate, devopsOnly);
}

function filterDataByDateRange(startDate, endDate, devopsOnly) {
    const originalData = window.originalData;
    
    // Filter daily activity data
    const filteredDailyActivity = originalData.daily_activity.filter(item => {
        const date = item.date;
        return date >= startDate && date <= endDate;
    });
    
    // Filter table data
    const filteredTableData = originalData.table_data.filter(item => {
        const createdAt = item.created_at;
        const closedAt = item.closed_at === 'Not closed' ? null : item.closed_at;
        
        return (createdAt >= startDate && createdAt <= endDate) || 
               (closedAt && closedAt >= startDate && closedAt <= endDate);
    });
    
    // Get all users who have any activity (creator, assignee, commenter) in the filtered issues
    const activeUsers = new Set();
    
    filteredTableData.forEach(issue => {
        // Users can be creators, assignees, or commenters on an issue
        if (issue.assignees !== 'None') {
            issue.assignees.split(', ').forEach(user => activeUsers.add(user));
        }
        // We might also want to include other users who interacted with issues
        // but we don't have that data in the table_data
    });
    
    // Filter user activity for all active users
    let filteredUserActivity = originalData.user_activity.filter(user => {
        return activeUsers.has(user.user) || 
               // Also include users with assigned issues or comments
               (user.assigned > 0 || user.comments > 0 || user.closed > 0);
    });
    
    // Apply DevOps team filter if selected
    if (devopsOnly) {
        const devopsTeamMembers = window.devopsTeamMembers;
        filteredUserActivity = filteredUserActivity.filter(user => devopsTeamMembers.includes(user.user));
    }
    
    // Recalculate summary statistics
    const summary = {
        total_issues: filteredTableData.length,
        open_issues: filteredTableData.filter(item => item.state === 'open').length,
        closed_issues: filteredTableData.filter(item => item.state === 'closed').length,
        total_comments: filteredTableData.reduce((sum, item) => sum + item.comments_count, 0),
        active_people: activeUsers.size
    };
    
    // Update summary cards
    $('#total-issues').text(summary.total_issues);
    $('#open-issues').text(summary.open_issues);
    $('#closed-issues').text(summary.closed_issues);
    $('#total-comments').text(summary.total_comments);
    $('#active-people').text(summary.active_people);
    
    // Update the DataTable
    const table = $('#issues-table').DataTable();
    table.clear();
    filteredTableData.forEach(row => {
        // Create issue link HTML properly by escaping special characters
        const issueLink = document.createElement('a');
        issueLink.href = row.url;
        issueLink.target = '_blank';
        issueLink.textContent = row.number;
        const issueLinkHtml = issueLink.outerHTML;
        
        table.row.add([
            issueLinkHtml,
            row.title,
            row.state,
            row.assignees,
            row.created_at,
            row.closed_at,
            row.comments_count,
            row.active_people
        ]);
    });
    table.draw();
    
    // Update charts
    updateCharts(filteredDailyActivity, filteredUserActivity);
}

// Add function to update user assignments table
function updateUserAssignmentsTable(userActivity) {
    const table = $('#user-assignments-table tbody');
    table.empty();
    
    if (!userActivity || userActivity.length === 0) {
        console.log("No user activity data to display");
        return;
    }
    
    userActivity.forEach(user => {
        const totalAssigned = user.assigned || 0;
        const closed = user.closed || 0;
        const open = totalAssigned - closed;
        const completionRate = totalAssigned > 0 ? ((closed / totalAssigned) * 100).toFixed(1) : '0.0';
        
        const row = `<tr>
            <td>${user.user}</td>
            <td>${totalAssigned}</td>
            <td>${open}</td>
            <td>${closed}</td>
            <td>${completionRate}%</td>
        </tr>`;
        table.append(row);
    });
}

// Update the updateCharts function to also update the assignments table
function updateCharts(dailyActivity, userActivity) {
    // Create a subplot layout
    const layout = {
        grid: { rows: 2, columns: 2, pattern: 'independent' },
        height: 800,
        autosize: true,
        showlegend: true,
        legend: { orientation: "h", y: -0.1 },  // Place legend at the bottom horizontally
        margin: { l: 50, r: 50, t: 100, b: 100 }, // Adjust margins to accommodate legend
        annotations: [
            { text: "Issues Created Per Day", showarrow: false, x: 0.225, y: 1, xref: 'paper', yref: 'paper' },
            { text: "Issues Closed Per Day", showarrow: false, x: 0.775, y: 1, xref: 'paper', yref: 'paper' },
            { text: "Comments Per Day", showarrow: false, x: 0.225, y: 0.475, xref: 'paper', yref: 'paper' },
            { text: "Active People Per Day", showarrow: false, x: 0.775, y: 0.475, xref: 'paper', yref: 'paper' }
        ]
    };
    
    // Clear existing line charts
    Plotly.purge('line-charts');
    
    // Create new subplot figure
    const traces = [
        {
            x: dailyActivity.map(d => d.date),
            y: dailyActivity.map(d => d.issues_created),
            mode: 'lines+markers',
            name: 'Issues Created',
            line: { color: 'blue' },
            xaxis: 'x',
            yaxis: 'y'
        },
        {
            x: dailyActivity.map(d => d.date),
            y: dailyActivity.map(d => d.issues_closed),
            mode: 'lines+markers',
            name: 'Issues Closed',
            line: { color: 'green' },
            xaxis: 'x2',
            yaxis: 'y2'
        },
        {
            x: dailyActivity.map(d => d.date),
            y: dailyActivity.map(d => d.comments),
            mode: 'lines+markers',
            name: 'Comments',
            line: { color: 'orange' },
            xaxis: 'x3',
            yaxis: 'y3'
        },
        {
            x: dailyActivity.map(d => d.date),
            y: dailyActivity.map(d => d.active_users),
            mode: 'lines+markers',
            name: 'Active People',
            line: { color: 'purple' },
            xaxis: 'x4',
            yaxis: 'y4'
        }
    ];
    
    // Add domain definitions to layout
    layout.xaxis = { domain: [0, 0.45] };
    layout.yaxis = { domain: [0.55, 1] };
    layout.xaxis2 = { domain: [0.55, 1], anchor: 'y2' };
    layout.yaxis2 = { domain: [0.55, 1], anchor: 'x2' };
    layout.xaxis3 = { domain: [0, 0.45], anchor: 'y3' };
    layout.yaxis3 = { domain: [0, 0.45], anchor: 'x3' };
    layout.xaxis4 = { domain: [0.55, 1], anchor: 'y4' };
    layout.yaxis4 = { domain: [0, 0.45], anchor: 'x4' };
    
    // Create the plot
    Plotly.newPlot('line-charts', traces, layout);
    
    // Update bar chart for user activity
    const usersByActivity = userActivity.sort((a, b) => 
        (b.assigned + b.closed + b.comments) - (a.assigned + a.closed + a.comments)
    ).slice(0, 20); // Limit to top 20 users
    
    const barChartData = [
        {
            x: usersByActivity.map(u => u.user),
            y: usersByActivity.map(u => u.assigned),
            name: 'Assigned',
            type: 'bar',
            marker: { color: 'rgb(49, 130, 189)' }  // Blue
        },
        {
            x: usersByActivity.map(u => u.user),
            y: usersByActivity.map(u => u.closed),
            name: 'Closed',
            type: 'bar',
            marker: { color: 'rgb(50, 171, 96)' }   // Green
        },
        {
            x: usersByActivity.map(u => u.user),
            y: usersByActivity.map(u => u.comments),
            name: 'Comments',
            type: 'bar',
            marker: { color: 'rgb(222, 45, 38)' }   // Red
        }
    ];
    
    // Create new layout for bar chart
    const barChartLayout = {
        title: 'Activity by User',
        height: 600,
        autosize: true,
        barmode: 'group',
        xaxis: { tickangle: 45 },
        margin: { l: 50, r: 50, t: 100, b: 100 }
    };
    
    // Clear existing bar chart and re-render
    Plotly.purge('bar-chart');
    Plotly.newPlot('bar-chart', barChartData, barChartLayout);
    
    // Update user assignments table
    updateUserAssignmentsTable(userActivity);
}

// Update the updateBarChart function to also update the assignments table
function updateBarChart(devopsOnly) {
    let userActivity = window.originalData.user_activity;
    
    // Apply DevOps team filter if selected
    if (devopsOnly) {
        const devopsTeamMembers = window.devopsTeamMembers;
        userActivity = userActivity.filter(user => devopsTeamMembers.includes(user.user));
    }
    
    // Update user assignments table with filtered data
    updateUserAssignmentsTable(userActivity);
    
    // Sort users by total activity
    const usersByActivity = userActivity.sort((a, b) => 
        (b.assigned + b.closed + b.comments) - (a.assigned + a.closed + a.comments)
    ).slice(0, 20); // Limit to top 20 users
    
    const barChartData = [
        {
            x: usersByActivity.map(u => u.user),
            y: usersByActivity.map(u => u.assigned),
            name: 'Assigned',
            type: 'bar',
            marker: { color: 'rgb(49, 130, 189)' }  // Blue
        },
        {
            x: usersByActivity.map(u => u.user),
            y: usersByActivity.map(u => u.closed),
            name: 'Closed',
            type: 'bar',
            marker: { color: 'rgb(50, 171, 96)' }   // Green
        },
        {
            x: usersByActivity.map(u => u.user),
            y: usersByActivity.map(u => u.comments),
            name: 'Comments',
            type: 'bar',
            marker: { color: 'rgb(222, 45, 38)' }   // Red
        }
    ];
    
    const barChartLayout = {
        title: 'Activity by User',
        height: 600,
        autosize: true,
        barmode: 'group',
        xaxis: { tickangle: 45 },
        margin: { l: 50, r: 50, t: 100, b: 100 }
    };
    
    Plotly.react('bar-chart', barChartData, barChartLayout);
}