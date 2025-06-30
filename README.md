# Architectural Smell Prediction Research Project

## 📖 Overview

This research project develops a comprehensive platform for code quality analysis and prediction of **architectural smell** evolution in Python open source projects. It combines multiple technological approaches: traditional static analysis, machine learning (LSTM), and generative artificial intelligence (LLM).

## 🏗️ Project Architecture

The project is organized into four main modules:

### 1. 🔍 **PyExamine** - Code Quality Analysis Tool
In-house developed code smell detector capable of identifying:
- **Code Smells**: Long Methods, Large Classes, Feature Envy, etc.
- **Architectural Smells**: Cyclic Dependencies, God Objects, Hub-like Dependencies
- **Structural Smells**: High Complexity, Deep Inheritance, High Coupling

### 2. 🤖 **AI Models** - Prediction Models
Machine learning models to predict smell evolution:
- **Multi-head LSTM**: Simultaneous prediction of multiple smell types
- **Loop LSTM**: Iterative model for temporal analysis

### 3. 🚀 **Data Pipeline** - Data Collection and Processing
Automated scripts for:
- GitHub project cloning and analysis
- Training dataset generation
- ML preprocessing

### 4. 🧠 **LLM Agent** - Advanced Architectural Analysis
Agent using Large Language Models for:
- Complex architectural analysis
- Advanced pattern detection
- Refactoring recommendations

## 🚀 Installation

### Prerequisites
- Python 3.7+
- Java Runtime Environment (for Depends tool)
- Git

### Dependencies Installation
```bash
# Install main dependencies
pip install -r requirements.txt

# Install PyExamine
cd pyexamine
pip install -e .
cd ..
```

### Configuration
1. Place the `depends.jar` file in the `LLM/` folder
2. Create a `.env` file for API keys (optional for LLM)
```bash
XAI_API_KEY=your_api_key_here
```

## 📊 Usage

### 1. Code Quality Analysis with PyExamine

```bash
# Complete project analysis
analyze_code_quality /path/to/project --config code_quality_config.yaml

# Specific analysis by type
analyze_code_quality /path/to/project --type structural
analyze_code_quality /path/to/project --type architectural
```

### 2. Data Collection from GitHub

```bash
# Automatic cloning and analysis of a GitHub project
python AI/Script/clone_and_clean_releases.py https://github.com/owner/repo.git
```

### 3. Dataset Generation

```bash
# Dataset for classification/regression models
python AI/Script/generate_final_dataset-count.py /path/to/analyzed/project

# Dataset for neural networks
python AI/Script/generate_ann_dataset.py /path/to/analyzed/project
```

### 4. LSTM Model Training

```bash
# Multi-head LSTM Model
cd AI/Model/multi-head-LSTM-model
Run the Jupyter notebook or Python file

# Loop LSTM Model
cd AI/Model/loop-LSTM-model
Run the Jupyter notebook or Python file
```

### 5. Analysis with LLM Agent

```bash
cd LLM
python agent.py https://github.com/owner/repo.git
```

## 📁 Data Structure

### Generated Datasets
```
AI/Dataset/
├── training-testing-set/           # Classic ML datasets
│   └── {project_name}/
│       ├── {project}_Dataset.csv
│       ├── {project}_Training_Set.csv
│       └── {project}_Test_Set.csv
├── training-testing-set-count-files/   # Datasets with file metadata
└── ANN-Dataset/                    # Neural network datasets
    └── {project_name}/
        ├── {project}_Dataset.csv
        └── {project}_LastVersion.csv
```

## 🔬 Detailed Features

### PyExamine - Smell Detection

#### Detected Code Smells
- **Long Method**: Methods too long (> 45 lines)
- **Large Class**: Classes with too many methods (> 15)
- **Feature Envy**: Methods excessively using other classes
- **Data Clumps**: Repeated parameter groups
- **Primitive Obsession**: Excessive use of primitive types

#### Architectural Smells
- **Cyclic Dependency**: Circular dependencies between modules
- **God Object**: Classes with too many responsibilities
- **Hub-like Dependency**: Over-centralized components
- **Unstable Dependency**: Dependencies on unstable components

#### Structural Smells
- **High Cyclomatic Complexity**: Complexity > 10
- **Deep Inheritance**: Hierarchy > 6 levels
- **High Coupling (CBO)**: High coupling between objects
- **Low Cohesion (LCOM)**: Low method cohesion

### Machine Learning Models

#### Multi-head LSTM
- Simultaneous prediction of 15+ smell types
- Architecture with separate heads per smell type
- Optimization with Early Stopping and Learning Rate Reduction

#### Data Pipeline
- Normalization with MinMaxScaler
- Configurable temporal windows
- Integrated cross-validation

### LLM Agent - Advanced Analysis
- Complex architectural pattern detection
- Cyclic dependency analysis
- Contextual refactoring recommendations
- Multiple LLM provider support

## 📈 Metrics and Evaluation

### Code Quality Metrics
- **Cyclomatic Complexity**: Execution path complexity
- **Lines of Code (LOC)**: File/method size
- **Coupling Between Objects (CBO)**: Inter-class coupling
- **Lack of Cohesion of Methods (LCOM)**: Intra-class cohesion

## 📊 Analyzed Projects

The dataset includes analysis of several popular Python projects:
- **bunkerweb** - Secure web proxy
- **celery** - Distributed task queue
- **homeassistant-powercalc** - Energy consumption calculations
- **jumpserver** - Bastion platform
- **locust** - Load testing tool
- **openai-python** - OpenAI SDK
- **optuna** - Hyperparameter optimization
- **python-telegram-bot** - Telegram bot
- **qlib** - Quantitative finance platform
- **streamlit** - Web application framework
- **supervision** - Computer vision
- **transformers** - NLP models
- **yt-dlp** - YouTube downloader

## 🔗 References

- A Study on Architectural Smells Prediction (University of Groningen) - https://pure.rug.nl/ws/portalfiles/portal/202232042/

## 🆘 Support

For bugs and feature requests, please use the GitHub issue system.

---
**Note**: This project is developed in an academic research context on software quality and code smell evolution in open source projects.