#!/usr/bin/env python3
"""
Script pour consolider les rapports de qualité de code de toutes les versions
en un seul fichier CSV avec les métriques spécifiées.
"""

import os
import csv
import glob
from collections import defaultdict, Counter
from pathlib import Path

def extract_version_from_path(path):
    """Extrait le numéro de version du chemin du dossier."""
    return Path(path).parent.name

def count_smells_by_type(csv_file_path):
    """
    Compte les types de smells dans un fichier CSV.
    
    Args:
        csv_file_path (str): Chemin vers le fichier CSV
        
    Returns:
        dict: Dictionnaire avec les comptes de chaque type de smell
    """
    smell_counts = defaultdict(int)
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                smell_name = row.get('Name', '').strip()
                
                # Mapping des noms de smells vers les colonnes demandées
                if smell_name:
                    smell_counts[smell_name] += 1
                    
    except FileNotFoundError:
        print(f"Fichier non trouvé: {csv_file_path}")
    except Exception as e:
        print(f"Erreur lors de la lecture de {csv_file_path}: {e}")
    
    return smell_counts

def map_smells_to_columns(smell_counts):
    """
    Mappe les smells détectés vers les colonnes demandées.
    
    Args:
        smell_counts (dict): Dictionnaire des comptes de smells
        
    Returns:
        dict: Dictionnaire avec les valeurs pour chaque colonne demandée
    """
    # Mapping des smells détectés vers les colonnes demandées
    column_mapping = {
        'Hub-like dependencies': smell_counts.get('Hub-like Dependency', 0),
        'Scattered functionality': smell_counts.get('Scattered Functionality', 0),
        'Cyclic dependencies': smell_counts.get('Cyclic Dependency', 0),
        'God objects': smell_counts.get('God Object', 0),
        'Unstable dependencies': smell_counts.get('Unstable Dependency', 0),
        'Improper API usage': smell_counts.get('Potential Improper API Usage', 0),
        'Redundant abstractions': smell_counts.get('Potential Redundant Abstractions', 0),
        'High cyclomatic complexity': smell_counts.get('High Cyclomatic Complexity', 0),
        'Deep inheritances trees': 0,  # Non détecté dans cette analyse
        'High coupling': smell_counts.get('High Response for a Class (RFC)', 0),
        'Low cohesion': smell_counts.get('High Lack of Cohesion of Methods (LCOM)', 0),
        'Excessive fan-in/fan-out': smell_counts.get('High Fan-in', 0) + smell_counts.get('High Fan-out', 0),
        'Large file sizes': smell_counts.get('Long File', 0) + smell_counts.get('High Lines of Code (LOC)', 0),
        'Complex conditional structures': smell_counts.get('Too Many Branches', 0),
        'Orphan modules': smell_counts.get('Orphan Module', 0)  # Colonne bonus détectée
    }
    
    return column_mapping

def analyze_versions():
    """
    Analyse toutes les versions dans le dossier versions_to_analyze.
    
    Returns:
        list: Liste des données pour chaque version
    """
    versions_data = []
    versions_dir = Path("versions_to_analyze")
    
    if not versions_dir.exists():
        print(f"Le dossier {versions_dir} n'existe pas!")
        return versions_data
    
    # Parcourir tous les dossiers de version
    for version_folder in sorted(versions_dir.iterdir()):
        if version_folder.is_dir() and version_folder.name.startswith('v'):
            version_name = version_folder.name
            csv_file = version_folder / "code_quality_report.csv"
            
            if csv_file.exists():
                print(f"Analyse de la version {version_name}...")
                
                # Compter les smells
                smell_counts = count_smells_by_type(csv_file)
                
                # Mapper vers les colonnes demandées
                column_data = map_smells_to_columns(smell_counts)
                
                # Ajouter la version
                row_data = {'Release version': version_name}
                row_data.update(column_data)
                
                versions_data.append(row_data)
                
                # Afficher un résumé pour cette version
                total_smells = sum(smell_counts.values())
                print(f"  - Total des smells détectés: {total_smells}")
                print(f"  - Types principaux: {dict(smell_counts)}")
                
            else:
                print(f"Aucun fichier code_quality_report.csv trouvé pour {version_name}")
    
    return versions_data

def generate_consolidated_report(versions_data, output_file="consolidated_code_quality_report.csv"):
    """
    Génère le rapport consolidé.
    
    Args:
        versions_data (list): Données de toutes les versions
        output_file (str): Nom du fichier de sortie
    """
    if not versions_data:
        print("Aucune donnée à écrire!")
        return
    
    # Définir les colonnes dans l'ordre demandé
    fieldnames = [
        'Release version',
        'Hub-like dependencies',
        'Scattered functionality',
        'Cyclic dependencies',
        'God objects',
        'Unstable dependencies',
        'Improper API usage',
        'Redundant abstractions',
        'High cyclomatic complexity',
        'Deep inheritances trees',
        'High coupling',
        'Low cohesion',
        'Excessive fan-in/fan-out',
        'Large file sizes',
        'Complex conditional structures',
        'Orphan modules'  # Colonne bonus
    ]
    
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Écrire l'en-tête
            writer.writeheader()
            
            # Écrire les données de chaque version
            for version_data in versions_data:
                writer.writerow(version_data)
        
        print(f"\n✅ Rapport consolidé généré: {output_file}")
        print(f"📊 {len(versions_data)} versions analysées")
        
    except Exception as e:
        print(f"❌ Erreur lors de la génération du rapport: {e}")

def main():
    """Fonction principale."""
    print("🔍 Consolidation des rapports de qualité de code")
    print("=" * 50)
    
    # Analyser toutes les versions
    versions_data = analyze_versions()
    
    if versions_data:
        # Générer le rapport consolidé
        generate_consolidated_report(versions_data)
        
        # Afficher un résumé final
        print("\n📈 Résumé des analyses:")
        print("-" * 30)
        for data in versions_data:
            version = data['Release version']
            total_issues = sum(v for k, v in data.items() if k != 'Release version' and isinstance(v, int))
            print(f"{version}: {total_issues} problèmes détectés")
    else:
        print("❌ Aucune donnée trouvée à consolider!")

if __name__ == "__main__":
    main() 