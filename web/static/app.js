const state = {
  config: null,
  params: {},
  imageFile: null,
  jsonFile: null,
  taskId: null,
  pollTimer: null,
};

const fieldMeta = {
  distance: { label: "distance", slider: true },
  min_area_ratio: { label: "min-area-ratio", slider: false },
  spacing: { label: "spacing", slider: true },
  sigma_scale: { label: "sigma-scale", slider: true },
  sigma_min: { label: "sigma-min", slider: false },
  alpha: { label: "alpha", slider: true },
};

const demoShapes = [
  {
    name: "Triangle",
    points: [
      [128, 36],
      [220, 214],
      [36, 214],
    ],
  },
  {
    name: "Hexagon",
    points: [
      [86, 30],
      [172, 30],
      [224, 124],
      [172, 218],
      [86, 218],
      [34, 124],
    ],
  },
  {
    name: "Irregular",
    points: [
      [58, 48],
      [192, 34],
      [228, 100],
      [180, 138],
      [214, 212],
      [106, 228],
      [32, 166],
      [46, 94],
    ],
  },
];

function qs(selector) {
  return document.querySelector(selector);
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function formatValue(value) {
  return Number(value).toFixed(2).replace(/\.00$/, "");
}

function renderField(key) {
  const container = qs(`#field-${key}`);
  const limits = state.config.limits[key];
  const isSlider = state.config.sliderFields.includes(key);
  const value = state.params[key];

  const head = document.createElement("div");
  head.className = "field-head";

  const label = document.createElement("label");
  label.htmlFor = `${key}-input`;
  label.textContent = fieldMeta[key].label;

  const badge = document.createElement("span");
  badge.className = "field-value";
  badge.id = `${key}-value`;
  badge.textContent = formatValue(value);

  head.append(label, badge);
  container.append(head);

  const input = document.createElement("input");
  input.id = `${key}-input`;
  input.name = key;
  input.type = isSlider ? "range" : "number";
  input.min = String(limits.min);
  input.max = String(limits.max);
  input.step = String(limits.step);
  input.value = String(value);
  input.addEventListener("input", (event) => {
    const nextValue = clamp(Number(event.target.value), limits.min, limits.max);
    state.params[key] = nextValue;
    badge.textContent = formatValue(nextValue);
    if (!isSlider) {
      event.target.value = String(nextValue);
    }
    renderDemo();
  });

  container.append(input);
}

function renderFields() {
  Object.keys(fieldMeta).forEach((key) => {
    qs(`#field-${key}`).innerHTML = "";
    renderField(key);
  });
}

function centroid(points) {
  let area = 0;
  let cx = 0;
  let cy = 0;
  for (let i = 0; i < points.length; i += 1) {
    const [x1, y1] = points[i];
    const [x2, y2] = points[(i + 1) % points.length];
    const cross = x1 * y2 - x2 * y1;
    area += cross;
    cx += (x1 + x2) * cross;
    cy += (y1 + y2) * cross;
  }
  if (Math.abs(area) < 1e-6) {
    const xs = points.reduce((sum, [x]) => sum + x, 0);
    const ys = points.reduce((sum, [, y]) => sum + y, 0);
    return [xs / points.length, ys / points.length];
  }
  return [cx / (3 * area), cy / (3 * area)];
}

function shrinkPolygon(points, distance, minAreaRatio) {
  const center = centroid(points);
  const distances = points.map(([x, y]) => Math.hypot(x - center[0], y - center[1]));
  const avgRadius = distances.reduce((sum, item) => sum + item, 0) / distances.length;
  const shrinkFactor = clamp(1 - distance / Math.max(avgRadius, 1), minAreaRatio, 0.98);

  return points.map(([x, y]) => [
    center[0] + (x - center[0]) * shrinkFactor,
    center[1] + (y - center[1]) * shrinkFactor,
  ]);
}

function pointInPolygon(x, y, polygon) {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i, i += 1) {
    const xi = polygon[i][0];
    const yi = polygon[i][1];
    const xj = polygon[j][0];
    const yj = polygon[j][1];
    const intersect =
      yi > y !== yj > y &&
      x < ((xj - xi) * (y - yi)) / ((yj - yi) || 1e-6) + xi;
    if (intersect) {
      inside = !inside;
    }
  }
  return inside;
}

