import sys
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

def main():
    if len(sys.argv) != 2:
        print("Usage: python plot_smell_by_subtype_layered.py <input_csv>")
        sys.exit(1)

    input_csv = sys.argv[1]

    # Chargement des données
    df = pd.read_csv(input_csv)

    # Nettoyage
    df = df.dropna(subset=["smell_count", "subtype"])
    df["smell_count"] = pd.to_numeric(df["smell_count"], errors='coerce')
    df = df.dropna(subset=["smell_count"])

    # Préparation du style
    sns.set_theme(style="whitegrid")

    plt.figure(figsize=(10, 6))

    # Graphique : nombre de smells sur X, subtype en Y
    sns.stripplot(
        data=df,
        x="smell_count",
        y="subtype",
        hue="subtype",
        dodge=False,
        alpha=0.7,
        jitter=True
    )

    plt.title("Répartition des smells par sous-type de fichier")
    plt.xlabel("Nombre de smells")
    plt.ylabel("Sous-type de fichier")
    plt.legend(title="Subtype", bbox_to_anchor=(1.05, 1), loc='upper left')

    # Enregistrement
    output_path = input_csv.replace(".csv", "_smell_layered_plot.png")
    plt.tight_layout()
    plt.savefig(output_path)
    print(f"Graphique sauvegardé dans : {output_path}")

if __name__ == "__main__":
    main()
