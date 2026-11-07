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
  nodeName: document.getElementById("node-name"),
  nodeParent: document.getElementById("node-parent"),
  playStart: document.getElementById("play-start"),
  playStep: document.getElementById("play-step"),
  playStop: document.getElementById("play-stop"),
  playFrames: document.getElementById("play-frames"),
  playActions: document.getElementById("play-actions"),
  playState: document.getElementById("play-state"),
  nodeCreate: document.getElementById("node-create"),
  nodeDuplicate: document.getElementById("node-duplicate"),
  nodeDelete: document.getElementById("node-delete"),
  nodeReparent: document.getElementById("node-reparent"),
  nodeVisible: document.getElementById("node-visible"),
  nodeTags: document.getElementById("node-tags"),
  nodeLayer: document.getElementById("node-layer"),
  nodeProperties: document.getElementById("node-properties"),
  editorUndo: document.getElementById("editor-undo"),
  editorRedo: document.getElementById("editor-redo"),
  sceneName: document.getElementById("scene-name"),
  sceneNames: document.getElementById("scene-names"),
  sceneNewName: document.getElementById("scene-new-name"),
  sceneSave: document.getElementById("scene-save"),
  sceneLoad: document.getElementById("scene-load"),
  sceneRename: document.getElementById("scene-rename"),
  sceneDelete: document.getElementById("scene-delete"),
  prefabName: document.getElementById("prefab-name"),
  prefabNames: document.getElementById("prefab-names"),
  prefabNewName: document.getElementById("prefab-new-name"),
  prefabInstance: document.getElementById("prefab-instance"),
  prefabSave: document.getElementById("prefab-save"),
  prefabInsert: document.getElementById("prefab-insert"),
  prefabRename: document.getElementById("prefab-rename"),
  prefabDelete: document.getElementById("prefab-delete"),
  position: document.getElementById("position"),
  rotation: document.getElementById("rotation"),
  scale: document.getElementById("scale"),
  transformApply: document.getElementById("transform-apply"),
  meshAsset: document.getElementById("mesh-asset"),
  materialAsset: document.getElementById("material-asset"),
  assignAsset: document.getElementById("assign-asset"),
  assetInfo: document.getElementById("asset-info"),
  componentType: document.getElementById("component-type"),
  componentFields: document.getElementById("component-fields"),
  componentHint: document.getElementById("component-hint"),
  componentData: document.getElementById("component-data"),
  componentSet: document.getElementById("component-set"),
  componentRemove: document.getElementById("component-remove"),
  editorRefresh: document.getElementById("editor-refresh"),
  editorState: document.getElementById("editor-state"),
  summary: document.getElementById("summary"),
  output: document.getElementById("output"),
  canvas: document.getElementById("canvas"),
  viewerStatus: document.getElementById("viewer-status"),
  viewReset: document.getElementById("view-reset"),
  viewFocus: document.getElementById("view-focus"),
  hud: document.getElementById("hud"),
};

let viewer = null;
let busy = false;
let editorState = null;

try {
  viewer = new SceneViewer(elements.canvas);
  viewer.onSelect = (nodeId) => run(() => selectNode(nodeId));
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
    elements.nodeCreate, elements.nodeDuplicate, elements.nodeDelete, elements.nodeReparent,
    elements.nodeProperties,
    elements.sceneSave, elements.sceneLoad, elements.sceneRename, elements.sceneDelete,
    elements.assignAsset, elements.playStart, elements.playStep, elements.playStop,
    elements.componentSet, elements.componentRemove,
    elements.prefabSave, elements.prefabInsert, elements.prefabRename, elements.prefabDelete,
    elements.transformApply, elements.editorRefresh,
  ]) {
    button.disabled = value;
  }
  if (value) {
    elements.editorUndo.disabled = true;
    elements.editorRedo.disabled = true;
  } else {
    const history = (editorState && editorState.history) || { undo: 0, redo: 0 };
    elements.editorUndo.disabled = history.undo === 0;
    elements.editorRedo.disabled = history.redo === 0;
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
    scenes: editor.scenes,
    assets: (editor.assets || []).length,
    component_types: editor.component_types,
    play: editor.play,
    actions: editor.actions,
    history: editor.history,
  };
}

function nodeDepth(node, byId) {
  let depth = 0;
  let current = node;
  while (current.parent_id && byId.has(current.parent_id) && depth < 64) {
    depth += 1;
    current = byId.get(current.parent_id);
  }
  return depth;
}