function samplePolygonPoints(polygon, spacing, width, height) {
  const points = [];
  const xs = polygon.map(([x]) => x);
  const ys = polygon.map(([, y]) => y);
  const minX = clamp(Math.floor(Math.min(...xs)), 0, width - 1);
  const maxX = clamp(Math.ceil(Math.max(...xs)), 0, width - 1);
  const minY = clamp(Math.floor(Math.min(...ys)), 0, height - 1);
  const maxY = clamp(Math.ceil(Math.max(...ys)), 0, height - 1);

  for (let y = minY; y <= maxY; y += spacing) {
    for (let x = minX; x <= maxX; x += spacing) {
      if (pointInPolygon(x, y, polygon)) {
        points.push([Math.round(x), Math.round(y)]);
      }
    }
  }
  return points;
}

function gaussianKernel1D(sigma) {
  const safeSigma = Math.max(0.5, sigma);
  const radius = Math.max(1, Math.ceil(safeSigma * 2));
  const kernel = [];
  let total = 0;
  for (let i = -radius; i <= radius; i += 1) {
    const value = Math.exp(-(i * i) / (2 * safeSigma * safeSigma));
    kernel.push(value);
    total += value;
  }
  return kernel.map((value) => value / total);
}

function blurField(field, width, height, sigma) {
  const kernel = gaussianKernel1D(sigma);
  const radius = Math.floor(kernel.length / 2);
  const temp = new Float32Array(field.length);
  const out = new Float32Array(field.length);

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      let sum = 0;
      for (let k = -radius; k <= radius; k += 1) {
        const sampleX = clamp(x + k, 0, width - 1);
        sum += field[y * width + sampleX] * kernel[k + radius];
      }
      temp[y * width + x] = sum;
    }
  }

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      let sum = 0;
      for (let k = -radius; k <= radius; k += 1) {
        const sampleY = clamp(y + k, 0, height - 1);
        sum += temp[sampleY * width + x] * kernel[k + radius];
      }
      out[y * width + x] = sum;
    }
  }

  return out;
}

function heatColor(value, alpha) {
  const v = clamp(value, 0, 1);
  const r = clamp(255 * Math.min(1, v * 1.6), 0, 255);
  const g = clamp(255 * Math.min(1, Math.max(0, (v - 0.15) * 1.35)), 0, 255);
  const b = clamp(255 * Math.max(0, 1 - v * 1.4), 0, 255);
  return [r, g, b, alpha];
}

function renderPolygonDemo(canvas, polygon, params) {
  const width = 256;
  const height = 256;
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, width, height);

  const shrunk = shrinkPolygon(polygon, params.distance, params.min_area_ratio);
  const samples = samplePolygonPoints(
    shrunk,
    Math.max(params.spacing, 1),
    width,
    height
  );
  const field = new Float32Array(width * height);
  samples.forEach(([x, y]) => {
    field[y * width + x] = 1;
  });

  const sigma = Math.max(params.sigma_min, params.distance * params.sigma_scale * 0.12);
  const blurred = blurField(field, width, height, sigma);
  let max = 0;
  for (let i = 0; i < blurred.length; i += 1) {
    if (blurred[i] > max) {
      max = blurred[i];
    }
  }

  const image = ctx.createImageData(width, height);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const idx = y * width + x;
      const offset = idx * 4;
      image.data[offset] = 248;
      image.data[offset + 1] = 244;
      image.data[offset + 2] = 236;
      image.data[offset + 3] = 255;

      const normalized = max > 0 ? blurred[idx] / max : 0;
      if (normalized > 0.015) {
        const [r, g, b, a] = heatColor(normalized, 255 * params.alpha);
        image.data[offset] = r;
        image.data[offset + 1] = g;
        image.data[offset + 2] = b;
        image.data[offset + 3] = a;
      }
    }
  }
  ctx.putImageData(image, 0, 0);

  ctx.strokeStyle = "#111";
  ctx.lineWidth = 3;
  ctx.beginPath();
  polygon.forEach(([x, y], index) => {
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.closePath();
  ctx.stroke();
}

function renderDemo() {
  const stage = qs("#demo-stage");
  stage.innerHTML = "";
  demoShapes.forEach((shape) => {
    const tile = document.createElement("article");
    tile.className = "demo-tile";

    const label = document.createElement("p");
    label.className = "demo-label";
    label.textContent = shape.name;

    const canvasWrap = document.createElement("div");
    canvasWrap.className = "demo-canvas-wrap";
    const canvas = document.createElement("canvas");
    canvasWrap.append(canvas);

    tile.append(label, canvasWrap);
    stage.append(tile);

    renderPolygonDemo(canvas, shape.points, state.params);
  });
}

async function fetchConfig() {
  const response = await fetch("/api/config");
  if (!response.ok) {
    throw new Error("Failed to load demo configuration.");
  }
  state.config = await response.json();
  state.params = { ...state.config.defaults };
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const value = String(reader.result || "");
      resolve(value.split(",")[1] || "");
    };
    reader.onerror = () => reject(new Error(`Failed to read ${file.name}`));
    reader.readAsDataURL(file);
  });
}

