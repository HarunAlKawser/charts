import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Set style
plt.style.use('ggplot')

# Data for the improvements
# Security Hotspot Data
security_names = [
    'laravel-ronreload-backend',
    'angular-sln-fccz',
    'wordpress-bagelboys-website',
    'angular-sln-cz',
    'angular-sln-at'
]
security_values = [525, 100, 98, 95, 90]

# Duplications Data - Note: These are small values so we'll scale them for visibility
duplications_names = [
    'angular-delta-erp',
    'laravel-pharmalys-corporatewebsite',
    'net-ipex-business',
    'net-delta-erp',
    'angular-sln-cz'
]
duplications_values = [0.55, 0.45, 0.35, 0.25, 0.22]
# Scale for visualization
duplications_values_scaled = [val * 100 for val in duplications_values]

# Code Smell Data
code_smell_names = [
    'net-vorwerk-kiwi',
    'net-amberg-engr',
    'net-delta-erp',
    'net-clm-business',
    'net-ipex-business'
]
code_smell_values = [200, 150, 120, 80, 50]

# Create figure and subplots
fig, axes = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
fig.suptitle('Top Improvements Across Categories (May - April)', fontsize=16)

# Colors
security_color = '#4CAF50'  # Green
duplications_color = '#2196F3'  # Blue
code_smell_color = '#FF9800'  # Orange

# Plot Security Hotspot Improvements
axes[0].barh(security_names, security_values, color=security_color, alpha=0.8)
axes[0].set_title('Top 5 Security Hotspot Improvements')
axes[0].set_ylabel('Repository and Branch')
axes[0].invert_yaxis()  # Highest value at the top

# Plot Duplications Improvements
axes[1].barh(duplications_names, duplications_values_scaled, color=duplications_color, alpha=0.8)
axes[1].set_title('Top 5 Duplications Improvements (scaled x100)')
axes[1].set_ylabel('Repository and Branch')
axes[1].invert_yaxis()

# Add actual values as annotations for duplications
for i, v in enumerate(duplications_values):
    axes[1].text(duplications_values_scaled[i] + 5, i, f'Actual: {v:.2f}', 
                 va='center', fontsize=9)

# Plot Code Smell Improvements
axes[2].barh(code_smell_names, code_smell_values, color=code_smell_color, alpha=0.8)
axes[2].set_title('Top 5 Code Smell Improvements')
axes[2].set_xlabel('Improvement Value')
axes[2].set_ylabel('Repository and Branch')
axes[2].invert_yaxis()

# Adjust layout
plt.tight_layout()
plt.subplots_adjust(top=0.93)

# Save figure
plt.savefig('top_improvements.png', dpi=300, bbox_inches='tight')

# Show plot
plt.show()

# Alternative version: All in one chart
plt.figure(figsize=(12, 10))

# Combine all data
all_names = security_names + duplications_names + code_smell_names
all_values = security_values + duplications_values_scaled + code_smell_values
categories = ['Security Hotspot'] * 5 + ['Duplications'] * 5 + ['Code Smell'] * 5

# Create DataFrame
df = pd.DataFrame({
    'Repository': all_names,
    'Value': all_values,
    'Category': categories
})

# Sort by category and value
df = df.sort_values(by=['Category', 'Value'], ascending=[True, False])

# Create color mapping
colors = []
for category in df['Category']:
    if category == 'Security Hotspot':
        colors.append(security_color)
    elif category == 'Duplications':
        colors.append(duplications_color)
    else:
        colors.append(code_smell_color)

# Plot
plt.figure(figsize=(12, 10))
bars = plt.barh(range(len(df)), df['Value'], color=colors, alpha=0.8)
plt.yticks(range(len(df)), df['Repository'])
plt.gca().invert_yaxis()  # Highest values at top
plt.xlabel('Improvement Value')
plt.title('Top Improvements Across Categories (May - April)', fontsize=16)

# Add category labels on the right
for i, (category, value) in enumerate(zip(df['Category'], df['Value'])):
    if category == 'Duplications':
        actual_value = value / 100
        plt.text(value + 5, i, f'{category} ({actual_value:.2f})', va='center')
    else:
        plt.text(value + 5, i, category, va='center')

# Add a legend
handles = [
    plt.Rectangle((0,0),1,1, color=security_color, alpha=0.8),
    plt.Rectangle((0,0),1,1, color=duplications_color, alpha=0.8),
    plt.Rectangle((0,0),1,1, color=code_smell_color, alpha=0.8)
]
labels = ['Security Hotspot', 'Duplications (scaled x100)', 'Code Smell']
plt.legend(handles, labels, loc='lower right')

plt.tight_layout()
plt.savefig('top_improvements_combined.png', dpi=300, bbox_inches='tight')
plt.show()