function renderParentOptions(editor, byId) {
  const previous = elements.nodeParent.value || "root";
  elements.nodeParent.replaceChildren();
  const rootOption = document.createElement("option");
  rootOption.value = "root";
  rootOption.textContent = "Scene root";
  elements.nodeParent.append(rootOption);
  for (const node of editor.nodes) {
    const option = document.createElement("option");
    option.value = node.id;
    option.textContent =
      `${"  ".repeat(nodeDepth(node, byId))}${node.name || node.id} · ${node.id}`;
    elements.nodeParent.append(option);
  }
  elements.nodeParent.value = Array.from(elements.nodeParent.options)
    .some((option) => option.value === previous) ? previous : "root";
}

function renderHierarchy(editor) {
  const byId = new Map(editor.nodes.map((node) => [node.id, node]));
  elements.hierarchy.replaceChildren();
  for (const node of editor.nodes) {
    const option = document.createElement("option");
    option.value = node.id;
    option.textContent =
      `${"  ".repeat(nodeDepth(node, byId))}${node.name || "(root)"} · ${node.id}`;
    elements.hierarchy.append(option);
  }
  if (editor.selection) {
    elements.hierarchy.value = editor.selection.id;
  }
  renderParentOptions(editor, byId);
}

function fillDatalist(list, entries) {
  list.replaceChildren();
  for (const entry of entries) {
    const option = document.createElement("option");
    option.value = entry.name;
    option.label = entry.error
      ? `${entry.name} (error)`
      : `${entry.name} · ${entry.node_count ?? "?"} nodes`;
    list.append(option);
  }
}

function renderLibraryOptions(editor) {
  fillDatalist(elements.sceneNames, editor.scenes || []);
  fillDatalist(elements.prefabNames, editor.prefabs || []);
}

function fillAssetSelect(select, kind, assets) {
  const previous = select.value;
  select.replaceChildren();
  const none = document.createElement("option");
  none.value = "";
  none.textContent = "(none)";
  select.append(none);
  for (const asset of assets.filter((item) => item.kind === kind)) {
    const option = document.createElement("option");
    option.value = asset.id;
    option.textContent = `${asset.id} · ${asset.kind}`;
    select.append(option);
  }
  select.value = Array.from(select.options).some((option) => option.value === previous)
    ? previous
    : "";
}

function renderAssets(editor) {
  const assets = editor.assets || [];
  fillAssetSelect(elements.meshAsset, "mesh", assets);
  fillAssetSelect(elements.materialAsset, "material", assets);
}

function fillAssets(selection) {
  elements.meshAsset.value = selection ? selection.mesh || "" : "";
  elements.materialAsset.value = selection ? selection.material || "" : "";
}

function assetSummary(assetId) {
  const assets = (editorState && editorState.assets) || [];
  const asset = assets.find((item) => item.id === assetId);
  if (!asset) {
    return null;
  }
  return `${asset.id} · ${asset.kind}\n${JSON.stringify(asset.metadata || {}, null, 2)}`;
}

function updateAssetInfo() {
  const summaries = [elements.meshAsset.value, elements.materialAsset.value]
    .filter(Boolean)
    .map(assetSummary)
    .filter(Boolean);
  elements.assetInfo.textContent = summaries.length
    ? summaries.join("\n\n")
    : "No registry assets selected.";
}

function renderComponentTypes(editor) {
  const previous = elements.componentType.value;
  elements.componentType.replaceChildren();
  for (const name of editor.component_types || []) {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    elements.componentType.append(option);
  }
  const values = Array.from(elements.componentType.options).map((option) => option.value);
  elements.componentType.value = values.includes(previous)
    ? previous
    : values[0] || "";
}

const COMPONENT_INPUTS = {
  int: { type: "number", step: "1" },
  float: { type: "number", step: "any" },
  str: { type: "text" },
  bool: { type: "checkbox" },
};

function componentDataFor(selection) {
  const documents = (selection && selection.component_data) || [];
  return (
    documents.find(
      (item) => item.type === elements.componentType.value && !item.error,
    ) || null
  );
}

function componentFieldValue(entry, field) {
  if (
    entry &&
    entry.data &&
    Object.prototype.hasOwnProperty.call(entry.data, field.name)
  ) {
    return entry.data[field.name];
  }
  if (
    field.default !== null &&
    field.default !== undefined &&
    field.default !== "<factory>"
  ) {
    return field.default;
  }
  return field.type === "bool" ? false : "";
}

