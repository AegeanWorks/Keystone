# Keystone

[![Built with AIKit](https://img.shields.io/badge/built%20with-AIKit-6f42c1)](https://github.com/AegeanWorks/AIKit)

A performance-first 3D game engine in Python with an OpenGL 3.3 renderer, scene graph, OBJ assets and a headless-testable core.

## ⚡ 30-Second Cold-Start Quick Reference

- **Runtime Prerequisites**: Python 3.10+ with the pinned `requirements.txt` stack (numpy 2.5.3, PyOpenGL 3.1.10, glfw 2.11.0, pytest 9.1.1) and an OpenGL 3.3-capable GPU driver.
- **Install**: `python -m pip install -r requirements.txt`
- **Canonical Regression Shield Gate**:
  ```bash
  python -m pytest -q
  ```

### 🛠️ AIKit Commands (run from the AIKit folder)
| Role | Command |
|---|---|
| Status, task and gates | `python aikit.py status keystone` |
| Phase 4: every gate | `python aikit.py check keystone` |
| Repair memory and map, then check | `python aikit.py fix keystone` |
| Resume an interrupted task | `python aikit.py resume keystone` |

## 📦 What's Inside

```text
keystone/
├── keystone/
│   ├── __init__.py           <- package surface and version
│   ├── math3d.py             <- Vec3, Mat4, Quat (column-major, OpenGL-ready)
│   ├── camera.py             <- perspective camera and fly-style movement
│   ├── scene.py              <- hierarchy, transforms, light and scene root
│   ├── geometry.py           <- indexed mesh data and Blinn-Phong material
│   ├── primitives.py         <- cube, ground plane and UV sphere
│   └── obj_loader.py         <- streaming Wavefront OBJ loader
├── assets/
│   └── octahedron.obj        <- sample OBJ asset
├── tests/
│   ├── test_math3d.py        <- unit tests for the math core
│   ├── test_scene.py         <- unit tests for hierarchy and camera
│   └── test_geometry.py      <- unit tests for meshes, primitives and OBJ
├── requirements.txt          <- pinned runtime and test dependencies
├── pyproject.toml            <- package metadata and pytest configuration
├── .gitignore                <- transient AIKit state excluded
├── LICENSE                   <- Aegean License 1.1 (AL-1.1): free personal use
├── COMMERCIAL.md             <- Commercial licensing terms
├── LICENSES/                 <- REUSE license texts
├── REUSE.toml                <- Machine-readable SPDX metadata
├── README.md
└── .aikit/                   <- this project's memory: record, ledger, decisions
```

## 📜 License

Free for personal use under the Aegean License 1.1 (AL-1.1); see [LICENSE](LICENSE). Any commercial use needs the Aegean Commercial License 1.0 (ACL-1.0); see [COMMERCIAL.md](COMMERCIAL.md).
