// Shared logic across all pages.
// Each submitForm()/button call below just does nothing if its
// form/button isn't present on the current page.

const API_BASE = "http://127.0.0.1:5000";

// Long names + units for every short/coded field the backend uses,
// so results and SHAP charts can show something readable instead of
// raw codes like "WSPM" or "EC".
const FIELD_META = {
  // air
  SO2:   { label: "Sulfur Dioxide",        unit: "µg/m³" },
  NO2:   { label: "Nitrogen Dioxide",      unit: "µg/m³" },
  CO:    { label: "Carbon Monoxide",       unit: "µg/m³" },
  O3:    { label: "Ozone",                 unit: "µg/m³" },
  TEMP:  { label: "Temperature",           unit: "°C" },
  PRES:  { label: "Atmospheric Pressure",  unit: "hPa" },
  DEWP:  { label: "Dew Point",             unit: "°C" },
  RAIN:  { label: "Rainfall",              unit: "mm" },
  wd:    { label: "Wind Direction",        unit: "" },
  WSPM:  { label: "Wind Speed",            unit: "m/s" },
  station: { label: "Station",             unit: "" },

  // water
  temperature:  { label: "Temperature",  unit: "°C" },
  conductivity: { label: "Conductivity", unit: "µS/cm" },
  ph:           { label: "pH",            unit: "" },

  // soil
  N:  { label: "Nitrogen",               unit: "kg/ha" },
  P:  { label: "Phosphorus",             unit: "kg/ha" },
  K:  { label: "Potassium",              unit: "kg/ha" },
  pH: { label: "pH",                     unit: "" },
  EC: { label: "Electrical Conductivity", unit: "dS/m" },
  OC: { label: "Organic Carbon",         unit: "%" },
  S:  { label: "Sulfur",                 unit: "ppm" },
  Zn: { label: "Zinc",                   unit: "ppm" },
  Fe: { label: "Iron",                   unit: "ppm" },
  Cu: { label: "Copper",                 unit: "ppm" },
  Mn: { label: "Manganese",              unit: "ppm" },
  B:  { label: "Boron",                  unit: "ppm" },
};

const WIND_COMPASS = {
  N: "North",
  NNE: "North-Northeast",
  NE: "Northeast",
  ENE: "East-Northeast",
  E: "East",
  ESE: "East-Southeast",
  SE: "Southeast",
  SSE: "South-Southeast",
  S: "South",
  SSW: "South-Southwest",
  SW: "Southwest",
  WSW: "West-Southwest",
  W: "West",
  WNW: "West-Northwest",
  NW: "Northwest",
  NNW: "North-Northwest",
};

function fieldLabel(key) {
  return (FIELD_META[key] && FIELD_META[key].label) || key;
}

function fieldUnit(key) {
  return (FIELD_META[key] && FIELD_META[key].unit) || "";
}

function fieldDisplayValue(key, value) {
  if (key === "wd" && WIND_COMPASS[value]) {
    return `${WIND_COMPASS[value]} (${value})`;
  }

  if (key === "station" && typeof value === "string") {
    return value.charAt(0).toUpperCase() + value.slice(1);
  }

  return value;
}

function renderReadableInputs(inputs) {
  const rows = Object.entries(inputs)
    .filter(([k, v]) => v !== undefined && v !== null && v !== "")
    .map(([k, v]) => {
      const unit = fieldUnit(k);
      const label = fieldLabel(k) + (unit ? ` (${unit})` : "");

      return `
        <tr>
          <td>${label}</td>
          <td>${fieldDisplayValue(k, v)}</td>
        </tr>
      `;
    })
    .join("");

  return `
    <table class="readings-table">
      <tbody>${rows}</tbody>
    </table>
  `;
}

const BAD_CATEGORIES = [
  "Unhealthy",
  "Unhealthy for Sensitive Groups",
  "Very Unhealthy",
  "Hazardous",
  "Unsafe",
  "Less Fertile",
];

const TOAST_SEVERITY = {
  "Unhealthy for Sensitive Groups": "warn",
  "Unhealthy": "bad",
  "Very Unhealthy": "severe",
  "Hazardous": "extreme",
  "Unsafe": "bad",
  "Less Fertile": "warn",
};

