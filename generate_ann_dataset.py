#!/usr/bin/env python3
"""
Script pour générer le dataset final recommandé avec les colonnes essentielles
pour l'entraînement du modèle ANN.
"""

import os
import csv
import glob
import sys
import re
from collections import defaultdict, Counter
from pathlib import Path

def clean_file_path(file_path):
    """
    Nettoie le file_path pour ne garder que la partie après vX.X.X/
    
    Args:
        file_path (str): Chemin complet du fichier
        
    Returns:
        str: Chemin nettoyé sans la partie version
    """
    try:
        # Chercher l'index de la dernière occurrence d'un pattern vX.X.X/
        # Plus simple et plus robuste que regex
        parts = file_path.split('/')
        version_index = -1
        
        for i, part in enumerate(parts):
            if part.startswith('v') and '.' in part:
                # Vérifier si c'est un pattern de version simple
                version_parts = part.split('.')
                if len(version_parts) >= 2:  # Au moins vX.X
                    version_index = i
        
        if version_index >= 0 and version_index < len(parts) - 1:
            # Prendre tout après l'index de version
            return '/'.join(parts[version_index + 1:])
        else:
            # Retourner le chemin original si pas de version trouvée
            return file_path
            
    except Exception as e:
        print(f"Erreur dans clean_file_path: {e}")
        return file_path

def extract_smells_from_csv(csv_file_path, version):
    """
    Extrait tous les smells individuels d'un fichier CSV.
    
    Args:
        csv_file_path (str): Chemin vers le fichier CSV
        version (str): Version correspondante
        
    Returns:
        list: Liste de dictionnaires contenant les informations de chaque smell
    """
    smells = []
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                # Créer un identifiant unique pour le smell (file_path/module_class/smell_type)
                file_path_raw = row.get('File', '').strip()
                smell_name = row.get('Name', '').strip()
                module_class = row.get('Module/Class', '').strip()
                severity = row.get('Severity', '').strip()
                
                if file_path_raw and smell_name:
                    # Nettoyer le file_path pour ne garder que la partie après vX.X.X/
                    file_path = clean_file_path(file_path_raw)
                    # Debug: vérifier le résultat
                    print(f"DEBUG: file_path_raw='{file_path_raw}' -> file_path='{file_path}' (type: {type(file_path)})")
                    if str(file_path).startswith('<function'):
                        print(f"ERREUR: La fonction est assignée au lieu du résultat!")
                        file_path = file_path_raw  # Fallback au path original
                    # Créer l'ID du smell (format: file/module-class/smell-type) - tout collé sans espaces
                    # Nettoyer les espaces dans tous les composants
                    clean_file_path_no_spaces = file_path.replace(" ", "")
                    clean_module_class = module_class.replace(" ", "") if module_class else ""
                    clean_smell_name = smell_name.replace(" ", "")
                    
                    if clean_module_class:
                        smell_id = f"{clean_file_path_no_spaces}/{clean_module_class}/{clean_smell_name}"
                    else:
                        smell_id = f"{clean_file_path_no_spaces}//{clean_smell_name}"  # Double slash si pas de module
                    
                    smell_data = {
                        'version': version,
                        'file_path': file_path,
                        'type_of_smell': smell_name,
                        'id_smell': smell_id,
                        'severity': severity
                    }
                    
                    smells.append(smell_data)
                    
    except FileNotFoundError:
        print(f"Fichier non trouvé: {csv_file_path}")
    except Exception as e:
        print(f"Erreur lors de la lecture de {csv_file_path}: {e}")
    
    return smells

def collect_all_smells_data(versions_directory):
    """
    Collecte toutes les données de smells de toutes les versions.
    
    Args:
        versions_directory (str): Chemin vers le dossier contenant les versions
    
    Returns:
        tuple: (all_smells, version_smells_map, sorted_versions)
    """
    all_smells = []
    version_smells_map = defaultdict(set)  # version -> set of smell_ids
    versions_dir = Path(versions_directory)
    
    if not versions_dir.exists():
        print(f"Le dossier {versions_dir} n'existe pas!")
        return [], {}, []
    
    # Collecter toutes les versions et les trier
    version_folders = [f for f in versions_dir.iterdir() if f.is_dir() and f.name.startswith('v')]
    sorted_versions = sorted(version_folders, key=lambda x: x.name)
    
    # Parcourir toutes les versions SAUF la dernière
    versions_to_process = sorted_versions[:-1] if len(sorted_versions) > 1 else sorted_versions
    
    for version_folder in versions_to_process:
        version_name = version_folder.name
        csv_file = version_folder / "code_quality_report.csv"
        
        if csv_file.exists():
            print(f"Collecte des données pour la version {version_name}...")
            
            # Extraire les smells de cette version
            version_smells = extract_smells_from_csv(csv_file, version_name)
            all_smells.extend(version_smells)
            
            # Enregistrer les IDs des smells pour cette version
            for smell in version_smells:
                version_smells_map[version_name].add(smell['id_smell'])
            
            print(f"  - {len(version_smells)} smells détectés")
        else:
            print(f"Aucun fichier code_quality_report.csv trouvé pour {version_name}")
    
    return all_smells, version_smells_map, [v.name for v in sorted_versions]

