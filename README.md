# Linux Log Summarizer & AI Assistant

An intelligent, full-stack log analysis framework that transforms raw Linux logs into human-readable executive reports. This tool leverages **Drain3** for template mining, **Ollama (Llama 3.1)** for semantic understanding, and **JustPy** for an interactive web dashboard.

<img width="1920" height="1080" alt="Data Ingestion   Preprocessing (1)" src="https://github.com/user-attachments/assets/c46286ff-8118-4641-8a79-093681bb3d55" />


## 🚀 Key Features

* **🧹 Automated Log Parsing:** Uses the Drain3 algorithm to cluster millions of log lines into manageable templates.
* **🤖 AI-Powered Analysis:** Integrates with local LLMs (via Ollama) to interpret cryptic log messages into plain English.
* **📊 Interactive Dashboard:** A web-based GUI to upload logs, view real-time parsing, and generate visual analytics.
* **🛡️ Security Audit:** Automatically detects potential threats (SSH failures, sudo abuse) and visualizes them.
* **💬 AI Chat Interface:** "Chat with your logs" to ask specific questions about the system's status.

---

## 🛠️ Prerequisites

Before running the application, ensure you have the following installed:

1.  **Python 3.10+**
2.  **Ollama**: This tool relies on a local LLM server.
    * Download from [ollama.com](https://ollama.com).
    * **Crucial Step:** You must pull the specific model used in the code:
        ```bash
        ollama pull llama3.1:8b
        ```
    * *Note: Ensure the Ollama service is running in the background (`ollama serve`).*

---

## 📦 Installation

1.  **Clone the Repository**

2.  **Install Python Dependencies**
    Install the required libraries (JustPy, Drain3, Ollama, Pandas, etc.):
    ```bash
    pip install pandas justpy drain3 ollama matplotlib python-dateutil markdown
    ```

---

## 🖥️ How to Use

### 1. Start the Application
Run the main pipeline script to start the web server:
```bash
python pipeline.py
```
### 2. Access the Dashboard
Open your web browser and navigate to:
> **http://127.0.0.1:8000**

### 3. Workflow
You can upload your own files or use the sample logs provided in the **`Logs/`** folder.

> **Note:** This architecture is **fine-tuned for standard Linux system logs** (e.g., `syslog`, `messages`, `kern.log`). For best results, use logs that match this format.

1.  **Cleaning:** The raw log data is pre-processed to remove specific noise (like repetitive kernel boot messages) based on the active blacklist.
2.  **Parsing:** The **Drain3** algorithm scans the cleaned logs and clusters them into structural templates to identify patterns.
3.  **Template Meaning Generation:** The local LLM (**Ollama**) analyzes the unique templates to generate human-readable semantic meanings.
4.  **Analytics & Reporting:** The system calculates statistics and generates visualizations (e.g., SSH brute-force attempts, process frequency graphs).
5.  **Summary & AI Chat:** A final Executive Summary is compiled, and the **AI Chat Assistant** is enabled, allowing you to ask specific questions about the log events.

---

## 📂 Project Structure

* **`pipeline.py`**: The main entry point. Orchestrates the UI (JustPy) and calls backend services.
* **`code/`**: Core logic modules.
    * **`ai_assistant.py`**: Manages the "Chat with Log" functionality using the LLM.
    * **`cleaner.py`**: Pre-processes raw logs to remove noise (blacklisting) before parsing.
    * **`fail2ban_logic.py`**: Detects security threats like SSH brute-force attacks and sudo abuse.
    * **`graph_generator.py`**: Uses Matplotlib to generate visual analytics (pie charts, bar graphs).
    * **`image_handler.py`**: Helper functions to manage and display images within the reports.
    * **`llama_meaning_generator.py`**: Connects to the local Ollama instance to interpret log templates.
    * **`markdown_handler.py`**: Formats the analysis results into a clean Markdown structure.
    * **`parser.py`**: Implements the Drain3 algorithm to cluster logs into templates.
    * **`report_engine.py`**: The central engine that coordinates parsing, analysis, and report compilation.
    * **`session_logic.py`**: Manages user session data to handle multiple uploads or states.
    * **`static_report.py`**: Handles the generation of the static Executive Summary for the UI.
* **`Logs/`**: Default folder for storing sample logs.
---

## ⚠️ Troubleshooting
* **"Ollama connection refused"**: Ensure Ollama is running (`ollama serve`) and you have pulled the model `llama3.1:8b`.
* **"No GPU found"**: The AI analysis will run on CPU if no NVIDIA GPU is detected, but it will be significantly slower.
* **"Port 8000 in use"**: JustPy defaults to port 8000. Ensure no other service is using this port.

---

## 📜 License
This project is licensed under the MIT License - see the `LICENSE` file for details.
