#include <WiFi.h>
#include <HTTPClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// =====================================================
// WIFI
// =====================================================

const char* WIFI_SSID = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Your laptop running Flask
const char* SERVER_URL =
  "YOUR_FLASK_BACKEND_URL/api/water/live-peek";

// =====================================================
// SENSOR PINS
// =====================================================

// DS18B20
#define ONE_WIRE_BUS 4

// TDS sensor
// You said TDS is connected to GPIO 34
#define TDS_PIN 34

// pH sensor
// You said pH is connected to GPIO 35
#define PH_PIN 35


// =====================================================
// DS18B20 SETUP
// =====================================================

OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);


// =====================================================
// TDS SETTINGS
// =====================================================

// ESP32 ADC
const float ADC_VREF = 3.3;
const int ADC_RESOLUTION = 4095;

// TDS conversion used in your previous testing
const float TDS_CONVERSION_FACTOR = 0.5;


// =====================================================
// pH CALIBRATION
// =====================================================

// These are based on the calibration readings you obtained.
//
// pH 7:
// Voltage ≈ 2.431 V
//
// pH 10:
// Voltage ≈ 2.028 V
//
// We use these two points to calculate the linear
// pH relationship.
//
// slope = (10 - 7) / (2.028 - 2.431)
//       ≈ -7.444
//
// intercept ≈ 24.99

const float PH7_VOLTAGE = 2.431;
const float PH7_VALUE = 7.0;

const float PH10_VOLTAGE = 2.028;
const float PH10_VALUE = 10.0;


// =====================================================
// TIMING
// =====================================================

unsigned long lastSendTime = 0;

// Send approximately every 10 seconds
const unsigned long SEND_INTERVAL = 10000;


// =====================================================
// CALCULATE pH
// =====================================================

float calculatePH(float voltage)
{
  float slope =
    (PH10_VALUE - PH7_VALUE) /
    (PH10_VOLTAGE - PH7_VOLTAGE);

  float intercept =
    PH7_VALUE - (slope * PH7_VOLTAGE);

  float ph =
    (slope * voltage) + intercept;

  return ph;
}


// =====================================================
// READ AVERAGE ADC
// =====================================================

int readAverageADC(int pin)
{
  const int samples = 20;

  long total = 0;

  for (int i = 0; i < samples; i++)
  {
    total += analogRead(pin);
    delay(5);
  }

  return total / samples;
}


// =====================================================
// READ TEMPERATURE
// =====================================================

float readTemperature()
{
  sensors.requestTemperatures();

  float temperature =
    sensors.getTempCByIndex(0);

  return temperature;
}


// =====================================================
// READ TDS AND CALCULATE EC
// =====================================================

float readConductivity()
{
  int adcValue =
    readAverageADC(TDS_PIN);

  float voltage =
    (adcValue * ADC_VREF) / ADC_RESOLUTION;

  // Approximate TDS calculation used during
  // your previous ESP32 testing.
  float tds =
    (voltage / 0.5) * 378.0;

  if (tds < 0)
    tds = 0;

  // EC = TDS / conversion factor
  float ec =
    tds / TDS_CONVERSION_FACTOR;

  return ec;
}


// =====================================================
// READ pH
// =====================================================

float readPH()
{
  int adcValue =
    readAverageADC(PH_PIN);

  float voltage =
    (adcValue * ADC_VREF) / ADC_RESOLUTION;

  float ph =
    calculatePH(voltage);

  return ph;
}


// =====================================================
// SEND DATA TO FLASK
// =====================================================

