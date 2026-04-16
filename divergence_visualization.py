"""
Create weekly divergence/convergence visualization for best predictable asset (LTCUSD).
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

# Load LTCUSD predictions
ltc_csv = Path("outputs/meta_historical/2026-04-16/14-55-45/LTCUSD/current_year_predictions.csv")
df = pd.read_csv(ltc_csv)
df['date'] = pd.to_datetime(df['date'])

# Aggregate to weekly (Monday is week start)
df['week'] = df['date'].dt.isocalendar().week
df['year'] = df['date'].dt.year

weekly_data = []
for (year, week), group in df.groupby(['year', 'week']):
    week_start = group['date'].min()
    week_end = group['date'].max()
    
    weekly_data.append({
        'week_start': week_start,
        'week_end': week_end,
        'actual_open': group['actual_close'].iloc[0],
        'actual_close': group['actual_close'].iloc[-1],
        'actual_high': group['actual_close'].max(),
        'actual_low': group['actual_close'].min(),
        'pred_open': group['predicted_close'].iloc[0],
        'pred_close': group['predicted_close'].iloc[-1],
        'pred_high': group['predicted_close'].max(),
        'pred_low': group['predicted_close'].min(),
        'abs_error_mean': group['abs_error'].mean(),
        'abs_error_max': group['abs_error'].max(),
        'abs_error_std': group['abs_error'].std(),
    })

weekly_df = pd.DataFrame(weekly_data)
weekly_df['divergence_pct'] = (weekly_df['abs_error_mean'] / weekly_df['actual_close']) * 100

# Calculate rolling average for divergence threshold
divergence_rolling_avg = weekly_df['abs_error_mean'].rolling(window=3, center=True).mean()
divergence_threshold = divergence_rolling_avg.mean()
convergence_threshold = divergence_rolling_avg.std() / 2

# Classify weeks
weekly_df['divergence_level'] = 'neutral'
weekly_df.loc[weekly_df['abs_error_mean'] > divergence_threshold + convergence_threshold, 'divergence_level'] = 'divergence'
weekly_df.loc[weekly_df['abs_error_mean'] < divergence_threshold - convergence_threshold, 'divergence_level'] = 'convergence'

# Create figure with 2 subplots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), sharex=True)

# ===== SUBPLOT 1: PRICE + PREDICTIONS + DIVERGENCE PEAKS =====
x_pos = np.arange(len(weekly_df))

# Plot actual price line
ax1.plot(x_pos, weekly_df['actual_close'], 'o-', color='steelblue', linewidth=2.5, markersize=6, 
         label='Actual Weekly Close', alpha=0.8)

# Plot predicted price line
ax1.plot(x_pos, weekly_df['pred_close'], 's--', color='orange', linewidth=2, markersize=5, 
         label='Predicted Weekly Close', alpha=0.7)

# Plot divergence/convergence bars with color coding
for i, row in weekly_df.iterrows():
    if row['divergence_level'] == 'divergence':
        ax1.axvspan(i - 0.4, i + 0.4, alpha=0.15, color='red')
    elif row['divergence_level'] == 'convergence':
        ax1.axvspan(i - 0.4, i + 0.4, alpha=0.15, color='green')

# Annotate divergence/convergence peaks
divergence_peaks = weekly_df[weekly_df['divergence_level'] == 'divergence']
convergence_peaks = weekly_df[weekly_df['divergence_level'] == 'convergence']

for i, row in divergence_peaks.iterrows():
    ax1.annotate('DIV', xy=(i, row['actual_close']), xytext=(i, row['actual_close'] + 2),
                fontsize=8, ha='center', color='red', weight='bold', alpha=0.7)

for i, row in convergence_peaks.iterrows():
    ax1.annotate('CON', xy=(i, row['actual_close']), xytext=(i, row['actual_close'] - 2),
                fontsize=8, ha='center', color='green', weight='bold', alpha=0.7)

ax1.set_ylabel('Price (USD)', fontsize=12, weight='bold')
ax1.set_title('LTCUSD: Weekly Price Predictions vs Actuals with Divergence/Convergence Peaks\n' + 
              '(Red=Divergence >Threshold | Green=Convergence <Threshold)', 
              fontsize=13, weight='bold', pad=15)
ax1.grid(True, alpha=0.3, linestyle='--')
ax1.legend(loc='upper left', fontsize=11)

# ===== SUBPLOT 2: ABSOLUTE ERROR (DIVERGENCE MAGNITUDE) =====
colors = ['red' if x == 'divergence' else 'green' if x == 'convergence' else 'gray' 
          for x in weekly_df['divergence_level']]
ax2.bar(x_pos, weekly_df['abs_error_mean'], color=colors, alpha=0.7, edgecolor='black', linewidth=1.2)

# Plot rolling average
ax2.plot(x_pos, divergence_rolling_avg, 'b-', linewidth=2.5, label='Rolling Avg (3-week)', alpha=0.8)

# Plot thresholds
ax2.axhline(divergence_threshold, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Divergence Threshold')
ax2.axhline(divergence_threshold - convergence_threshold, color='green', linestyle='--', linewidth=2, alpha=0.7, label='Convergence Threshold')

ax2.set_ylabel('Mean Absolute Error (USD)', fontsize=12, weight='bold')
ax2.set_xlabel('Week Number', fontsize=12, weight='bold')
ax2.set_title('Weekly Prediction Error Magnitude (Divergence Analysis)', fontsize=13, weight='bold', pad=15)
ax2.grid(True, alpha=0.3, linestyle='--', axis='y')
ax2.legend(loc='upper right', fontsize=11)

# Set x-axis labels (week numbers)
week_labels = [f"W{i+1}" for i in range(len(weekly_df))]
ax2.set_xticks(x_pos)
ax2.set_xticklabels(week_labels, fontsize=9)

plt.tight_layout()

# Save
output_path = Path("outputs/meta_historical/best_asset_divergence_analysis.png")
output_path.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"\n✓ Divergence visualization saved: {output_path}")

# Print summary statistics
print("\n" + "="*70)
print("LTCUSD WEEKLY DIVERGENCE/CONVERGENCE ANALYSIS")
print("="*70)
print(f"\nTotal Weeks Analyzed: {len(weekly_df)}")
print(f"Divergence Peaks (high error): {len(divergence_peaks)} weeks")
print(f"Convergence Peaks (low error): {len(convergence_peaks)} weeks")
print(f"\nMean Absolute Error Statistics:")
print(f"  Overall Mean Error: ${weekly_df['abs_error_mean'].mean():.4f}")
print(f"  Weekly Error Std Dev: ${weekly_df['abs_error_mean'].std():.4f}")
print(f"  Max Weekly Error: ${weekly_df['abs_error_mean'].max():.4f}")
print(f"  Min Weekly Error: ${weekly_df['abs_error_mean'].min():.4f}")
print(f"\nDivergence Threshold: ${divergence_threshold:.4f} (mean + 1σ)")
print(f"Convergence Threshold: ${divergence_threshold - convergence_threshold:.4f} (mean - 0.5σ)")

# Identify worst and best weeks
worst_week_idx = weekly_df['abs_error_mean'].idxmax()
best_week_idx = weekly_df['abs_error_mean'].idxmin()

print(f"\nWorst Prediction Week:")
print(f"  {weekly_df.loc[worst_week_idx, 'week_start'].strftime('%Y-%m-%d')} - " +
      f"{weekly_df.loc[worst_week_idx, 'week_end'].strftime('%Y-%m-%d')}")
print(f"  Error: ${weekly_df.loc[worst_week_idx, 'abs_error_mean']:.4f} (Max: ${weekly_df.loc[worst_week_idx, 'abs_error_max']:.4f})")
print(f"  Actual Close: ${weekly_df.loc[worst_week_idx, 'actual_close']:.2f}")

print(f"\nBest Prediction Week:")
print(f"  {weekly_df.loc[best_week_idx, 'week_start'].strftime('%Y-%m-%d')} - " +
      f"{weekly_df.loc[best_week_idx, 'week_end'].strftime('%Y-%m-%d')}")
print(f"  Error: ${weekly_df.loc[best_week_idx, 'abs_error_mean']:.4f} (Max: ${weekly_df.loc[best_week_idx, 'abs_error_max']:.4f})")
print(f"  Actual Close: ${weekly_df.loc[best_week_idx, 'actual_close']:.2f}")

print("\n" + "="*70)
