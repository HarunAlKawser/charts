import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np
import re
from openpyxl import Workbook
from openpyxl.styles import PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.drawing.image import Image

# Function to extract clean repository name
def clean_repo_name(repo_name):
    # Look for patterns like l3-angular-delta, l3-laravel-pharmalys, etc.
    patterns = [
        r'l\d+-(\w+)-([^_\s]+)',  # Matches l3-angular-delta or l3-laravel-pharmalys
        r'l\d+-(\w+)-([^_\s]+)-(\w+)'  # Matches l3-angular-delta-erp or l3-net-ipex-business
    ]
    
    for pattern in patterns:
        match = re.search(pattern, repo_name, re.IGNORECASE)
        if match:
            if len(match.groups()) == 2:
                tech, project = match.groups()
                return f"{tech}-{project}"
            elif len(match.groups()) == 3:
                tech, project, suffix = match.groups()
                return f"{tech}-{project}-{suffix}"
    
    # If no standard pattern, try to extract meaningful part
    if '_' in repo_name:
        # Try to extract from SELISEdigitalplatforms_l3-name_ID format
        parts = repo_name.split('_')
        if len(parts) >= 2:
            for part in parts:
                if part.startswith('l'):
                    return clean_repo_name(part)  # Recursively clean this part
    
    # If we can't extract a cleaner name, return the original
    return repo_name

# Function to filter data based on branch criteria
def filter_branch_data(df):
    # Remove any blank rows where any essential column is missing
    df = df.dropna(subset=['Repository Name', 'Branch'])
    
    branch_filters = ['stg', 'stage', 'stg-aks', 'stagging']
    mask = df['Branch'].str.contains('|'.join(branch_filters), case=False, na=False)
    return df[mask]

# Function to compare metrics and generate results
def compare_metrics(first_month, second_month, metric_name, min_diff=0):
    # Create a dictionary to store the results
    results = []
    
    # Create a unique identifier for each repo-branch combination
    first_month['RepoAndBranch'] = first_month['Repository Name'] + '___' + first_month['Branch']
    second_month['RepoAndBranch'] = second_month['Repository Name'] + '___' + second_month['Branch']
    
    # Get unique repo-branch combinations from both months
    first_repo_branches = set(first_month['RepoAndBranch'])
    second_repo_branches = set(second_month['RepoAndBranch'])
    
    # Find common repo-branch combinations
    common_repo_branches = first_repo_branches.intersection(second_repo_branches)
    
    # For each common repo-branch, compare the metric values
    for repo_branch in common_repo_branches:
        # Skip if the identifier is empty or NaN
        if pd.isna(repo_branch) or repo_branch == '':
            continue
        
        # Split the identifier back to repository and branch
        repo, branch = repo_branch.split('___')
        
        # Skip if repo is empty
        if pd.isna(repo) or repo == '':
            continue
            
        # Get the first value for this repo-branch, skip if missing
        first_row = first_month[first_month['RepoAndBranch'] == repo_branch]
        if first_row.empty or pd.isna(first_row[metric_name].values[0]):
            continue
        first_value = first_row[metric_name].values[0]
        
        # Get the second value for this repo-branch, skip if missing
        second_row = second_month[second_month['RepoAndBranch'] == repo_branch]
        if second_row.empty or pd.isna(second_row[metric_name].values[0]):
            continue
        second_value = second_row[metric_name].values[0]
        
        # Calculate the difference
        difference = second_value - first_value
        
        # For Code Smell, check if the absolute difference is >= 20 OR <= -20
        if metric_name == 'Code Smell' and abs(difference) < 20:
            continue
        
        # For other metrics, check if there's any change
        if metric_name != 'Code Smell' and difference == 0:
            continue
        
        # Get a clean repository name
        clean_name = clean_repo_name(repo)
        
        # Add to results
        results.append({
            'Repository Name': repo,
            'Branch': branch,
            'Clean Name': clean_name,
            f'{metric_name}_first': first_value,
            f'{metric_name}_second': second_value,
            f'{metric_name}_Difference': difference
        })
    
    # Convert results to DataFrame
    result_df = pd.DataFrame(results)
    
    return result_df

