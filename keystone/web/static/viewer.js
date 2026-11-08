const VERTEX_SHADER = `#version 300 es
layout(location = 0) in vec3 a_position;
layout(location = 1) in vec3 a_normal;
layout(location = 2) in vec3 a_color;
layout(location = 3) in vec2 a_uv;
uniform mat4 u_world;
uniform mat4 u_view_proj;
uniform mat3 u_normal;
out vec3 v_world;
out vec3 v_normal;
out vec2 v_uv;
out vec3 v_color;
void main() {
  vec4 world = u_world * vec4(a_position, 1.0);
  v_world = world.xyz;
  v_normal = u_normal * a_normal;
  v_uv = a_uv;
  v_color = a_color;
  gl_Position = u_view_proj * world;
}
`;

const FRAGMENT_SHADER = `#version 300 es
precision highp float;
in vec3 v_world;
in vec3 v_normal;
in vec2 v_uv;
in vec3 v_color;
uniform vec3 u_color;
uniform sampler2D u_texture;
uniform float u_has_texture;
uniform float u_specular;
uniform float u_shininess;
uniform float u_metallic;
uniform float u_roughness;
uniform vec3 u_emissive;
uniform float u_checker_scale;
uniform float u_selected;
uniform vec3 u_camera_pos;
uniform vec3 u_light_dir;
uniform vec3 u_light_color;
uniform vec3 u_ambient;
uniform vec3 u_fog_color;
uniform float u_fog_density;
uniform vec3 u_point_pos;
uniform vec3 u_point_color;
uniform float u_point_radius;
out vec4 frag_color;
void main() {
  vec3 normal = normalize(v_normal);
  vec3 to_eye = u_camera_pos - v_world;
  float distance = length(to_eye);
  vec3 view = to_eye / max(distance, 1e-4);
  vec3 light = normalize(-u_light_dir);
  float diffuse = max(dot(normal, light), 0.0);
  vec3 halfway = normalize(light + view);
  float dielectric_spec = pow(max(dot(normal, halfway), 0.0), max(u_shininess, 1.0)) * u_specular;
  float pbr_spec = pow(max(dot(normal, halfway), 0.0), mix(8.0, 128.0, 1.0 - u_roughness));
  float spec_strength = mix(dielectric_spec, pbr_spec, u_metallic) * (1.0 - u_roughness * 0.85);
  vec3 base_color = u_color * v_color;
  if (u_has_texture > 0.5) {
    base_color *= texture(u_texture, v_uv).rgb;
  }
  vec3 diffuse_color = base_color * (1.0 - u_metallic * 0.8);
  vec3 color = diffuse_color * (u_ambient + u_light_color * diffuse) + u_light_color * spec_strength + u_emissive;
  if (u_point_radius > 0.0) {
    vec3 to_point = u_point_pos - v_world;
    float point_distance = length(to_point);
    float attenuation = max(0.0, 1.0 - point_distance / u_point_radius);
    float point_diffuse = max(dot(normal, normalize(to_point)), 0.0);
    color += diffuse_color * u_point_color * attenuation * attenuation * point_diffuse;
  }
  if (u_checker_scale > 0.0) {
    float tile = mod(floor(v_world.x * u_checker_scale) + floor(v_world.z * u_checker_scale), 2.0);
    color *= mix(0.62, 1.0, tile);
  }
  float rim = pow(1.0 - max(dot(normal, view), 0.0), 2.0);
  color += vec3(0.18, 0.50, 0.38) * rim * u_selected;
  float fog = 1.0 - exp(-u_fog_density * u_fog_density * distance * distance);
  frag_color = vec4(mix(color, u_fog_color, clamp(fog, 0.0, 1.0)), 1.0);
}
`;

function compile(gl, type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const log = gl.getShaderInfoLog(shader) || "shader compilation failed";
    gl.deleteShader(shader);
    throw new Error(log);
  }
  return shader;
}

const GIZMO_VERTEX_SHADER = `#version 300 es
layout(location = 0) in vec3 a_position;
uniform mat4 u_mvp;
void main() {
  gl_Position = u_mvp * vec4(a_position, 1.0);
}
`;

const GIZMO_FRAGMENT_SHADER = `#version 300 es
precision highp float;
uniform vec3 u_color;
out vec4 frag_color;
void main() {
  frag_color = vec4(u_color, 1.0);
}
`;

function link(gl, vertexSource = VERTEX_SHADER, fragmentSource = FRAGMENT_SHADER) {
  const program = gl.createProgram();
  const vertex = compile(gl, gl.VERTEX_SHADER, vertexSource);
  const fragment = compile(gl, gl.FRAGMENT_SHADER, fragmentSource);
  gl.attachShader(program, vertex);
  gl.attachShader(program, fragment);
  gl.linkProgram(program);
  gl.deleteShader(vertex);
  gl.deleteShader(fragment);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    const log = gl.getProgramInfoLog(program) || "shader link failed";
    gl.deleteProgram(program);
    throw new Error(log);
  }
  return program;
}

function perspective(fovYDegrees, aspect, near, far) {
  const f = 1.0 / Math.tan((fovYDegrees * Math.PI) / 360.0);
  const depth = 1.0 / (near - far);
  return new Float32Array([
    f / aspect, 0, 0, 0,
    0, f, 0, 0,
    0, 0, (far + near) * depth, -1,
    0, 0, 2 * far * near * depth, 0,
  ]);
}

function orthographic(left, right, bottom, top, near, far) {
  const width = left - right;
  const height = bottom - top;
  const depth = near - far;
  return new Float32Array([
    -2 / width, 0, 0, 0,
    0, -2 / height, 0, 0,
    0, 0, 2 / depth, 0,
    (left + right) / width,
    (top + bottom) / height,
    (far + near) / depth,
    1,
  ]);
}

function multiply(left, right) {
  const out = new Float32Array(16);
  for (let column = 0; column < 4; column += 1) {
    for (let row = 0; row < 4; row += 1) {
      let sum = 0;
      for (let index = 0; index < 4; index += 1) {
        sum += left[index * 4 + row] * right[column * 4 + index];
      }
      out[column * 4 + row] = sum;
    }
  }
  return out;
}

function normalMatrix(matrix) {
  const a = matrix[0];
  const b = matrix[1];
  const c = matrix[2];
  const d = matrix[4];
  const e = matrix[5];
  const f = matrix[6];
  const g = matrix[8];
  const h = matrix[9];
  const i = matrix[10];
  const determinant = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g);
  if (Math.abs(determinant) < 1e-12) {
    return new Float32Array([1, 0, 0, 0, 1, 0, 0, 0, 1]);
  }
  const inverse = 1.0 / determinant;
  return new Float32Array([
    (e * i - f * h) * inverse,
    (c * h - b * i) * inverse,
    (b * f - c * e) * inverse,
    (f * g - d * i) * inverse,
    (a * i - c * g) * inverse,
    (c * d - a * f) * inverse,
    (d * h - e * g) * inverse,
    (b * g - a * h) * inverse,
    (a * e - b * d) * inverse,
  ]);
}

function subtract(left, right) {
  return [left[0] - right[0], left[1] - right[1], left[2] - right[2]];
}

function dot(left, right) {
  return left[0] * right[0] + left[1] * right[1] + left[2] * right[2];
}

function cross(left, right) {
  return [
    left[1] * right[2] - left[2] * right[1],
    left[2] * right[0] - left[0] * right[2],
    left[0] * right[1] - left[1] * right[0],
  ];
}

function length(value) {
  return Math.hypot(value[0], value[1], value[2]);
}

function normalize(value) {
  const size = length(value) || 1;
  return [value[0] / size, value[1] / size, value[2] / size];
}

function lookAt(eye, target, up = [0, 1, 0]) {
  const z = normalize(subtract(eye, target));
  const x = normalize(cross(up, z));
  const y = cross(z, x);
  return new Float32Array([
    x[0], y[0], z[0], 0,
    x[1], y[1], z[1], 0,
    x[2], y[2], z[2], 0,
    -dot(x, eye), -dot(y, eye), -dot(z, eye), 1,
  ]);
}

function rayBox(origin, direction, min, max) {
  let near = -Infinity;
  let far = Infinity;
  for (let axis = 0; axis < 3; axis += 1) {
    const start = origin[axis];
    const delta = direction[axis];
    if (Math.abs(delta) < 1e-8) {
      if (start < min[axis] || start > max[axis]) {
        return null;
      }
      continue;
    }
    let first = (min[axis] - start) / delta;
    let second = (max[axis] - start) / delta;
    if (first > second) {
      [first, second] = [second, first];
    }
    near = Math.max(near, first);
    far = Math.min(far, second);
    if (near > far) {
      return null;
    }
  }
  if (far < 0.0) {
    return null;
  }
  return near >= 0.0 ? near : far;
}