function renderComponentFields(editor, selection) {
  const type = elements.componentType.value;
  const schema =
    (editor && editor.component_schemas && editor.component_schemas[type]) || null;
  const fields = (schema && schema.fields) || [];
  const entry = componentDataFor(selection);
  elements.componentFields.replaceChildren();
  if (!fields.length) {
    elements.componentHint.textContent =
      (schema && schema.note) || "Custom codec: edit the JSON data.";
    return;
  }
  elements.componentHint.textContent =
    "Typed fields for dataclass components; use JSON for other constructors.";
  for (const field of fields) {
    const label = document.createElement("label");
    label.textContent = field.name;
    const input = document.createElement("input");
    const spec = COMPONENT_INPUTS[field.type];
    input.dataset.fieldName = field.name;
    input.dataset.fieldType = field.type;
    if (spec) {
      input.type = spec.type;
      if (spec.step) {
        input.step = spec.step;
      }
    } else {
      input.type = "text";
    }
    const value = componentFieldValue(entry, field);
    if (field.type === "bool") {
      input.checked = Boolean(value);
    } else {
      input.value = value === null ? "" : String(value);
    }
    label.append(input);
    elements.componentFields.append(label);
  }
}

function readComponentFields() {
  const data = {};
  for (const input of elements.componentFields.querySelectorAll(
    "input[data-field-name]",
  )) {
    const name = input.dataset.fieldName;
    const type = input.dataset.fieldType;
    if (type === "bool") {
      data[name] = input.checked;
    } else if (type === "int") {
      if (input.value.trim() === "") {
        throw new Error(`${name} is required.`);
      }
      const value = Number(input.value);
      if (!Number.isInteger(value)) {
        throw new Error(`${name} must be an integer.`);
      }
      data[name] = value;
    } else if (type === "float") {
      if (input.value.trim() === "") {
        throw new Error(`${name} is required.`);
      }
      const value = Number(input.value);
      if (!Number.isFinite(value)) {
        throw new Error(`${name} must be a finite number.`);
      }
      data[name] = value;
    } else if (type === "str") {
      data[name] = input.value;
    } else {
      try {
        data[name] = JSON.parse(input.value);
      } catch (error) {
        throw new Error(`${name}: ${error.message}`);
      }
    }
  }
  return data;
}

function fillComponentData(selection) {
  const selected = componentDataFor(selection);
  elements.componentData.value = selected
    ? JSON.stringify(selected.data, null, 2)
    : "{}";
}

