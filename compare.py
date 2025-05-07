import matplotlib.pyplot as plt
import numpy as np

fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 20))
fig.suptitle('Top Code Quality Improvements (May - April)', fontsize=22, y=0.98)
plt.subplots_adjust(hspace=1.0)

bar_height = 0.9  # Makes bars fully occupy vertical slot

# Chart 1: Security Hotspot
security_repos = [
    'laravel-ronreload-backend (stage)',
    'angular-sln-fccz (stg)',
    'wordpress-bagelboys-website (stage)',
    'angular-sln-cz (stg)',
    'angular-sln-at (stg)'
]
security_values = [520, 105, 105, 100, 95]
y_pos1 = np.arange(len(security_repos))

ax1.barh(y_pos1, security_values, color='#2ecc71', height=bar_height)
ax1.set_yticks(y_pos1)
ax1.set_yticklabels(security_repos)
ax1.set_ylim(-0.5, len(security_repos) - 0.5)
ax1.set_title('Top Security Hotspot Improvements', fontsize=18)
ax1.title.set_position([0.5, 1.05])
ax1.grid(axis='x', linestyle='--', alpha=0.7)

for i, v in enumerate(security_values):
    ax1.text(v + 5, i, str(v), va='center', fontweight='bold')

# Chart 2: Duplication
duplication_repos = [
    'angular-delta-erp (stg-aks)',
    'laravel-pharmalys-corporatewebsite (stage)',
    'net-ipex-business (stg-aks)'
]
duplication_values = [0.60, 0.55, 0.40]
y_pos2 = np.arange(len(duplication_repos))

ax2.barh(y_pos2, duplication_values, color='#3498db', height=bar_height)
ax2.set_yticks(y_pos2)
ax2.set_yticklabels(duplication_repos)
ax2.set_ylim(-0.5, len(duplication_repos) - 0.5)
ax2.set_title('Top Duplication Improvements', fontsize=18)
ax2.title.set_position([0.5, 1.05])
ax2.grid(axis='x', linestyle='--', alpha=0.7)

for i, v in enumerate(duplication_values):
    ax2.text(v + 0.02, i, str(v), va='center', fontweight='bold')

# Chart 3: Code Smells
code_smell_repos = [
    'net-vorwerk-kiwi (stg)',
    'net-amberg-engr (stg)',
    'net-delta-erp (stg-aks)'
]
code_smell_values = [250, 150, 100]
y_pos3 = np.arange(len(code_smell_repos))

ax3.barh(y_pos3, code_smell_values, color='#9b59b6', height=bar_height)
ax3.set_yticks(y_pos3)
ax3.set_yticklabels(code_smell_repos)
ax3.set_ylim(-0.5, len(code_smell_repos) - 0.5)
ax3.set_title('Top Code Smell Improvements', fontsize=18)
ax3.title.set_position([0.5, 1.05])
ax3.grid(axis='x', linestyle='--', alpha=0.7)

for i, v in enumerate(code_smell_values):
    ax3.text(v + 5, i, str(v), va='center', fontweight='bold')

# Caption
plt.figtext(0.5, 0.015, 'Teams with the most significant code quality improvements worthy of recognition',
            ha='center', fontsize=12, bbox=dict(facecolor='#f8f9fa', alpha=0.8, boxstyle='round,pad=0.5'))

# Final layout
plt.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.show()