function showToast(title, message, severity) {
  let container = document.querySelector(".toast-container");

  if (!container) {
    container = document.createElement("div");
    container.className = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");

  toast.className =
    "toast" +
    (severity && severity !== "bad"
      ? ` severity-${severity}`
      : "");

  toast.innerHTML = `
    <button type="button" class="toast-close">&times;</button>
    <strong>${title}</strong>
    ${message}
  `;

  container.appendChild(toast);

  toast
    .querySelector(".toast-close")
    .addEventListener("click", () => toast.remove());

  setTimeout(() => toast.remove(), 10000);
}

function renderShapChart(containerEl, contributions, domain) {
  const top = contributions.slice(0, 8);

  const maxAbs = Math.max(
    ...top.map(c => Math.abs(c.contribution)),
    0.0001
  );

  const leader = top[0];

  const leaderLabel = fieldLabel(leader.feature);
  const leaderUnit = fieldUnit(leader.feature);

  const direction =
    leader.contribution >= 0
      ? "pushed this result up"
      : "pushed this result down";

  const summary =
    domain === "air"
      ? `<strong>${leaderLabel}</strong> had the biggest effect here, changing the predicted PM2.5 by about ${Math.abs(leader.contribution)}${leaderUnit ? " " + leaderUnit : ""}.`
      : `<strong>${leaderLabel}</strong> had the biggest effect here, and ${direction}.`;

  function strengthLabel(value) {
    const ratio = Math.abs(value) / maxAbs;

    if (ratio > 0.66) return "Strong";
    if (ratio > 0.33) return "Moderate";

    return "Slight";
  }

  containerEl.innerHTML =
    `<p style="margin:12px 0 10px;">${summary}</p>` +

    `<p class="muted" style="margin:0 0 10px;">
      Full breakdown (green = pushed toward this result, red = pushed away from it):
    </p>` +

    `<div class="shap-chart">` +

    top.map(c => {
      const pct = (
        Math.abs(c.contribution) /
        maxAbs *
        50
      ).toFixed(1);

      const cls =
        c.contribution >= 0
          ? "positive"
          : "negative";

      const unit = fieldUnit(c.feature);

      const longLabel =
        fieldLabel(c.feature) +
        (unit ? ` (${unit})` : "");

      const valueDisplay =
        domain === "air"
          ? `${c.contribution >= 0 ? "+" : ""}${c.contribution}${unit ? " " + unit : ""}`
          : strengthLabel(c.contribution);

      return `
        <div class="shap-row" title="${longLabel}">
          <span class="shap-label">${longLabel}</span>

          <div class="shap-track">
            <div
              class="shap-bar ${cls}"
              style="width:${pct}%"
            ></div>
          </div>

          <span class="shap-value">${valueDisplay}</span>
        </div>
      `;
    }).join("") +

    "</div>";
}

async function loadShapExplanation(
  domain,
  inputs,
  containerEl,
  buttonEl
) {
  buttonEl.disabled = true;
  buttonEl.textContent = "Loading explanation...";

  try {
    const response = await fetch(
      API_BASE + "/api/" + domain + "/explain",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(inputs),
      }
    );

    const data = await response.json();

    if (data.error) {
      containerEl.innerHTML = "";

      showToast(
        "Explanation unavailable",
        data.error ||
          "The feature-importance explanation could not be loaded. Please try again.",
        "warn"
      );
    } else {
      renderShapChart(
        containerEl,
        data.contributions,
        domain
      );
    }

  } catch (err) {
    containerEl.innerHTML = "";

    showToast(
      "Explanation unavailable",
      "Feature-importance information is not currently available. Please try again when sufficient data is available.",
      "warn"
    );
  }

  buttonEl.style.display = "none";
}

