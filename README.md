# Lendmark - Intelligent Loan Decisioning System

Lendmark is a modern, lightweight, and high-performance financial dashboard application. It provides an intelligent loan prediction engine built for speed, simplicity, and premium user experience.

## 🚀 Quick Start

Lendmark uses a simple Python backend and a vanilla HTML/JS frontend.

### 1. Requirements
Ensure you have **Python 3.10+** installed on your system.

### 2. Setup (Run once)
Install the minimal dependencies required for the backend:
```bash
pip3 install flask flask-cors
```

### 3. Start the Application
Run the included start script to launch the local API server:
```bash
./start-server.sh
```
The server will start at `http://localhost:5001`.

### 4. Access the Dashboard
**IMPORTANT:** Do not open the HTML files directly (via double-click or `file://`). 

Instead, visit the application at:
👉 **[http://localhost:5001](http://localhost:5001)**

---

## 🔑 Default Credentials
- **Manager Account:** `harixx@gmail.com`
- **Password:** `harixx`

---

## 🛠 Tech Stack
- **Frontend:** Vanilla HTML5, JavaScript (ES6+), CSS3 (Tailwind v4 via CDN)
- **Backend:** Python + Flask (RESTful Architecture)
- **Database:** SQLite (Embedded, zero-config)
- **Aesthetics:** Lucide Icons, Modern Typography (Outfit, Inter)

## 🏗 Key Features
- **Intelligent Prediction Engine:** Proprietary machine learning logic handles risk assessment based on CIBIL, Assets, and Income ratios.
- **Dynamic Role Management:** Unified codebase for both Managers and Customers with adaptive UI components.
- **Real-time Ledger:** Full transaction history with instant balance synchronization and overdraft protection.
- **Micro-Animations:** Fluid transitions and premium feedback loops for an elite user experience.
- **Dark Mode:** System-aware native dark mode support.
