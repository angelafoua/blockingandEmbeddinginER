# 🔗 BlockingMainlyER

This repository contains a **blocking-focused Entity Resolution (ER) system** designed to process PII data and group duplicate records efficiently.

---

## 📌 Overview

This project implements a **PII Entity Resolution Pipeline** that:

* Extracts structured data from raw records
* Normalizes inconsistent values
* Generates blocking keys
* Performs recursive blocking
* Produces candidate record pairs
* Matches records
* Clusters duplicates into unified entities

---

## ⚙️ Pipeline Steps

1. Extract PII using Ollama
2. Normalize fields
3. Generate blocking keys
4. Recursive blocking
5. Candidate pair generation
6. Record matching
7. Clustering (Union-Find)
8. Output cluster IDs

---

## 🚀 How to Run

Run the pipeline:

```
pip install -r requirements.txt
```

```
python main.py
```

Input file:

```
data/input/records.csv
```

Output file:

```
data/output/clusters.csv
```

---

## 📂 Project Structure

```
entity-resolution-pipeline/
├── data/
│   ├── input/
│   │   └── records.csv
│   └── output/
│       └── clusters.csv
│
├── src/
│   ├── main.py
│   ├── pii_extraction.py
│   ├── normalization.py
│   ├── blocking.py
│   ├── hashing.py
│   ├── matching.py
│   ├── clustering.py
│   └── utils.py
│
├── config/
│   └── config.yaml
│
├── requirements.txt
├── README.md
└── .gitignore
```

---

## 📈 Output Example

```
record_id,cluster_id
rec1,0
rec2,0
rec3,1
```

Records with the same cluster_id belong to the same entity.

---

## 🔧 Requirements

Install dependencies:

```
pip install -r requirements.txt
```