function setFileState(kind, file) {
  if (kind === "image") {
    state.imageFile = file;
    qs("#image-file-name").textContent = file ? file.name : "尚未选择图片";
  } else {
    state.jsonFile = file;
    qs("#json-file-name").textContent = file ? file.name : "尚未选择 JSON";
  }
}

function setStatus({ label, progress, error, logs, overlayUrl, status }) {
  qs("#status-label").textContent = label || "Idle";
  qs("#progress-text").textContent = `${progress || 0}%`;
  qs("#progress-fill").style.width = `${progress || 0}%`;

  const errorText = qs("#error-text");
  if (error) {
    errorText.hidden = false;
    errorText.textContent = error;
  } else {
    errorText.hidden = true;
    errorText.textContent = "";
  }

  qs("#log-output").textContent =
    logs && logs.length ? logs.join("\n") : "暂无日志。";

  const resultStage = qs("#result-stage");
  if (overlayUrl && status === "completed") {
    resultStage.classList.remove("empty");
    resultStage.innerHTML = "";
    const img = document.createElement("img");
    img.alt = "Overlay result";
    img.src = `${overlayUrl}?t=${Date.now()}`;
    resultStage.append(img);
  } else if (status !== "running" && status !== "completed") {
    resultStage.classList.add("empty");
    resultStage.innerHTML = '<p class="empty-copy">尚未运行。结果将显示在这里。</p>';
  }
}

async function pollTask(taskId) {
  const response = await fetch(`/api/tasks/${taskId}`);
  if (!response.ok) {
    throw new Error("Failed to query task status.");
  }
  const payload = await response.json();
  setStatus({
    label: payload.stepLabel,
    progress: payload.progress,
    error: payload.error,
    logs: payload.logs,
    overlayUrl: payload.overlayUrl,
    status: payload.status,
  });

  if (payload.status === "running" || payload.status === "queued") {
    state.pollTimer = window.setTimeout(() => {
      pollTask(taskId).catch((error) => {
        setStatus({ label: "Polling failed", progress: 0, error: error.message, logs: [] });
        qs("#run-button").disabled = false;
      });
    }, 700);
    return;
  }

  qs("#run-button").disabled = false;
}

async function runPipeline() {
  if (!state.imageFile || !state.jsonFile) {
    setStatus({
      label: "Validation failed",
      progress: 0,
      error: "必须同时选择图片和 JSON 文件。",
      logs: [],
      status: "failed",
    });
    return;
  }

  const imageStem = state.imageFile.name.replace(/\.[^.]+$/, "");
  const jsonStem = state.jsonFile.name.replace(/\.[^.]+$/, "");
  if (imageStem !== jsonStem) {
    setStatus({
      label: "Validation failed",
      progress: 0,
      error: "图片和 JSON 文件名必须同名。",
      logs: [],
      status: "failed",
    });
    return;
  }

  qs("#run-button").disabled = true;
  setStatus({
    label: "Uploading files",
    progress: 3,
    error: "",
    logs: ["Preparing request..."],
    status: "running",
  });

  try {
    const [imageContent, jsonContent] = await Promise.all([
      fileToBase64(state.imageFile),
      fileToBase64(state.jsonFile),
    ]);

    const response = await fetch("/api/run", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        image: {
          name: state.imageFile.name,
          content: imageContent,
        },
        annotation: {
          name: state.jsonFile.name,
          content: jsonContent,
        },
        params: state.params,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Run request failed.");
    }

    state.taskId = payload.taskId;
    if (state.pollTimer) {
      window.clearTimeout(state.pollTimer);
    }
    pollTask(state.taskId).catch((error) => {
      setStatus({
        label: "Polling failed",
        progress: 0,
        error: error.message,
        logs: [],
        status: "failed",
      });
      qs("#run-button").disabled = false;
    });
  } catch (error) {
    setStatus({
      label: "Request failed",
      progress: 0,
      error: error.message,
      logs: [],
      status: "failed",
    });
    qs("#run-button").disabled = false;
  }
}

function bindEvents() {
  qs("#image-input").addEventListener("change", (event) => {
    setFileState("image", event.target.files[0] || null);
  });
  qs("#json-input").addEventListener("change", (event) => {
    setFileState("json", event.target.files[0] || null);
  });
  qs("#run-button").addEventListener("click", () => {
    runPipeline();
  });
}

async function bootstrap() {
  await fetchConfig();
  renderFields();
  renderDemo();
  bindEvents();
}

bootstrap().catch((error) => {
  setStatus({
    label: "Initialization failed",
    progress: 0,
    error: error.message,
    logs: [],
    status: "failed",
  });
});
