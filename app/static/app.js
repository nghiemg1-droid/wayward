(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  let token = localStorage.getItem("wayward_token");
  let map = null;
  let mapLayer = null;
  let selectedId = null;
  let refreshTimer = null;
  let fitNext = true;

  // ---------- helpers ----------

  // The API sends UTC timestamps without a time zone, so add one before parsing.
  function parseUtc(value) {
    let text = value.replace(/(\.\d{3})\d+/, "$1");
    if (!/(Z|[+-]\d\d:?\d\d)$/i.test(text)) text += "Z";
    return new Date(text);
  }

  function timeAgo(value) {
    if (!value) return "never";
    const seconds = Math.max(0, Math.round((Date.now() - parseUtc(value).getTime()) / 1000));
    if (seconds < 60) return seconds + " s ago";
    if (seconds < 3600) return Math.round(seconds / 60) + " min ago";
    if (seconds < 86400) return Math.round(seconds / 3600) + " h ago";
    return Math.round(seconds / 86400) + " d ago";
  }

  function formatDistance(meters) {
    return meters >= 1000 ? (meters / 1000).toFixed(1) + " km" : Math.round(meters) + " m";
  }

  function el(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text; // textContent, never innerHTML: names come from users
    if (className) node.className = className;
    return node;
  }

  async function errorMessage(response) {
    if (response.status === 422) return "Please check what you entered (passwords need at least 8 characters).";
    try {
      const data = await response.json();
      if (typeof data.detail === "string") return data.detail;
    } catch (error) { /* no JSON body */ }
    return "Something went wrong (" + response.status + ")";
  }

  async function api(path, { method = "GET", json } = {}) {
    const headers = {};
    if (token) headers.Authorization = "Bearer " + token;
    let body;
    if (json !== undefined) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(json);
    }
    const response = await fetch(path, { method, headers, body });
    if (response.status === 401 && token) {
      signOut("Your session expired. Please log in again.");
      throw new Error("Session expired");
    }
    if (!response.ok) throw new Error(await errorMessage(response));
    return response.status === 204 ? null : response.json();
  }

  // ---------- authentication ----------

  async function logIn(email, password) {
    const response = await fetch("/auth/login", {
      method: "POST",
      body: new URLSearchParams({ username: email, password }),
    });
    if (!response.ok) {
      throw new Error(response.status === 401 ? "Incorrect email or password" : await errorMessage(response));
    }
    token = (await response.json()).access_token;
    localStorage.setItem("wayward_token", token);
  }

  async function authenticate(register) {
    const email = $("email").value.trim();
    const password = $("password").value;
    $("login-btn").disabled = true;
    $("register-btn").disabled = true;
    $("auth-message").textContent = "";
    try {
      if (register) await api("/auth/register", { method: "POST", json: { email, password } });
      await logIn(email, password);
      $("password").value = "";
      await showApp();
    } catch (error) {
      $("auth-message").textContent = error.message;
    } finally {
      $("login-btn").disabled = false;
      $("register-btn").disabled = false;
    }
  }

  function signOut(message) {
    token = null;
    localStorage.removeItem("wayward_token");
    selectedId = null;
    showAuth(message);
  }

  // ---------- views ----------

  function showAuth(message) {
    stopRefresh();
    $("app-view").hidden = true;
    $("auth-view").hidden = false;
    $("auth-message").textContent = message || "";
  }

  async function showApp() {
    $("auth-view").hidden = true;
    $("app-view").hidden = false;
    initMap();
    map.invalidateSize();
    const me = await api("/auth/me");
    $("who").textContent = me.email;
    await refresh();
    startRefresh();
  }

  function startRefresh() {
    stopRefresh();
    refreshTimer = setInterval(refresh, 10000);
  }

  function stopRefresh() {
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = null;
  }

  // ---------- data ----------

  async function refresh() {
    if (!token) return;
    try {
      const devices = await api("/devices");
      const latest = await Promise.all(devices.map(async (device) => {
        const pings = await api("/devices/" + device.id + "/pings?limit=1");
        return pings[0] || null;
      }));

      const selected = devices.find((device) => device.id === selectedId) || null;
      if (!selected) selectedId = null;
      let trail = [];
      let alerts = [];
      if (selected) {
        [trail, alerts] = await Promise.all([
          api("/devices/" + selected.id + "/pings?limit=50"),
          api("/devices/" + selected.id + "/alerts?limit=20"),
        ]);
      }

      renderDevices(devices, latest);
      renderDetail(selected, latest[devices.indexOf(selected)] || null, alerts);
      renderMap(devices, latest, selected, trail, alerts);
    } catch (error) {
      /* a failed refresh (offline, expired session) is handled in api(); try again next tick */
    }
  }

  // ---------- rendering ----------

  function renderDevices(devices, latest) {
    const list = $("device-list");
    list.replaceChildren();
    $("empty-hint").hidden = devices.length > 0;
    devices.forEach((device, index) => {
      const item = document.createElement("li");
      const button = el("button", undefined, "device-btn" + (device.id === selectedId ? " selected" : ""));
      button.type = "button";
      button.append(el("strong", device.name), el("span", "last seen " + timeAgo(device.last_seen), "meta"));
      button.addEventListener("click", () => {
        selectedId = device.id;
        fitNext = true;
        refresh();
      });
      item.append(button);
      list.append(item);
    });
  }

  function renderDetail(device, ping, alerts) {
    $("device-detail").hidden = !device;
    if (!device) return;
    $("detail-name").textContent = device.name;
    const home = device.home_lat === null ? "no home location set" : "home radius " + device.radius_m + " m";
    $("detail-meta").textContent = "Last seen " + timeAgo(device.last_seen) + " · " + home;
    const list = $("alert-list");
    list.replaceChildren();
    $("no-alerts").hidden = alerts.length > 0;
    alerts.forEach((alert) => {
      const item = el("li", formatDistance(alert.distance_m) + " from home · " + timeAgo(alert.created_at));
      list.append(item);
    });
  }

  function initMap() {
    if (map) return;
    map = L.map("map").setView([20, 0], 2);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);
    mapLayer = L.layerGroup().addTo(map);
  }

  function renderMap(devices, latest, selected, trail, alerts) {
    mapLayer.clearLayers();
    const bounds = L.latLngBounds([]);

    devices.forEach((device, index) => {
      const isSelected = selected && device.id === selected.id;
      if (device.home_lat !== null && device.home_lng !== null) {
        const home = L.circle([device.home_lat, device.home_lng], {
          radius: device.radius_m,
          color: isSelected ? "#2563eb" : "#94a3b8",
          weight: 2,
          fill: false,
        }).addTo(mapLayer);
        if (isSelected || !selected) bounds.extend(home.getBounds());
      }
      const ping = latest[index];
      if (ping) {
        const marker = L.circleMarker([ping.lat, ping.lng], {
          radius: isSelected ? 9 : 7,
          color: "#111827",
          weight: 2,
          fillColor: isSelected ? "#2563eb" : "#64748b",
          fillOpacity: 0.9,
        }).addTo(mapLayer);
        marker.bindTooltip(el("span", device.name));
        if (isSelected || !selected) bounds.extend([ping.lat, ping.lng]);
      }
    });

    if (selected) {
      const points = trail.map((ping) => [ping.lat, ping.lng]);
      if (points.length > 1) L.polyline(points, { color: "#2563eb", weight: 3, opacity: 0.6 }).addTo(mapLayer);
      points.forEach((point) => bounds.extend(point));
      alerts.forEach((alert) => {
        const marker = L.circleMarker([alert.lat, alert.lng], {
          radius: 8, color: "#dc2626", weight: 2, fillColor: "#dc2626", fillOpacity: 0.9,
        }).addTo(mapLayer);
        marker.bindTooltip(el("span", "Alert: " + formatDistance(alert.distance_m) + " from home"));
      });
    }

    if (fitNext && bounds.isValid()) {
      map.fitBounds(bounds.pad(0.3), { maxZoom: 16 });
      fitNext = false;
    }
  }

  // ---------- events ----------

  $("auth-form").addEventListener("submit", (event) => {
    event.preventDefault();
    authenticate(false);
  });

  $("register-btn").addEventListener("click", () => {
    if ($("auth-form").reportValidity()) authenticate(true);
  });

  $("logout-btn").addEventListener("click", () => signOut(""));

  $("device-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const number = (id) => ($(id).value.trim() === "" ? null : Number($(id).value));
    const payload = {
      name: $("device-name").value.trim(),
      home_lat: number("device-lat"),
      home_lng: number("device-lng"),
      radius_m: Number($("device-radius").value) || 500,
    };
    try {
      const device = await api("/devices", { method: "POST", json: payload });
      event.target.reset();
      $("form-message").textContent = "";
      $("token-name").textContent = device.name;
      $("token-value").textContent = device.device_token;
      $("token-box").hidden = false;
      selectedId = device.id;
      fitNext = true;
      await refresh();
    } catch (error) {
      $("form-message").textContent = error.message;
    }
  });

  $("use-location").addEventListener("click", () => {
    if (!navigator.geolocation) {
      $("form-message").textContent = "This browser cannot read your location.";
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        $("device-lat").value = position.coords.latitude.toFixed(5);
        $("device-lng").value = position.coords.longitude.toFixed(5);
        $("form-message").textContent = "";
      },
      (error) => { $("form-message").textContent = "Could not get your location: " + error.message; },
      { enableHighAccuracy: true, timeout: 15000 },
    );
  });

  $("copy-token").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText($("token-value").textContent);
      $("copy-token").textContent = "Copied";
    } catch (error) {
      $("copy-token").textContent = "Select and copy manually";
    }
  });

  $("hide-token").addEventListener("click", () => {
    $("token-value").textContent = "";
    $("token-box").hidden = true;
    $("copy-token").textContent = "Copy";
  });

  $("delete-btn").addEventListener("click", async () => {
    if (selectedId === null || !confirm("Delete this device and its history?")) return;
    try {
      await api("/devices/" + selectedId, { method: "DELETE" });
      selectedId = null;
      fitNext = true;
      await refresh();
    } catch (error) {
      alert(error.message);
    }
  });

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) refresh();
  });

  // ---------- start ----------

  if (token) {
    showApp().catch((error) => {
      if (token) showAuth("Could not load your data: " + error.message);
    });
  } else {
    showAuth("");
  }
})();
