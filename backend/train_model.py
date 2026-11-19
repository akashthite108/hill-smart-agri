import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# Generate realistic hilly-terrain terrace telemetry dataset (2,000 samples)
np.random.seed(42)
n = 2000

soil_moisture = np.random.uniform(10, 65, n)       # % volumetric moisture
soil_temp = np.random.uniform(14, 34, n)           # Celsius
humidity = np.random.uniform(35, 95, n)            # %
rain_forecast_mm = np.random.exponential(4.0, n)   # Next 12h rain forecast (mm)
slope_deg = np.random.uniform(5, 40, n)            # Terrace slope angle (degrees)
elevation_tier = np.random.choice([1, 2, 3], n)    # 1=Lower, 2=Middle, 3=Upper terrace

# Domain-grounded irrigation decision logic for sloped farms:
# Upper terraces & steeper slopes drain faster, needing water sooner,
# BUT if rain_forecast > 5mm, skip irrigation to prevent topsoil runoff & erosion.
effective_threshold = 28.0 + (slope_deg * 0.18) + (elevation_tier * 1.5)
irrigate = (
    (soil_moisture < effective_threshold) & (rain_forecast_mm < 5.0)
).astype(int)

df = pd.DataFrame({
    "soil_moisture": soil_moisture,
    "soil_temp": soil_temp,
    "humidity": humidity,
    "rain_forecast_mm": rain_forecast_mm,
    "slope_deg": slope_deg,
    "elevation_tier": elevation_tier,
    "irrigate": irrigate,
})

X = df.drop(columns=["irrigate"])
y = df["irrigate"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
model.fit(X_train, y_train)

acc = accuracy_score(y_test, model.predict(X_test))
print(f"Model trained successfully! Validation Accuracy: {acc * 100:.2f}%")

joblib.dump(model, "backend/irrigation_model.pkl")
df.to_csv("backend/hill_telemetry_dataset.csv", index=False)
print("Saved backend/irrigation_model.pkl and backend/hill_telemetry_dataset.csv")