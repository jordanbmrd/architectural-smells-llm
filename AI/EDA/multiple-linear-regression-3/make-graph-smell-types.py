import sys
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os

def main():
    if len(sys.argv) != 2:
        print("Usage: python make-graph-smell-types.py <input_csv>")
        sys.exit(1)

    input_csv = sys.argv[1]

    # Loading data
    df = pd.read_csv(input_csv, low_memory=False)

    # Cleaning
    df = df.dropna(subset=["count", "smell"])
    df["count"] = pd.to_numeric(df["count"], errors='coerce')
    df = df.dropna(subset=["count"])
    
    # Define all required smell types
    required_smells = [
        "Hub-like Dependency",
        "Scattered Functionality", 
        "Cyclic Dependency",
        "God Object",
        "Unstable Dependency",
        "Potential Improper API Usage",
        "Redundant Abstraction",
        "Orphan Module"
    ]
    
    # Aggregate data by smell type (sum of all occurrences per smell type)
    smell_aggregated = df.groupby("smell")["count"].sum().reset_index()
    
    # Ensure all required smells are present, even with 0 count
    all_smells_df = pd.DataFrame({"smell": required_smells, "count": 0})
    smell_aggregated = pd.concat([all_smells_df, smell_aggregated], ignore_index=True)
    smell_aggregated = smell_aggregated.groupby("smell")["count"].max().reset_index()
    
    # Sort by count (descending)
    smell_aggregated = smell_aggregated.sort_values("count", ascending=False)

    # Style setup
    sns.set_theme(style="whitegrid")

    plt.figure(figsize=(12, 8))

    # Plot: horizontal bar chart
    sns.barplot(
        data=smell_aggregated,
        x="count",
        y="smell",
        palette="viridis"
    )

    plt.title("Total occurrences by smell type")
    plt.xlabel("Total number of occurrences")
    plt.ylabel("Smell type")

    # Saving
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_filename = os.path.basename(input_csv)
    output_filename = csv_filename.replace(".csv", "_smell_types_plot.png")
    output_path = os.path.join(script_dir, output_filename)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Graph saved to: {output_path}")

if __name__ == "__main__":
    main() 