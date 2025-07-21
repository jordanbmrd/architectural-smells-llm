import sys
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

def main():
    if len(sys.argv) != 2:
        print("Usage: python plot_smell_by_subtype_layered.py <input_csv>")
        sys.exit(1)

    input_csv = sys.argv[1]

    # Loading data
    df = pd.read_csv(input_csv)

    # Cleaning
    df = df.dropna(subset=["smell_count", "subtype"])
    df["smell_count"] = pd.to_numeric(df["smell_count"], errors='coerce')
    df = df.dropna(subset=["smell_count"])

    # Style setup
    sns.set_theme(style="whitegrid")

    plt.figure(figsize=(10, 6))

    # Plot: smell count on X-axis, subtype on Y-axis
    sns.stripplot(
        data=df,
        x="smell_count",
        y="subtype",
        hue="subtype",
        dodge=False,
        alpha=0.7,
        jitter=True
    )

    plt.title("Distribution of smells by file subtype")
    plt.xlabel("Number of smells")
    plt.ylabel("File subtype")
    plt.legend(title="Subtype", bbox_to_anchor=(1.05, 1), loc='upper left')

    # Saving
    output_path = input_csv.replace(".csv", "_smell_layered_plot.png")
    plt.tight_layout()
    plt.savefig(output_path)
    print(f"Graph saved to: {output_path}")

if __name__ == "__main__":
    main()
