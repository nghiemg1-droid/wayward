(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const STORAGE_KEY = "wayward_device_token";
  let timer = null;
  let wakeLock = null;
  let sent = 0;
  let busy = false;

  $("token").value = localStorage.getItem(STORAGE_KEY) || "";

  function setStatus(text, isError) {
    const node = $("status");
    node.textContent = text;
    node.className = isError ? "error" : "muted";
  }

  function getPosition() {
    return new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: true,
        maximumAge: 0,
        timeout: 20000,
      });
    });
  }

  // Turn an error into a message. Permission problems stop the reporting; the rest are retried.
  function describe(error) {
    if (error && typeof error.code === "number") {
      if (error.code === 1) {
        stop();
        return "Location permission was denied. On iPhone: Settings > Privacy & Security > "
          + "Location Services > Safari Websites, then reload this page.";
      }
      if (error.code === 3) return "Still waiting for a GPS fix. Trying again...";
      return "Location is unavailable right now. Trying again...";
    }
    return "Could not reach the server. Trying again...";
  }

  async function reportOnce() {
    if (busy) return;
    busy = true;
    try {
      const position = await getPosition();
      const { latitude, longitude, accuracy } = position.coords;
      const response = await fetch("/pings", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Device-Token": $("token").value.trim(),
        },
        body: JSON.stringify({ lat: latitude, lng: longitude, accuracy_m: accuracy }),
      });
      if (response.status === 401) {
        stop();
        setStatus("The server rejected this device token. Check it and press Start again.", true);
        return;
      }
      if (!response.ok) throw new Error("Server answered " + response.status);
      sent += 1;
      $("last-sent").textContent = new Date().toLocaleTimeString();
      $("last-accuracy").textContent = Math.round(accuracy) + " m";
      $("sent-count").textContent = String(sent);
      setStatus("Reporting every " + $("interval").value + " seconds. Keep this page open.", false);
    } catch (error) {
      setStatus(describe(error), true);
    } finally {
      busy = false;
    }
  }

  async function requestWakeLock() {
    if (!$("keep-awake").checked || !("wakeLock" in navigator)) return;
    try {
      wakeLock = await navigator.wakeLock.request("screen");
      wakeLock.addEventListener("release", () => {
        wakeLock = null;
        $("awake").textContent = "no";
      });
      $("awake").textContent = "yes";
    } catch (error) {
      $("awake").textContent = "no (not allowed)";
    }
  }

  function releaseWakeLock() {
    if (wakeLock) wakeLock.release();
    wakeLock = null;
    $("awake").textContent = "no";
  }

  async function start() {
    if (!navigator.geolocation) {
      setStatus("This browser cannot read your location.", true);
      return;
    }
    if (!window.isSecureContext) {
      setStatus("Location only works on https pages (or localhost). Open this page through an https link.", true);
      return;
    }
    const value = $("token").value.trim();
    if (!value) {
      setStatus("Paste the device token first.", true);
      return;
    }
    localStorage.setItem(STORAGE_KEY, value);
    $("start").disabled = true;
    $("stop").disabled = false;
    $("token").disabled = true;
    $("interval").disabled = true;
    setStatus("Getting a location fix...", false);
    timer = setInterval(reportOnce, Number($("interval").value) * 1000);
    await requestWakeLock();
    await reportOnce();
  }

  function stop() {
    clearInterval(timer);
    timer = null;
    releaseWakeLock();
    $("start").disabled = false;
    $("stop").disabled = true;
    $("token").disabled = false;
    $("interval").disabled = false;
    setStatus("Not reporting.", false);
  }

  $("start").addEventListener("click", start);
  $("stop").addEventListener("click", stop);
  $("forget").addEventListener("click", () => {
    localStorage.removeItem(STORAGE_KEY);
    $("token").value = "";
    setStatus("Saved token removed from this device.", false);
  });

  // The screen lock is released when the page is hidden; take it again and report right away.
  document.addEventListener("visibilitychange", () => {
    if (timer && document.visibilityState === "visible") {
      requestWakeLock();
      reportOnce();
    }
  });
})();