function renderResult(el, data, domain) {
  const pm25Line =
    data.prediction.predicted_pm25 !== undefined
      ? `<p>Predicted PM2.5: <strong>${data.prediction.predicted_pm25} &micro;g/m&sup3;</strong></p>`
      : "";

  const stationLine =
    data.inputs && data.inputs.station
      ? `<p>Station: <strong>${data.inputs.station.charAt(0).toUpperCase() + data.inputs.station.slice(1)}</strong></p>`
      : "";

  const isBad =
    BAD_CATEGORIES.includes(
      data.prediction.category
    );

  el.classList.remove(
    "result-good",
    "result-bad"
  );

  el.classList.add(
    isBad
      ? "result-bad"
      : "result-good"
  );

  el.innerHTML = `
    <h3>${data.prediction.category}</h3>

    ${stationLine}

    ${pm25Line}

    <p>Source: ${data.source}</p>

    <p
      class="muted"
      style="margin-top:14px;"
    >
      Readings used for this prediction:
    </p>

    ${renderReadableInputs(data.inputs)}

    <button
      type="button"
      class="explain-btn"
    >
      Why this result?
    </button>

    <div class="shap-container"></div>
  `;

  const explainBtn =
    el.querySelector(".explain-btn");

  const shapContainer =
    el.querySelector(".shap-container");

  explainBtn.addEventListener(
    "click",
    () => {
      loadShapExplanation(
        domain,
        data.inputs,
        shapContainer,
        explainBtn
      );
    }
  );

  if (isBad) {
    const severity =
      TOAST_SEVERITY[
        data.prediction.category
      ] || "bad";

    const domainLabel =
      domain.charAt(0).toUpperCase() +
      domain.slice(1);

    showToast(
      `${domainLabel}: ${data.prediction.category}`,
      "This reading came back outside the safe range.",
      severity
    );
  }
}

function submitForm(
  formId,
  resultId,
  endpoint,
  fieldIds,
  domain
) {
  const form =
    document.getElementById(formId);

  if (!form) return;

  form.addEventListener(
    "submit",
    async (e) => {
      e.preventDefault();

      const resultEl =
        document.getElementById(resultId);

      resultEl.classList.remove(
        "result-good",
        "result-bad"
      );

      resultEl.textContent =
        "Predicting...";

      const payload = {
        source: "manual"
      };

      fieldIds.forEach((id) => {
        payload[id] =
          document.getElementById(id).value;
      });

      try {
        const response =
          await fetch(
            API_BASE + endpoint,
            {
              method: "POST",
              headers: {
                "Content-Type":
                  "application/json"
              },
              body:
                JSON.stringify(payload),
            }
          );

        const data =
          await response.json();

        renderResult(
          resultEl,
          data,
          domain
        );

      } catch (err) {
        resultEl.textContent = "";

        showToast(
          "Prediction unavailable",
          "No prediction is currently available. Please try again shortly.",
          "bad"
        );
      }
    }
  );
}

submitForm(
  "water-form",
  "water-result",
  "/api/water/predict",
  [
    "temperature",
    "conductivity",
    "ph"
  ],
  "water"
);

submitForm(
  "soil-form",
  "soil-result",
  "/api/soil/predict",
  [
    "N",
    "P",
    "K",
    "pH",
    "EC",
    "OC",
    "S",
    "Zn",
    "Fe",
    "Cu",
    "Mn",
    "B"
  ],
  "soil"
);

const airDemoForm =
  document.getElementById(
    "air-demo-form"
  );

if (airDemoForm) {

  const fieldIds = [
    "SO2",
    "NO2",
    "CO",
    "O3",
    "TEMP",
    "PRES",
    "DEWP",
    "RAIN",
    "wd",
    "WSPM"
  ];

  airDemoForm.addEventListener(
    "submit",
    async (e) => {

      e.preventDefault();

      const resultEl =
        document.getElementById(
          "air-demo-result"
        );

      resultEl.classList.remove(
        "result-good",
        "result-bad"
      );

      resultEl.textContent =
        "Predicting...";

      const payload = {};

      fieldIds.forEach((id) => {
        payload[id] =
          document.getElementById(id).value;
      });

      try {

        const response =
          await fetch(
            API_BASE +
              "/api/air/predict-demo",
            {
              method: "POST",
              headers: {
                "Content-Type":
                  "application/json"
              },
              body:
                JSON.stringify(payload),
            }
          );

        const data =
          await response.json();

        renderResult(
          resultEl,
          data,
          "air"
        );

      } catch (err) {

        resultEl.textContent = "";

        showToast(
          "Prediction unavailable",
          "No prediction is currently available. Please try again shortly.",
          "bad"
        );
      }
    }
  );
}

