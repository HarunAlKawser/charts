import matplotlib.pyplot as plt
import pandas as pd

# Set style and increase font size for better readability in emails
plt.style.use('ggplot')
plt.rcParams.update({'font.size': 11})

# Data for the improvements
data = {
    'Security Hotspot': {
        'laravel-ronreload-backend': 525,
        'angular-sln-fccz': 100,
        'wordpress-bagelboys-website': 98,
        'angular-sln-cz': 95,
        'angular-sln-at': 90
    },
    'Duplications': {
        'angular-delta-erp': 0.55,
        'laravel-pharmalys-corporatewebsite': 0.45,
        'net-ipex-business': 0.35,
        'net-delta-erp': 0.25,
        'angular-sln-cz': 0.22
    },
    'Code Smell': {
        'net-vorwerk-kiwi': 200,
        'net-amberg-engr': 150,
        'net-delta-erp': 120,
        'net-clm-business': 80,
        'net-ipex-business': 50
    }
}

# Colors
colors = {
    'Security Hotspot': '#4CAF50',  # Green
    'Duplications': '#2196F3',      # Blue
    'Code Smell': '#FF9800'         # Orange
}

# Create a single figure with three subplots
fig, axes = plt.subplots(3, 1, figsize=(10, 12), sharex=False)
fig.suptitle('Top Improvements Across Categories (May - April)', fontsize=16, y=0.98)

# Plot each category
for i, (category, values) in enumerate(data.items()):
    names = list(values.keys())
    values_list = list(values.values())
    
    # For duplications, we'll show the original values
    if category == 'Duplications':
        # Create a separate y-axis for the duplications to handle the small values
        bars = axes[i].barh(names, values_list, color=colors[category], alpha=0.8)
        axes[i].set_title(f'Top 5 {category} Improvements')
        # Add value labels directly on the bars
        for j, v in enumerate(values_list):
            axes[i].text(v + 0.01, j, f'{v:.2f}', va='center')
    else:
        bars = axes[i].barh(names, values_list, color=colors[category], alpha=0.8)
        axes[i].set_title(f'Top 5 {category} Improvements')
        # Add value labels for larger values
        for j, v in enumerate(values_list):
            axes[i].text(v + 10, j, f'{v}', va='center')
    
    axes[i].set_ylabel('Repository')
    axes[i].invert_yaxis()  # Highest value at the top
    
    # Set appropriate x-axis limits
    if category == 'Duplications':
        axes[i].set_xlim(0, max(values_list) * 1.3)
    else:
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
        all_data.append({
            'Repository': repo,
            'Value': value,
            'Category': category,
            'DisplayValue': value if category != 'Duplications' else value * 100  # Scale duplications for display
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
plt.title('Top Improvements Across Categories (May - April)', fontsize=16)

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