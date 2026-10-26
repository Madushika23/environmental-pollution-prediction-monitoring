#include <WiFi.h>
#include <HTTPClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// =====================================================
// PIN CONFIGURATION
// =====================================================

#define ONE_WIRE_BUS 4     // DS18B20
#define TDS_PIN 34         // TDS / conductivity analog output
#define PH_PIN 35          // PH-4502C analog output

// =====================================================
// WIFI CONFIGURATION
// =====================================================

const char* WIFI_SSID = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Your computer's Wi-Fi IPv4 address
const char* SERVER_URL = "YOUR_FLASK_BACKEND_URL/api/water/live-peek";
// =====================================================
// DS18B20
// =====================================================

OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

// =====================================================
// ADC CONFIGURATION
// =====================================================

const float ADC_MAX = 4095.0;
const float ADC_VOLTAGE = 3.3;

// =====================================================
// PH CALIBRATION
//
// Your measured buffer values:
//
// pH 4  = 2180 mV
// pH 7  = 2049 mV
// pH 10 = 1914 mV
// =====================================================

const float PH4_VOLTAGE  = 2.180;
const float PH7_VOLTAGE  = 2.049;
const float PH10_VOLTAGE = 1.914;


// =====================================================
// FUNCTION: Convert voltage to calibrated pH
// =====================================================

float calculatePH(float voltage)
{
  float pH;

  // Region 1: pH 4 to pH 7
  if (voltage >= PH7_VOLTAGE)
  {
    pH = 7.0 +
         (voltage - PH7_VOLTAGE) *
         (4.0 - 7.0) /
         (PH4_VOLTAGE - PH7_VOLTAGE);
  }

  // Region 2: pH 7 to pH 10
  else
  {
    pH = 7.0 +
         (voltage - PH7_VOLTAGE) *
         (10.0 - 7.0) /
         (PH10_VOLTAGE - PH7_VOLTAGE);
  }

  return pH;
}


// =====================================================
// FUNCTION: Read pH
// =====================================================

float readPH()
{
  const int samples = 20;

  long totalADC = 0;

  for (int i = 0; i < samples; i++)
  {
    totalADC += analogRead(PH_PIN);
    delay(10);
  }

  float averageADC = totalADC / (float)samples;

  float voltage = (averageADC / ADC_MAX) * ADC_VOLTAGE;

  float pH = calculatePH(voltage);

  return pH;
}


// =====================================================
// FUNCTION: Read pH ADC
// =====================================================

int readPHADC()
{
  const int samples = 20;

  long totalADC = 0;

  for (int i = 0; i < samples; i++)
  {
    totalADC += analogRead(PH_PIN);
    delay(10);
  }

  return totalADC / samples;
}


// =====================================================
// FUNCTION: Read TDS / Conductivity ADC
// =====================================================

int readTDSADC()
{
  const int samples = 20;

  long totalADC = 0;

  for (int i = 0; i < samples; i++)
  {
    totalADC += analogRead(TDS_PIN);
    delay(10);
  }

  return totalADC / samples;
}


// =====================================================
// FUNCTION: Convert TDS ADC to voltage
// =====================================================

float readTDSVoltage(int adcValue)
{
  return (adcValue / ADC_MAX) * ADC_VOLTAGE;
}


// =====================================================
// FUNCTION: Calculate conductivity
//
// TEMPORARY calibration based on your previous output:
//
// ADC 173 -> Conductivity 104.60 uS/cm
//
// Therefore:
//
// 104.60 / 173 = 0.6046
//
// We can replace this with your actual conductivity
// calibration once you give me the calibration values.
// =====================================================

float calculateConductivity(int adcValue)
{
  float conductivity = adcValue * 0.6046;

  return conductivity;
}


// =====================================================
// FUNCTION: Connect WiFi
// =====================================================

void connectWiFi()
{
  Serial.println();
  Serial.println("Connecting to WiFi...");

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;

  while (WiFi.status() != WL_CONNECTED && attempts < 30)
  {
    delay(500);
    Serial.print(".");

    attempts++;
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED)
  {
    Serial.println("----------------------------------------");
    Serial.println("WiFi connected!");
    Serial.print("ESP32 IP address: ");
    Serial.println(WiFi.localIP());

    Serial.print("Gateway: ");
    Serial.println(WiFi.gatewayIP());

    Serial.print("Signal strength: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");

    Serial.println("----------------------------------------");
  }
  else
  {
    Serial.println("ERROR: WiFi connection failed!");
  }
}