document
  .querySelectorAll(".station-btn")
  .forEach(btn => {

    btn.addEventListener(
      "click",
      () => {

        document
          .querySelectorAll(
            ".station-btn"
          )
          .forEach(
            b =>
              b.classList.remove(
                "active"
              )
          );

        btn.classList.add(
          "active"
        );
      }
    );

  });


// --------------------------------------------------
// LIVE AIR WIDGET
// --------------------------------------------------

const LIVE_INTERVAL_MS =
  30000;

const liveWidget =
  document.getElementById(
    "live-widget"
  );

if (liveWidget) {

  const toggleBtn =
    document.getElementById(
      "live-widget-toggle"
    );

  const statusDot =
    document.getElementById(
      "live-widget-dot"
    );

  const body =
    document.getElementById(
      "live-widget-body"
    );

  const stationName =
    document.getElementById(
      "live-widget-station"
    );

  let timer = null;

  let running = false;

  let backendOfflineAlerted =
    false;

  function currentStation() {

    const activeBtn =
      document.querySelector(
        ".station-btn.active"
      );

    return activeBtn
      ? activeBtn.dataset.station
      : "colombo";
  }

  async function pollOnce() {

    const station =
      currentStation();

    stationName.textContent =
      station.charAt(0).toUpperCase() +
      station.slice(1);

    body.classList.add(
      "loading"
    );

    try {

      const res =
        await fetch(
          `${API_BASE}/api/air/live-peek?station=${station}`
        );

      const data =
        await res.json();

      if (data.error) {

        body.innerHTML =
          `<p class="muted">${data.error}</p>`;

        if (!backendOfflineAlerted) {

          backendOfflineAlerted =
            true;

          showToast(
           "Air data not fetched",
           "Unable to retrieve the latest air-quality data. Please try again shortly.",
           "bad"
          );
        }

        return;
      }

      backendOfflineAlerted =
        false;

      const cat =
        data.prediction.category;

      const isBad =
        BAD_CATEGORIES.includes(cat);

      const rows =
        Object.entries(
          data.inputs
        )
          .filter(
            ([k]) =>
              k !== "station"
          )
          .map(
            ([k, v]) => {

              const unit =
                fieldUnit(k);

              return `
                <div class="live-row">
                  <span>
                    ${fieldLabel(k)}
                    ${unit ? ` (${unit})` : ""}
                  </span>

                  <strong>
                    ${fieldDisplayValue(
                      k,
                      v
                    )}
                  </strong>
                </div>
              `;
            }
          )
          .join("");

      const now =
        new Date();

      body.innerHTML = `
        <div
          class="live-category ${isBad ? "bad" : "good"}"
        >
          ${cat}
          &middot;
          PM2.5
          ${data.prediction.predicted_pm25}
        </div>

        <div class="live-rows">
          ${rows}
        </div>

        <p class="live-updated">
          Updated ${now.toLocaleTimeString()}
        </p>

        <button
          type="button"
          class="explain-btn"
        >
          Why this result?
        </button>

        <div class="shap-container"></div>
      `;

      const explainBtn =
        body.querySelector(
          ".explain-btn"
        );

      const shapContainer =
        body.querySelector(
          ".shap-container"
        );

      explainBtn.addEventListener(
        "click",
        () => {

          loadShapExplanation(
            "air",
            data.inputs,
            shapContainer,
            explainBtn
          );

        }
      );

    } catch (err) {

      body.innerHTML =
        `<p class="muted">
          The live air feed is temporarily unavailable.
        </p>`;

      if (!backendOfflineAlerted) {

        backendOfflineAlerted =
          true;

        showToast(
          "Air data not fetched",
          "Unable to retrieve the latest air-quality data. Please try again shortly.",
          "bad"
        );
      }
    }

    body.classList.remove(
      "loading"
    );
  }

  function start() {

    running = true;

    statusDot.classList.add(
      "on"
    );

    toggleBtn.textContent =
      "Stop live feed";

    pollOnce();

    timer =
      setInterval(
        pollOnce,
        LIVE_INTERVAL_MS
      );
  }

  function stop() {

    running = false;

    statusDot.classList.remove(
      "on"
    );

    toggleBtn.textContent =
      "Start live feed";

    if (timer)
      clearInterval(timer);

    body.innerHTML =
      `<p class="muted">
        Live feed is off. Turn it on to see current readings update automatically every 30s.
      </p>`;
  }

  toggleBtn.addEventListener(
    "click",
    () =>
      running
        ? stop()
        : start()
  );

  document
    .querySelectorAll(
      ".station-btn"
    )
    .forEach(btn => {

      btn.addEventListener(
        "click",
        () => {

          if (running)
            pollOnce();

        }
      );

    });

  start();
}


