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
  hierarchyFilter: document.getElementById("hierarchy-filter"),
  assetFilter: document.getElementById("asset-filter"),
  nodeName: document.getElementById("node-name"),
  nodeParent: document.getElementById("node-parent"),
  playStart: document.getElementById("play-start"),
  playPause: document.getElementById("play-pause"),
  playResume: document.getElementById("play-resume"),
  playStep: document.getElementById("play-step"),
  playStop: document.getElementById("play-stop"),
  playFrames: document.getElementById("play-frames"),
  playActions: document.getElementById("play-actions"),
  playState: document.getElementById("play-state"),
  playSnapshot: document.getElementById("play-snapshot"),
  animationClip: document.getElementById("animation-clip"),
  animationTime: document.getElementById("animation-time"),
  animationScrub: document.getElementById("animation-scrub"),
  animationName: document.getElementById("animation-name"),
  animationNames: document.getElementById("animation-names"),
  animationPreview: document.getElementById("animation-preview"),
  animationSample: document.getElementById("animation-sample"),
  animationPlay: document.getElementById("animation-play"),
  animationSave: document.getElementById("animation-save"),
  animationDelete: document.getElementById("animation-delete"),
  animationRestore: document.getElementById("animation-restore"),
  animationState: document.getElementById("animation-state"),
  nodeCreate: document.getElementById("node-create"),
  nodeDuplicate: document.getElementById("node-duplicate"),
  nodeDelete: document.getElementById("node-delete"),
  selectionToggleVisible: document.getElementById("selection-toggle-visible"),
  boxSelect: document.getElementById("box-select"),
  nodeReparent: document.getElementById("node-reparent"),
  nodeVisible: document.getElementById("node-visible"),
  nodeTags: document.getElementById("node-tags"),
  nodeLayer: document.getElementById("node-layer"),
  nodeProperties: document.getElementById("node-properties"),
  editorUndo: document.getElementById("editor-undo"),
  editorRedo: document.getElementById("editor-redo"),
  historySteps: document.getElementById("history-steps"),
  historyState: document.getElementById("history-state"),
  sceneName: document.getElementById("scene-name"),
  sceneNames: document.getElementById("scene-names"),
  sceneNewName: document.getElementById("scene-new-name"),
  sceneSave: document.getElementById("scene-save"),
  sceneLoad: document.getElementById("scene-load"),
  sceneRevert: document.getElementById("scene-revert"),
  sceneDirtyState: document.getElementById("scene-dirty-state"),
  sceneDiff: document.getElementById("scene-diff"),
  sceneRename: document.getElementById("scene-rename"),
  sceneDuplicate: document.getElementById("scene-duplicate"),
  sceneDelete: document.getElementById("scene-delete"),
  sceneRestore: document.getElementById("scene-restore"),
  startupSet: document.getElementById("startup-set"),
  startupClear: document.getElementById("startup-clear"),
  startupState: document.getElementById("startup-state"),
  sceneSettings: document.getElementById("scene-settings"),
  sceneSettingsApply: document.getElementById("scene-settings-apply"),
  sceneValidate: document.getElementById("scene-validate"),
  validationState: document.getElementById("validation-state"),
  cameraPosition: document.getElementById("camera-position"),
  cameraYaw: document.getElementById("camera-yaw"),
  cameraPitch: document.getElementById("camera-pitch"),
  cameraFov: document.getElementById("camera-fov"),
  cameraSettingsApply: document.getElementById("camera-settings-apply"),
  lightDirection: document.getElementById("light-direction"),
  lightColor: document.getElementById("light-color"),
  lightIntensity: document.getElementById("light-intensity"),
  ambientColor: document.getElementById("ambient-color"),
  fogDensity: document.getElementById("fog-density"),
  environmentSettingsApply: document.getElementById("environment-settings-apply"),
  shadowToggle: document.getElementById("shadow-toggle"),
  colorToggle: document.getElementById("color-toggle"),
  postToggle: document.getElementById("post-toggle"),
  bloomToggle: document.getElementById("bloom-toggle"),
  spritesToggle: document.getElementById("sprites-toggle"),
  cullingToggle: document.getElementById("culling-toggle"),
  prefabName: document.getElementById("prefab-name"),
  prefabNames: document.getElementById("prefab-names"),
  prefabNewName: document.getElementById("prefab-new-name"),
  prefabInstance: document.getElementById("prefab-instance"),
  prefabSave: document.getElementById("prefab-save"),
  prefabInsert: document.getElementById("prefab-insert"),
  prefabRevert: document.getElementById("prefab-revert"),
  prefabApply: document.getElementById("prefab-apply"),
  prefabRefresh: document.getElementById("prefab-refresh"),
  prefabLink: document.getElementById("prefab-link"),
  prefabOverrides: document.getElementById("prefab-overrides"),
  prefabRename: document.getElementById("prefab-rename"),
  prefabDuplicate: document.getElementById("prefab-duplicate"),
  prefabDelete: document.getElementById("prefab-delete"),
  prefabRestore: document.getElementById("prefab-restore"),
  prefabEditState: document.getElementById("prefab-edit-state"),
  prefabEdit: document.getElementById("prefab-edit"),
  prefabEditSave: document.getElementById("prefab-edit-save"),
  prefabEditClose: document.getElementById("prefab-edit-close"),
  prefabEditDiscard: document.getElementById("prefab-edit-discard"),
  position: document.getElementById("position"),
  rotation: document.getElementById("rotation"),
  scale: document.getElementById("scale"),
  transformApply: document.getElementById("transform-apply"),
  meshAsset: document.getElementById("mesh-asset"),
  materialAsset: document.getElementById("material-asset"),
  materialName: document.getElementById("material-name"),
  materialNames: document.getElementById("material-names"),
  materialColor: document.getElementById("material-color"),
  materialMetallic: document.getElementById("material-metallic"),
  materialRoughness: document.getElementById("material-roughness"),
  materialEmissive: document.getElementById("material-emissive"),
  materialSpecular: document.getElementById("material-specular"),
  materialShininess: document.getElementById("material-shininess"),
  materialChecker: document.getElementById("material-checker"),
  materialTexture: document.getElementById("material-texture"),
  materialSave: document.getElementById("material-save"),
  materialAssign: document.getElementById("material-assign"),
  materialClear: document.getElementById("material-clear"),
  materialDelete: document.getElementById("material-delete"),
  materialRestore: document.getElementById("material-restore"),
  materialState: document.getElementById("material-state"),
  assignAsset: document.getElementById("assign-asset"),
  assetInfo: document.getElementById("asset-info"),
  assetPreview: document.getElementById("asset-preview"),
  importPath: document.getElementById("import-path"),
  importAsset: document.getElementById("import-asset"),
  importState: document.getElementById("import-state"),
  projectAssets: document.getElementById("project-assets"),
  forgetAsset: document.getElementById("forget-asset"),
  findUsages: document.getElementById("find-usages"),
  usageState: document.getElementById("usage-state"),
  reloadAssets: document.getElementById("reload-assets"),
  reloadState: document.getElementById("reload-state"),
  buildTarget: document.getElementById("build-target"),
  buildForce: document.getElementById("build-force"),
  buildProject: document.getElementById("build-project"),
  buildState: document.getElementById("build-state"),
  componentType: document.getElementById("component-type"),
  componentFields: document.getElementById("component-fields"),
  componentHint: document.getElementById("component-hint"),
  componentData: document.getElementById("component-data"),
  componentSet: document.getElementById("component-set"),
  componentRemove: document.getElementById("component-remove"),
  editorRefresh: document.getElementById("editor-refresh"),
  editorState: document.getElementById("editor-state"),
  selectionSummary: document.getElementById("selection-summary"),
  summary: document.getElementById("summary"),
  output: document.getElementById("output"),
  canvas: document.getElementById("canvas"),
  viewerStatus: document.getElementById("viewer-status"),
  viewReset: document.getElementById("view-reset"),
  viewFocus: document.getElementById("view-focus"),
  viewMode: document.getElementById("view-mode"),
  gridToggle: document.getElementById("grid-toggle"),
  snapToggle: document.getElementById("snap-toggle"),
  snapMove: document.getElementById("snap-move"),
  snapRotate: document.getElementById("snap-rotate"),
  snapScale: document.getElementById("snap-scale"),
  projectionMode: document.getElementById("projection-mode"),
  layoutReset: document.getElementById("layout-reset"),
  gizmoMove: document.getElementById("gizmo-move"),
  gizmoRotate: document.getElementById("gizmo-rotate"),
  gizmoScale: document.getElementById("gizmo-scale"),
  gizmoSpace: document.getElementById("gizmo-space"),
  hud: document.getElementById("hud"),
};

let viewer = null;
let busy = false;
let editorState = null;
let playLoopActive = false;
let playLoopTimer = null;
let playLoopBusy = false;
let playLoopLast = 0;
let wasPlaying = false;
let layoutTimer = null;
let animationPlayActive = false;
let animationPlayTimer = null;
let animationPlayBusy = false;
let animationPlayLast = 0;
let collapsedNodes = new Set();
let lastHierarchySelection = "";
let gizmoSpace = "world";
let boxSelect = false;