function pointSegmentDistance(px, py, ax, ay, bx, by) {
  const dx = bx - ax;
  const dy = by - ay;
  const lengthSquared = dx * dx + dy * dy;
  if (lengthSquared < 1e-9) {
    return Math.hypot(px - ax, py - ay);
  }
  const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / lengthSquared));
  return Math.hypot(px - (ax + dx * t), py - (ay + dy * t));
}

const BOX_FACES = [
  [0, 1, 2, 3],
  [4, 5, 6, 7],
  [0, 1, 5, 4],
  [3, 2, 6, 7],
  [0, 4, 7, 3],
  [1, 5, 6, 2],
];

function transformPoint(matrix, point) {
  return [
    matrix[0] * point[0] + matrix[4] * point[1] + matrix[8] * point[2] + matrix[12],
    matrix[1] * point[0] + matrix[5] * point[1] + matrix[9] * point[2] + matrix[13],
    matrix[2] * point[0] + matrix[6] * point[1] + matrix[10] * point[2] + matrix[14],
  ];
}

function clipNearPolygon(points, nearZ) {
  const clipped = [];
  for (let index = 0; index < points.length; index += 1) {
    const current = points[index];
    const next = points[(index + 1) % points.length];
    const currentInside = current[2] <= nearZ;
    const nextInside = next[2] <= nearZ;
    if (currentInside) {
      clipped.push(current);
    }
    if (currentInside !== nextInside) {
      const ratio = (nearZ - current[2]) / (next[2] - current[2]);
      clipped.push([
        current[0] + (next[0] - current[0]) * ratio,
        current[1] + (next[1] - current[1]) * ratio,
        nearZ,
      ]);
    }
  }
  return clipped;
}

function projectViewPoint(point, projection, rect) {
  const x =
    projection[0] * point[0] +
    projection[4] * point[1] +
    projection[8] * point[2] +
    projection[12];
  const y =
    projection[1] * point[0] +
    projection[5] * point[1] +
    projection[9] * point[2] +
    projection[13];
  const w =
    projection[3] * point[0] +
    projection[7] * point[1] +
    projection[11] * point[2] +
    projection[15];
  if (w <= 1e-5) {
    return null;
  }
  return [
    rect.left + ((x / w) * 0.5 + 0.5) * rect.width,
    rect.top + (1.0 - ((y / w) * 0.5 + 0.5)) * rect.height,
  ];
}

function pointInBox(point, min, max) {
  return (
    point[0] >= min[0] &&
    point[0] <= max[0] &&
    point[1] >= min[1] &&
    point[1] <= max[1] &&
    point[2] >= min[2] &&
    point[2] <= max[2]
  );
}

function pushBox(positions, start, end, half) {
  const corners = [
    [start, -half, -half], [start, half, -half], [start, half, half], [start, -half, half],
    [end, -half, -half], [end, half, -half], [end, half, half], [end, -half, half],
  ];
  const faces = [
    [0, 1, 2], [0, 2, 3],
    [4, 6, 5], [4, 7, 6],
    [0, 4, 5], [0, 5, 1],
    [1, 5, 6], [1, 6, 2],
    [2, 6, 7], [2, 7, 3],
    [3, 7, 4], [3, 4, 0],
  ];
  for (const [a, b, c] of faces) {
    for (const index of [a, b, c]) {
      positions.push(...corners[index]);
    }
  }
}

function gizmoArrow() {
  const positions = [];
  pushBox(positions, 0.08, 0.78, 0.035);
  const headHalf = 0.075;
  const headBase = 0.78;
  const baseCorners = [
    [headBase, -headHalf, -headHalf], [headBase, headHalf, -headHalf],
    [headBase, headHalf, headHalf], [headBase, -headHalf, headHalf],
  ];
  const tip = [1.0, 0.0, 0.0];
  for (let index = 0; index < 4; index += 1) {
    const first = baseCorners[index];
    const second = baseCorners[(index + 1) % 4];
    positions.push(...first, ...second, ...tip);
  }
  positions.push(...baseCorners[0], ...baseCorners[2], ...baseCorners[1]);
  positions.push(...baseCorners[0], ...baseCorners[3], ...baseCorners[2]);
  return { positions: new Float32Array(positions), count: positions.length / 3 };
}

function gizmoScaleArrow() {
  const positions = [];
  pushBox(positions, 0.08, 0.82, 0.025);
  pushBox(positions, 0.82, 0.98, 0.065);
  return { positions: new Float32Array(positions), count: positions.length / 3 };
}

function gizmoRing() {
  const positions = [];
  const segments = 48;
  const inner = 0.72;
  const outer = 0.78;
  for (let index = 0; index < segments; index += 1) {
    const first = (index / segments) * Math.PI * 2;
    const second = ((index + 1) / segments) * Math.PI * 2;
    const y0 = Math.cos(first);
    const z0 = Math.sin(first);
    const y1 = Math.cos(second);
    const z1 = Math.sin(second);
    positions.push(
      0, y0 * inner, z0 * inner,
      0, y1 * inner, z1 * inner,
      0, y1 * outer, z1 * outer,
      0, y0 * inner, z0 * inner,
      0, y1 * outer, z1 * outer,
      0, y0 * outer, z0 * outer,
    );
  }
  return { positions: new Float32Array(positions), count: positions.length / 3 };
}

function negate(value) {
  return [-value[0], -value[1], -value[2]];
}

function translationMatrix(offset) {
  return new Float32Array([
    1, 0, 0, 0,
    0, 1, 0, 0,
    0, 0, 1, 0,
    offset[0], offset[1], offset[2], 1,
  ]);
}

function axisAngleMatrix(axis, angle) {
  const [x, y, z] = normalize(axis);
  const cos = Math.cos(angle);
  const sin = Math.sin(angle);
  const rest = 1 - cos;
  return new Float32Array([
    rest * x * x + cos, rest * x * y + sin * z, rest * x * z - sin * y, 0,
    rest * x * y - sin * z, rest * y * y + cos, rest * y * z + sin * x, 0,
    rest * x * z + sin * y, rest * y * z - sin * x, rest * z * z + cos, 0,
    0, 0, 0, 1,
  ]);
}

function scaleMatrix(axis, factor) {
  return new Float32Array([
    axis === "x" ? factor : 1, 0, 0, 0,
    0, axis === "y" ? factor : 1, 0, 0,
    0, 0, axis === "z" ? factor : 1, 0,
    0, 0, 0, 1,
  ]);
}

