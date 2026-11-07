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

function link(gl) {
  const program = gl.createProgram();
  const vertex = compile(gl, gl.VERTEX_SHADER, VERTEX_SHADER);
  const fragment = compile(gl, gl.FRAGMENT_SHADER, FRAGMENT_SHADER);
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
    this.cameraState = null;
    this.dragging = false;
    this.lastPointer = [0, 0];
    this.canvas.addEventListener("pointerdown", (event) => {
      if (event.button !== 0) {
        return;
      }
      this.dragging = true;
      this.lastPointer = [event.clientX, event.clientY];
      this.canvas.setPointerCapture(event.pointerId);
      event.preventDefault();
    });
    this.canvas.addEventListener("pointermove", (event) => {
      if (!this.dragging || !this.cameraState) {
        return;
      }
      const dx = event.clientX - this.lastPointer[0];
      const dy = event.clientY - this.lastPointer[1];
      this.lastPointer = [event.clientX, event.clientY];
      this.cameraState.yaw -= dx * 0.01;
      this.cameraState.pitch = Math.max(
        -1.5,
        Math.min(1.5, this.cameraState.pitch - dy * 0.01),
      );
      this.render();
    });
    this.canvas.addEventListener("pointerup", (event) => {
      this.dragging = false;
      if (this.canvas.hasPointerCapture(event.pointerId)) {
        this.canvas.releasePointerCapture(event.pointerId);
      }
    });
    this.canvas.addEventListener("pointercancel", () => {
      this.dragging = false;
    });
    this.canvas.addEventListener(
      "wheel",
      (event) => {
        if (!this.cameraState) {
          return;
        }
        event.preventDefault();
        const factor = Math.exp(event.deltaY * 0.001);
        this.cameraState.distance = Math.max(
          0.5,
          Math.min(500, this.cameraState.distance * factor),
        );
        this.render();
      },
      { passive: false },
    );
    this.resize = this.resize.bind(this);
    window.addEventListener("resize", this.resize);
    this.resize();
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

  resetCamera() {
    this.cameraState = null;
    if (this.scene) {
      this.ensureCamera(this.scene);
    }
    this.render();
  }

  setSelected(nodeId) {
    this.selectedId = nodeId || null;
    this.render();
  }

  focusNode(nodeId) {
    if (!this.scene) {
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

  loadScene(scene) {
    this.clearScene();
    this.scene = scene;
    this.ensureCamera(scene);
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
      gl.uniform1f(this.uniforms.selected, node.id === this.selectedId ? 1 : 0);
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
  }
}