try {
  viewer = new SceneViewer(elements.canvas);
  viewer.onSelect = (nodeId, modifiers) =>
    run(() => selectViewportNode(nodeId, modifiers || {}));
  viewer.onBoxSelect = (ids, mode) =>
    run(() => selectMany(ids, mode));
  viewer.onTransform = (axis, delta) =>
    run(() => applyGizmoTransform(axis, delta));
  viewer.onTransformSelection = (delta) =>
    run(() => applyGizmoSelectionTransform(delta));
  viewer.onRotate = (axis, degrees) =>
    run(() => applyGizmoRotation(axis, degrees));
  viewer.onRotateSelection = (axis, degrees, pivot) =>
    run(() => applyGizmoSelectionRotation(axis, degrees, pivot));
  viewer.onScale = (axis, factor) =>
    run(() => applyGizmoScale(axis, factor));
  viewer.onScaleSelection = (axis, factor, pivot) =>
    run(() => applyGizmoSelectionScale(axis, factor, pivot));
  viewer.onViewMode = updateViewModeButton;
  updateViewModeButton(viewer.viewMode);
  viewer.onProjectionMode = updateProjectionButton;
  updateProjectionButton(viewer.viewPreset);
  viewer.onLayoutChange = scheduleLayoutSave;
  syncSnapSteps();
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
    elements.selectionToggleVisible,
    elements.sceneSave, elements.sceneLoad, elements.sceneDiff, elements.sceneRename,
    elements.sceneDuplicate, elements.sceneDelete, elements.sceneRestore,
    elements.sceneSettingsApply, elements.cameraSettingsApply,
    elements.environmentSettingsApply, elements.sceneValidate,
    elements.assignAsset,
    elements.materialSave, elements.materialAssign, elements.materialClear,
    elements.materialDelete, elements.materialRestore,
    elements.playStart,
    elements.playPause, elements.playResume, elements.playStep, elements.playStop, elements.componentSet, elements.componentRemove,
    elements.animationPreview, elements.animationSample,
    elements.animationPlay,
    elements.animationSave, elements.animationDelete, elements.animationRestore,
    elements.prefabSave, elements.prefabInsert, elements.prefabRename,
    elements.prefabRevert, elements.prefabApply, elements.prefabRefresh,
    elements.prefabDuplicate, elements.prefabDelete, elements.prefabRestore,
    elements.prefabEdit, elements.prefabEditSave, elements.prefabEditClose,
    elements.prefabEditDiscard,
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
    updatePlayButtons(editorState && editorState.play);
    updatePrefabEditButtons(editorState && editorState.prefab_edit);
  }
}

function updatePlayButtons(play) {
  const active = Boolean(play && play.active);
  const paused = Boolean(play && play.paused);
  elements.playPause.disabled = !active || paused;
  elements.playResume.disabled = !active || !paused;
}

