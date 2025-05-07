import matplotlib.pyplot as plt
import pandas as pd
import os

def read_excel_data(security_file, duplications_file, code_smell_file):
    """
    Read data from three Excel files and extract top improvements.
    """
    # Read Excel files
    sec_df = pd.read_excel(security_file)
    dup_df = pd.read_excel(duplications_file)
    smell_df = pd.read_excel(code_smell_file)
    
    # Calculate differences (improvements)
    sec_df['Improvement'] = sec_df['Security Hotspot (first)'] - sec_df['Security Hotspot (second)']
    dup_df['Improvement'] = dup_df['Duplications (first)'] - dup_df['Duplications (second)']
    smell_df['Improvement'] = smell_df['Code Smell (first)'] - smell_df['Code Smell (second)']
    
    # Filter for positive improvements only (first > second indicates improvement)
    sec_improvements = sec_df[sec_df['Improvement'] > 0].sort_values('Improvement', ascending=False)
    dup_improvements = dup_df[dup_df['Improvement'] > 0].sort_values('Improvement', ascending=False)
    smell_improvements = smell_df[smell_df['Improvement'] > 0].sort_values('Improvement', ascending=False)
    
    # Get top improvements (up to 5 per category)
    top_security = sec_improvements.head(5)
    top_duplications = dup_improvements.head(5)
    top_code_smell = smell_improvements.head(5)
    
    # Extract data for visualization
    data = {
        'Security Hotspot': dict(zip(top_security['Clean Name'], top_security['Improvement'])),
        'Duplications': dict(zip(top_duplications['Clean Name'], top_duplications['Improvement'])),
        'Code Smell': dict(zip(top_code_smell['Clean Name'], top_code_smell['Improvement']))
    }
    
    return data

def visualize_improvements(data, top_n=3):
    """
    Create visualizations for top improvements across categories.
    """
    # Colors
    colors = {
        'Security Hotspot': '#4CAF50',  # Green
        'Duplications': '#2196F3',      # Blue
        'Code Smell': '#FF9800'         # Orange
    }
    
    # Set style and increase font size for better readability
    plt.style.use('ggplot')
    plt.rcParams.update({'font.size': 11})
    
    # Take only top N for each category
    for category in data:
        # Sort items by value in descending order and keep only top N
        sorted_items = sorted(data[category].items(), key=lambda x: x[1], reverse=True)[:top_n]
        data[category] = dict(sorted_items)
    
    # Create a single figure with three subplots
    fig, axes = plt.subplots(3, 1, figsize=(10, 12), sharex=False)
    fig.suptitle(f'Top {top_n} Improvements Across Categories', fontsize=16, y=0.98)
    
    # Plot each category
    for i, (category, values) in enumerate(data.items()):
        names = list(values.keys())
        values_list = list(values.values())
        
        # Create horizontal bar chart
        bars = axes[i].barh(names, values_list, color=colors[category], alpha=0.8)
        axes[i].set_title(f'Top {top_n} {category} Improvements')
        
        # Add value labels on the bars
        for j, v in enumerate(values_list):
            if category == 'Duplications':
                # Format duplication values differently due to their small scale
                axes[i].text(v + (max(values_list) * 0.02), j, f'{v:.2f}', va='center')
            else:
                axes[i].text(v + (max(values_list) * 0.02), j, f'{v}', va='center')
        
        axes[i].set_ylabel('Repository')
        axes[i].invert_yaxis()  # Highest value at the top
        
        # Set appropriate x-axis limits
        axes[i].set_xlim(0, max(values_list) * 1.1)
    
    # Set the bottom x-axis label
    axes[2].set_xlabel('Improvement Value')
    
    # Adjust layout
    plt.tight_layout()
    plt.subplots_adjust(top=0.93)
    
    # Save figure
    plt.savefig('top_improvements_by_category.png', dpi=300, bbox_inches='tight')
    
    # Create a single combined chart
    plt.figure(figsize=(12, 10))
    
    # Prepare combined data
    all_data = []
    for category, repo_data in data.items():
        for repo, value in repo_data.items():
            # For display purposes, scale up duplication values
            display_value = value * 100 if category == 'Duplications' else value
            all_data.append({
                'Repository': repo,
                'Value': value,
                'Category': category,
                'DisplayValue': display_value
            })
    
    df = pd.DataFrame(all_data)
    
    # Sort by category
    df = df.sort_values(by=['Category', 'Value'], ascending=[True, False])
    
    # Create color mapping
    color_list = [colors[cat] for cat in df['Category']]
    
    # Plot combined chart
    plt.figure(figsize=(12, 10))
    bars = plt.barh(range(len(df)), df['DisplayValue'], color=color_list, alpha=0.8)
    plt.yticks(range(len(df)), df['Repository'])
    plt.gca().invert_yaxis()  # Highest values at top
    plt.xlabel('Improvement Value')
    plt.title(f'Top {top_n} Improvements Across Categories', fontsize=16)
    
    # Add a note about duplications scaling
    plt.figtext(0.5, 0.01, 'Note: Duplication values are scaled (x100) for better visibility', 
                ha='center', fontsize=10, style='italic')
    
    # Create legend
    handles = [plt.Rectangle((0,0),1,1, color=colors[cat], alpha=0.8) for cat in colors]
    plt.legend(handles, list(colors.keys()), loc='lower right')
    
    plt.tight_layout()
    plt.savefig('top_improvements_combined.png', dpi=300, bbox_inches='tight')
    
    print("Visualization completed! Two images have been saved:")
    print("1. top_improvements_by_category.png - Three separate charts")
    print("2. top_improvements_combined.png - Combined chart with all improvements")

# Example usage
if __name__ == "__main__":
    # File paths - update these to your actual Excel files
    security_file = "Security_Hotspot_comparison.xlsx"
    duplications_file = "Duplications_comparison.xlsx"
    code_smell_file = "Code_Smell_comparison.xlsx"
    
    # Read data from Excel files
    data = read_excel_data(security_file, duplications_file, code_smell_file)
    
    # Create visualizations showing top 3 improvements per category
    visualize_improvements(data, top_n=3)