// --------------------------------------------------
// WATER IoT LIVE PANEL
// --------------------------------------------------

const iotResultEl =
  document.getElementById(
    "iot-water-result"
  );

if (iotResultEl) {

  let lastAlertedTimestamp =
    null;

  let backendOfflineAlerted =
    false;

  async function loadLatestIotReading() {

    try {

      const res =
        await fetch(
          API_BASE +
            "/api/water/live-latest"
        );

      const data =
        await res.json();

      if (!data.available) {

        backendOfflineAlerted =
          false;

        iotResultEl.innerHTML =
          `<p class="muted">
            No sensor reading received yet. Check the ESP32 is powered on and connected to Wi-Fi.
          </p>`;

        return;
      }

      backendOfflineAlerted =
        false;

      const isBad =
        BAD_CATEGORIES.includes(
          data.prediction.category
        );

      iotResultEl.classList.remove(
        "result-good",
        "result-bad"
      );

      iotResultEl.classList.add(
        isBad
          ? "result-bad"
          : "result-good"
      );

      iotResultEl.innerHTML = `
        <h3>
          ${data.prediction.category}
        </h3>

        <p
          class="muted"
          style="margin-top:14px;"
        >
          Readings from the sensor:
        </p>

        ${renderReadableInputs(
          data.inputs
        )}

        <p
          class="muted"
          style="margin-top:10px;"
        >
          Received
          ${data.timestamp
            .replace("T", " ")
            .slice(0, 19)}
        </p>

        <button
          type="button"
          class="explain-btn"
        >
          Why this result?
        </button>

        <div class="shap-container"></div>
      `;

      const explainBtn =
        iotResultEl.querySelector(
          ".explain-btn"
        );

      const shapContainer =
        iotResultEl.querySelector(
          ".shap-container"
        );

      explainBtn.addEventListener(
        "click",
        () => {

          loadShapExplanation(
            "water",
            data.inputs,
            shapContainer,
            explainBtn
          );

        }
      );

      if (
        isBad &&
        data.timestamp !==
          lastAlertedTimestamp
      ) {

        lastAlertedTimestamp =
          data.timestamp;

        const severity =
          TOAST_SEVERITY[
            data.prediction.category
          ] || "bad";

        showToast(
          "Water (IoT): " +
            data.prediction.category,
          "This reading came back outside the safe range.",
          severity
        );
      }

    } catch (err) {

      iotResultEl.innerHTML =
        `<p class="muted">
          The water IoT service is temporarily unavailable.
        </p>`;

      if (!backendOfflineAlerted) {

        backendOfflineAlerted =
          true;

        showToast(
          "Water data not fetched",
          "No new water-quality reading is currently available. Please try again shortly ",
          "bad"
        );
      }
    }
  }

  loadLatestIotReading();

  setInterval(
    loadLatestIotReading,
    30000
  );
}


// --------------------------------------------------
// MODE CARD SWITCHER
// --------------------------------------------------

document
  .querySelectorAll(
    ".mode-card"
  )
  .forEach(card => {

    card.addEventListener(
      "click",
      () => {

        if (!card.dataset.target)
          return;

        document
          .querySelectorAll(
            ".mode-card"
          )
          .forEach(
            c =>
              c.classList.remove(
                "active"
              )
          );

        document
          .querySelectorAll(
            ".mode-panel"
          )
          .forEach(
            p =>
              p.classList.remove(
                "active"
              )
          );

        card.classList.add(
          "active"
        );

        const target =
          document.getElementById(
            card.dataset.target
          );

        if (target) {
          target.classList.add(
            "active"
          );
        }
      }
    );

  });