function updatePrefabEditButtons(prefabEdit) {
  const active = Boolean(prefabEdit);
  elements.prefabEdit.disabled = active;
  elements.prefabEditSave.disabled = !active;
  elements.prefabEditClose.disabled = !active;
  elements.prefabEditDiscard.disabled = !active;
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
      ? {
          id: editor.selection.id,
          name: editor.selection.name,
          transform: editor.selection.transform,
          prefab_link: editor.selection.prefab_link,
        }
      : null,
    selected_ids: editor.selected_ids,
    selection_count: editor.selection_count,
    prefabs: editor.prefabs,
    scenes: editor.scenes,
    scene_group_count: editor.scene_group_count,
    prefab_override_count: editor.prefab_override_count,
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

function ancestorCollapsed(node, byId) {
  let current = byId.get(node.parent_id);
  while (current) {
    if (collapsedNodes.has(current.id)) {
      return true;
    }
    current = byId.get(current.parent_id);
  }
  return false;
}

function renderHierarchy(editor) {
  const byId = new Map(editor.nodes.map((node) => [node.id, node]));
  const query = elements.hierarchyFilter.value.trim().toLowerCase();
  const selected = new Set(
    editor.selected_ids ||
      (editor.selection ? [editor.selection.id] : []),
  );
  const selectionKey = [...selected].sort().join("\u0000");
  if (selectionKey !== lastHierarchySelection) {
    for (const nodeId of selected) {
      let current = byId.get(nodeId);
      while (current && current.parent_id) {
        collapsedNodes.delete(current.parent_id);
        current = byId.get(current.parent_id);
      }
    }
    lastHierarchySelection = selectionKey;
  }
  elements.hierarchy.replaceChildren();
  let visible = 0;
  for (const node of editor.nodes) {
    if (!query && ancestorCollapsed(node, byId)) {
      continue;
    }
    if (query) {
      const haystack = [
        node.id,
        node.name,
        node.layer,
        ...(node.tags || []),
        ...(node.components || []),
        ...(node.prefab_link
          ? [node.prefab_link.name, node.prefab_link.instance]
          : []),
      ]
        .join(" ")
        .toLowerCase();
      if (!haystack.includes(query)) {
        continue;
      }
    }
    const row = document.createElement("div");
    row.className =
      "hierarchy-row" + (selected.has(node.id) ? " selected" : "");
    row.dataset.nodeId = node.id;
    row.draggable = true;
    row.setAttribute("role", "treeitem");
    const hasChildren = (node.children || []).length > 0;
    const toggle = document.createElement("span");
    toggle.className =
      "hierarchy-toggle" + (hasChildren ? "" : " hierarchy-toggle-empty");
    if (hasChildren) {
      const collapsed = collapsedNodes.has(node.id);
      toggle.textContent = collapsed ? "\u25b8" : "\u25be";
      toggle.setAttribute("role", "button");
      toggle.setAttribute("aria-label", collapsed ? "Expand" : "Collapse");
      toggle.addEventListener("click", (event) => {
        event.stopPropagation();
        if (collapsedNodes.has(node.id)) {
          collapsedNodes.delete(node.id);
        } else {
          collapsedNodes.add(node.id);
        }
        renderHierarchy(editorState);
      });
    } else {
      toggle.textContent = " ";
    }
    row.append(toggle);
    const label = document.createElement("span");
    label.className = "hierarchy-label";
    const badge = node.prefab_link
      ? ` [prefab:${node.prefab_link.name}/${node.prefab_link.instance}]`
      : "";
    label.textContent =
      `${"  ".repeat(nodeDepth(node, byId))}${node.name || "(root)"} · ${node.id}${badge}`;
    row.append(label);
    row.addEventListener("click", (event) => {
      if (event.ctrlKey || event.metaKey) {
        run(() => selectMany([node.id], "toggle"));
      } else {
        run(() => selectMany([node.id], "replace"));
      }
    });
    row.addEventListener("dragstart", (event) => {
      event.dataTransfer.setData("text/plain", node.id);
      event.dataTransfer.effectAllowed = "move";
      row.classList.add("dragging");
    });
    row.addEventListener("dragend", () => row.classList.remove("dragging"));
    row.addEventListener("dragover", (event) => {
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      row.classList.add("drag-over");
    });
    row.addEventListener("dragleave", () => row.classList.remove("drag-over"));
    row.addEventListener("drop", (event) => {
      event.preventDefault();
      row.classList.remove("drag-over");
      const dragged = event.dataTransfer.getData("text/plain");
      if (dragged && dragged !== node.id) {
        run(() => reparentNodeTo(dragged, node.id));
      }
    });
    elements.hierarchy.append(row);
    visible += 1;
  }
  if (!visible) {
    const empty = document.createElement("div");
    empty.className = "hierarchy-empty";
    empty.textContent = "No matching nodes.";
    empty.style.pointerEvents = "none";
    elements.hierarchy.append(empty);
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

function fillPathDatalist(list, paths) {
  list.replaceChildren();
  for (const path of paths) {
    const option = document.createElement("option");
    option.value = path;
    list.append(option);
  }
}

function renderLibraryOptions(editor) {
  fillDatalist(elements.sceneNames, editor.scenes || []);
  fillDatalist(elements.prefabNames, editor.prefabs || []);
  fillDatalist(elements.animationNames, editor.animations || []);
  fillDatalist(elements.materialNames, editor.materials || []);
}

function fillAssetSelect(select, kind, assets) {
  const previous = select.value;
  const query = elements.assetFilter.value.trim().toLowerCase();
  select.replaceChildren();
  const none = document.createElement("option");
  none.value = "";
  none.textContent = "(none)";
  select.append(none);
  for (const asset of assets.filter((item) => item.kind === kind)) {
    if (query) {
      const haystack =
        `${asset.id} ${asset.kind} ${JSON.stringify(asset.metadata || {})}`.toLowerCase();
      if (!haystack.includes(query)) {
        continue;
      }
    }
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

function fillMaterialForm(editor) {
  const selection = editor.selection;
  const materialId = selection ? selection.material : null;
  const asset = (editor.assets || []).find((item) => item.id === materialId);
  const metadata = (asset && asset.metadata) || {};
  const entry = (editor.materials || []).find(
    (item) => `material.${item.name}` === materialId,
  );
  elements.materialName.value = entry
    ? entry.name
    : materialId
      ? String(materialId).replace(/^material\./, "")
      : "";
  elements.materialColor.value = (
    metadata.color || [0.78, 0.78, 0.82]
  ).join(", ");
  elements.materialMetallic.value = metadata.metallic ?? 0;
  elements.materialRoughness.value = metadata.roughness ?? 0.7;
  elements.materialEmissive.value = (
    metadata.emissive || [0, 0, 0]
  ).join(", ");
  elements.materialSpecular.value = metadata.specular ?? 0.35;
  elements.materialShininess.value = metadata.shininess ?? 32;
  elements.materialChecker.value = metadata.checker_scale ?? 0;
  elements.materialTexture.value =
    metadata.texture_id || (entry && entry.texture) || "";
  elements.materialState.textContent = materialId
    ? `Selected ${materialId}`
    : "No material selected.";
}

function assetSummary(assetId) {
  const assets = (editorState && editorState.assets) || [];
  const asset = assets.find((item) => item.id === assetId);
  if (!asset) {
    return null;
  }
  return `${asset.id} · ${asset.kind}\n${JSON.stringify(asset.metadata || {}, null, 2)}`;
}

function selectedAssetPreview() {
  const selected = [elements.meshAsset.value, elements.materialAsset.value].filter(Boolean);
  const assets = (editorState && editorState.assets) || [];
  for (const assetId of selected) {
    const asset = assets.find((item) => item.id === assetId);
    const metadata = (asset && asset.metadata) || {};
    const preview =
      metadata.preview || (metadata.texture && metadata.texture.preview) || null;
    if (preview) {
      return preview;
    }
  }
  return null;
}

function updateAssetInfo() {
  const summaries = [elements.meshAsset.value, elements.materialAsset.value]
    .filter(Boolean)
    .map(assetSummary)
    .filter(Boolean);
  elements.assetInfo.textContent = summaries.length
    ? summaries.join("\n\n")
    : "No registry assets selected.";
  const preview = selectedAssetPreview();
  if (preview) {
    elements.assetPreview.src = preview;
    elements.assetPreview.hidden = false;
  } else {
    elements.assetPreview.removeAttribute("src");
    elements.assetPreview.hidden = true;
  }
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

function fillSceneSettings(settings) {
  const camera = settings.camera || {};
  const environment = settings.environment || {};
  const light = environment.light || {};
  elements.cameraPosition.value = (camera.position || [0, 3.5, 9]).join(", ");
  elements.cameraYaw.value = camera.yaw ?? 0;
  elements.cameraPitch.value = camera.pitch ?? 0;
  elements.cameraFov.value = camera.fov_y ?? 60;
  elements.lightDirection.value = (light.direction || [0, -1, 0]).join(", ");
  elements.lightColor.value = (light.color || [1, 1, 1]).join(", ");
  elements.lightIntensity.value = light.intensity ?? 1;
  elements.ambientColor.value = (environment.ambient || [0.2, 0.2, 0.2]).join(
    ", ",
  );
  elements.fogDensity.value = environment.fog_density ?? 0;
  elements.shadowToggle.checked = Boolean(environment.shadow);
  elements.colorToggle.checked = Boolean(environment.color);
  elements.postToggle.checked = Boolean(environment.post);
  elements.bloomToggle.checked = Boolean(environment.bloom);
  elements.spritesToggle.checked = Boolean(environment.sprites);
  elements.cullingToggle.checked = Boolean(environment.culling);
}

function renderHistory(history) {
  const undoLabels = (history.undo_stack || []).slice(0, 4);
  const redoLabels = (history.redo_stack || []).slice(0, 4);
  const undo = undoLabels.length
    ? `Undo: ${undoLabels.join(" \u2190 ")}`
    : "Undo: none";
  const redo = redoLabels.length
    ? `Redo: ${redoLabels.join(" \u2192 ")}`
    : "Redo: none";
  elements.historyState.textContent = `${undo} \u00b7 ${redo}`;
}

function showEditor(editor) {
  editorState = editor;
  if (viewer) {
    viewer.setSelectedIds(
      editor.selected_ids ||
        (editor.selection ? [editor.selection.id] : []),
    );
  }
  elements.sceneSettings.value = JSON.stringify(
    editor.scene_settings || {},
    null,
    2,
  );
  fillSceneSettings(editor.scene_settings || {});
  renderHierarchy(editor);
  renderLibraryOptions(editor);
  renderAssets(editor);
  renderComponentTypes(editor);
  fillNodeProperties(editor.selection);
  fillTransform(editor.selection);
  const link = editor.selection && editor.selection.prefab_link;
  elements.prefabLink.textContent = link
    ? `Prefab instance ${link.name} (${link.instance})`
    : "No prefab instance selected";
  renderPrefabOverrides(editor);
  fillAssets(editor.selection);
  fillMaterialForm(editor);
  updateAssetInfo();
  fillComponentData(editor.selection);
  renderComponentFields(editor, editor.selection);
  const history = editor.history || {
    undo: 0,
    redo: 0,
    undo_stack: [],
    redo_stack: [],
  };
  renderHistory(history);
  const play = editor.play || { active: false, paused: false, frames: 0 };
  const lifecycle = play.lifecycle || { started: 0 };
  if (viewer) {
    if (play.active && !wasPlaying) {
      viewer.setViewMode("game");
    } else if (!play.active && wasPlaying) {
      viewer.setViewMode("scene");
    }
    viewer.setEditable(!play.active);
  }
  wasPlaying = Boolean(play.active);
  elements.playState.textContent = play.active
    ? `${play.paused ? "Paused" : "Playing"} · ${play.frames} frames · ${lifecycle.started ?? 0} behaviors`
    : "Stopped";
  const playDocument = play.active
    ? {
        status: play.status ?? null,
        snapshot: play.snapshot ?? null,
        status_error: play.status_error,
        snapshot_error: play.snapshot_error,
      }
    : null;
  elements.playSnapshot.textContent = playDocument
    ? JSON.stringify(playDocument, null, 2)
    : "No play snapshot.";
  const animationPreview = editor.animation_preview;
  elements.animationState.textContent = animationPreview
    ? `Previewed ${animationPreview.name} at ${animationPreview.time}s · ` +
      `${animationPreview.updated.length} nodes`
    : "No animation preview.";
  syncAnimationTimeline(editor);
  if (!busy) {
    updatePlayButtons(play);
  }
  const prefabEdit = editor.prefab_edit;
  elements.prefabEditState.textContent = prefabEdit
    ? `Editing prefab ${prefabEdit.name} · ${prefabEdit.root_count} roots` +
      `${prefabEdit.dirty ? " · unsaved" : ""}`
    : "Scene editing";
  if (!busy) {
    updatePrefabEditButtons(prefabEdit);
  }
  const selectionSummary = editor.selection_summary || {
    count: 0,
    mixed: [],
  };
  if (selectionSummary.count > 1) {
    elements.selectionSummary.textContent =
      `Editing ${selectionSummary.count} nodes · mixed: ` +
      `${selectionSummary.mixed.join(", ") || "none"}`;
  } else if (selectionSummary.count === 1) {
    elements.selectionSummary.textContent = "Editing 1 node";
  } else {
    elements.selectionSummary.textContent = "No selection";
  }
  elements.editorState.textContent =
    `${editor.nodes.length} nodes · ${editor.prefabs.length} prefabs · ` +
    `${editor.prefab_instance_count ?? (editor.prefab_instances || []).length} instances · ` +
    `${editor.prefab_override_count ?? 0} overrides · ` +
    `${editor.scene_group_count ?? 0} scenes · ` +
    `undo ${history.undo} / redo ${history.redo} · ` +
    `selected ${editor.selection_count ?? (editor.selection ? 1 : 0)}` +
    `${editor.selection ? ` (${editor.selection.id})` : ""}`;
  const validation = editor.validation;
  elements.validationState.textContent = validation
    ? `${validation.ok ? "OK" : "Errors"} · ${validation.errors} errors · ` +
      `${validation.warnings} warnings`
    : "Not validated.";
  const imported = editor.imported_asset;
  const importedGltf = editor.imported_gltf;
  const forgotten = editor.forgotten_asset;
  const projectDir = editor.workspace && editor.workspace.project_dir;
  const projectCount = (editor.project_assets || []).length;
  fillPathDatalist(elements.projectAssets, editor.project_assets || []);
  if (importedGltf) {
    elements.importState.textContent =
      `${importedGltf.duplicate ? "Reimported" : "Imported"} glTF ` +
      `${importedGltf.path} → prefab ${importedGltf.prefab} · ` +
      `${importedGltf.asset_count} assets · ${importedGltf.count} project assets` +
      `${importedGltf.replaced_prefab ? " · replaced prefab" : ""}`;
  } else if (imported) {
    elements.importState.textContent =
      `${imported.duplicate ? "Refreshed" : "Imported"} ${imported.path} · ` +
      `${imported.asset} (${imported.kind}) · ${imported.count} project assets`;
  } else if (forgotten) {
    elements.importState.textContent =
      `Forgot ${forgotten.path} · ` +
      `${forgotten.removed ? "unregistered" : "manifest only"} · ` +
      `${forgotten.count} project assets · source kept`;
  } else if (!projectDir) {
    elements.importState.textContent =
      "Open a project with --project to import .obj, .png, .kprefab, .gltf or .glb files.";
  } else {
    elements.importState.textContent =
      `Enter a project-relative .obj, .png, .kprefab, .gltf or .glb path. ` +
      `${projectCount} project assets listed.`;
  }
  elements.importAsset.disabled = !projectDir;
  elements.forgetAsset.disabled = !projectDir;
  const usages = editor.asset_usages;
  elements.usageState.textContent = usages
    ? `${usages.found ? "Used" : "Unused"} · ${usages.references} refs · ` +
      `${usages.scene_nodes.length} nodes · ${usages.prefabs.length} prefabs · ` +
      `${usages.scenes.length} scenes`
    : "Select a path or asset id to find usages.";
  const reload = editor.asset_reload;
  elements.reloadState.textContent = reload
    ? `${reload.ok ? "OK" : "Attention"} · ${reload.checked} checked · ` +
      `${reload.reloaded.length} reloaded · ${reload.rebound} rebound · ` +
      `${reload.failed.length} failed · ${reload.missing.length} missing`
    : "No assets reloaded.";
  elements.startupState.textContent = editor.startup_scene
    ? `Startup: ${editor.startup_scene}`
    : "No startup scene.";
  elements.startupSet.disabled = !projectDir;
  elements.startupClear.disabled = !projectDir || !editor.startup_scene;
  elements.sceneDirtyState.textContent = editor.scene_dirty
    ? `Unsaved changes${editor.saved_scene ? ` · saved: ${editor.saved_scene}` : ""}`
    : editor.saved_scene
      ? `Saved: ${editor.saved_scene}`
      : "New scene";
  elements.sceneRevert.disabled = !editor.saved_scene || !editor.scene_dirty;
  elements.buildState.textContent = editor.build
    ? `Built ${editor.build.target} · ${editor.build.summary.files} files · ` +
      `${editor.build.summary.bytes} bytes`
    : "No build yet.";
  elements.buildProject.disabled = !projectDir;
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
  stopAnimationPlay();
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

function readNumber(id, label) {
  const value = Number(elements[id].value);
  if (!Number.isFinite(value)) {
    throw new Error(`${label} must be a finite number.`);
  }
  return value;
}

async function selectNode(nodeId) {
  await editorAction({ action: "select", id: nodeId }, "selecting node");
}

async function selectMany(ids, mode = "replace") {
  await editorAction(
    { action: "select_many", ids, mode },
    "selecting nodes",
  );
}

async function selectViewportNode(nodeId, modifiers) {
  const additive = Boolean(modifiers.shift || modifiers.ctrl || modifiers.meta);
  if (nodeId === null) {
    if (!additive) {
      await selectNode(null);
    }
    return;
  }
  if (additive) {
    await selectMany([nodeId], "toggle");
  } else {
    await selectNode(nodeId);
  }
}

async function nudgeSelection(delta) {
  if (!editorState || !editorState.selection) {
    return;
  }
  if ((editorState.selection_count || 1) > 1) {
    await editorAction(
      { action: "transform_selection", position: delta },
      "nudging selection",
    );
    await refreshScene(false);
    return;
  }
  const current = editorState.selection.transform.position;
  await editorAction(
    {
      action: "transform",
      id: editorState.selection.id,
      position: [
        current[0] + delta[0],
        current[1] + delta[1],
        current[2] + delta[2],
      ],
    },
    "nudging node",
  );
  await refreshScene(false);
}

function worldDeltaToLocal(world, delta) {
  const matrix = world || [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
  const a = matrix[0];
  const b = matrix[4];
  const c = matrix[8];
  const d = matrix[1];
  const e = matrix[5];
  const f = matrix[9];
  const g = matrix[2];
  const h = matrix[6];
  const i = matrix[10];
  const determinant = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g);
  if (Math.abs(determinant) < 1e-9) {
    return [...delta];
  }
  const inverse = 1.0 / determinant;
  return [
    ((e * i - f * h) * delta[0] + (c * h - b * i) * delta[1] + (b * f - c * e) * delta[2]) * inverse,
    ((f * g - d * i) * delta[0] + (a * i - c * g) * delta[1] + (c * d - a * f) * delta[2]) * inverse,
    ((d * h - e * g) * delta[0] + (b * g - a * h) * delta[1] + (a * e - b * d) * delta[2]) * inverse,
  ];
}

async function applyGizmoTransform(axis, delta) {
  if (!editorState || !editorState.selection) {
    return;
  }
  const selection = editorState.selection;
  const parent = selection.parent_id
    ? (editorState.nodes || []).find((node) => node.id === selection.parent_id)
    : null;
  const localDelta = worldDeltaToLocal(parent ? parent.world : null, delta);
  const position = selection.transform.position.map(
    (value, index) => Math.round((value + localDelta[index]) * 1e6) / 1e6,
  );
  await editorAction(
    { action: "transform", id: selection.id, position },
    `moving node on ${axis.toUpperCase()}`,
  );
  await refreshScene(false);
}

async function applyGizmoSelectionTransform(delta) {
  await editorAction(
    { action: "transform_selection", position: delta },
    "moving selection",
  );
  await refreshScene(false);
}

async function applyGizmoSelectionRotation(axis, degrees, pivot) {
  await editorAction(
    {
      action: "transform_selection",
      pivot,
      group_rotation: axisAngleQuaternion(axis, degrees),
    },
    "rotating selection",
  );
  await refreshScene(false);
}

async function applyGizmoSelectionScale(axis, factor, pivot) {
  const factors =
    axis === "x"
      ? [factor, 1.0, 1.0]
      : axis === "y"
        ? [1.0, factor, 1.0]
        : [1.0, 1.0, factor];
  await editorAction(
    { action: "transform_selection", pivot, group_scale: factors },
    "scaling selection",
  );
  await refreshScene(false);
}

function axisAngleQuaternion(axis, degrees) {
  const half = (degrees * Math.PI) / 360;
  const sine = Math.sin(half);
  return [
    axis === "x" ? sine : 0,
    axis === "y" ? sine : 0,
    axis === "z" ? sine : 0,
    Math.cos(half),
  ];
}

function multiplyQuaternion(left, right) {
  const [lx, ly, lz, lw] = left;
  const [rx, ry, rz, rw] = right;
  return [
    lw * rx + lx * rw + ly * rz - lz * ry,
    lw * ry - lx * rz + ly * rw + lz * rx,
    lw * rz + lx * ry - ly * rx + lz * rw,
    lw * rw - lx * rx - ly * ry - lz * rz,
  ];
}

async function applyGizmoRotation(axis, degrees) {
  if (!editorState || !editorState.selection) {
    return;
  }
  const selection = editorState.selection;
  const rotation = multiplyQuaternion(
    selection.transform.rotation,
    axisAngleQuaternion(axis, degrees),
  );
  const size = Math.hypot(...rotation) || 1;
  await editorAction(
    {
      action: "transform",
      id: selection.id,
      rotation: rotation.map(
        (value) => Math.round((value / size) * 1e6) / 1e6,
      ),
    },
    `rotating node on ${axis.toUpperCase()}`,
  );
  await refreshScene(false);
}

async function applyGizmoScale(axis, factor) {
  if (!editorState || !editorState.selection) {
    return;
  }
  const selection = editorState.selection;
  const index = { x: 0, y: 1, z: 2 }[axis];
  const scale = selection.transform.scale.map((value, position) =>
    position === index
      ? Math.round(value * factor * 1e6) / 1e6
      : value,
  );
  await editorAction(
    { action: "transform", id: selection.id, scale },
    `scaling node on ${axis.toUpperCase()}`,
  );
  await refreshScene(false);
}

function setGizmoMode(mode) {
  if (viewer) {
    viewer.setGizmoMode(mode);
  }
  setStatus(`gizmo: ${mode}`);
}

function updateViewModeButton(mode) {
  elements.viewMode.textContent = mode === "game" ? "View: Game" : "View: Scene";
}

function toggleViewMode() {
  if (!viewer) {
    return;
  }
  const next = viewer.viewMode === "game" ? "scene" : "game";
  viewer.setViewMode(next);
  setStatus(next === "game" ? "game view" : "scene view");
}

function toggleGrid() {
  if (!viewer) {
    return;
  }
  const enabled = viewer.setGrid(!viewer.gridEnabled);
  elements.gridToggle.textContent = `Grid: ${enabled ? "on" : "off"}`;
  setStatus(`grid ${enabled ? "on" : "off"}`);
}

function toggleSnap() {
  if (!viewer) {
    return;
  }
  const enabled = viewer.setSnap(!viewer.snapEnabled);
  elements.snapToggle.textContent = `Snap: ${enabled ? "on" : "off"}`;
  setStatus(`snap ${enabled ? "on" : "off"}`);
}

function syncSnapSteps() {
  if (!viewer) {
    return;
  }
  elements.snapMove.value = viewer.snapSteps.translate;
  elements.snapRotate.value = viewer.snapSteps.rotate;
  elements.snapScale.value = viewer.snapSteps.scale;
}

function applySnapSteps() {
  if (!viewer) {
    return;
  }
  viewer.setSnapSteps({
    translate: Number(elements.snapMove.value),
    rotate: Number(elements.snapRotate.value),
    scale: Number(elements.snapScale.value),
  });
  syncSnapSteps();
  setStatus(
    `snap steps: ${viewer.snapSteps.translate} / ` +
      `${viewer.snapSteps.rotate}° / ${viewer.snapSteps.scale}`,
  );
}

function updateProjectionButton(preset) {
  const labels = {
    persp: "Persp",
    top: "Top",
    front: "Front",
    side: "Side",
  };
  elements.projectionMode.textContent =
    `Proj: ${labels[preset] || labels.persp}`;
}

function toggleProjection() {
  if (!viewer) {
    return;
  }
  const presets = ["persp", "top", "front", "side"];
  const current = viewer.viewPreset || "persp";
  const next = presets[(presets.indexOf(current) + 1) % presets.length];
  viewer.setProjectionPreset(next);
  setStatus(`projection: ${next}`);
}

function layoutKey() {
  const game = (elements.game.textContent || "game").trim() || "game";
  return `keystone.layout.v1:${game}`;
}

function scheduleLayoutSave() {
  if (layoutTimer !== null) {
    window.clearTimeout(layoutTimer);
  }
  layoutTimer = window.setTimeout(saveLayout, 250);
}

function saveLayout() {
  layoutTimer = null;
  if (!viewer) {
    return;
  }
  try {
    window.localStorage.setItem(
      layoutKey(),
      JSON.stringify(viewer.layoutSnapshot()),
    );
  } catch {
    // Storage can be unavailable; layout persistence is optional.
  }
}

function restoreLayout() {
  if (!viewer) {
    return;
  }
  let layout = null;
  try {
    layout = JSON.parse(window.localStorage.getItem(layoutKey()) || "null");
  } catch {
    layout = null;
  }
  if (!layout || typeof layout !== "object") {
    return;
  }
  viewer.applyLayout(layout);
  updateViewModeButton(viewer.viewMode);
  updateProjectionButton(viewer.viewPreset);
  elements.gridToggle.textContent =
    `Grid: ${viewer.gridEnabled ? "on" : "off"}`;
  elements.snapToggle.textContent =
    `Snap: ${viewer.snapEnabled ? "on" : "off"}`;
  syncSnapSteps();
}

function resetLayout() {
  if (!viewer) {
    return;
  }
  try {
    window.localStorage.removeItem(layoutKey());
  } catch {
    // ignore unavailable storage
  }
  viewer.setViewMode("scene");
  viewer.setProjectionPreset("persp");
  viewer.setGrid(true);
  viewer.setSnap(false);
  viewer.setSnapSteps({ translate: 0.25, rotate: 15, scale: 0.1 });
  syncSnapSteps();
  viewer.resetCamera();
  updateViewModeButton(viewer.viewMode);
  updateProjectionButton(viewer.viewPreset);
  elements.gridToggle.textContent = "Grid: on";
  elements.snapToggle.textContent = "Snap: off";
  setStatus("layout reset");
}

function toggleGizmoSpace() {
  gizmoSpace = gizmoSpace === "world" ? "local" : "world";
  if (viewer) {
    viewer.setGizmoSpace(gizmoSpace);
  }
  elements.gizmoSpace.textContent = `Space: ${gizmoSpace}`;
  setStatus(`gizmo space: ${gizmoSpace}`);
}

function toggleBoxSelect() {
  boxSelect = !boxSelect;
  if (viewer) {
    viewer.setBoxSelect(boxSelect);
  }
  elements.boxSelect.textContent = `Box select: ${boxSelect ? "on" : "off"}`;
  setStatus(`box select ${boxSelect ? "on" : "off"}`);
}

async function applyTransform() {
  if (!editorState || !editorState.selection) {
    throw new Error("Select a node before editing its transform.");
  }
  const multi = (editorState.selection_count || 0) > 1;
  const payload = {
    action: multi ? "set_selection_transform" : "transform",
    position: readVector("position", 3, "Position"),
    rotation: readVector("rotation", 4, "Rotation"),
    scale: readVector("scale", 3, "Scale"),
  };
  if (!multi) {
    payload.id = editorState.selection.id;
  }
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

async function duplicatePrefab() {
  const name = elements.prefabName.value.trim();
  const newName = elements.prefabNewName.value.trim();
  if (!name || !newName) {
    throw new Error("Enter the source and duplicate prefab names.");
  }
  await editorAction(
    { action: "duplicate_prefab", name, new_name: newName },
    "duplicating prefab",
  );
  elements.prefabName.value = newName;
}

async function restorePrefab() {
  const entry = ((editorState && editorState.trash && editorState.trash.prefabs) || [])[0];
  if (!entry) {
    throw new Error("No trashed prefab is available.");
  }
  await editorAction(
    { action: "restore_prefab", trash: entry.trash },
    "restoring prefab",
  );
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
    throw new Error("Select at least one node before saving a prefab.");
  }
  const name = elements.prefabName.value.trim() || editorState.selection.id;
  const payload = { action: "save_prefab", name };
  if ((editorState.selection_count || 0) > 1) {
    payload.ids = editorState.selected_ids;
  } else {
    payload.id = editorState.selection.id;
  }
  await editorAction(payload, "saving prefab");
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

async function revertPrefabInstance() {
  if (!editorState || !editorState.selection) {
    throw new Error("Select a prefab instance first.");
  }
  await editorAction(
    { action: "revert_prefab", id: editorState.selection.id },
    "reverting prefab instance",
  );
  await refreshScene(false);
}

async function applyPrefabInstance() {
  if (!editorState || !editorState.selection) {
    throw new Error("Select a prefab instance first.");
  }
  await editorAction(
    { action: "apply_prefab", id: editorState.selection.id },
    "applying prefab instance",
  );
}

function overrideValue(value) {
  if (value === null || value === undefined) {
    return "\u2014";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

function renderPrefabOverrides(editor) {
  const groups = editor.prefab_overrides || [];
  elements.prefabOverrides.replaceChildren();
  if (!groups.length) {
    const hint = document.createElement("div");
    hint.className = "hint";
    hint.textContent = "No prefab overrides.";
    elements.prefabOverrides.append(hint);
    return;
  }
  for (const group of groups) {
    const container = document.createElement("div");
    container.className = "override-group";
    const title = document.createElement("div");
    title.className = "override-title";
    title.textContent = `${group.prefab} / ${group.instance}`;
    container.append(title);
    if (group.error) {
      const error = document.createElement("div");
      error.className = "hint";
      error.textContent = group.error;
      container.append(error);
    }
    for (const node of group.nodes || []) {
      const fields = node.fields || {};
      for (const field of Object.keys(fields).sort()) {
        const values = fields[field];
        const row = document.createElement("div");
        row.className = "override-row";
        const label = document.createElement("span");
        label.textContent =
          `${node.id} \u00b7 ${field}: ` +
          `${overrideValue(values.template)} \u2192 ${overrideValue(values.instance)}`;
        const revert = document.createElement("button");
        revert.type = "button";
        revert.textContent = "Revert";
        revert.addEventListener("click", () =>
          run(() => revertPrefabOverride(node.id, field)),
        );
        const apply = document.createElement("button");
        apply.type = "button";
        apply.textContent = "Apply";
        apply.addEventListener("click", () =>
          run(() => applyPrefabOverride(node.id, field)),
        );
        row.append(label, revert, apply);
        container.append(row);
      }
    }
    elements.prefabOverrides.append(container);
  }
}

async function revertPrefabOverride(nodeId, field) {
  await editorAction(
    { action: "revert_prefab_override", id: nodeId, field },
    `reverting ${field}`,
  );
  await refreshScene(false);
}

async function applyPrefabOverride(nodeId, field) {
  await editorAction(
    { action: "apply_prefab_override", id: nodeId, field },
    `applying ${field}`,
  );
  await refreshScene(false);
}

async function refreshPrefabInstances() {
  const name = elements.prefabName.value.trim();
  if (!name) {
    throw new Error("Enter the prefab name to refresh.");
  }
  const editor = await editorAction(
    { action: "refresh_prefab_instances", name },
    `refreshing ${name} instances`,
  );
  await refreshScene(false);
  show({ ok: true, action: "refresh_prefab_instances", refresh: editor.prefab_refresh });
}

async function editPrefab() {
  const link =
    editorState && editorState.selection
      ? editorState.selection.prefab_link
      : null;
  const name = (link && link.name) || elements.prefabName.value.trim();
  if (!name) {
    throw new Error("Select a prefab instance or enter a prefab name.");
  }
  await editorAction(
    { action: "edit_prefab", name },
    `editing prefab ${name}`,
  );
  await refreshScene(false);
}

async function savePrefabEdit() {
  await editorAction({ action: "save_prefab_edit" }, "saving prefab edit");
}

async function closePrefabEdit(save) {
  await editorAction(
    { action: "close_prefab_edit", save },
    save ? "saving and closing prefab edit" : "discarding prefab edit",
  );
  await refreshScene(false);
}

function readPlayActions() {
  let actions;
  try {
    actions = JSON.parse(elements.playActions.value || "[]");
  } catch (error) {
    throw new Error(`Play actions JSON: ${error.message}`);
  }
  if (!Array.isArray(actions)) {
    throw new Error("Play actions JSON must be a list.");
  }
  return actions;
}

function stopPlayLoop() {
  playLoopActive = false;
  if (playLoopTimer !== null) {
    window.clearTimeout(playLoopTimer);
    playLoopTimer = null;
  }
}

function startPlayLoop() {
  stopPlayLoop();
  playLoopActive = true;
  playLoopLast = performance.now();
  playLoopTimer = window.setTimeout(playTick, 0);
}

async function playTick() {
  playLoopTimer = null;
  if (!playLoopActive || playLoopBusy) {
    if (playLoopActive) {
      playLoopTimer = window.setTimeout(playTick, 16);
    }
    return;
  }
  playLoopBusy = true;
  const now = performance.now();
  const elapsed = Math.min(0.25, Math.max(0, (now - playLoopLast) / 1000));
  playLoopLast = now;
  const frames = Math.max(1, Math.round(elapsed / 0.016666666666666666));
  try {
    const editor = await api("/api/editor", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "play_step",
        frames,
        actions: readPlayActions(),
      }),
    });
    showEditor(editor);
    await refreshScene(false);
  } catch (error) {
    stopPlayLoop();
    setStatus(error.message, "error");
    show({ ok: false, error: error.message });
    await refreshEditor(false).catch(() => {});
  } finally {
    playLoopBusy = false;
    if (playLoopActive) {
      playLoopTimer = window.setTimeout(playTick, 16);
    }
  }
}

async function playStart() {
  stopPlayLoop();
  const editor = await editorAction({ action: "play_start" }, "starting play");
  await refreshScene(false);
  if (editor.play && editor.play.active && !editor.play.paused) {
    startPlayLoop();
  }
}

async function playPause() {
  stopPlayLoop();
  await editorAction({ action: "play_pause" }, "pausing play");
}

async function playResume() {
  await editorAction({ action: "play_resume" }, "resuming play");
  startPlayLoop();
}

async function playStep() {
  const play = (editorState && editorState.play) || {
    active: false,
    paused: true,
  };
  if (play.active && !play.paused) {
    stopPlayLoop();
    await editorAction({ action: "play_pause" }, "pausing play");
  }
  const frames = Number.parseInt(elements.playFrames.value, 10);
  if (!Number.isInteger(frames) || frames < 1 || frames > 10000) {
    throw new Error("Play frames must be an integer between 1 and 10000.");
  }
  const actions = readPlayActions();
  await editorAction(
    { action: "play_step", frames, actions },
    "stepping play",
  );
  await refreshScene(false);
}

async function playStop() {
  stopPlayLoop();
  await editorAction({ action: "play_stop" }, "stopping play");
  await refreshScene(false);
}

function sampleAnimationClip() {
  if (!editorState || !editorState.selection) {
    throw new Error("Select a node before sampling an animation clip.");
  }
  const node = editorState.selection;
  const position = node.transform.position;
  const clip = {
    schema: 1,
    name: `${node.name || node.id}-preview`,
    position: {
      [node.id]: {
        interpolation: "linear",
        keys: [
          { t: 0.0, v: position },
          { t: 1.0, v: [position[0], position[1] + 1.0, position[2]] },
        ],
      },
    },
    rotation: {},
    scale: {},
    events: [],
  };
  elements.animationClip.value = JSON.stringify(clip, null, 2);
  if (!elements.animationName.value.trim()) {
    elements.animationName.value = `${node.name || node.id}-clip`;
  }
  elements.animationState.textContent = `Sample clip for ${node.id}.`;
  syncAnimationTimeline(editorState);
}

function animationDuration(editor) {
  const name = elements.animationName.value.trim();
  if (name && editor) {
    const entry = (editor.animations || []).find(
      (item) => item.name === name,
    );
    if (entry && Number.isFinite(entry.duration)) {
      return Math.max(0.01, Number(entry.duration));
    }
  }
  try {
    const clip = JSON.parse(elements.animationClip.value || "{}");
    let duration = 0.0;
    for (const group of ["position", "rotation", "scale"]) {
      const tracks = clip[group] || {};
      for (const track of Object.values(tracks)) {
        for (const key of (track && track.keys) || []) {
          const time = Number(key && key.t);
          if (Number.isFinite(time)) {
            duration = Math.max(duration, time);
          }
        }
      }
    }
    return Math.max(0.01, duration);
  } catch {
    return 1.0;
  }
}

function syncAnimationTimeline(editor) {
  const duration = animationDuration(editor);
  elements.animationScrub.max = String(duration);
  const time = Number(elements.animationTime.value);
  elements.animationScrub.value = String(
    Math.min(Math.max(Number.isFinite(time) ? time : 0, 0), duration),
  );
}

function animationPreviewPayload() {
  const time = Number(elements.animationTime.value);
  if (!Number.isFinite(time) || time < 0) {
    throw new Error("Preview time must be a non-negative number.");
  }
  const name = elements.animationName.value.trim();
  if (name) {
    return { action: "preview_animation", name, time };
  }
  let clip;
  try {
    clip = JSON.parse(elements.animationClip.value || "{}");
  } catch (error) {
    throw new Error(`Animation clip JSON: ${error.message}`);
  }
  if (!clip || typeof clip !== "object" || Array.isArray(clip)) {
    throw new Error("Animation clip JSON must be an object.");
  }
  return { action: "preview_animation", clip, time };
}

async function previewAnimation() {
  const payload = animationPreviewPayload();
  const editor = await editorAction(
    { ...payload, record: true },
    "previewing animation",
  );
  await refreshScene(false);
  show({
    ok: true,
    action: "preview_animation",
    preview: editor.animation_preview,
  });
}

function stopAnimationPlay() {
  animationPlayActive = false;
  if (animationPlayTimer !== null) {
    window.clearTimeout(animationPlayTimer);
    animationPlayTimer = null;
  }
  elements.animationPlay.textContent = "Play preview";
}

async function toggleAnimationPlay() {
  if (animationPlayActive) {
    stopAnimationPlay();
    return;
  }
  const duration = animationDuration(editorState);
  let time = Number(elements.animationTime.value);
  if (!Number.isFinite(time) || time < 0 || time >= duration) {
    time = 0;
    elements.animationTime.value = "0";
  }
  elements.animationScrub.value = String(Math.min(time, duration));
  const payload = animationPreviewPayload();
  await editorAction(
    { ...payload, record: true },
    "starting animation preview",
  );
  animationPlayActive = true;
  animationPlayLast = performance.now();
  elements.animationPlay.textContent = "Pause preview";
  animationPlayTimer = window.setTimeout(animationTick, 33);
}

async function animationTick() {
  animationPlayTimer = null;
  if (!animationPlayActive) {
    return;
  }
  if (animationPlayBusy) {
    animationPlayTimer = window.setTimeout(animationTick, 33);
    return;
  }
  animationPlayBusy = true;
  const now = performance.now();
  const elapsed = Math.min(
    0.2,
    Math.max(0, (now - animationPlayLast) / 1000),
  );
  animationPlayLast = now;
  const duration = animationDuration(editorState);
  let time = Number(elements.animationTime.value) + elapsed;
  if (!Number.isFinite(time) || time >= duration) {
    time = 0;
  }
  elements.animationTime.value = String(Math.round(time * 1000) / 1000);
  elements.animationScrub.value = String(Math.min(time, duration));
  try {
    const payload = animationPreviewPayload();
    const editor = await api("/api/editor", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, record: false }),
    });
    showEditor(editor);
    await refreshScene(false);
  } catch (error) {
    stopAnimationPlay();
    setStatus(error.message, "error");
    show({ ok: false, error: error.message });
  } finally {
    animationPlayBusy = false;
    if (animationPlayActive) {
      animationPlayTimer = window.setTimeout(animationTick, 33);
    }
  }
}

async function saveAnimation() {
  const name = elements.animationName.value.trim();
  if (!name) {
    throw new Error("Enter a clip name before saving.");
  }
  let clip;
  try {
    clip = JSON.parse(elements.animationClip.value || "{}");
  } catch (error) {
    throw new Error(`Animation clip JSON: ${error.message}`);
  }
  if (!clip || typeof clip !== "object" || Array.isArray(clip)) {
    throw new Error("Animation clip JSON must be an object.");
  }
  clip.name = name;
  await editorAction(
    { action: "save_animation", name, clip },
    `saving animation ${name}`,
  );
}

async function deleteAnimation() {
  const name = elements.animationName.value.trim();
  if (!name) {
    throw new Error("Enter the clip name to delete.");
  }
  await editorAction(
    { action: "delete_animation", name },
    `deleting animation ${name}`,
  );
}

async function restoreAnimation() {
  const entry = (
    (editorState && editorState.trash && editorState.trash.animations) || []
  )[0];
  if (!entry) {
    throw new Error("No trashed animation is available.");
  }
  await editorAction(
    { action: "restore_animation", trash: entry.trash },
    "restoring animation",
  );
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
  const multi = (editorState.selection_count || 0) > 1;
  const payload = {
    action: multi ? "set_selection_properties" : "set_node",
    name,
    visible: elements.nodeVisible.checked,
    tags,
    layer,
  };
  if (!multi) {
    payload.id = editorState.selection.id;
  }
  await editorAction(payload, "applying node properties");
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

async function importAsset() {
  const path = elements.importPath.value.trim();
  if (!path) {
    throw new Error("Enter a project-relative asset path.");
  }
  const gltf = /\.(gltf|glb)$/i.test(path);
  const editor = await editorAction(
    { action: gltf ? "import_gltf" : "import_asset", path },
    `importing ${path}`,
  );
  if (gltf) {
    const imported = editor.imported_gltf;
    if (imported) {
      show({ ok: true, action: "import_gltf", imported_gltf: imported });
    }
    return;
  }
  const imported = editor.imported_asset;
  if (imported) {
    show({ ok: true, action: "import_asset", imported_asset: imported });
  }
}

async function reloadAssets() {
  const editor = await editorAction({ action: "reload_assets" }, "reloading assets");
  const reload = editor.asset_reload;
  if (reload) {
    show({ ok: reload.ok, action: "reload_assets", asset_reload: reload });
  }
}

async function forgetAsset() {
  const path = elements.importPath.value.trim();
  if (!path) {
    throw new Error("Enter a project-relative asset path to forget.");
  }
  const editor = await editorAction(
    { action: "forget_asset", path },
    `forgetting ${path}`,
  );
  const forgotten = editor.forgotten_asset;
  if (forgotten) {
    show({ ok: true, action: "forget_asset", forgotten_asset: forgotten });
  }
}

async function findUsages() {
  const value = elements.importPath.value.trim();
  if (!value) {
    throw new Error("Enter a project-relative path or asset id.");
  }
  const known =
    editorState &&
    (editorState.assets || []).some((asset) => asset.id === value);
  const payload =
    known || value.includes(":")
      ? { action: "asset_usages", asset: value }
      : { action: "asset_usages", path: value };
  const editor = await editorAction(payload, `finding usages for ${value}`);
  const usages = editor.asset_usages;
  if (usages) {
    show({ ok: true, action: "asset_usages", asset_usages: usages });
  }
}

async function buildProject() {
  const target = elements.buildTarget.value.trim() || "build";
  const force = elements.buildForce.checked;
  const editor = await editorAction(
    { action: "build_project", target, force },
    `building ${target}`,
  );
  const build = editor.build;
  if (build) {
    show({ ok: true, action: "build_project", build });
  }
}

async function saveMaterial() {
  const name = elements.materialName.value.trim();
  if (!name) {
    throw new Error("Enter a material name before saving.");
  }
  const color = readVector("materialColor", 3, "Material color");
  const emissive = readVector("materialEmissive", 3, "Material emissive");
  const metallic = readNumber("materialMetallic", "Material metallic");
  const roughness = readNumber("materialRoughness", "Material roughness");
  const specular = readNumber("materialSpecular", "Material specular");
  const shininess = readNumber("materialShininess", "Material shininess");
  const checker = readNumber("materialChecker", "Material checker");
  const texture = elements.materialTexture.value.trim() || null;
  await editorAction(
    {
      action: "save_material",
      name,
      color,
      metallic,
      roughness,
      emissive,
      specular,
      shininess,
      checker_scale: checker,
      texture,
    },
    `saving material ${name}`,
  );
}

async function assignMaterial() {
  if (!editorState || !editorState.selection) {
    throw new Error("Select a node before assigning a material.");
  }
  const name = elements.materialName.value.trim();
  if (!name) {
    throw new Error("Enter a material name before assigning.");
  }
  await editorAction(
    { action: "assign_material", id: editorState.selection.id, name },
    `assigning material ${name}`,
  );
  await refreshScene(false);
}

async function clearMaterial() {
  if (!editorState || !editorState.selection) {
    throw new Error("Select a node before clearing its material.");
  }
  await editorAction(
    { action: "assign_material", id: editorState.selection.id, name: null },
    "clearing material",
  );
  await refreshScene(false);
}

async function deleteMaterial() {
  const name = elements.materialName.value.trim();
  if (!name) {
    throw new Error("Enter the material name to delete.");
  }
  await editorAction(
    { action: "delete_material", name },
    `deleting material ${name}`,
  );
}

async function restoreMaterial() {
  const entry = (
    (editorState && editorState.trash && editorState.trash.materials) || []
  )[0];
  if (!entry) {
    throw new Error("No trashed material is available.");
  }
  await editorAction(
    { action: "restore_material", trash: entry.trash },
    "restoring material",
  );
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

async function applyCameraSettings() {
  const position = readVector("cameraPosition", 3, "Camera position");
  const yaw = readNumber("cameraYaw", "Camera yaw");
  const pitch = readNumber("cameraPitch", "Camera pitch");
  const fov = readNumber("cameraFov", "Camera FOV");
  await editorAction(
    { action: "set_scene", camera: { position, yaw, pitch, fov_y: fov } },
    "applying camera",
  );
  await refreshScene(false);
}

async function applyEnvironmentSettings() {
  const direction = readVector("lightDirection", 3, "Light direction");
  const color = readVector("lightColor", 3, "Light color");
  const intensity = readNumber("lightIntensity", "Light intensity");
  const ambient = readVector("ambientColor", 3, "Ambient color");
  const fog = readNumber("fogDensity", "Fog density");
  await editorAction(
    {
      action: "set_scene",
      environment: {
        ambient,
        fog_density: fog,
        light: { direction, color, intensity },
        shadow: elements.shadowToggle.checked,
        color: elements.colorToggle.checked,
        post: elements.postToggle.checked,
        bloom: elements.bloomToggle.checked,
        sprites: elements.spritesToggle.checked,
        culling: elements.cullingToggle.checked,
      },
    },
    "applying environment",
  );
  await refreshScene(false);
}

async function validateScene() {
  const editor = await editorAction(
    { action: "validate_scene" },
    "validating scene",
  );
  const validation = editor.validation;
  if (validation) {
    elements.validationState.textContent =
      `${validation.ok ? "OK" : "Errors"} · ${validation.errors} errors · ` +
      `${validation.warnings} warnings`;
  }
  show({ ok: true, action: "validate_scene", validation });
}

async function applySceneSettings() {
  let data;
  try {
    data = JSON.parse(elements.sceneSettings.value || "{}");
  } catch (error) {
    throw new Error(`Scene settings JSON: ${error.message}`);
  }
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new Error("Scene settings JSON must be an object.");
  }
  if (!("camera" in data) && !("environment" in data)) {
    throw new Error("Scene settings need camera or environment.");
  }
  await editorAction(
    { action: "set_scene", ...data },
    "applying scene settings",
  );
  await refreshScene(false);
}

async function saveScene() {
  const name = elements.sceneName.value.trim() || "scene";
  await editorAction({ action: "save_scene", name }, "saving scene");
}

async function setStartupScene() {
  const name = elements.sceneName.value.trim();
  if (!name) {
    throw new Error("Enter the saved scene name to make startup.");
  }
  const editor = await editorAction(
    { action: "set_startup_scene", name },
    `setting startup scene ${name}`,
  );
  show({
    ok: true,
    action: "set_startup_scene",
    startup_scene: editor.startup_scene,
  });
}

async function clearStartupScene() {
  const editor = await editorAction(
    { action: "set_startup_scene", name: null },
    "clearing startup scene",
  );
  show({
    ok: true,
    action: "set_startup_scene",
    startup_scene: editor.startup_scene,
  });
}

async function revertScene() {
  const editor = await editorAction(
    { action: "revert_scene" },
    "reverting scene",
  );
  await refreshScene(false);
  show({ ok: true, action: "revert_scene", revert: editor.revert });
}

async function diffScene() {
  const name = elements.sceneName.value.trim();
  if (!name) {
    throw new Error("Enter the saved scene name to compare.");
  }
  const editor = await editorAction(
    { action: "diff_scene", name },
    "diffing scene",
  );
  show({ ok: true, action: "diff_scene", diff: editor.diff });
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

async function duplicateScene() {
  const name = elements.sceneName.value.trim();
  const newName = elements.sceneNewName.value.trim();
  if (!name || !newName) {
    throw new Error("Enter the source and duplicate scene names.");
  }
  await editorAction(
    { action: "duplicate_scene", name, new_name: newName },
    "duplicating scene",
  );
  elements.sceneName.value = newName;
}

async function restoreScene() {
  const entry = ((editorState && editorState.trash && editorState.trash.scenes) || [])[0];
  if (!entry) {
    throw new Error("No trashed scene is available.");
  }
  await editorAction(
    { action: "restore_scene", trash: entry.trash },
    "restoring scene",
  );
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

async function deleteSelection() {
  if (!editorState || !(editorState.selected_ids || []).length) {
    throw new Error("Select at least one node before deleting.");
  }
  await editorAction({ action: "delete_selection" }, "deleting selection");
  await refreshScene(false);
}

async function toggleSelectionVisible() {
  if (!editorState || !(editorState.selected_ids || []).length) {
    throw new Error("Select at least one node before toggling visibility.");
  }
  await editorAction(
    { action: "toggle_selection_visible" },
    "toggling selection visibility",
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

async function reparentNodeTo(nodeId, parentId) {
  if (!nodeId) {
    return;
  }
  await editorAction(
    { action: "reparent_node", id: nodeId, parent: parentId || "root" },
    "reparenting node",
  );
  await refreshScene(false);
}

function historyStepCount() {
  const steps = Number.parseInt(elements.historySteps.value, 10);
  if (!Number.isInteger(steps) || steps < 1 || steps > 100) {
    throw new Error("History steps must be an integer between 1 and 100.");
  }
  return steps;
}

async function undoEditor() {
  const steps = historyStepCount();
  await editorAction(
    { action: "undo", steps },
    `undoing ${steps} editor action${steps === 1 ? "" : "s"}`,
  );
  await refreshScene(false);
}

async function redoEditor() {
  const steps = historyStepCount();
  await editorAction(
    { action: "redo", steps },
    `redoing ${steps} editor action${steps === 1 ? "" : "s"}`,
  );
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
    restoreLayout();
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

const NUDGE_DIRECTIONS = {
  ArrowLeft: [-1, 0, 0],
  ArrowRight: [1, 0, 0],
  ArrowUp: [0, 0, -1],
  ArrowDown: [0, 0, 1],
  PageUp: [0, 1, 0],
  PageDown: [0, -1, 0],
};

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
  if (!modifier && (key === "w" || key === "e" || key === "r")) {
    event.preventDefault();
    setGizmoMode({ w: "translate", e: "rotate", r: "scale" }[key]);
    return;
  }
  if (!modifier && key === "x") {
    event.preventDefault();
    toggleGizmoSpace();
    return;
  }
  if (!modifier && key === "b") {
    event.preventDefault();
    toggleBoxSelect();
    return;
  }
  if (!modifier && key === "g") {
    event.preventDefault();
    toggleGrid();
    return;
  }
  if (!modifier && key === "s") {
    event.preventDefault();
    toggleSnap();
    return;
  }
  if (!modifier && key === "o") {
    event.preventDefault();
    toggleProjection();
    return;
  }
  const direction = NUDGE_DIRECTIONS[event.key];
  if (direction && editorState.selection) {
    event.preventDefault();
    const step = event.shiftKey ? 1.0 : 0.1;
    run(() =>
      nudgeSelection([
        direction[0] * step,
        direction[1] * step,
        direction[2] * step,
      ]),
    );
    return;
  }
  if (event.key === "Delete" && (editorState.selection_count || 0) > 0) {
    event.preventDefault();
    run(deleteSelection);
    return;
  }
  if (key === "f" && (editorState.selection_count || 0) > 0 && viewer) {
    event.preventDefault();
    if ((editorState.selection_count || 0) > 1) {
      viewer.focusSelection();
    } else {
      viewer.focusNode(editorState.selection.id);
    }
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
elements.viewMode.addEventListener("click", () => run(toggleViewMode));
elements.gridToggle.addEventListener("click", toggleGrid);
elements.snapToggle.addEventListener("click", toggleSnap);
for (const input of [
  elements.snapMove,
  elements.snapRotate,
  elements.snapScale,
]) {
  input.addEventListener("change", () => run(applySnapSteps));
}
elements.projectionMode.addEventListener("click", toggleProjection);
elements.layoutReset.addEventListener("click", resetLayout);
elements.viewFocus.addEventListener("click", () => {
  if (viewer && editorState && (editorState.selection_count || 0) > 0) {
    if ((editorState.selection_count || 0) > 1) {
      viewer.focusSelection();
    } else {
      viewer.focusNode(editorState.selection.id);
    }
  }
});
elements.step.addEventListener("click", () => run(() => simulate(1)));
elements.run.addEventListener("click", () => run(() => simulate(60)));
elements.simulate.addEventListener("click", () => run(() => simulate()));
elements.refresh.addEventListener("click", () => run(() => refreshScene(true)));
elements.editorRefresh.addEventListener("click", () => run(() => refreshEditor(true)));
elements.hierarchy.addEventListener("dragover", (event) => {
  if (event.target !== elements.hierarchy) {
    return;
  }
  event.preventDefault();
  event.dataTransfer.dropEffect = "move";
  elements.hierarchy.classList.add("drag-over");
});
elements.hierarchy.addEventListener("dragleave", (event) => {
  if (event.target === elements.hierarchy) {
    elements.hierarchy.classList.remove("drag-over");
  }
});
elements.hierarchy.addEventListener("drop", (event) => {
  if (event.target !== elements.hierarchy) {
    return;
  }
  event.preventDefault();
  elements.hierarchy.classList.remove("drag-over");
  const dragged = event.dataTransfer.getData("text/plain");
  if (dragged) {
    run(() => reparentNodeTo(dragged, "root"));
  }
});
elements.transformApply.addEventListener("click", () => run(applyTransform));
elements.playStart.addEventListener("click", () => run(playStart));
elements.playPause.addEventListener("click", () => run(playPause));
elements.playResume.addEventListener("click", () => run(playResume));
elements.playStep.addEventListener("click", () => run(playStep));
elements.playStop.addEventListener("click", () => run(playStop));
elements.animationPreview.addEventListener("click", () => run(previewAnimation));
elements.animationSample.addEventListener("click", () => run(sampleAnimationClip));
elements.animationPlay.addEventListener("click", () => run(toggleAnimationPlay));
elements.animationSave.addEventListener("click", () => run(saveAnimation));
elements.animationDelete.addEventListener("click", () => run(deleteAnimation));
elements.animationRestore.addEventListener("click", () => run(restoreAnimation));
elements.animationTime.addEventListener("input", () => {
  stopAnimationPlay();
  const time = Number(elements.animationTime.value);
  if (!Number.isFinite(time)) {
    return;
  }
  const max = Number(elements.animationScrub.max) || 1;
  elements.animationScrub.value = String(Math.min(Math.max(0, time), max));
});
elements.animationScrub.addEventListener("input", () => {
  stopAnimationPlay();
  elements.animationTime.value = elements.animationScrub.value;
});
elements.animationScrub.addEventListener("change", () => {
  stopAnimationPlay();
  run(previewAnimation);
});
elements.hierarchyFilter.addEventListener("input", () => {
  if (editorState) {
    renderHierarchy(editorState);
  }
});
elements.assetFilter.addEventListener("input", () => {
  if (editorState) {
    renderAssets(editorState);
  }
});
elements.meshAsset.addEventListener("change", updateAssetInfo);
elements.materialAsset.addEventListener("change", updateAssetInfo);
elements.assignAsset.addEventListener("click", () => run(assignAssets));
elements.importAsset.addEventListener("click", () => run(importAsset));
elements.reloadAssets.addEventListener("click", () => run(reloadAssets));
elements.forgetAsset.addEventListener("click", () => run(forgetAsset));
elements.findUsages.addEventListener("click", () => run(findUsages));
elements.buildProject.addEventListener("click", () => run(buildProject));
elements.materialSave.addEventListener("click", () => run(saveMaterial));
elements.materialAssign.addEventListener("click", () => run(assignMaterial));
elements.materialClear.addEventListener("click", () => run(clearMaterial));
elements.materialDelete.addEventListener("click", () => run(deleteMaterial));
elements.materialRestore.addEventListener("click", () => run(restoreMaterial));
elements.componentSet.addEventListener("click", () => run(setComponent));
elements.componentRemove.addEventListener("click", () => run(removeComponent));
elements.componentType.addEventListener("change", () => {
  fillComponentData(editorState && editorState.selection);
  renderComponentFields(editorState, editorState && editorState.selection);
});
elements.nodeCreate.addEventListener("click", () => run(createNode));
elements.nodeDuplicate.addEventListener("click", () => run(duplicateNode));
elements.nodeDelete.addEventListener("click", () => run(deleteSelection));
elements.selectionToggleVisible.addEventListener("click", () =>
  run(toggleSelectionVisible),
);
elements.boxSelect.addEventListener("click", toggleBoxSelect);
elements.nodeReparent.addEventListener("click", () => run(reparentNode));
elements.nodeProperties.addEventListener("click", () => run(applyNodeProperties));
elements.editorUndo.addEventListener("click", () => run(undoEditor));
elements.editorRedo.addEventListener("click", () => run(redoEditor));
elements.sceneSave.addEventListener("click", () => run(saveScene));
elements.sceneLoad.addEventListener("click", () => run(loadScene));
elements.sceneRevert.addEventListener("click", () => run(revertScene));
elements.startupSet.addEventListener("click", () => run(setStartupScene));
elements.startupClear.addEventListener("click", () => run(clearStartupScene));
elements.sceneDiff.addEventListener("click", () => run(diffScene));
elements.sceneRename.addEventListener("click", () => run(renameScene));
elements.sceneDuplicate.addEventListener("click", () => run(duplicateScene));
elements.sceneDelete.addEventListener("click", () => run(deleteScene));
elements.sceneRestore.addEventListener("click", () => run(restoreScene));
elements.sceneSettingsApply.addEventListener("click", () => run(applySceneSettings));
elements.sceneValidate.addEventListener("click", () => run(validateScene));
elements.cameraSettingsApply.addEventListener("click", () => run(applyCameraSettings));
elements.environmentSettingsApply.addEventListener("click", () =>
  run(applyEnvironmentSettings),
);
elements.prefabSave.addEventListener("click", () => run(savePrefab));
elements.prefabRename.addEventListener("click", () => run(renamePrefab));
elements.prefabDuplicate.addEventListener("click", () => run(duplicatePrefab));
elements.prefabDelete.addEventListener("click", () => run(deletePrefab));
elements.prefabRestore.addEventListener("click", () => run(restorePrefab));
elements.prefabInsert.addEventListener("click", () => run(insertPrefab));
elements.prefabRevert.addEventListener("click", () => run(revertPrefabInstance));
elements.prefabApply.addEventListener("click", () => run(applyPrefabInstance));
elements.prefabRefresh.addEventListener("click", () => run(refreshPrefabInstances));
elements.prefabEdit.addEventListener("click", () => run(editPrefab));
elements.prefabEditSave.addEventListener("click", () => run(savePrefabEdit));
elements.prefabEditClose.addEventListener("click", () => run(() => closePrefabEdit(true)));
elements.prefabEditDiscard.addEventListener("click", () => run(() => closePrefabEdit(false)));
elements.gizmoMove.addEventListener("click", () => setGizmoMode("translate"));
elements.gizmoRotate.addEventListener("click", () => setGizmoMode("rotate"));
elements.gizmoScale.addEventListener("click", () => setGizmoMode("scale"));
elements.gizmoSpace.addEventListener("click", toggleGizmoSpace);

init();
