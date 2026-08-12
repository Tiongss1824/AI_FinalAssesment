# BTIS3043 eBook Predicate + Fuzzy Query System

## Files
- `ebook_ai_system.py` — data loading, keyword vocab, fuzzy membership functions, aggregation
- `predicates.py` — dataset-specific predicate (crisp) classification functions for both scenarios
- `run_scenarios.py` — runs the full pipeline for both fixed scenarios across all 3 datasets, prints results, saves CSVs
- three excel files provided in Teams

## Setup (Windows)
1. Download three excel files and three python files in this repo, put into a new folder, open the folder in vscode
2. Use Ctrl + ` to open terminal in vscode to create virtual environment (Optional: 2, 3, 4)
3. Type `python -m venv venv`
4. Type `venv\Scripts\activate` to finish set up virtual environment
5. Type `pip install pandas numpy openpyxl`
6. Type `cd code_package`
7. Type `python run_scenarios.py`
8. 12 results should now appear