function base64ToBytes(encoded) {
  const binary = atob(encoded);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

export class SceneViewer {
  constructor(canvas) {
    this.canvas = canvas;
    this.gl = canvas.getContext("webgl2", { antialias: true, alpha: false });
    if (!this.gl) {
      throw new Error("WebGL2 is not available in this browser.");
    }
    this.program = link(this.gl);
    this.gizmoProgram = link(this.gl, GIZMO_VERTEX_SHADER, GIZMO_FRAGMENT_SHADER);
    this.gizmoUniforms = {
      mvp: this.gl.getUniformLocation(this.gizmoProgram, "u_mvp"),
      color: this.gl.getUniformLocation(this.gizmoProgram, "u_color"),
    };
    this.gizmoArrow = this.buildGizmoVao(gizmoArrow());
    this.gizmoRing = this.buildGizmoVao(gizmoRing());
    this.gizmoScaleHandle = this.buildGizmoVao(gizmoScaleArrow());
    this.gridEnabled = true;
    this.snapEnabled = false;
    this.grid = this.buildGridVaos();
    this.pivotIcon = this.buildGizmoVao({
      positions: new Float32Array([
        -0.35, 0, 0, 0.35, 0, 0,
        0, -0.35, 0, 0, 0.35, 0,
        0, 0, -0.35, 0, 0, 0.35,
      ]),
      count: 6,
    });
    this.uniforms = {};
    for (const name of [
      "world", "view_proj", "normal", "color", "texture", "has_texture", "specular",
      "shininess", "metallic", "roughness", "emissive", "checker_scale", "selected", "camera_pos",
      "light_dir", "light_color", "ambient",
      "fog_color", "fog_density", "point_pos", "point_color", "point_radius",
    ]) {
      this.uniforms[name] = this.gl.getUniformLocation(this.program, `u_${name}`);
    }
    this.white = this.gl.createTexture();
    this.gl.bindTexture(this.gl.TEXTURE_2D, this.white);
    this.gl.texImage2D(
      this.gl.TEXTURE_2D, 0, this.gl.RGBA, 1, 1, 0, this.gl.RGBA, this.gl.UNSIGNED_BYTE,
      new Uint8Array([255, 255, 255, 255]),
    );
    this.meshes = new Map();
    this.textures = new Map();
    this.scene = null;
    this.selectedId = null;
    this.selectedIds = new Set();
    this.boxSelect = false;
    this.boxDrag = null;
    this.selectionBox = document.createElement("div");
    this.selectionBox.className = "selection-box";
    this.selectionBox.hidden = true;
    this.canvas.parentElement.appendChild(this.selectionBox);
    this.cameraState = null;
    this.nodeBounds = new Map();
    this.boxBounds = new Map();
    this.boxProxies = new Map();
    this.dragging = false;
    this.gizmoDrag = null;
    this.gizmoMode = "translate";
    this.gizmoSpace = "world";
    this.hoverAxis = null;
    this.editable = true;
    this.viewMode = "scene";
    this.projectionMode = "perspective";
    this.viewPreset = "persp";
    this.onProjectionMode = null;
    this.editorCameraState = null;
    this.onViewMode = null;
    this.onLayoutChange = null;
    this.pointerStart = [0, 0];
    this.pointerMoved = false;
    this.lastPointer = [0, 0];
    this.canvas.addEventListener("pointerdown", (event) => {
      if (this.viewMode === "game") {
        event.preventDefault();
        return;
      }
      if (event.button !== 0) {
        return;
      }
      const axis = this.gizmoAt(event.clientX, event.clientY);
      if (axis && this.beginGizmoDrag(axis, event)) {
        this.canvas.setPointerCapture(event.pointerId);
        event.preventDefault();
        return;
      }
      if (this.boxSelect && this.editable) {
        this.startBoxDrag(event);
        this.canvas.setPointerCapture(event.pointerId);
        event.preventDefault();
        return;
      }
      this.dragging = true;
      this.pointerStart = [event.clientX, event.clientY];
      this.pointerMoved = false;
      this.lastPointer = [event.clientX, event.clientY];
      this.canvas.setPointerCapture(event.pointerId);
      event.preventDefault();
    });
    this.canvas.addEventListener("pointermove", (event) => {
      if (this.viewMode === "game") {
        return;
      }
      if (this.boxDrag) {
        this.updateBoxDrag(event);
        event.preventDefault();
        return;
      }
      if (this.gizmoDrag) {
        this.updateGizmoDrag(event);
        event.preventDefault();
        return;
      }
      if (!this.dragging) {
        this.updateGizmoHover(event.clientX, event.clientY);
        return;
      }
      if (!this.cameraState) {
        return;
      }
      const dx = event.clientX - this.lastPointer[0];
      const dy = event.clientY - this.lastPointer[1];
      this.lastPointer = [event.clientX, event.clientY];
      if (
        Math.hypot(
          event.clientX - this.pointerStart[0],
          event.clientY - this.pointerStart[1],
        ) > 4
      ) {
        this.pointerMoved = true;
      }
      if (event.shiftKey) {
        const scale = this.cameraState.distance * 0.0015;
        const { right, up } = this.cameraBasis();
        this.cameraState.target = [
          this.cameraState.target[0] - right[0] * dx * scale + up[0] * dy * scale,
          this.cameraState.target[1] - right[1] * dx * scale + up[1] * dy * scale,
          this.cameraState.target[2] - right[2] * dx * scale + up[2] * dy * scale,
        ];
      } else {
        this.cameraState.yaw -= dx * 0.01;
        this.cameraState.pitch = Math.max(
          -1.5,
          Math.min(1.5, this.cameraState.pitch - dy * 0.01),
        );
      }
      this.render();
    });
    this.canvas.addEventListener("pointerup", (event) => {
      if (this.viewMode === "game") {
        return;
      }
      if (this.boxDrag) {
        this.finishBoxDrag(event);
        if (this.canvas.hasPointerCapture(event.pointerId)) {
          this.canvas.releasePointerCapture(event.pointerId);
        }
        return;
      }
      if (this.gizmoDrag) {
        this.finishGizmoDrag();
        if (this.canvas.hasPointerCapture(event.pointerId)) {
          this.canvas.releasePointerCapture(event.pointerId);
        }
        return;
      }
      const wasClick = !this.pointerMoved && !event.shiftKey;
      this.dragging = false;
      if (this.canvas.hasPointerCapture(event.pointerId)) {
        this.canvas.releasePointerCapture(event.pointerId);
      }
      if (wasClick) {
        this.selectAt(event.clientX, event.clientY, event);
      }
      this.notifyLayoutChange();
    });
    this.canvas.addEventListener("pointercancel", () => {
      this.cancelGizmoDrag();
      this.cancelBoxDrag();
      this.dragging = false;
    });
    this.canvas.addEventListener("pointerleave", () => {
      if (this.viewMode === "game") {
        return;
      }
      if (!this.dragging && !this.gizmoDrag && !this.boxDrag) {
        this.updateGizmoHover(-Infinity, -Infinity);
      }
    });
    this.canvas.addEventListener(
      "wheel",
      (event) => {
        if (!this.cameraState || this.viewMode === "game") {
          return;
        }
        event.preventDefault();
        const factor = Math.exp(event.deltaY * 0.001);
        this.cameraState.distance = Math.max(
          0.5,
          Math.min(500, this.cameraState.distance * factor),
        );
        this.render();
        this.notifyLayoutChange();
      },
      { passive: false },
    );
    this.resize = this.resize.bind(this);
    window.addEventListener("resize", this.resize);
    this.resize();
  }

  buildGizmoVao(geometry) {
    const gl = this.gl;
    const vao = gl.createVertexArray();
    const buffer = gl.createBuffer();
    gl.bindVertexArray(vao);
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, geometry.positions, gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);
    gl.bindVertexArray(null);
    return { vao, buffer, count: geometry.count };
  }

  buildGridVaos() {
    const half = 20;
    const majorEvery = 5;
    const minor = [];
    const major = [];
    for (let index = -half; index <= half; index += 1) {
      if (index === 0) {
        continue;
      }
      const target = index % majorEvery === 0 ? major : minor;
      target.push(-half, 0, index, half, 0, index);
      target.push(index, 0, -half, index, 0, half);
    }
    const line = (positions) =>
      this.buildGizmoVao({
        positions: new Float32Array(positions),
        count: positions.length / 3,
      });
    return {
      minor: line(minor),
      major: line(major),
      xAxis: line([-half, 0, 0, half, 0, 0]),
      zAxis: line([0, 0, -half, 0, 0, half]),
    };
  }

  setGrid(enabled) {
    this.gridEnabled = Boolean(enabled);
    this.render();
    this.notifyLayoutChange();
    return this.gridEnabled;
  }

  setSnap(enabled) {
    this.snapEnabled = Boolean(enabled);
    this.notifyLayoutChange();
    return this.snapEnabled;
  }

  snapActive(event) {
    return (
      this.snapEnabled ||
      Boolean(event && (event.ctrlKey || event.metaKey))
    );
  }

  ensureCamera(scene) {
    if (this.cameraState) {
      return;
    }
    const target = [0, 1, 0];
    const offset = subtract(scene.camera.position, target);
    const distance = Math.max(0.5, length(offset));
    this.cameraState = {
      target,
      distance,
      yaw: Math.atan2(offset[0], offset[2]),
      pitch: Math.asin(Math.max(-1, Math.min(1, offset[1] / distance))),
    };
  }

  cameraStateFromScene(scene) {
    if (!scene || !scene.camera) {
      return null;
    }
    const camera = scene.camera;
    const distance = 10.0;
    const cosPitch = Math.cos(camera.pitch);
    const forward = [
      -cosPitch * Math.sin(camera.yaw),
      -Math.sin(camera.pitch),
      -cosPitch * Math.cos(camera.yaw),
    ];
    return {
      target: [
        camera.position[0] + forward[0] * distance,
        camera.position[1] + forward[1] * distance,
        camera.position[2] + forward[2] * distance,
      ],
      distance,
      yaw: camera.yaw,
      pitch: camera.pitch,
    };
  }

  setViewMode(mode) {
    const next = mode === "game" ? "game" : "scene";
    if (next === this.viewMode) {
      return this.viewMode;
    }
    if (next === "game") {
      this.editorCameraState = this.cameraState
        ? {
            target: [...this.cameraState.target],
            distance: this.cameraState.distance,
            yaw: this.cameraState.yaw,
            pitch: this.cameraState.pitch,
          }
        : null;
      this.cameraState = this.cameraStateFromScene(this.scene);
    } else {
      this.cameraState =
        this.editorCameraState || this.cameraStateFromScene(this.scene);
      this.editorCameraState = null;
    }
    this.viewMode = next;
    this.cancelGizmoDrag();
    this.cancelBoxDrag();
    this.dragging = false;
    this.hoverAxis = null;
    this.canvas.style.cursor =
      this.viewMode === "scene" && this.boxSelect ? "crosshair" : "";
    if (typeof this.onViewMode === "function") {
      this.onViewMode(this.viewMode);
    }
    this.render();
    this.notifyLayoutChange();
    return this.viewMode;
  }

  setProjectionPreset(preset) {
    const next = ["persp", "top", "front", "side"].includes(preset)
      ? preset
      : "persp";
    if (next === "persp") {
      this.projectionMode = "perspective";
      this.viewPreset = "persp";
    } else {
      this.projectionMode = "ortho";
      this.viewPreset = next;
      if (!this.cameraState && this.scene) {
        this.ensureCamera(this.scene);
      }
      if (this.cameraState) {
        this.cameraState.yaw = next === "side" ? Math.PI / 2 : 0;
        this.cameraState.pitch = next === "top" ? Math.PI / 2 : 0;
        this.cameraState.distance = Math.max(1.0, this.cameraState.distance);
      }
    }
    this.cancelGizmoDrag();
    this.cancelBoxDrag();
    this.dragging = false;
    this.hoverAxis = null;
    this.canvas.style.cursor =
      this.viewMode === "scene" && this.boxSelect ? "crosshair" : "";
    if (typeof this.onProjectionMode === "function") {
      this.onProjectionMode(this.viewPreset);
    }
    this.render();
    this.notifyLayoutChange();
    return this.viewPreset;
  }

  layoutSnapshot() {
    const state =
      this.viewMode === "game" && this.editorCameraState
        ? this.editorCameraState
        : this.cameraState;
    return {
      camera: state
        ? {
            target: [...state.target],
            distance: state.distance,
            yaw: state.yaw,
            pitch: state.pitch,
          }
        : null,
      viewMode: this.viewMode,
      projection: this.viewPreset,
      grid: this.gridEnabled,
      snap: this.snapEnabled,
    };
  }

  applyLayout(layout) {
    if (!layout || typeof layout !== "object") {
      return false;
    }
    const camera = layout.camera;
    if (camera && typeof camera === "object") {
      const target =
        Array.isArray(camera.target) && camera.target.length === 3
          ? camera.target.map(Number)
          : null;
      const distance = Number(camera.distance);
      const yaw = Number(camera.yaw);
      const pitch = Number(camera.pitch);
      if (
        target &&
        target.every((value) => Number.isFinite(value)) &&
        Number.isFinite(distance) &&
        distance >= 0.5 &&
        distance <= 500 &&
        Number.isFinite(yaw) &&
        Number.isFinite(pitch)
      ) {
        this.cameraState = { target, distance, yaw, pitch };
      }
    }
    this.gridEnabled = Boolean(layout.grid);
    this.snapEnabled = Boolean(layout.snap);
    this.viewMode = layout.viewMode === "game" ? "game" : "scene";
    const projection = ["persp", "top", "front", "side"].includes(
      layout.projection,
    )
      ? layout.projection
      : "persp";
    this.viewPreset = projection;
    this.projectionMode =
      projection === "persp" ? "perspective" : "ortho";
    if (this.viewMode === "game") {
      this.editorCameraState = this.cameraState
        ? {
            target: [...this.cameraState.target],
            distance: this.cameraState.distance,
            yaw: this.cameraState.yaw,
            pitch: this.cameraState.pitch,
          }
        : null;
      this.cameraState = this.cameraStateFromScene(this.scene);
    }
    this.render();
    return true;
  }

  notifyLayoutChange() {
    if (typeof this.onLayoutChange === "function") {
      this.onLayoutChange();
    }
  }

  resetCamera() {
    if (this.viewMode === "game") {
      this.cameraState = this.cameraStateFromScene(this.scene);
    } else {
      this.cameraState = null;
      if (this.scene) {
        this.ensureCamera(this.scene);
      }
    }
    this.render();
    this.notifyLayoutChange();
  }

  setSelected(nodeId) {
    this.setSelectedIds(nodeId ? [nodeId] : []);
  }

  setSelectedIds(ids) {
    const selected = [];
    const seen = new Set();
    for (const nodeId of ids || []) {
      if (typeof nodeId === "string" && !seen.has(nodeId)) {
        seen.add(nodeId);
        selected.push(nodeId);
      }
    }
    this.selectedIds = new Set(selected);
    this.selectedId = selected[0] || null;
    this.cancelGizmoDrag();
    this.hoverAxis = null;
    this.render();
  }

  setEditable(value) {
    this.editable = Boolean(value);
    if (!this.editable) {
      this.cancelGizmoDrag();
      this.cancelBoxDrag();
      this.hoverAxis = null;
      this.canvas.style.cursor = "";
      this.render();
    }
  }

  setGizmoMode(mode) {
    if (!["translate", "rotate", "scale"].includes(mode)) {
      return;
    }
    this.gizmoMode = mode;
    this.cancelGizmoDrag();
    this.hoverAxis = null;
    this.canvas.style.cursor = "";
    this.render();
  }

  setGizmoSpace(space) {
    if (!["world", "local"].includes(space)) {
      return;
    }
    this.gizmoSpace = space;
    this.cancelGizmoDrag();
    this.hoverAxis = null;
    this.canvas.style.cursor = "";
    this.render();
  }

  selectedNode() {
    if (!this.scene || !this.selectedId) {
      return null;
    }
    return (this.scene.nodes || []).find((node) => node.id === this.selectedId) || null;
  }

  selectedNodes() {
    if (!this.scene || !this.selectedIds.size) {
      return [];
    }
    return (this.scene.nodes || []).filter((node) => this.selectedIds.has(node.id));
  }

  selectionRoots() {
    const byId = new Map(
      (this.scene ? this.scene.nodes || [] : []).map((node) => [node.id, node]),
    );
    return this.selectedNodes().filter((node) => {
      let parentId = node.parent_id;
      while (parentId) {
        if (this.selectedIds.has(parentId)) {
          return false;
        }
        const parent = byId.get(parentId);
        parentId = parent ? parent.parent_id : null;
      }
      return true;
    });
  }

  selectionOrigin() {
    const roots = this.selectionRoots();
    if (!roots.length) {
      return null;
    }
    const origin = [0, 0, 0];
    for (const node of roots) {
      const world = node.world || [];
      origin[0] += world[12] || 0;
      origin[1] += world[13] || 0;
      origin[2] += world[14] || 0;
    }
    return origin.map((value) => value / roots.length);
  }

  focusSelection() {
    if (!this.scene || this.viewMode === "game") {
      return;
    }
    const origin = this.selectionOrigin();
    if (!origin) {
      return;
    }
    this.ensureCamera(this.scene);
    this.cameraState.target = origin;
    this.cameraState.distance = Math.max(
      2.0,
      Math.min(12.0, this.cameraState.distance),
    );
    this.render();
    this.notifyLayoutChange();
  }

  setBoxSelect(enabled) {
    this.boxSelect = Boolean(enabled);
    this.cancelBoxDrag();
    this.canvas.style.cursor = this.boxSelect ? "crosshair" : "";
    this.render();
  }

  startBoxDrag(event) {
    this.boxDrag = {
      startX: event.clientX,
      startY: event.clientY,
      currentX: event.clientX,
      currentY: event.clientY,
    };
    this.selectionBox.hidden = false;
    this.updateBoxOverlay();
  }

  updateBoxDrag(event) {
    if (!this.boxDrag) {
      return;
    }
    this.boxDrag.currentX = event.clientX;
    this.boxDrag.currentY = event.clientY;
    this.updateBoxOverlay();
  }

  updateBoxOverlay() {
    const drag = this.boxDrag;
    if (!drag || !this.selectionBox.parentElement) {
      return;
    }
    const parent = this.selectionBox.parentElement.getBoundingClientRect();
    this.selectionBox.style.left = `${
      Math.min(drag.startX, drag.currentX) - parent.left
    }px`;
    this.selectionBox.style.top = `${
      Math.min(drag.startY, drag.currentY) - parent.top
    }px`;
    this.selectionBox.style.width = `${
      Math.abs(drag.currentX - drag.startX)
    }px`;
    this.selectionBox.style.height = `${
      Math.abs(drag.currentY - drag.startY)
    }px`;
  }

  finishBoxDrag(event) {
    const drag = this.boxDrag;
    this.boxDrag = null;
    this.selectionBox.hidden = true;
    if (!drag) {
      return;
    }
    const left = Math.min(drag.startX, drag.currentX);
    const right = Math.max(drag.startX, drag.currentX);
    const top = Math.min(drag.startY, drag.currentY);
    const bottom = Math.max(drag.startY, drag.currentY);
    if (right - left < 4 && bottom - top < 4) {
      return;
    }
    const mode = event.shiftKey
      ? "add"
      : event.ctrlKey || event.metaKey
        ? "toggle"
        : "replace";
    const hits = this.boxSelectionHits(left, top, right, bottom);
    if (typeof this.onBoxSelect === "function") {
      this.onBoxSelect(hits, mode);
    }
  }

  cancelBoxDrag() {
    this.boxDrag = null;
    if (this.selectionBox) {
      this.selectionBox.hidden = true;
    }
  }

  boxSelectionHits(left, top, right, bottom) {
    if (!this.scene || !this.cameraState) {
      return [];
    }
    const view = this.viewMatrix();
    const projection = this.projectionMatrix();
    const rect = this.canvas.getBoundingClientRect();
    if (!view || !projection || rect.width <= 0 || rect.height <= 0) {
      return [];
    }
    const nearZ = -this.scene.camera.near;
    const camera = this.cameraPosition();
    const hits = [];
    for (const [nodeId, bounds] of this.boxBounds.entries()) {
      const worldCorners = [
        [bounds.min[0], bounds.min[1], bounds.min[2]],
        [bounds.max[0], bounds.min[1], bounds.min[2]],
        [bounds.max[0], bounds.max[1], bounds.min[2]],
        [bounds.min[0], bounds.max[1], bounds.min[2]],
        [bounds.min[0], bounds.min[1], bounds.max[2]],
        [bounds.max[0], bounds.min[1], bounds.max[2]],
        [bounds.max[0], bounds.max[1], bounds.max[2]],
        [bounds.min[0], bounds.max[1], bounds.max[2]],
      ];
      const viewCorners = worldCorners.map((corner) =>
        transformPoint(view, corner),
      );
      const clipped = [];
      for (const face of BOX_FACES) {
        clipped.push(
          ...clipNearPolygon(
            face.map((index) => viewCorners[index]),
            nearZ,
          ),
        );
      }
      if (!clipped.length) {
        if (pointInBox(camera, bounds.min, bounds.max)) {
          hits.push(nodeId);
        }
        continue;
      }
      let minX = Infinity;
      let minY = Infinity;
      let maxX = -Infinity;
      let maxY = -Infinity;
      for (const point of clipped) {
        const screen = projectViewPoint(point, projection, rect);
        if (!screen) {
          continue;
        }
        minX = Math.min(minX, screen[0]);
        minY = Math.min(minY, screen[1]);
        maxX = Math.max(maxX, screen[0]);
        maxY = Math.max(maxY, screen[1]);
      }
      if (minX === Infinity) {
        continue;
      }
      if (maxX < left || minX > right || maxY < top || minY > bottom) {
        continue;
      }
      hits.push(nodeId);
    }
    for (const [nodeId, proxy] of this.boxProxies.entries()) {
      const viewPoint = transformPoint(view, proxy.position);
      const screen = projectViewPoint(viewPoint, projection, rect);
      if (!screen) {
        continue;
      }
      if (
        screen[0] >= left - 8 &&
        screen[0] <= right + 8 &&
        screen[1] >= top - 8 &&
        screen[1] <= bottom + 8
      ) {
        hits.push(nodeId);
      }
    }
    return hits;
  }

  focusNode(nodeId) {
    if (!this.scene || this.viewMode === "game") {
      return;
    }
    const node = (this.scene.nodes || []).find((item) => item.id === nodeId);
    if (!node) {
      return;
    }
    this.ensureCamera(this.scene);
    const world = node.world || [];
    this.cameraState.target = [
      world[12] || 0.0,
      world[13] || 0.0,
      world[14] || 0.0,
    ];
    this.cameraState.distance = Math.max(
      2.0,
      Math.min(12.0, this.cameraState.distance),
    );
    this.render();
    this.notifyLayoutChange();
  }

  cameraBasis() {
    const state = this.cameraState;
    if (!state) {
      return { right: [1, 0, 0], up: [0, 1, 0], forward: [0, 0, -1] };
    }
    const cosPitch = Math.cos(state.pitch);
    const forward = [
      -cosPitch * Math.sin(state.yaw),
      -Math.sin(state.pitch),
      -cosPitch * Math.cos(state.yaw),
    ];
    const right = normalize(cross(forward, [0, 1, 0]));
    const up = normalize(cross(right, forward));
    return { right, up, forward };
  }

  updateNodeBounds() {
    this.nodeBounds.clear();
    this.boxBounds.clear();
    this.boxProxies.clear();
    if (!this.scene) {
      return;
    }
    const meshes = this.scene.meshes || {};
    const identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
    for (const node of this.scene.nodes || []) {
      if (node.id === "root") {
        continue;
      }
      const mesh = node.mesh ? meshes[node.mesh] : null;
      const positions = (mesh && mesh.positions) || [];
      if (!positions.length) {
        const world = node.world || identity;
        this.boxProxies.set(node.id, {
          position: [world[12] || 0, world[13] || 0, world[14] || 0],
        });
        continue;
      }
      const world = node.world || identity;
      let minX = Infinity;
      let minY = Infinity;
      let minZ = Infinity;
      let maxX = -Infinity;
      let maxY = -Infinity;
      let maxZ = -Infinity;
      for (let index = 0; index < positions.length; index += 3) {
        const x = positions[index];
        const y = positions[index + 1];
        const z = positions[index + 2];
        const wx = world[0] * x + world[4] * y + world[8] * z + world[12];
        const wy = world[1] * x + world[5] * y + world[9] * z + world[13];
        const wz = world[2] * x + world[6] * y + world[10] * z + world[14];
        minX = Math.min(minX, wx);
        minY = Math.min(minY, wy);
        minZ = Math.min(minZ, wz);
        maxX = Math.max(maxX, wx);
        maxY = Math.max(maxY, wy);
        maxZ = Math.max(maxZ, wz);
      }
      const bounds = {
        min: [minX, minY, minZ],
        max: [maxX, maxY, maxZ],
      };
      this.boxBounds.set(node.id, bounds);
      if (node.visible) {
        this.nodeBounds.set(node.id, bounds);
      }
    }
  }

  rayAt(clientX, clientY) {
    if (!this.scene || !this.cameraState) {
      return null;
    }
    const rect = this.canvas.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) {
      return null;
    }
    const x = ((clientX - rect.left) / rect.width) * 2.0 - 1.0;
    const y = 1.0 - ((clientY - rect.top) / rect.height) * 2.0;
    const tangent = Math.tan((this.scene.camera.fov_y * Math.PI) / 360.0);
    const aspect = rect.width / rect.height;
    const { right, up, forward } = this.cameraBasis();
    return {
      origin: this.cameraPosition(),
      direction: normalize([
        forward[0] + right[0] * x * aspect * tangent + up[0] * y * tangent,
        forward[1] + right[1] * x * aspect * tangent + up[1] * y * tangent,
        forward[2] + right[2] * x * aspect * tangent + up[2] * y * tangent,
      ]),
      rect,
    };
  }

  selectAt(clientX, clientY, event = null) {
    const ray = this.rayAt(clientX, clientY);
    if (!ray) {
      return;
    }
    let bestId = null;
    let bestDistance = Infinity;
    for (const [nodeId, bounds] of this.nodeBounds.entries()) {
      const distance = rayBox(ray.origin, ray.direction, bounds.min, bounds.max);
      if (distance !== null && distance < bestDistance) {
        bestDistance = distance;
        bestId = nodeId;
      }
    }
    if (typeof this.onSelect === "function") {
      this.onSelect(bestId, {
        shift: Boolean(event && event.shiftKey),
        ctrl: Boolean(event && event.ctrlKey),
        meta: Boolean(event && event.metaKey),
      });
    }
  }

  gizmoAxes() {
    const colors = {
      x: [0.93, 0.29, 0.32],
      y: [0.36, 0.88, 0.42],
      z: [0.36, 0.58, 0.97],
    };
    const node = this.selectedNode();
    if (
      this.selectedIds.size > 1 ||
      (this.gizmoMode === "translate" && this.gizmoSpace === "world")
    ) {
      return [
        {
          name: "x",
          vector: [1, 0, 0],
          basis: [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
          color: colors.x,
        },
        {
          name: "y",
          vector: [0, 1, 0],
          basis: [[0, 1, 0], [-1, 0, 0], [0, 0, 1]],
          color: colors.y,
        },
        {
          name: "z",
          vector: [0, 0, 1],
          basis: [[0, 0, 1], [0, 1, 0], [-1, 0, 0]],
          color: colors.z,
        },
      ];
    }
    const world = (node && node.world) || [];
    const x = normalize([world[0] || 1, world[1] || 0, world[2] || 0]);
    const y = normalize([world[4] || 0, world[5] || 1, world[6] || 0]);
    const z = normalize([world[8] || 0, world[9] || 0, world[10] || 1]);
    return [
      { name: "x", vector: x, basis: [x, y, z], color: colors.x },
      { name: "y", vector: y, basis: [y, negate(x), z], color: colors.y },
      { name: "z", vector: z, basis: [z, y, negate(x)], color: colors.z },
    ];
  }

  gizmoScale(origin) {
    const distance = length(subtract(this.cameraPosition(), origin));
    return Math.max(0.2, Math.min(40, distance * 0.12));
  }

  projectToScreen(point, matrix, rect) {
    const x = matrix[0] * point[0] + matrix[4] * point[1] + matrix[8] * point[2] + matrix[12];
    const y = matrix[1] * point[0] + matrix[5] * point[1] + matrix[9] * point[2] + matrix[13];
    const w = matrix[3] * point[0] + matrix[7] * point[1] + matrix[11] * point[2] + matrix[15];
    if (w <= 1e-5) {
      return null;
    }
    return [
      rect.left + ((x / w) * 0.5 + 0.5) * rect.width,
      rect.top + (1.0 - ((y / w) * 0.5 + 0.5)) * rect.height,
    ];
  }

  gizmoAt(clientX, clientY) {
    if (
      !this.editable ||
      this.viewMode !== "scene" ||
      !this.scene ||
      !this.selectedIds.size
    ) {
      return null;
    }
    const matrix = this.viewProjectionMatrix();
    if (!matrix) {
      return null;
    }
    const rect = this.canvas.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) {
      return null;
    }
    const origin = this.selectionOrigin();
    if (!origin) {
      return null;
    }
    const scale = this.gizmoScale(origin);
    const start = this.projectToScreen(origin, matrix, rect);
    if (!start) {
      return null;
    }
    let best = null;
    let bestDistance = 10.0;
    const handles = this.gizmoAxes();
    if (this.gizmoMode === "rotate") {
      for (const handle of handles) {
        const distance = this.ringDistance(
          clientX,
          clientY,
          origin,
          handle,
          scale,
          matrix,
          rect,
        );
        if (distance < bestDistance) {
          best = handle.name;
          bestDistance = distance;
        }
      }
      return best;
    }
    for (const handle of handles) {
      const end = this.projectToScreen(
        [
          origin[0] + handle.vector[0] * scale,
          origin[1] + handle.vector[1] * scale,
          origin[2] + handle.vector[2] * scale,
        ],
        matrix,
        rect,
      );
      if (!end) {
        continue;
      }
      const distance = pointSegmentDistance(
        clientX,
        clientY,
        start[0],
        start[1],
        end[0],
        end[1],
      );
      if (distance < bestDistance) {
        best = handle.name;
        bestDistance = distance;
      }
    }
    return best;
  }

  ringDistance(clientX, clientY, origin, handle, scale, matrix, rect) {
    const basis = handle.basis;
    const radius = 0.75 * scale;
    let previous = null;
    let best = Infinity;
    for (let index = 0; index <= 32; index += 1) {
      const angle = (index / 32) * Math.PI * 2;
      const cosine = Math.cos(angle);
      const sine = Math.sin(angle);
      const point = [
        origin[0] + (basis[1][0] * cosine + basis[2][0] * sine) * radius,
        origin[1] + (basis[1][1] * cosine + basis[2][1] * sine) * radius,
        origin[2] + (basis[1][2] * cosine + basis[2][2] * sine) * radius,
      ];
      const screen = this.projectToScreen(point, matrix, rect);
      if (!screen) {
        previous = null;
        continue;
      }
      if (previous) {
        best = Math.min(
          best,
          pointSegmentDistance(
            clientX,
            clientY,
            previous[0],
            previous[1],
            screen[0],
            screen[1],
          ),
        );
      }
      previous = screen;
    }
    return best;
  }

  updateGizmoHover(clientX, clientY) {
    const axis = this.gizmoAt(clientX, clientY);
    if (axis === this.hoverAxis) {
      return;
    }
    this.hoverAxis = axis;
    this.canvas.style.cursor = axis
      ? "grab"
      : this.boxSelect
        ? "crosshair"
        : "";
    this.render();
  }

  axisParameter(clientX, clientY, origin, axis) {
    const ray = this.rayAt(clientX, clientY);
    if (!ray) {
      return null;
    }
    const denominator = dot(ray.direction, axis);
    if (Math.abs(denominator) > 0.2) {
      const distance = dot(subtract(origin, ray.origin), axis) / denominator;
      if (distance < 0) {
        return null;
      }
      return dot(
        subtract(
          [
            ray.origin[0] + ray.direction[0] * distance,
            ray.origin[1] + ray.direction[1] * distance,
            ray.origin[2] + ray.direction[2] * distance,
          ],
          origin,
        ),
        axis,
      );
    }
    const w0 = subtract(origin, ray.origin);
    const b = dot(axis, ray.direction);
    const d = dot(axis, w0);
    const e = dot(ray.direction, w0);
    const swing = 1.0 - b * b;
    if (Math.abs(swing) < 1e-6) {
      return null;
    }
    return (b * e - d) / swing;
  }

  previewBases(nodeId) {
    const ids = new Set([nodeId]);
    let changed = true;
    while (changed) {
      changed = false;
      for (const node of this.scene.nodes || []) {
        if (node.parent_id && ids.has(node.parent_id) && !ids.has(node.id)) {
          ids.add(node.id);
          changed = true;
        }
      }
    }
    return (this.scene.nodes || [])
      .filter((node) => ids.has(node.id))
      .map((node) => ({ node, world: Array.from(node.world) }));
  }

  previewBasesForSelection() {
    const ids = new Set(this.selectionRoots().map((node) => node.id));
    let changed = true;
    while (changed) {
      changed = false;
      for (const node of this.scene.nodes || []) {
        if (node.parent_id && ids.has(node.parent_id) && !ids.has(node.id)) {
          ids.add(node.id);
          changed = true;
        }
      }
    }
    return (this.scene.nodes || [])
      .filter((node) => ids.has(node.id))
      .map((node) => ({ node, world: Array.from(node.world) }));
  }

  beginGizmoDrag(axis, event) {
    if (!this.editable) {
      return false;
    }
    const origin = this.selectionOrigin();
    const handle = this.gizmoAxes().find((item) => item.name === axis);
    if (!origin || !handle) {
      return false;
    }
    const multi = this.selectedIds.size > 1;
    const mode = this.gizmoMode;
    const bases = multi
      ? this.previewBasesForSelection()
      : this.previewBases(this.selectedId);
    if (mode === "rotate") {
      const basis = this.ringBasis(handle.vector);
      const start = this.rotationVector(
        event.clientX,
        event.clientY,
        origin,
        handle.vector,
        basis,
      );
      if (start === null) {
        return false;
      }
      this.gizmoDrag = {
        mode: "rotate",
        axis,
        vector: handle.vector,
        origin,
        basis,
        start,
        angle: 0,
        bases,
        selection: false,
      };
    } else {
      const start = this.axisParameter(
        event.clientX,
        event.clientY,
        origin,
        handle.vector,
      );
      if (start === null) {
        return false;
      }
      this.gizmoDrag = {
        mode,
        axis,
        vector: handle.vector,
        origin,
        start,
        delta: [0, 0, 0],
        factor: 1,
        bases,
        selection: multi,
      };
    }
    this.hoverAxis = axis;
    this.canvas.style.cursor = "grabbing";
    this.render();
    return true;
  }

  ringBasis(axis) {
    const helper = Math.abs(axis[1]) < 0.9 ? [0, 1, 0] : [1, 0, 0];
    const u = normalize(cross(axis, helper));
    const v = cross(axis, u);
    return { u, v };
  }

  rotationVector(clientX, clientY, origin, axis, basis) {
    const ray = this.rayAt(clientX, clientY);
    if (!ray) {
      return null;
    }
    const denominator = dot(ray.direction, axis);
    if (Math.abs(denominator) < 1e-5) {
      return null;
    }
    const distance = dot(subtract(origin, ray.origin), axis) / denominator;
    if (distance < 0) {
      return null;
    }
    const point = [
      ray.origin[0] + ray.direction[0] * distance,
      ray.origin[1] + ray.direction[1] * distance,
      ray.origin[2] + ray.direction[2] * distance,
    ];
    const relative = subtract(point, origin);
    return [dot(relative, basis.u), dot(relative, basis.v)];
  }

  updateGizmoDrag(event) {
    const drag = this.gizmoDrag;
    if (!drag) {
      return;
    }
    if (drag.mode === "rotate") {
      const current = this.rotationVector(
        event.clientX,
        event.clientY,
        drag.origin,
        drag.vector,
        drag.basis,
      );
      if (current === null) {
        return;
      }
      let angle = Math.atan2(
        drag.start[0] * current[1] - drag.start[1] * current[0],
        drag.start[0] * current[0] + drag.start[1] * current[1],
      );
      if (this.snapActive(event)) {
        const step = Math.PI / 12;
        angle = Math.round(angle / step) * step;
      }
      drag.angle = Math.round(angle * 1e6) / 1e6;
      const transform = multiply(
        multiply(
          translationMatrix(drag.origin),
          axisAngleMatrix(drag.vector, drag.angle),
        ),
        translationMatrix(negate(drag.origin)),
      );
      for (const base of drag.bases) {
        base.node.world = multiply(transform, base.world);
      }
      this.render();
      return;
    }
    const current = this.axisParameter(
      event.clientX,
      event.clientY,
      drag.origin,
      drag.vector,
    );
    if (current === null) {
      return;
    }
    if (drag.mode === "scale") {
      let factor = 1 + (current - drag.start) / (this.gizmoScale(drag.origin) * 2.0);
      if (this.snapActive(event)) {
        factor = Math.round(factor / 0.1) * 0.1;
      }
      factor = Math.max(0.01, Math.round(factor * 1e6) / 1e6);
      drag.factor = factor;
      if (drag.selection) {
        const transform = multiply(
          multiply(
            translationMatrix(drag.origin),
            scaleMatrix(drag.axis, factor),
          ),
          translationMatrix(negate(drag.origin)),
        );
        for (const base of drag.bases) {
          base.node.world = multiply(transform, base.world);
        }
      } else {
        const matrix = scaleMatrix(drag.axis, factor);
        for (const base of drag.bases) {
          base.node.world = multiply(base.world, matrix);
        }
      }
      this.render();
      return;
    }
    let distance = current - drag.start;
    if (this.snapActive(event)) {
      distance = Math.round(distance / 0.25) * 0.25;
    }
    distance = Math.round(distance * 1e6) / 1e6;
    drag.delta = [
      drag.vector[0] * distance,
      drag.vector[1] * distance,
      drag.vector[2] * distance,
    ];
    for (const base of drag.bases) {
      base.node.world[12] = base.world[12] + drag.delta[0];
      base.node.world[13] = base.world[13] + drag.delta[1];
      base.node.world[14] = base.world[14] + drag.delta[2];
    }
    this.render();
  }

  finishGizmoDrag() {
    const drag = this.gizmoDrag;
    this.gizmoDrag = null;
    this.hoverAxis = null;
    this.canvas.style.cursor = "";
    if (!drag) {
      return;
    }
    for (const base of drag.bases) {
      base.node.world = Array.from(base.world);
    }
    if (drag.mode === "rotate") {
      if (drag.angle !== 0) {
        if (drag.selection && typeof this.onRotateSelection === "function") {
          this.onRotateSelection(
            drag.axis,
            (drag.angle * 180) / Math.PI,
            drag.origin,
          );
        } else if (typeof this.onRotate === "function") {
          this.onRotate(drag.axis, (drag.angle * 180) / Math.PI);
        }
      }
    } else if (drag.mode === "scale") {
      if (drag.factor !== 1) {
        if (drag.selection && typeof this.onScaleSelection === "function") {
          this.onScaleSelection(drag.axis, drag.factor, drag.origin);
        } else if (typeof this.onScale === "function") {
          this.onScale(drag.axis, drag.factor);
        }
      }
    } else if (drag.selection) {
      if (
        (drag.delta[0] !== 0 ||
          drag.delta[1] !== 0 ||
          drag.delta[2] !== 0) &&
        typeof this.onTransformSelection === "function"
      ) {
        this.onTransformSelection(drag.delta);
      }
    } else if (
      (drag.delta[0] !== 0 || drag.delta[1] !== 0 || drag.delta[2] !== 0) &&
      typeof this.onTransform === "function"
    ) {
      this.onTransform(drag.axis, drag.delta);
    }
    this.render();
  }

  cancelGizmoDrag() {
    const drag = this.gizmoDrag;
    this.gizmoDrag = null;
    if (!drag) {
      return;
    }
    for (const base of drag.bases) {
      base.node.world = Array.from(base.world);
    }
    this.hoverAxis = null;
    this.canvas.style.cursor = "";
    this.render();
  }

  cameraPosition() {
    const state = this.cameraState;
    if (!state) {
      return [0, 0, 0];
    }
    const cosPitch = Math.cos(state.pitch);
    return [
      state.target[0] + state.distance * cosPitch * Math.sin(state.yaw),
      state.target[1] + state.distance * Math.sin(state.pitch),
      state.target[2] + state.distance * cosPitch * Math.cos(state.yaw),
    ];
  }

  viewMatrix() {
    if (!this.cameraState) {
      return new Float32Array(this.scene.camera.view);
    }
    return lookAt(this.cameraPosition(), this.cameraState.target);
  }

  projectionMatrix() {
    if (!this.scene) {
      return null;
    }
    const camera = this.scene.camera;
    const aspect =
      Math.max(1, this.canvas.width) / Math.max(1, this.canvas.height);
    if (this.projectionMode === "ortho" && this.viewMode === "scene") {
      const height = Math.max(
        1.0,
        this.cameraState ? this.cameraState.distance : 10.0,
      );
      const width = height * aspect;
      return orthographic(
        -width / 2,
        width / 2,
        -height / 2,
        height / 2,
        camera.near,
        camera.far,
      );
    }
    return perspective(camera.fov_y, aspect, camera.near, camera.far);
  }

  viewProjectionMatrix() {
    const projection = this.projectionMatrix();
    if (!projection) {
      return null;
    }
    return multiply(projection, this.viewMatrix());
  }

  loadScene(scene) {
    this.clearScene();
    this.scene = scene;
    if (this.viewMode === "game") {
      this.cameraState = this.cameraStateFromScene(scene);
    } else {
      this.ensureCamera(scene);
    }
    this.updateNodeBounds();
    for (const [id, mesh] of Object.entries(scene.meshes || {})) {
      this.meshes.set(id, this.uploadMesh(mesh));
    }
    for (const [id, texture] of Object.entries(scene.textures || {})) {
      this.textures.set(id, this.uploadTexture(texture));
    }
    this.resize();
  }

  clearScene() {
    const gl = this.gl;
    for (const mesh of this.meshes.values()) {
      gl.deleteVertexArray(mesh.vao);
      for (const buffer of mesh.buffers) {
        gl.deleteBuffer(buffer);
      }
    }
    for (const texture of this.textures.values()) {
      gl.deleteTexture(texture);
    }
    this.meshes.clear();
    this.textures.clear();
  }

  uploadMesh(mesh) {
    const gl = this.gl;
    const vao = gl.createVertexArray();
    const buffers = [];
    gl.bindVertexArray(vao);
    const attrib = (location, values, size) => {
      const buffer = gl.createBuffer();
      buffers.push(buffer);
      gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(values), gl.STATIC_DRAW);
      gl.enableVertexAttribArray(location);
      gl.vertexAttribPointer(location, size, gl.FLOAT, false, 0, 0);
    };
    const vertexCount = mesh.positions.length / 3;
    attrib(0, mesh.positions, 3);
    attrib(1, mesh.normals, 3);
    attrib(2, mesh.colors.length ? mesh.colors : new Array(vertexCount * 3).fill(1), 3);
    attrib(3, mesh.uvs.length ? mesh.uvs : new Array(vertexCount * 2).fill(0), 2);
    const indices = new Uint32Array(mesh.indices);
    const element = gl.createBuffer();
    buffers.push(element);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, element);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, indices, gl.STATIC_DRAW);
    gl.bindVertexArray(null);
    return { vao, buffers, count: indices.length };
  }

  uploadTexture(texture) {
    const gl = this.gl;
    const result = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, result);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
    gl.texImage2D(
      gl.TEXTURE_2D, 0, gl.RGBA, texture.width, texture.height, 0,
      gl.RGBA, gl.UNSIGNED_BYTE, base64ToBytes(texture.rgba_base64),
    );
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
    gl.generateMipmap(gl.TEXTURE_2D);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.bindTexture(gl.TEXTURE_2D, null);
    return result;
  }

  resize() {
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    const width = Math.max(1, Math.floor(this.canvas.clientWidth * ratio));
    const height = Math.max(1, Math.floor(this.canvas.clientHeight * ratio));
    if (this.canvas.width !== width || this.canvas.height !== height) {
      this.canvas.width = width;
      this.canvas.height = height;
    }
    this.render();
  }

  render() {
    const gl = this.gl;
    gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    if (!this.scene) {
      gl.clearColor(0.03, 0.045, 0.07, 1);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      return;
    }
    const scene = this.scene;
    const background = scene.atmosphere.background;
    gl.clearColor(background[0], background[1], background[2], 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.DEPTH_TEST);
    gl.depthFunc(gl.LEQUAL);
    gl.enable(gl.CULL_FACE);
    gl.cullFace(gl.BACK);
    gl.frontFace(gl.CCW);
    gl.useProgram(this.program);

    const camera = scene.camera;
    const projection = perspective(
      camera.fov_y,
      this.canvas.width / this.canvas.height,
      camera.near,
      camera.far,
    );
    const viewProjection = multiply(projection, this.viewMatrix());
    gl.uniformMatrix4fv(this.uniforms.view_proj, false, viewProjection);
    gl.uniform3fv(this.uniforms.camera_pos, this.cameraPosition());
    gl.uniform3fv(this.uniforms.light_dir, scene.light.direction);
    gl.uniform3fv(this.uniforms.light_color, scene.light.color.map((value) => value * scene.light.intensity));
    gl.uniform3fv(this.uniforms.ambient, scene.atmosphere.ambient);
    gl.uniform3fv(this.uniforms.fog_color, background);
    gl.uniform1f(this.uniforms.fog_density, scene.atmosphere.fog_density);
    gl.uniform1i(this.uniforms.texture, 0);

    const point = scene.point_light;
    if (point) {
      gl.uniform3fv(this.uniforms.point_pos, point.position);
      gl.uniform3fv(this.uniforms.point_color, point.color.map((value) => value * point.intensity));
      gl.uniform1f(this.uniforms.point_radius, point.radius);
    } else {
      gl.uniform3f(this.uniforms.point_pos, 0, 0, 0);
      gl.uniform3f(this.uniforms.point_color, 0, 0, 0);
      gl.uniform1f(this.uniforms.point_radius, 0);
    }

    for (const node of scene.nodes) {
      if (!node.visible || !node.mesh) {
        continue;
      }
      const mesh = this.meshes.get(node.mesh);
      if (!mesh) {
        continue;
      }
      const material = node.material || {
        color: [1, 1, 1], specular: 0, shininess: 1, checker_scale: 0, texture: null,
        metallic: 0, roughness: 0.7, emissive: [0, 0, 0],
      };
      gl.uniform3fv(this.uniforms.color, material.color);
      gl.uniform1f(this.uniforms.specular, material.specular);
      gl.uniform1f(this.uniforms.shininess, material.shininess);
      gl.uniform1f(this.uniforms.metallic, material.metallic || 0);
      gl.uniform1f(this.uniforms.roughness, material.roughness ?? 0.7);
      gl.uniform3fv(this.uniforms.emissive, material.emissive || [0, 0, 0]);
      gl.uniform1f(this.uniforms.checker_scale, material.checker_scale || 0);
      gl.uniform1f(
        this.uniforms.selected,
        this.viewMode === "scene" && this.selectedIds.has(node.id) ? 1 : 0,
      );
      const texture = material.texture ? this.textures.get(material.texture) : null;
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, texture || this.white);
      gl.uniform1f(this.uniforms.has_texture, texture ? 1 : 0);
      gl.uniformMatrix4fv(this.uniforms.world, false, new Float32Array(node.world));
      gl.uniformMatrix3fv(this.uniforms.normal, false, normalMatrix(node.world));
      gl.bindVertexArray(mesh.vao);
      gl.drawElements(gl.TRIANGLES, mesh.count, gl.UNSIGNED_INT, 0);
    }
    gl.bindVertexArray(null);
    this.renderPivots(viewProjection);
    this.renderGrid(viewProjection);
    this.renderGizmo(viewProjection);
  }

  renderPivots(viewProjection) {
    if (this.viewMode !== "scene" || !this.boxProxies.size) {
      return;
    }
    const gl = this.gl;
    gl.useProgram(this.gizmoProgram);
    gl.disable(gl.CULL_FACE);
    for (const [nodeId, proxy] of this.boxProxies.entries()) {
      const position = proxy.position;
      const scale = Math.max(0.05, this.gizmoScale(position) * 0.45);
      const model = new Float32Array([
        scale, 0, 0, 0,
        0, scale, 0, 0,
        0, 0, scale, 0,
        position[0], position[1], position[2], 1,
      ]);
      gl.uniformMatrix4fv(
        this.gizmoUniforms.mvp,
        false,
        multiply(viewProjection, model),
      );
      gl.uniform3fv(
        this.gizmoUniforms.color,
        this.selectedIds.has(nodeId)
          ? [0.46, 0.84, 0.77]
          : [0.95, 0.72, 0.42],
      );
      gl.bindVertexArray(this.pivotIcon.vao);
      gl.drawArrays(gl.LINES, 0, this.pivotIcon.count);
    }
    gl.bindVertexArray(null);
    gl.enable(gl.CULL_FACE);
  }

  renderGrid(viewProjection) {
    if (!this.gridEnabled || this.viewMode !== "scene") {
      return;
    }
    const gl = this.gl;
    const draw = (geometry, color) => {
      gl.uniform3fv(this.gizmoUniforms.color, color);
      gl.bindVertexArray(geometry.vao);
      gl.drawArrays(gl.LINES, 0, geometry.count);
    };
    gl.useProgram(this.gizmoProgram);
    gl.disable(gl.CULL_FACE);
    gl.uniformMatrix4fv(this.gizmoUniforms.mvp, false, viewProjection);
    draw(this.grid.minor, [0.22, 0.25, 0.30]);
    draw(this.grid.major, [0.34, 0.38, 0.45]);
    draw(this.grid.xAxis, [0.62, 0.24, 0.24]);
    draw(this.grid.zAxis, [0.24, 0.38, 0.62]);
    gl.bindVertexArray(null);
    gl.enable(gl.CULL_FACE);
  }

  renderGizmo(viewProjection) {
    if (!this.editable || this.viewMode !== "scene") {
      return;
    }
    const nodes = this.selectedNodes();
    if (!nodes.length) {
      return;
    }
    const origin = this.selectionOrigin();
    if (!origin) {
      return;
    }
    const gl = this.gl;
    const scale = this.gizmoScale(origin);
    const active = this.gizmoDrag ? this.gizmoDrag.axis : this.hoverAxis;
    const geometry = this.gizmoMode === "rotate"
      ? this.gizmoRing
      : this.gizmoMode === "scale"
        ? this.gizmoScaleHandle
        : this.gizmoArrow;
    gl.useProgram(this.gizmoProgram);
    gl.disable(gl.DEPTH_TEST);
    gl.disable(gl.CULL_FACE);
    for (const handle of this.gizmoAxes()) {
      const highlighted = handle.name === active;
      const color = handle.color.map((value) =>
        highlighted ? Math.min(1, value + 0.45) : value,
      );
      const basis = handle.basis;
      const model = new Float32Array([
        basis[0][0] * scale, basis[0][1] * scale, basis[0][2] * scale, 0,
        basis[1][0] * scale, basis[1][1] * scale, basis[1][2] * scale, 0,
        basis[2][0] * scale, basis[2][1] * scale, basis[2][2] * scale, 0,
        origin[0], origin[1], origin[2], 1,
      ]);
      gl.uniformMatrix4fv(
        this.gizmoUniforms.mvp,
        false,
        multiply(viewProjection, model),
      );
      gl.uniform3fv(this.gizmoUniforms.color, color);
      gl.bindVertexArray(geometry.vao);
      gl.drawArrays(gl.TRIANGLES, 0, geometry.count);
    }
    gl.bindVertexArray(null);
    gl.enable(gl.DEPTH_TEST);
    gl.enable(gl.CULL_FACE);
  }
}