function fillNodeProperties(selection) {
  elements.nodeName.value = selection ? selection.name : "node";
  elements.nodeVisible.checked = selection ? selection.visible : true;
  elements.nodeTags.value = selection ? selection.tags.join(", ") : "";
  elements.nodeLayer.value = selection ? selection.layer : "default";
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
  if (viewer) {
    viewer.setSelected(editor.selection ? editor.selection.id : null);
  }
  renderHierarchy(editor);
  renderLibraryOptions(editor);
  renderAssets(editor);
  renderComponentTypes(editor);
  fillNodeProperties(editor.selection);
  fillTransform(editor.selection);
  fillAssets(editor.selection);
  updateAssetInfo();
  fillComponentData(editor.selection);
  renderComponentFields(editor, editor.selection);
  const history = editor.history || { undo: 0, redo: 0 };
  const play = editor.play || { active: false, frames: 0 };
  elements.playState.textContent = play.active
    ? `Playing · ${play.frames} frames`
    : "Stopped";
  elements.editorState.textContent =
    `${editor.nodes.length} nodes · ${editor.prefabs.length} prefabs · ` +
    `undo ${history.undo} / redo ${history.redo} · ` +
    `selected ${editor.selection ? editor.selection.id : "none"}`;
  if (!busy) {
    elements.editorUndo.disabled = history.undo === 0;
    elements.editorRedo.disabled = history.redo === 0;
  }
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

async function renamePrefab() {
  const name = elements.prefabName.value.trim();
  const newName = elements.prefabNewName.value.trim();
  if (!name || !newName) {
    throw new Error("Enter the current and new prefab names.");
  }
  await editorAction(
    { action: "rename_prefab", name, new_name: newName },
    "renaming prefab",
  );
  elements.prefabName.value = newName;
}

async function deletePrefab() {
  const name = elements.prefabName.value.trim();
  if (!name) {
    throw new Error("Enter the prefab name to delete.");
  }
  await editorAction({ action: "delete_prefab", name }, "deleting prefab");
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

async function playStart() {
  await editorAction({ action: "play_start" }, "starting play");
}

async function playStep() {
  const frames = Number.parseInt(elements.playFrames.value, 10);
  if (!Number.isInteger(frames) || frames < 1 || frames > 10000) {
    throw new Error("Play frames must be an integer between 1 and 10000.");
  }
  let actions;
  try {
    actions = JSON.parse(elements.playActions.value || "[]");
  } catch (error) {
    throw new Error(`Play actions JSON: ${error.message}`);
  }
  if (!Array.isArray(actions)) {
    throw new Error("Play actions JSON must be a list.");
  }
  await editorAction(
    { action: "play_step", frames, actions },
    "stepping play",
  );
  await refreshScene(false);
}

async function playStop() {
  await editorAction({ action: "play_stop" }, "stopping play");
  await refreshScene(false);
}

async function applyNodeProperties() {
  if (!editorState || !editorState.selection) {
    throw new Error("Select a node before editing its properties.");
  }
  const name = elements.nodeName.value.trim();
  if (!name) {
    throw new Error("Node name must be non-blank.");
  }
  const tags = elements.nodeTags.value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
  const layer = elements.nodeLayer.value.trim() || "default";
  await editorAction(
    {
      action: "set_node",
      id: editorState.selection.id,
      name,
      visible: elements.nodeVisible.checked,
      tags,
      layer,
    },
    "applying node properties",
  );
  await refreshScene(false);
}

async function assignAssets() {
  if (!editorState || !editorState.selection) {
    throw new Error("Select a node before assigning assets.");
  }
  const mesh = elements.meshAsset.value || null;
  const material = elements.materialAsset.value || null;
  await editorAction(
    { action: "assign_asset", id: editorState.selection.id, mesh, material },
    "assigning assets",
  );
  await refreshScene(false);
}

async function setComponent() {
  if (!editorState || !editorState.selection) {
    throw new Error("Select a node before editing components.");
  }
  const type = elements.componentType.value;
  if (!type) {
    throw new Error("The game exposes no component types.");
  }
  let data;
  if (elements.componentFields.querySelector("input[data-field-name]")) {
    data = readComponentFields();
  } else {
    try {
      data = JSON.parse(elements.componentData.value || "null");
    } catch (error) {
      throw new Error(`Component data JSON: ${error.message}`);
    }
  }
  await editorAction(
    { action: "set_component", id: editorState.selection.id, type, data },
    "setting component",
  );
  await refreshScene(false);
}

async function removeComponent() {
  if (!editorState || !editorState.selection) {
    throw new Error("Select a node before editing components.");
  }
  const type = elements.componentType.value;
  if (!type) {
    throw new Error("The game exposes no component types.");
  }
  await editorAction(
    { action: "remove_component", id: editorState.selection.id, type },
    "removing component",
  );
  await refreshScene(false);
}

async function saveScene() {
  const name = elements.sceneName.value.trim() || "scene";
  await editorAction({ action: "save_scene", name }, "saving scene");
}

async function renameScene() {
  const name = elements.sceneName.value.trim();
  const newName = elements.sceneNewName.value.trim();
  if (!name || !newName) {
    throw new Error("Enter the current and new scene names.");
  }
  await editorAction(
    { action: "rename_scene", name, new_name: newName },
    "renaming scene",
  );
  elements.sceneName.value = newName;
}

async function deleteScene() {
  const name = elements.sceneName.value.trim();
  if (!name) {
    throw new Error("Enter the scene name to delete.");
  }
  await editorAction({ action: "delete_scene", name }, "deleting scene");
}

async function loadScene() {
  const name = elements.sceneName.value.trim();
  if (!name) {
    throw new Error("Enter the name of a saved scene.");
  }
  await editorAction({ action: "load_scene", name }, "loading scene");
  await refreshScene(false);
}

async function createNode() {
  const name = elements.nodeName.value.trim() || "node";
  const parent = elements.nodeParent.value || "root";
  await editorAction({ action: "create_node", name, parent }, "creating node");
  await refreshScene(false);
}

async function duplicateNode() {
  if (!editorState || !editorState.selection) {
    throw new Error("Select a node before duplicating it.");
  }
  const selected = editorState.selection;
  const name = `${selected.name || "node"} copy`;
  await editorAction({ action: "duplicate_node", id: selected.id, name }, "duplicating node");
  await refreshScene(false);
}

async function deleteNode() {
  if (!editorState || !editorState.selection) {
    throw new Error("Select a node before deleting it.");
  }
  await editorAction(
    { action: "delete_node", id: editorState.selection.id },
    "deleting node",
  );
  await refreshScene(false);
}

async function reparentNode() {
  if (!editorState || !editorState.selection) {
    throw new Error("Select a node before reparenting it.");
  }
  const parent = elements.nodeParent.value || "root";
  await editorAction(
    { action: "reparent_node", id: editorState.selection.id, parent },
    "reparenting node",
  );
  await refreshScene(false);
}

async function undoEditor() {
  await editorAction({ action: "undo" }, "undoing editor action");
  await refreshScene(false);
}

async function redoEditor() {
  await editorAction({ action: "redo" }, "redoing editor action");
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

function isEditingTarget(target) {
  const tag = target && target.tagName;
  return (
    tag === "INPUT" ||
    tag === "TEXTAREA" ||
    tag === "SELECT" ||
    Boolean(target && target.isContentEditable)
  );
}

document.addEventListener("keydown", (event) => {
  if (isEditingTarget(event.target) || !editorState) {
    return;
  }
  const modifier = event.ctrlKey || event.metaKey;
  const key = event.key.toLowerCase();
  if (modifier && key === "z") {
    event.preventDefault();
    run(() => (event.shiftKey ? redoEditor() : undoEditor()));
    return;
  }
  if (modifier && key === "y") {
    event.preventDefault();
    run(redoEditor);
    return;
  }
  if (event.key === "Delete" && editorState.selection) {
    event.preventDefault();
    run(deleteNode);
    return;
  }
  if (key === "f" && editorState.selection && viewer) {
    event.preventDefault();
    viewer.focusNode(editorState.selection.id);
    return;
  }
  if (event.key === "Escape") {
    event.preventDefault();
    run(() => selectNode(null));
  }
});

elements.viewReset.addEventListener("click", () => {
  if (viewer) {
    viewer.resetCamera();
  }
});
elements.viewFocus.addEventListener("click", () => {
  if (viewer && editorState && editorState.selection) {
    viewer.focusNode(editorState.selection.id);
  }
});
elements.step.addEventListener("click", () => run(() => simulate(1)));
elements.run.addEventListener("click", () => run(() => simulate(60)));
elements.simulate.addEventListener("click", () => run(() => simulate()));
elements.refresh.addEventListener("click", () => run(() => refreshScene(true)));
elements.editorRefresh.addEventListener("click", () => run(() => refreshEditor(true)));
elements.hierarchy.addEventListener("change", () => run(() => selectNode(elements.hierarchy.value)));
elements.transformApply.addEventListener("click", () => run(applyTransform));
elements.playStart.addEventListener("click", () => run(playStart));
elements.playStep.addEventListener("click", () => run(playStep));
elements.playStop.addEventListener("click", () => run(playStop));
elements.meshAsset.addEventListener("change", updateAssetInfo);
elements.materialAsset.addEventListener("change", updateAssetInfo);
elements.assignAsset.addEventListener("click", () => run(assignAssets));
elements.componentSet.addEventListener("click", () => run(setComponent));
elements.componentRemove.addEventListener("click", () => run(removeComponent));
elements.componentType.addEventListener("change", () => {
  fillComponentData(editorState && editorState.selection);
  renderComponentFields(editorState, editorState && editorState.selection);
});
elements.nodeCreate.addEventListener("click", () => run(createNode));
elements.nodeDuplicate.addEventListener("click", () => run(duplicateNode));
elements.nodeDelete.addEventListener("click", () => run(deleteNode));
elements.nodeReparent.addEventListener("click", () => run(reparentNode));
elements.nodeProperties.addEventListener("click", () => run(applyNodeProperties));
elements.editorUndo.addEventListener("click", () => run(undoEditor));
elements.editorRedo.addEventListener("click", () => run(redoEditor));
elements.sceneSave.addEventListener("click", () => run(saveScene));
elements.sceneLoad.addEventListener("click", () => run(loadScene));
elements.sceneRename.addEventListener("click", () => run(renameScene));
elements.sceneDelete.addEventListener("click", () => run(deleteScene));
elements.prefabSave.addEventListener("click", () => run(savePrefab));
elements.prefabRename.addEventListener("click", () => run(renamePrefab));
elements.prefabDelete.addEventListener("click", () => run(deletePrefab));
elements.prefabInsert.addEventListener("click", () => run(insertPrefab));

init();