# Function to create Excel file with color coding
def create_excel_with_color(df, metric_name, output_file):
    # If no changes, create a simple excel with a message
    if df.empty:
        wb = Workbook()
        ws = wb.active
        ws.title = f"{metric_name} Changes"
        ws.cell(row=1, column=1).value = f"No significant changes in {metric_name} between first and second"
        wb.save(output_file)
        print(f"No significant changes found for {metric_name}")
        return
    
    # Create a new workbook and select the active sheet
    wb = Workbook()
    ws = wb.active
    ws.title = f"{metric_name} Changes"
    
    # Add headers and data to worksheet
    headers = [
        "Repository Name",
        "Branch", 
        "Clean Name",
        f"{metric_name} (first)", 
        f"{metric_name} (second)", 
        f"{metric_name} Difference"
    ]
    
    # Add the headers
    for col_num, header in enumerate(headers, 1):
        ws.cell(row=1, column=col_num).value = header
    
    # Add the data
    for row_num, row in enumerate(df.itertuples(index=False), 2):
        ws.cell(row=row_num, column=1).value = row[0]  # Repository Name
        ws.cell(row=row_num, column=2).value = row[1]  # Branch
        ws.cell(row=row_num, column=3).value = row[2]  # Clean Name
        ws.cell(row=row_num, column=4).value = row[3]  # first value
        ws.cell(row=row_num, column=5).value = row[4]  # second value
        ws.cell(row=row_num, column=6).value = row[5]  # Difference
        
        # Apply color to the difference cell
        # Green if negative (improvement), Red if positive (regression)
        if row[5] < 0:
            ws.cell(row=row_num, column=6).fill = PatternFill(start_color="00FF00", end_color="00FF00", fill_type="solid")
        else:
            ws.cell(row=row_num, column=6).fill = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")
    
    # Create a vertical bar chart with positive and negative values going in opposite directions
    fig, ax = plt.figure(figsize=(10, 8)), plt.subplot(111)
    
    # Sort by difference for better visualization
    plot_df = df.sort_values(f'{metric_name}_Difference')
    
    # Add branch name to the clean name for the chart
    plot_df['Display_Name'] = plot_df['Clean Name'] + ' (' + plot_df['Branch'] + ')'
    
    # Plot the horizontal bars (which will appear as vertical when we flip the axes)
    # Separate positive and negative values
    pos_mask = plot_df[f'{metric_name}_Difference'] >= 0
    neg_mask = plot_df[f'{metric_name}_Difference'] < 0
    
    # SWAPPED: Plot positive values (regressions) on the LEFT
    if pos_mask.any():
        ax.barh(
            y=plot_df.loc[pos_mask, 'Display_Name'],
            width=-plot_df.loc[pos_mask, f'{metric_name}_Difference'],  # Negative width to go left
            color='red',
            label='Regression'
        )
    
    # SWAPPED: Plot negative values (improvements) on the RIGHT
    if neg_mask.any():
        ax.barh(
            y=plot_df.loc[neg_mask, 'Display_Name'],
            width=-plot_df.loc[neg_mask, f'{metric_name}_Difference'],  # Negative width to flip direction
            color='green',
            label='Improvement'
        )
    
    # Add a vertical line at x=0
    ax.axvline(0, color='black', linestyle='-', linewidth=0.5)
    
    plt.title(f'{metric_name} Difference (May - April)')
    plt.xlabel('Difference (absolute value)')
    plt.ylabel('Repository and Branch')
    plt.grid(axis='x', linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    # Add legend
    if pos_mask.any() or neg_mask.any():
        plt.legend()
    
    # Save the chart
    chart_file = f"{metric_name}_chart.png"
    plt.savefig(chart_file)
    plt.close()
    
    # Add the chart to the Excel file
    img = Image(chart_file)
    img.width, img.height = 600, 400
    ws.add_image(img, 'H2')
    
    # Save the Excel workbook
    wb.save(output_file)
    
    # Clean up the temporary chart file
    os.remove(chart_file)

# NEW FUNCTION: Extract top improvements for each metric
def get_top_improvements(df, metric_name, top_n=5):
    """Extract top N improvements (negative differences) for a metric"""
    if df.empty:
        return pd.DataFrame()
    
    # Filter only improvements (negative difference)
    improvements = df[df[f'{metric_name}_Difference'] < 0].copy()
    
    if improvements.empty:
        return pd.DataFrame()
    
    # Sort by difference (ascending, so most negative values first)
    improvements = improvements.sort_values(by=f'{metric_name}_Difference')
    
    # Take top N improvements
    top_improvements = improvements.head(top_n)
    
    # Add display name for the chart
    top_improvements['Display_Name'] = top_improvements['Clean Name'] + ' (' + top_improvements['Branch'] + ')'
    
    return top_improvements

# NEW FUNCTION: Create combined chart with top improvements for all metrics
def create_combined_top_improvements_chart(result_dfs, metrics, output_file='top_improvements.png', top_n=3):
    """Create a combined chart showing top improvements for all metrics"""
    
    # Create figure with subplots (one for each metric)
    # Reduce overall figure size and adjust height per subplot
    fig, axes = plt.subplots(len(metrics), 1, figsize=(10, 2.5 * len(metrics)), constrained_layout=False)
    
    # Set an even slimmer bar height
    bar_height = 0.5
    
    # Set a consistent style for a more professional look
    plt.style.use('seaborn-v0_8-whitegrid')
    
    # Set consistent colors
    bar_color = '#2ECC71'  # A nicer green
    
    # Standard padding between subplots
    plt.subplots_adjust(hspace=0.4)
    
    # If only one metric has data, axes will be a single object instead of array
    if len(metrics) == 1:
        axes = [axes]
    
    # Process each metric
    for i, metric in enumerate(metrics):
        ax = axes[i]
        
        # Get the dataframe for this metric
        df = result_dfs[i]
        
        if df.empty:
            ax.text(0.5, 0.5, f"No improvements found for {metric}", 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes, fontsize=12)
            continue
        
        # Get top improvements
        # Use top_n=2 or 3 as requested
        actual_top_n = 2 if metric == 'Duplications' else 3
        top_improvements = get_top_improvements(df, metric, actual_top_n)
        
        if top_improvements.empty:
            ax.text(0.5, 0.5, f"No improvements found for {metric}", 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes, fontsize=12)
            continue
        
        # Plot the horizontal bars
        # We want to display the bars in descending order (biggest improvement at top)
        top_improvements = top_improvements.iloc[::-1]  # Reverse the order
        
        # Normalize the y-positions to ensure consistent spacing regardless of number of bars
        # Create positions with no gaps between bars
        positions = np.arange(len(top_improvements))
        
        # Create horizontal bars with consistent height and no gaps
        bars = ax.barh(
            y=positions,  # Use normalized positions
            width=-top_improvements[f'{metric}_Difference'],  # Negative to show positive bars for improvements
            color=bar_color,
            height=bar_height,  # Even slimmer bars
            align='center'  # Center alignment
        )
        
        # Adjust y-axis to ensure proper labeling
        ax.set_yticks(positions)
        ax.set_yticklabels(top_improvements['Display_Name'], fontsize=9)
        
        # Set consistent y-limits regardless of number of bars
        # This ensures the chart height is the same whether it has 2 or 3 bars
        ax.set_ylim(-0.5, max(2.5, len(positions) - 0.1))  # Ensure minimum of 3 positions worth of height
        
        # Add values at the end of each bar
        for bar in bars:
            width = bar.get_width()
            label_x_pos = width * 1.01  # Position just to the right of the bar
            
            # Format label based on metric
            if metric == 'Duplications':
                # Show Duplications with fraction/decimal values
                formatted_value = f'{abs(width):.2f}'
            else:
                # Show other metrics as integers
                formatted_value = f'{abs(width):.0f}'
                
            ax.text(label_x_pos, bar.get_y() + bar.get_height()/2, formatted_value,
                    va='center', fontsize=8, color='#555555', fontweight='bold')
        
        # Set title and labels - more concise and clean
        ax.set_title(f'Top {metric} Improvements', fontsize=10, pad=6)
        ax.set_xlabel('Improvement Value', fontsize=9)
        
        # Lighter grid for better appearance
        ax.grid(axis='x', linestyle='--', alpha=0.3)
        
        # Remove y-axis label to save space
        ax.set_ylabel('')
        
        # Add a subtle vertical line at x=0
        ax.axvline(0, color='#CCCCCC', linestyle='-', linewidth=0.5, alpha=0.5)
    
    # Add overall title - more concise and professional
    plt.suptitle('Code Quality Improvements (May - April)', fontsize=14, y=0.98, fontweight='bold')
    
    # Save the combined chart with a white background
    plt.savefig(output_file, bbox_inches='tight', dpi=120, facecolor='white')
    
    plt.close()
    
    print(f"Created professional combined top improvements chart: {output_file}")
    return output_file

def main():
    try:
        # Load the Excel files (replace with your actual file paths)
        first_month = pd.read_excel('april_report.xlsx')
        second_month = pd.read_excel('may_report.xlsx')
        
        # Remove blank rows from both datasets by specifically checking essential columns
        # First, remove rows where Repository Name or Branch is missing
        first_month = first_month.dropna(subset=['Repository Name', 'Branch'])
        second_month = second_month.dropna(subset=['Repository Name', 'Branch'])
        
        # Also remove rows where the Repository Name is an empty string
        first_month = first_month[first_month['Repository Name'].str.strip() != '']
        second_month = second_month[second_month['Repository Name'].str.strip() != '']
        
        # Filter the data based on branch criteria
        first_filtered = filter_branch_data(first_month)
        second_filtered = filter_branch_data(second_month)
        
        # Compare and process each metric
        metrics = ['Code Smell', 'Duplications', 'Security Hotspot']
        all_results = []  # Store results for all metrics for combined chart
        
        for metric in metrics:
            # Only process repositories that have non-null values for this metric
            first_metric_filtered = first_filtered.dropna(subset=[metric])
            second_metric_filtered = second_filtered.dropna(subset=[metric])
            
            # Compare the metric between the two months
            result_df = compare_metrics(first_metric_filtered, second_metric_filtered, metric)
            all_results.append(result_df)  # Store result for combined chart
            
            # Create the output Excel file with color coding and chart
            output_file = f"{metric.replace(' ', '_')}_comparison.xlsx"
            create_excel_with_color(result_df, metric, output_file)
            
            if not result_df.empty:
                print(f"Generated {output_file} with {len(result_df)} repositories that had significant changes in {metric}")
                if metric == 'Code Smell':
                    print("Note: For Code Smell, only changes with absolute difference ≥ 20 are included")
        
        # Create a combined chart with top improvements for all metrics
        create_combined_top_improvements_chart(all_results, metrics, 'top_improvements.png')
        
        print("\nProcessing complete! All output files have been generated.")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()