def remove_duplicate_smell_ids_within_version(all_smells):
    """
    Enlève les doublons basés sur (version, smell_id), en gardant la première occurrence.
    Les mêmes smell_id peuvent exister dans différentes versions.
    
    Args:
        all_smells (list): Liste de tous les smells
        
    Returns:
        list: Liste des smells sans doublons au sein de chaque version
    """
    seen_version_smell_ids = set()
    unique_smells = []
    duplicates_count = 0
    
    for smell in all_smells:
        # Créer une clé unique (version, smell_id)
        version_smell_key = (smell['version'], smell['id_smell'])
        
        if version_smell_key not in seen_version_smell_ids:
            seen_version_smell_ids.add(version_smell_key)
            unique_smells.append(smell)
        else:
            duplicates_count += 1
    
    print(f"🔄 Doublons supprimés (au sein de chaque version): {duplicates_count} smells dupliqués")
    print(f"📊 Smells uniques conservés: {len(unique_smells)}")
    
    return unique_smells

def calculate_version_counts_and_next_version_presence(all_smells, version_smells_map, sorted_versions):
    """
    Calcule le nombre de versions PRÉCÉDENTES où chaque smell apparaît et s'il est présent dans la version suivante.
    
    Args:
        all_smells (list): Liste de tous les smells
        version_smells_map (dict): Mapping version -> set of smell_ids
        sorted_versions (list): Liste des versions triées
        
    Returns:
        list: Liste enrichie des smells avec les nouvelles colonnes
    """
    # Créer un mapping version -> index pour faciliter les recherches
    version_index = {version: i for i, version in enumerate(sorted_versions)}
    
    # Enrichir chaque smell avec les nouvelles colonnes
    enriched_smells = []
    for smell in all_smells:
        current_version = smell['version']
        smell_id = smell['id_smell']
        
        # Compter dans combien de versions PRÉCÉDENTES ce smell apparaît
        current_index = version_index.get(current_version, -1)
        count_previous_versions = 0
        
        if current_index > 0:  # Il y a des versions précédentes
            for i in range(current_index):  # Parcourir toutes les versions précédentes
                previous_version = sorted_versions[i]
                if smell_id in version_smells_map.get(previous_version, set()):
                    count_previous_versions += 1
        
        # Vérifier si le smell est présent dans la version suivante
        present_in_next = False
        if current_index >= 0 and current_index < len(sorted_versions) - 1:
            next_version = sorted_versions[current_index + 1]
            present_in_next = smell_id in version_smells_map.get(next_version, set())
        
        # Créer l'enregistrement enrichi
        enriched_smell = smell.copy()
        enriched_smell['count_versions_appears'] = count_previous_versions
        enriched_smell['present_in_next_version'] = 1 if present_in_next else 0
        
        enriched_smells.append(enriched_smell)
    
    return enriched_smells

def generate_final_dataset(enriched_smells, output_file="final_dataset_ann_format.csv"):
    """
    Génère le dataset final dans le format recommandé.
    
    Args:
        enriched_smells (list): Liste des smells enrichis
        output_file (str): Nom du fichier de sortie
    """
    if not enriched_smells:
        print("Aucune donnée à écrire!")
        return
    
    # Définir les colonnes dans l'ordre demandé
    fieldnames = [
        'version',
        'file_path', 
        'smell_type',
        'smell_id',
        'severity',
        'version_count',
        'next_version_present'
    ]
    
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Écrire l'en-tête
            writer.writeheader()
            
            # Écrire les données de chaque smell
            for smell in enriched_smells:
                row = {
                    'version': smell['version'],
                    'file_path': smell['file_path'],
                    'smell_type': smell['type_of_smell'],
                    'smell_id': smell['id_smell'],
                    'severity': smell['severity'],
                    'version_count': smell['count_versions_appears'],
                    'next_version_present': smell['present_in_next_version']
                }
                writer.writerow(row)
        
        print(f"\n✅ Dataset final généré: {output_file}")
        print(f"📊 {len(enriched_smells)} enregistrements de smells")
        
        # Statistiques additionnelles
        versions = set(smell['version'] for smell in enriched_smells)
        smell_types = set(smell['type_of_smell'] for smell in enriched_smells)
        
        print(f"📈 Statistiques du dataset:")
        print(f"  - Versions analysées: {len(versions)}")
        print(f"  - Types de smells uniques: {len(smell_types)}")
        print(f"  - Smells présents dans la version suivante: {sum(1 for s in enriched_smells if s['present_in_next_version'])}")
        
    except Exception as e:
        print(f"❌ Erreur lors de la génération du dataset: {e}")

def main():
    """Fonction principale."""
    # Vérifier les arguments de ligne de commande
    if len(sys.argv) != 2:
        print("Usage: python script.py <dossier_versions>")
        print("Exemple: python script.py tensorflow")
        sys.exit(1)
    
    versions_directory = sys.argv[1]
    
    print("🚀 Génération du dataset final pour le modèle ANN")
    print("=" * 60)
    print(f"📁 Dossier de versions: {versions_directory}")
    
    # Étape 1: Collecter toutes les données de smells
    print("\n🔍 Étape 1: Collecte des données...")
    all_smells, version_smells_map, sorted_versions = collect_all_smells_data(versions_directory)
    
    if not all_smells:
        print("❌ Aucune donnée trouvée!")
        return
    
    # Étape 2: Supprimer les doublons au sein de chaque version
    print("\n🧹 Étape 2: Suppression des doublons au sein de chaque version...")
    all_smells = remove_duplicate_smell_ids_within_version(all_smells)
    
    # Étape 3: Calculer les comptes et la présence dans la version suivante
    print("\n📊 Étape 3: Calcul des métriques...")
    enriched_smells = calculate_version_counts_and_next_version_presence(
        all_smells, version_smells_map, sorted_versions
    )
    
    # Étape 4: Générer le dataset final
    print("\n💾 Étape 4: Génération du dataset final...")
    generate_final_dataset(enriched_smells)
    
    print("\n🎉 Processus terminé avec succès!")

if __name__ == "__main__":
    main() 