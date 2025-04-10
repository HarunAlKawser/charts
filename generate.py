import pandas as pd
import matplotlib.pyplot as plt

# Load the Excel files for March and April reports
march_df = pd.read_excel('march_report.xlsx')  # Replace with your March file path
april_df = pd.read_excel('april_report.xlsx')  # Replace with your April file path

# Define the branches to filter
branches_to_check = ['stg', 'stage', 'stg-aks.stagging']

# Filter both dataframes by the given branches
march_filtered = march_df[march_df['Branch'].isin(branches_to_check)]
april_filtered = april_df[april_df['Branch'].isin(branches_to_check)]

# Remove rows with NaN or 0 in the relevant columns for both March and April data
columns_to_check = ['Code Smell', 'Duplications', 'Security Hotspot']

march_filtered = march_filtered[~march_filtered[columns_to_check].isin([0, '0']).any(axis=1)]
april_filtered = april_filtered[~april_filtered[columns_to_check].isin([0, '0']).any(axis=1)]

# Merge the two dataframes based on 'Repository Name'
merged_df = pd.merge(march_filtered, april_filtered, on='Repository Name', suffixes=('_march', '_april'))

# Remove rows where any relevant column (Code Smell, Duplications, Security Hotspot) is NaN or 0
merged_df = merged_df.dropna(subset=['Code Smell_march', 'Duplications_march', 'Security Hotspot_march', 
                                     'Code Smell_april', 'Duplications_april', 'Security Hotspot_april'])
merged_df = merged_df[~merged_df[['Code Smell_march', 'Duplications_march', 'Security Hotspot_march', 
                                  'Code Smell_april', 'Duplications_april', 'Security Hotspot_april']].isin([0, '0']).any(axis=1)]

# Initialize empty lists to store the results
code_smell_changes = []
duplication_changes = []
security_changes = []

# Compare Code Smell, Duplications, and Security Hotspot
for index, row in merged_df.iterrows():
    # Compare Code Smell (if different)
    if row['Code Smell_march'] != row['Code Smell_april']:
        code_smell_changes.append(row)

    # Compare Duplications (if different)
    if row['Duplications_march'] != row['Duplications_april']:
        duplication_changes.append(row)

    # Compare Security Hotspot (if different)
    if row['Security Hotspot_march'] != row['Security Hotspot_april']:
        security_changes.append(row)

# Convert the lists of changes to DataFrames
code_smell_df = pd.DataFrame(code_smell_changes)
duplication_df = pd.DataFrame(duplication_changes)
security_df = pd.DataFrame(security_changes)

# Save the results to separate Excel files with only the relevant columns
if not code_smell_df.empty:
    code_smell_df = code_smell_df[['Repository Name', 'Code Smell_march', 'Code Smell_april']]  # Only Code Smell columns
    code_smell_df.to_excel('code_smell_changes.xlsx', index=False)

if not duplication_df.empty:
    duplication_df = duplication_df[['Repository Name', 'Duplications_march', 'Duplications_april']]  # Only Duplications columns
    duplication_df.to_excel('duplication_changes.xlsx', index=False)

if not security_df.empty:
    security_df = security_df[['Repository Name', 'Security Hotspot_march', 'Security Hotspot_april']]  # Only Security Hotspot columns
    security_df.to_excel('security_changes.xlsx', index=False)

# Function to plot bar chart with color coding (green for decrease, red for increase)
def plot_bar_chart(df, column, title):
    # Create color list based on change direction: green for decrease, red for increase
    colors = ['green' if row[f'{column}_april'] < row[f'{column}_march'] else 'red' for _, row in df.iterrows()]
    
    # Plotting the bar chart
    plt.figure(figsize=(10, 6))
    plt.bar(df['Repository Name'], df[f'{column}_april'], color=colors)
    plt.title(title)
    plt.xlabel('Repository Name')
    plt.ylabel(f'{column} Value')
    plt.xticks(rotation=90)  # Rotate repository names for readability
    plt.tight_layout()  # Ensure everything fits in the plot
    plt.show()

# Plot bar charts for Code Smell, Duplications, and Security Hotspot
if not code_smell_df.empty:
    plot_bar_chart(code_smell_df, 'Code Smell', 'Code Smell Changes (March vs April)')
if not duplication_df.empty:
    plot_bar_chart(duplication_df, 'Duplications', 'Duplication Changes (March vs April)')
if not security_df.empty:
    plot_bar_chart(security_df, 'Security Hotspot', 'Security Hotspot Changes (March vs April)')

print("Comparison completed and files generated.")
