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
uniform float u_checker_scale;
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
  float specular = pow(max(dot(normal, halfway), 0.0), max(u_shininess, 1.0)) * u_specular;
  vec3 base_color = u_color * v_color;
  if (u_has_texture > 0.5) {
    base_color *= texture(u_texture, v_uv).rgb;
  }
  vec3 color = base_color * (u_ambient + u_light_color * diffuse) + u_light_color * specular;
  if (u_point_radius > 0.0) {
    vec3 to_point = u_point_pos - v_world;
    float point_distance = length(to_point);
    float attenuation = max(0.0, 1.0 - point_distance / u_point_radius);
    float point_diffuse = max(dot(normal, normalize(to_point)), 0.0);
    color += base_color * u_point_color * attenuation * attenuation * point_diffuse;
  }
  if (u_checker_scale > 0.0) {
    float tile = mod(floor(v_world.x * u_checker_scale) + floor(v_world.z * u_checker_scale), 2.0);
    color *= mix(0.62, 1.0, tile);
  }
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
      "shininess", "checker_scale", "camera_pos", "light_dir", "light_color", "ambient",
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
    this.resize = this.resize.bind(this);
    window.addEventListener("resize", this.resize);
    this.resize();
  }

  loadScene(scene) {
    this.clearScene();
    this.scene = scene;
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
    const viewProjection = multiply(projection, new Float32Array(camera.view));
    gl.uniformMatrix4fv(this.uniforms.view_proj, false, viewProjection);
    gl.uniform3fv(this.uniforms.camera_pos, camera.position);
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
      };
      gl.uniform3fv(this.uniforms.color, material.color);
      gl.uniform1f(this.uniforms.specular, material.specular);
      gl.uniform1f(this.uniforms.shininess, material.shininess);
      gl.uniform1f(this.uniforms.checker_scale, material.checker_scale || 0);
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
