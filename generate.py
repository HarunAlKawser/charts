import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.drawing.image import Image

# Function to filter data based on branch criteria
def filter_branch_data(df):
    # Remove any blank rows
    df = df.dropna(how='all')
    
    branch_filters = ['stg', 'stage', 'stg-aks.stagging']
    mask = df['Branch'].str.contains('|'.join(branch_filters), case=False, na=False)
    return df[mask]

# Function to compare metrics and generate results
def compare_metrics(march_df, april_df, metric_name, min_diff=0):
    # Merge the dataframes on Repository Name to find common repositories
    merged_df = pd.merge(
        march_df[['Repository Name', metric_name]], 
        april_df[['Repository Name', metric_name]], 
        on='Repository Name', 
        suffixes=('_March', '_April')
    )
    
    # Calculate the difference
    merged_df[f'{metric_name}_Difference'] = merged_df[f'{metric_name}_April'] - merged_df[f'{metric_name}_March']
    
    # Filter based on the metric and minimum difference
    if metric_name == 'Code Smell':
        # For Code Smell, only include if absolute difference is >= 50
        changed_df = merged_df[abs(merged_df[f'{metric_name}_Difference']) >= 50]
    else:
        # For other metrics, just filter out where there's no change
        changed_df = merged_df[merged_df[f'{metric_name}_Difference'] != 0]
    
    # Remove any rows with NaN values
    changed_df = changed_df.dropna()
    
    return changed_df

# Function to create Excel file with color coding
def create_excel_with_color(df, metric_name, output_file):
    # If no changes, create a simple excel with a message
    if df.empty:
        wb = Workbook()
        ws = wb.active
        ws.title = f"{metric_name} Changes"
        ws.cell(row=1, column=1).value = f"No significant changes in {metric_name} between March and April"
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
        f"{metric_name} (March)", 
        f"{metric_name} (April)", 
        f"{metric_name} Difference"
    ]
    
    # Add the headers
    for col_num, header in enumerate(headers, 1):
        ws.cell(row=1, column=col_num).value = header
    
    # Add the data
    for row_num, row in enumerate(df.itertuples(index=False), 2):
        ws.cell(row=row_num, column=1).value = row[0]  # Repository Name
        ws.cell(row=row_num, column=2).value = row[1]  # March value
        ws.cell(row=row_num, column=3).value = row[2]  # April value
        ws.cell(row=row_num, column=4).value = row[3]  # Difference
        
        # Apply color to the difference cell
        # Green if negative (improvement), Red if positive (regression)
        if row[3] < 0:
            ws.cell(row=row_num, column=4).fill = PatternFill(start_color="00FF00", end_color="00FF00", fill_type="solid")
        else:
            ws.cell(row=row_num, column=4).fill = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")
    
    # Create a vertical bar chart with positive and negative values going in opposite directions
    fig, ax = plt.figure(figsize=(10, 8)), plt.subplot(111)
    
    # Sort by difference for better visualization
    plot_df = df.sort_values(f'{metric_name}_Difference')
    
    # Plot the horizontal bars (which will appear as vertical when we flip the axes)
    # Separate positive and negative values
    pos_mask = plot_df[f'{metric_name}_Difference'] >= 0
    neg_mask = plot_df[f'{metric_name}_Difference'] < 0
    
    # Plot positive values (regressions)
    if pos_mask.any():
        ax.barh(
            y=plot_df.loc[pos_mask, 'Repository Name'],
            width=plot_df.loc[pos_mask, f'{metric_name}_Difference'],
            color='red',
            label='Regression'
        )
    
    # Plot negative values (improvements)
    if neg_mask.any():
        ax.barh(
            y=plot_df.loc[neg_mask, 'Repository Name'],
            width=plot_df.loc[neg_mask, f'{metric_name}_Difference'],
            color='green',
            label='Improvement'
        )
    
    # Add a vertical line at x=0
    ax.axvline(0, color='black', linestyle='-', linewidth=0.5)
    
    plt.title(f'{metric_name} Difference (April - March)')
    plt.xlabel('Difference')
    plt.ylabel('Repository')
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
    ws.add_image(img, 'F2')
    
    # Save the Excel workbook
    wb.save(output_file)
    
    # Clean up the temporary chart file
    os.remove(chart_file)

def main():
    try:
        # Load the Excel files (replace with your actual file paths)
        march_df = pd.read_excel('march_report.xlsx')
        april_df = pd.read_excel('april_report.xlsx')
        
        # Remove blank rows from both datasets
        march_df = march_df.dropna(how='all')
        april_df = april_df.dropna(how='all')
        
        # Filter the data based on branch criteria
        march_filtered = filter_branch_data(march_df)
        april_filtered = filter_branch_data(april_df)
        
        # Compare and process each metric
        metrics = ['Code Smell', 'Duplications', 'Security Hotspot']
        
        for metric in metrics:
            # Compare the metric between the two months
            result_df = compare_metrics(march_filtered, april_filtered, metric)
            
            # Create the output Excel file with color coding and chart
            output_file = f"{metric.replace(' ', '_')}_comparison.xlsx"
            create_excel_with_color(result_df, metric, output_file)
            
            if not result_df.empty:
                print(f"Generated {output_file} with {len(result_df)} repositories that had significant changes in {metric}")
                if metric == 'Code Smell':
                    print("Note: For Code Smell, only changes with absolute difference ≥ 50 are included")
        
        print("\nProcessing complete! All output files have been generated.")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()