// =====================================================
// FUNCTION: Send data to Flask backend
// =====================================================

void sendDataToBackend(
  float temperature,
  int tdsADC,
  float tdsVoltage,
  float conductivity,
  int phADC,
  float phVoltage,
  float pH
)
{
  if (WiFi.status() != WL_CONNECTED)
  {
    Serial.println("WiFi is not connected.");
    return;
  }

  Serial.println();
  Serial.println("Sending data to backend...");

  HTTPClient http;

  // Start HTTP connection
  http.begin(SERVER_URL);

  // Tell Flask that we are sending JSON
  http.addHeader("Content-Type", "application/json");

  // Create JSON data
  String jsonData = "{";

  jsonData += "\"temperature\":";
  jsonData += String(temperature, 2);

  jsonData += ",\"tds_adc\":";
  jsonData += String(tdsADC);

  jsonData += ",\"tds_voltage\":";
  jsonData += String(tdsVoltage, 3);

  jsonData += ",\"conductivity\":";
  jsonData += String(conductivity, 2);

  jsonData += ",\"ph_adc\":";
  jsonData += String(phADC);

  jsonData += ",\"ph_voltage\":";
  jsonData += String(phVoltage, 3);

  jsonData += ",\"ph\":";
  jsonData += String(pH, 2);

  jsonData += "}";

  Serial.println("JSON:");
  Serial.println(jsonData);

  // Send POST request
  int httpResponseCode = http.POST(jsonData);

  Serial.print("HTTP Response: ");
  Serial.println(httpResponseCode);

  if (httpResponseCode > 0)
  {
    String response = http.getString();

    Serial.println("Backend response:");
    Serial.println(response);
  }
  else
  {
    Serial.print("HTTP request failed: ");
    Serial.println(http.errorToString(httpResponseCode));
  }

  http.end();

  Serial.println("----------------------------------------");
}


// =====================================================
// SETUP
// =====================================================

void setup()
{
  Serial.begin(115200);

  delay(1000);

  Serial.println();
  Serial.println("=====================================================");
  Serial.println("ESP32 WATER QUALITY MONITOR");
  Serial.println("=====================================================");

  // ADC configuration
  analogReadResolution(12);

  // Start DS18B20
  sensors.begin();

  Serial.println("DS18B20 initialized.");

  // Connect WiFi
  connectWiFi();

  Serial.println("System ready.");
}


// =====================================================
// LOOP
// =====================================================

void loop()
{
  Serial.println();
  Serial.println("Reading sensors...");
  Serial.println();

  // ===================================================
  // TEMPERATURE
  // ===================================================

  sensors.requestTemperatures();

  float temperature = sensors.getTempCByIndex(0);

  Serial.println("----------------------------------------");

  if (temperature == DEVICE_DISCONNECTED_C)
  {
    Serial.println("Temperature: SENSOR ERROR");
    temperature = 25.0;
  }
  else
  {
    Serial.print("Temperature: ");
    Serial.print(temperature, 2);
    Serial.println(" °C");
  }


  // ===================================================
  // TDS / CONDUCTIVITY
  // ===================================================

  int tdsADC = readTDSADC();

  float tdsVoltage = readTDSVoltage(tdsADC);

  float conductivity = calculateConductivity(tdsADC);

  Serial.print("TDS ADC: ");
  Serial.println(tdsADC);

  Serial.print("TDS Voltage: ");
  Serial.print(tdsVoltage, 3);
  Serial.println(" V");

  Serial.print("Conductivity: ");
  Serial.print(conductivity, 2);
  Serial.println(" µS/cm");


  // ===================================================
  // PH
  // ===================================================

  int phADC = readPHADC();

  float phVoltage =
    (phADC / ADC_MAX) * ADC_VOLTAGE;

  float pH = calculatePH(phVoltage);

  Serial.print("pH ADC: ");
  Serial.println(phADC);

  Serial.print("pH Voltage: ");
  Serial.print(phVoltage, 3);
  Serial.println(" V");

  Serial.print("pH: ");
  Serial.println(pH, 2);

  Serial.println("----------------------------------------");


  // ===================================================
  // SEND TO BACKEND
  // ===================================================

  sendDataToBackend(
    temperature,
    tdsADC,
    tdsVoltage,
    conductivity,
    phADC,
    phVoltage,
    pH
  );


  // ===================================================
  // WAIT 10 SECONDS
  // ===================================================

  Serial.println("Waiting 10 seconds...");
  delay(10000);
}