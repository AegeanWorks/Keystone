import { SceneViewer } from "/viewer.js";

const elements = {
  game: document.getElementById("game"),
  status: document.getElementById("status"),
  frames: document.getElementById("frames"),
  actions: document.getElementById("actions"),
  step: document.getElementById("step"),
  run: document.getElementById("run"),
  simulate: document.getElementById("simulate"),
  refresh: document.getElementById("refresh"),
  hierarchy: document.getElementById("hierarchy"),
  prefabName: document.getElementById("prefab-name"),
  prefabInstance: document.getElementById("prefab-instance"),
  prefabSave: document.getElementById("prefab-save"),
  prefabInsert: document.getElementById("prefab-insert"),
  position: document.getElementById("position"),
  rotation: document.getElementById("rotation"),
  scale: document.getElementById("scale"),
  transformApply: document.getElementById("transform-apply"),
  editorRefresh: document.getElementById("editor-refresh"),
  editorState: document.getElementById("editor-state"),
  summary: document.getElementById("summary"),
  output: document.getElementById("output"),
  canvas: document.getElementById("canvas"),
  viewerStatus: document.getElementById("viewer-status"),
  hud: document.getElementById("hud"),
};

let viewer = null;
let busy = false;
let editorState = null;

try {
  viewer = new SceneViewer(elements.canvas);
} catch (error) {
  elements.viewerStatus.textContent = `Viewer unavailable: ${error.message}`;
}

function setStatus(message, kind = "") {
  elements.status.textContent = message;
  if (kind) {
    elements.status.dataset.kind = kind;
  } else {
    delete elements.status.dataset.kind;
  }
}

function show(value) {
  elements.output.textContent = JSON.stringify(value, null, 2);
}

function setBusy(value) {
  busy = value;
  for (const button of [
    elements.step, elements.run, elements.simulate, elements.refresh,
    elements.prefabSave, elements.prefabInsert, elements.transformApply, elements.editorRefresh,
  ]) {
    button.disabled = value;
  }
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const text = await response.text();
  let payload;
  try {
    payload = text ? JSON.parse(text) : {};
  } catch {
    throw new Error(`${path}: response was not JSON`);
  }
  if (!response.ok) {
    throw new Error(payload.error || `${path}: HTTP ${response.status}`);
  }
  return payload;
}

function triangleCount(scene) {
  return (scene.nodes || []).reduce((total, node) => {
    if (!node.visible || !node.mesh) {
      return total;
    }
    const mesh = (scene.meshes || {})[node.mesh];
    return total + Math.floor(((mesh && mesh.indices) || []).length / 3);
  }, 0);
}

function showScene(scene) {
  if (viewer) {
    viewer.loadScene(scene);
  }
  const triangles = triangleCount(scene);
  elements.summary.textContent =
    `${scene.node_count} nodes · ${scene.mesh_count} meshes · ` +
    `${scene.texture_count} textures · ${triangles} triangles`;
  elements.hud.textContent =
    `${scene.game.toUpperCase()} · ${scene.node_count} NODES · ${triangles} TRIS`;
}

async function refreshScene(display) {
  const scene = await api("/api/scene");
  showScene(scene);
  if (display) {
    show({
      schema: scene.schema,
      game: scene.game,
      node_count: scene.node_count,
      mesh_count: scene.mesh_count,
      texture_count: scene.texture_count,
      camera: scene.camera,
      light: scene.light,
    });
  }
  return scene;
}

function editorSummary(editor) {
  return {
    schema: editor.schema,
    game: editor.game,
    roots: editor.roots,
    node_count: editor.nodes.length,
    selection: editor.selection
      ? { id: editor.selection.id, name: editor.selection.name, transform: editor.selection.transform }
      : null,
    prefabs: editor.prefabs,
    actions: editor.actions,
  };
}

function renderHierarchy(editor) {
  const byId = new Map(editor.nodes.map((node) => [node.id, node]));
  elements.hierarchy.replaceChildren();
  for (const node of editor.nodes) {
    let depth = 0;
    let current = node;
    while (current.parent_id && byId.has(current.parent_id) && depth < 64) {
      depth += 1;
      current = byId.get(current.parent_id);
    }
    const option = document.createElement("option");
    option.value = node.id;
    option.textContent = `${"  ".repeat(depth)}${node.name || "(root)"} · ${node.id}`;
    elements.hierarchy.append(option);
  }
  if (editor.selection) {
    elements.hierarchy.value = editor.selection.id;
  }
}

function fillTransform(selection) {
  if (!selection) {
    elements.position.value = "0, 0, 0";
    elements.rotation.value = "0, 0, 0, 1";
    elements.scale.value = "1, 1, 1";
    return;
  }
  elements.position.value = selection.transform.position.join(", ");
  elements.rotation.value = selection.transform.rotation.join(", ");
  elements.scale.value = selection.transform.scale.join(", ");
}