void sendToBackend(
  float temperature,
  float conductivity,
  float ph
)
{
  if (WiFi.status() != WL_CONNECTED)
  {
    Serial.println("WiFi disconnected.");
    return;
  }

  HTTPClient http;

  Serial.println();
  Serial.println("Connecting to Flask backend...");

  http.begin(SERVER_URL);

  http.addHeader(
    "Content-Type",
    "application/json"
  );

  // IMPORTANT:
  // These names match water.py:
  //
  // temperature
  // conductivity
  // ph

  String jsonData = "{";
  jsonData += "\"temperature\":" + String(temperature, 2) + ",";
  jsonData += "\"conductivity\":" + String(conductivity, 2) + ",";
  jsonData += "\"ph\":" + String(ph, 2);
  jsonData += "}";

  Serial.println("Sending:");
  Serial.println(jsonData);

  int httpResponseCode =
    http.POST(jsonData);

  Serial.print("HTTP Response Code: ");
  Serial.println(httpResponseCode);

  if (httpResponseCode > 0)
  {
    String response =
      http.getString();

    Serial.println("Backend response:");
    Serial.println(response);
  }
  else
  {
    Serial.print("Error sending data: ");
    Serial.println(http.errorToString(httpResponseCode));
  }

  http.end();
}


// =====================================================
// WIFI CONNECTION
// =====================================================

void connectWiFi()
{
  Serial.println();
  Serial.println("Connecting to WiFi...");

  WiFi.mode(WIFI_STA);

  WiFi.begin(
    WIFI_SSID,
    WIFI_PASSWORD
  );

  int attempts = 0;

  while (
    WiFi.status() != WL_CONNECTED &&
    attempts < 30
  )
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

    Serial.print("ESP32 IP: ");
    Serial.println(WiFi.localIP());

    Serial.print("Backend: ");
    Serial.println(SERVER_URL);

    Serial.println("----------------------------------------");
  }
  else
  {
    Serial.println("WiFi connection failed.");
  }
}


// =====================================================
// SETUP
// =====================================================

void setup()
{
  Serial.begin(115200);

  delay(1000);

  Serial.println();
  Serial.println("========================================");
  Serial.println("ESP32 WATER MONITORING SYSTEM");
  Serial.println("========================================");

  // ADC configuration
  analogReadResolution(12);

  // Start temperature sensor
  sensors.begin();

  // Connect WiFi
  connectWiFi();
}


// =====================================================
// LOOP
// =====================================================

void loop()
{
  // Reconnect WiFi if necessary
  if (WiFi.status() != WL_CONNECTED)
  {
    connectWiFi();
  }

  unsigned long currentTime =
    millis();

  if (
    currentTime - lastSendTime >=
    SEND_INTERVAL
  )
  {
    lastSendTime = currentTime;

    Serial.println();
    Serial.println("----------------------------------------");

    // -----------------------------
    // TEMPERATURE
    // -----------------------------

    float temperature =
      readTemperature();

    Serial.print("Temperature: ");
    Serial.print(temperature, 2);
    Serial.println(" °C");


    // -----------------------------
    // CONDUCTIVITY
    // -----------------------------

    int tdsADC =
      readAverageADC(TDS_PIN);

    float tdsVoltage =
      (tdsADC * ADC_VREF) /
      ADC_RESOLUTION;

    float tds =
      (tdsVoltage / 0.5) * 378.0;

    if (tds < 0)
      tds = 0;

    float conductivity =
      tds / TDS_CONVERSION_FACTOR;

    Serial.print("TDS ADC: ");
    Serial.println(tdsADC);

    Serial.print("TDS Voltage: ");
    Serial.print(tdsVoltage, 3);
    Serial.println(" V");

    Serial.print("TDS: ");
    Serial.print(tds, 2);
    Serial.println(" ppm");

    Serial.print("EC: ");
    Serial.print(conductivity, 2);
    Serial.println(" µS/cm");


    // -----------------------------
    // pH
    // -----------------------------

    int phADC =
      readAverageADC(PH_PIN);

    float phVoltage =
      (phADC * ADC_VREF) /
      ADC_RESOLUTION;

    float ph =
      calculatePH(phVoltage);

    Serial.print("pH ADC: ");
    Serial.println(phADC);

    Serial.print("pH Voltage: ");
    Serial.print(phVoltage, 3);
    Serial.println(" V");

    Serial.print("pH: ");
    Serial.println(ph, 2);


    // -----------------------------
    // SEND TO BACKEND
    // -----------------------------

    sendToBackend(
      temperature,
      conductivity,
      ph
    );

    Serial.println("----------------------------------------");
  }

  delay(100);
}