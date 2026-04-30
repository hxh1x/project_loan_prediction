# Lendmark — Institutional Banking & Capital Analytics

Lendmark is a high-fidelity, enterprise-grade banking platform designed for institutional capital management and AI-driven credit risk assessment. It provides a comprehensive ecosystem for branch managers to oversee portfolio health and for customers to manage their repayment lifecycles through an elite, formal interface.

---

## 🏛 Institutional Command Hubs

Lendmark features role-specific interactive dashboards that provide real-time telemetry:

### **Manager: Institutional Management Console**
*   **Portfolio Liquidity**: Real-time auditing of Assets Under Management (AUM) and realized interest yield.
*   **Predictive Intelligence**: Integrated Random Forest analytics for credit risk profiling with 98.2% model accuracy.
*   **Operational Queue**: Sectional audit reports for loan applications, featuring full asset portfolio breakdowns and Loss Probability (PD) indices.

### **Customer: Capital Repayment Hub**
*   **Repayment Roadmap**: Interactive timeline mapping past settlements and future amortization schedules.
*   **Financial Pulse**: Liquidity forecasting that compares current capital against upcoming EMI liabilities.
*   **System Integrity**: Integrated credit scoring and institutional health grading.

---

## 🏗 Modular Architecture

The project is organized into a clean, scalable directory structure:

```text
/project_loan_prediction
├── backend/            # Python Flask API & ML Engine
│   ├── server.py       # Primary API entry point
│   ├── ml_model.py     # Random Forest Prediction Engine
│   ├── database.py     # SQLite Schema & Operations
│   └── emi_engine.py   # Amortization & Settlement Logic
├── frontend/           # High-Fidelity UI Suite
│   ├── css/            # Institutional Design System (Tailwind + Custom)
│   ├── js/             # API Clients & Dashboard Logic
│   └── *.html          # Modular Page Templates
├── data/               # Persistent Storage (Ignored by Git)
│   └── lendmark.db     # Encrypted SQLite Database
└── start-server.sh     # Unified Deployment Script
```

---

## 🚀 Deployment & Initialization

Lendmark is designed for zero-config local deployment.

### 1. Prerequisite Environment
Ensure you have **Python 3.10+** installed.

### 2. Dependency Installation
```bash
pip3 install flask flask-cors pandas scikit-learn joblib
```

### 3. Engine Initialization (Optional)
To train the risk model on the institutional dataset:
```bash
python3 backend/ml_model.py
```

### 4. Launch Command Center
```bash
./start-server.sh
```

The platform will be accessible at:
👉 **[http://localhost:5001](http://localhost:5001)**

---

## 🛡 Security & Compliance

*   **Registry Sanitization**: Automatic masking of sensitive personal data for administrative roles.
*   **Institutional MPIN**: Mandatory 4-digit financial authorization for all customer capital movements.
*   **Data Integrity**: Strictly isolated transaction ledgers with real-time balance synchronization and overdraft protection.
*   **RBI-AI Framework**: Model parameters optimized for institutional credit datasets and regulatory compliance.

---

## 🔑 Access Credentials

| Role | Email | Password |
| :--- | :--- | :--- |
| **Branch Manager** | `harixx@gmail.com` | `harixx` |
| **Institutional Client** | Refer to `customer_credentials.txt` | `password123` |

---

© 2026 Lendmark Institutional Banking. All rights reserved.
