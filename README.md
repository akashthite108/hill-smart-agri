Smart Agriculture for Efficient Cultivation in Hilly Regions



An Edge-to-Cloud IoT, Machine Learning, and Data Analytics system engineered for sloped and terraced farms where water scarcity, soil runoff, and intermittent connectivity challenge traditional farming.



 Key Features

Edge-Resilient ESP32 Sensor Nodes:Deep-sleep solar nodes with offline fail-safe valve control.

Slope \& Weather-Aware ML Engine: Random Forest classifier accounting for terrace elevation tier, slope angle, soil moisture, and rainfall forecast to prevent topsoil erosion.

Live Telemetry \& Advisory Dashboard: Real-time water savings tracker, multi-terrace simulator, and leaf disease screening API.



Quick Start

1.pip install fastapi uvicorn scikit-learn pandas numpy joblib`

2.python backend/train\_model.py`

3.uvicorn backend.app:app --reload`

4.Open `http://127.0.0.1:8000`

