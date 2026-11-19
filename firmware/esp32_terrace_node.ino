#include <WiFi.h>
#include <HTTPClient.h>

const char* WIFI_SSID = "HillGateway_LoRaBridge";
const char* WIFI_PASS = "agri2026";
const char* SERVER_URL = "http://127.0.0.1:8000/api/telemetry";

const int SOIL_SENSOR_PIN = 34; // Capacitive soil moisture sensor (ADC1)
const int RELAY_VALVE_PIN = 26; // Solenoid drip valve relay
const int OFFLINE_MOISTURE_LIMIT = 30; // Fail-safe edge threshold (%)

int readSoilMoisture() {
  int raw = analogRead(SOIL_SENSOR_PIN);
  int pct = map(raw, 3100, 1200, 0, 100);
  return constrain(pct, 0, 100);
}

void controlValve(bool openValve) {
  digitalWrite(RELAY_VALVE_PIN, openValve ? HIGH : LOW);
  if (openValve) {
    delay(12000); // Safety-capped irrigation window
    digitalWrite(RELAY_VALVE_PIN, LOW);
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(RELAY_VALVE_PIN, OUTPUT);
  digitalWrite(RELAY_VALVE_PIN, LOW);

  int moisture = readSoilMoisture();
  bool edgeFallbackDecision = (moisture < OFFLINE_MOISTURE_LIMIT);

  WiFi.begin(WIFI_SSID, WIFI_PASS);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 15) {
    delay(400);
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "application/json");
    String json = "{\"zone_id\":\"Terrace-Upper-01\",\"elevation_tier\":3,\"slope_deg\":28.0,\"soil_moisture\":" + String(moisture) + "}";
    int code = http.POST(json);
    if (code == 200) {
      String response = http.getString();
      controlValve(response.indexOf("\"irrigate\":true") != -1);
    } else {
      controlValve(edgeFallbackDecision); // Offline edge resilience
    }
    http.end();
  } else {
    controlValve(edgeFallbackDecision); // Offline edge resilience
  }

  esp_sleep_enable_timer_wakeup(900ULL * 1000000ULL); // 15-min solar deep sleep
  esp_deep_sleep_start();
}

void loop() {}