function showEditor(editor) {
  editorState = editor;
  renderHierarchy(editor);
  fillTransform(editor.selection);
  elements.editorState.textContent =
    `${editor.nodes.length} nodes · ${editor.prefabs.length} prefabs · ` +
    `selected ${editor.selection ? editor.selection.id : "none"}`;
}

async function refreshEditor(display) {
  const editor = await api("/api/editor");
  showEditor(editor);
  if (display) {
    show(editorSummary(editor));
  }
  return editor;
}

async function editorAction(payload, label) {
  setStatus(label, "busy");
  const editor = await api("/api/editor", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  showEditor(editor);
  show({ ok: true, action: payload.action, editor: editorSummary(editor) });
  setStatus("ready");
  return editor;
}

function readVector(id, length, label) {
  const values = elements[id].value
    .split(/[,\s]+/)
    .filter(Boolean)
    .map(Number);
  if (values.length !== length || values.some((value) => !Number.isFinite(value))) {
    throw new Error(`${label} must contain ${length} finite numbers.`);
  }
  return values;
}

async function selectNode(nodeId) {
  await editorAction({ action: "select", id: nodeId }, "selecting node");
}

async function applyTransform() {
  if (!editorState || !editorState.selection) {
    throw new Error("Select a node before editing its transform.");
  }
  const payload = {
    action: "transform",
    id: editorState.selection.id,
    position: readVector("position", 3, "Position"),
    rotation: readVector("rotation", 4, "Rotation"),
    scale: readVector("scale", 3, "Scale"),
  };
  await editorAction(payload, "applying transform");
  await refreshScene(false);
}

async function savePrefab() {
  if (!editorState || !editorState.selection) {
    throw new Error("Select a node before saving a prefab.");
  }
  const name = elements.prefabName.value.trim() || editorState.selection.id;
  await editorAction({ action: "save_prefab", name }, "saving prefab");
}

async function insertPrefab() {
  const name = elements.prefabName.value.trim();
  if (!name) {
    throw new Error("Enter the name of a saved prefab.");
  }
  const instance = elements.prefabInstance.value.trim() || null;
  await editorAction({ action: "insert_prefab", name, instance }, "inserting prefab");
  await refreshScene(false);
}

function readActions() {
  let parsed;
  try {
    parsed = JSON.parse(elements.actions.value || "[]");
  } catch (error) {
    throw new Error(`Actions JSON: ${error.message}`);
  }
  if (!Array.isArray(parsed)) {
    throw new Error("Actions JSON must be a list.");
  }
  return parsed;
}

function readFrames(fallback) {
  if (fallback !== undefined) {
    return fallback;
  }
  const value = Number.parseInt(elements.frames.value, 10);
  if (!Number.isInteger(value) || value < 0 || value > 100000) {
    throw new Error("Frames must be an integer between 0 and 100000.");
  }
  return value;
}

async function simulate(frames) {
  const count = readFrames(frames);
  const actions = readActions();
  setStatus(`simulating ${count} frame${count === 1 ? "" : "s"}`, "busy");
  const result = await api("/api/simulate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ frames: count, actions }),
  });
  show({
    ok: result.ok,
    game: result.game,
    frames: result.frames,
    step: result.step,
    hash: result.hash,
    final: result.final,
  });
  await refreshScene(false);
  await refreshEditor(false);
  setStatus("ready");
  return result;
}

async function run(action) {
  if (busy) {
    return;
  }
  setBusy(true);
  try {
    await action();
  } catch (error) {
    setStatus(error.message, "error");
    show({ ok: false, error: error.message });
  } finally {
    setBusy(false);
  }
}

async function init() {
  setStatus("connecting", "busy");
  try {
    const description = await api("/api/describe");
    elements.game.textContent = description.game;
    const scene = await refreshScene(false);
    await refreshEditor(false);
    show({
      schema: description.schema,
      game: description.game,
      actions: description.actions,
      capabilities: description.capabilities,
      snapshot: description.snapshot,
      scene: {
        schema: scene.schema,
        node_count: scene.node_count,
        mesh_count: scene.mesh_count,
        texture_count: scene.texture_count,
      },
    });
    setStatus("ready");
  } catch (error) {
    setStatus(error.message, "error");
    show({ ok: false, error: error.message });
  }
}

elements.step.addEventListener("click", () => run(() => simulate(1)));
elements.run.addEventListener("click", () => run(() => simulate(60)));
elements.simulate.addEventListener("click", () => run(() => simulate()));
elements.refresh.addEventListener("click", () => run(() => refreshScene(true)));
elements.editorRefresh.addEventListener("click", () => run(() => refreshEditor(true)));
elements.hierarchy.addEventListener("change", () => run(() => selectNode(elements.hierarchy.value)));
elements.transformApply.addEventListener("click", () => run(applyTransform));
elements.prefabSave.addEventListener("click", () => run(savePrefab));
elements.prefabInsert.addEventListener("click", () => run(insertPrefab));

init();
