# ONSINT Core 🛰️

[![Deploy to Render](https://render.com/images/deploy-to-render.svg)](https://render.com/deploy?repo=https://github.com/RonitGupta007/onsint-core)

**ONSINT Core** is a general-purpose, self-hosted open-source intelligence (OSINT) suite designed for security analysts, penetration testers, and digital researchers. It provides a visual dashboard for target profiling, stealth network lookups, and connection-graph visualizers.

Made with 💜 by **Ronit Gupta**.

---

## 🌟 Key Features

*   **Modular Target Profiling**: Run automated lookups for domain WHOIS records, IP geolocation, DNS record lookups, and username checkers.
*   **Stealth Proxy Cycling**: Scrape and rotate free proxy IP addresses to mask scanning origins.
*   **Interactive Connection Mapping**: Instantly maps target nodes, platforms, servers, and geotags on a dynamic 2D graph powered by **Vis.js**.
*   **Case File Registry**: Store, retrieve, and catalog findings inside an SQLite vault without losing historical audits.
*   **Modern Web UI**: A glassmorphic dark-themed front end with outfit typography, dynamic animations, and a **resizable sidebar** (drag-to-resize with neon indicator lines).
*   **Streamlit Reporting Panel**: Includes a secondary, clean Streamlit reporting dashboard (`app.py`) for tabular data viewing and case audit management.
*   **Dockerized & Cloud-Ready**: Fully containerized with persistent storage configuration for serverless deployment on Render, Railway, or VPS nodes.

---

## 📁 Project Structure

```text
ONSINT/
├── backend/
│   ├── database.py    # Database connection & case CRUD operations
│   ├── osint.py       # Query scripts (WHOIS, GeoIP, proxy scraping, username lists)
│   └── main.py        # FastAPI endpoints & static files server
├── frontend/
│   └── static/
│       ├── index.html # Main dashboard structure
│       ├── style.css  # Dark-theme layout stylesheet & resizer handle styling
│       └── app.js     # Ajax request handlers, Vis.js graph configs, and resizer drag bindings
├── app.py             # Streamlit secondary reporting interface
├── Dockerfile         # Docker container configuration
├── requirements.txt   # Python dependency list
└── README.md          # Project documentation
```

---

## 🚀 How to Run Locally

### Prerequisites
*   Python 3.10 or higher
*   pip (Python package manager)

### 1. Clone & Install Dependencies
Navigate to your project root folder and run:
```bash
pip install -r requirements.txt
```

### 2. Launch FastAPI Dashboard (Main App)
To start the FastAPI web interface, run:
```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
```
Open **[http://127.0.0.1:8001](http://127.0.0.1:8001)** in your web browser.

### 3. Launch Streamlit Reporting Panel (Optional)
To run the Streamlit interface alongside the main app:
```bash
streamlit run app.py
```
Open **[http://localhost:8501](http://localhost:8501)** in your web browser.

---

## 🐳 Docker Deployment

To run ONSINT Core inside a container:

1.  **Build the Docker Image**:
    ```bash
    docker build -t onsint-core .
    ```
2.  **Run with Persistent Database**:
    ```bash
    docker run -p 8000:8000 -v onsint-data:/app/data -e DATABASE_PATH=/app/data/ig_int_vault.db onsint-core
    ```
    *This maps database files to a persistent volume `/app/data` to ensure you never lose case histories when container tasks restart.*

---

## 🛡️ License & Ethical Use
This tool is built for ethical research, vulnerability assessments, and cybersecurity auditing. Please ensure compliance with local laws, GDPR, and target platform terms of service.
