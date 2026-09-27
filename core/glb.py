"""
Tiny GLB (binary glTF 2.0) reader written with only json, struct and NumPy.

A .glb file is laid out like this:

    12-byte header  ->  magic "glTF", version, total length
    chunk 0 (JSON)  ->  describes nodes, meshes, accessors ...
    chunk 1 (BIN)   ->  raw bytes for vertex positions and triangle indices

We read the JSON with `json`, the header with `struct`, and turn the
binary buffer into arrays with `numpy.frombuffer`.
"""

import json
import struct
from pathlib import Path

import numpy as np

# glTF componentType code -> NumPy dtype
COMPONENT_DTYPES = {
    5120: np.int8,
    5121: np.uint8,
    5122: np.int16,
    5123: np.uint16,
    5125: np.uint32,
    5126: np.float32,
}

# How many numbers make up one element of each accessor type
TYPE_SIZES = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def read_glb(path):
    """Return (gltf_json: dict, binary_buffer: bytes) for a .glb file."""
    data = Path(path).read_bytes()

    magic, version, total_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2:
        raise ValueError(f"{path} is not a glTF 2.0 binary file")

    gltf, binary = None, b""
    offset = 12
    while offset < total_length:
        chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
        chunk = data[offset + 8: offset + 8 + chunk_length]
        if chunk_type == 0x4E4F534A:      # "JSON"
            gltf = json.loads(chunk)
        elif chunk_type == 0x004E4942:    # "BIN\0"
            binary = chunk
        offset += 8 + chunk_length

    return gltf, binary


def read_accessor(gltf, binary, index):
    """Turn one glTF accessor into a NumPy array of shape (count, size)."""
    acc = gltf["accessors"][index]
    view = gltf["bufferViews"][acc["bufferView"]]
    dtype = np.dtype(COMPONENT_DTYPES[acc["componentType"]])
    size = TYPE_SIZES[acc["type"]]
    count = acc["count"]

    start = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    stride = view.get("byteStride", 0)
    item_bytes = dtype.itemsize * size

    if stride and stride != item_bytes:
        # interleaved data: read every row with the given stride
        raw = np.frombuffer(binary, dtype=np.uint8, count=stride * (count - 1) + item_bytes, offset=start)
        rows = np.lib.stride_tricks.as_strided(raw, shape=(count, item_bytes), strides=(stride, 1))
        return rows.copy().view(dtype).reshape(count, size)

    return np.frombuffer(binary, dtype=dtype, count=count * size, offset=start).reshape(count, size)


def node_matrix(node):
    """Local 4x4 transform of a node (either a matrix or translation/rotation/scale)."""
    if "matrix" in node:
        # glTF stores matrices column by column
        return np.array(node["matrix"], dtype=float).reshape(4, 4).T

    t = np.array(node.get("translation", [0, 0, 0]), dtype=float)
    x, y, z, w = node.get("rotation", [0, 0, 0, 1])
    s = np.array(node.get("scale", [1, 1, 1]), dtype=float)

    rotation = np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])
    m = np.eye(4)
    m[:3, :3] = rotation * s        # scale each column
    m[:3, 3] = t
    return m


def load_mesh_parts(path):
    """
    Walk the scene graph and return a list of parts:
        {"name": str, "vertices": (N, 3) float array, "faces": (M, 3) int array}
    Vertices are already moved into world space.
    """
    gltf, binary = read_glb(path)
    parts = []

    def visit(node_index, parent_matrix):
        node = gltf["nodes"][node_index]
        world = parent_matrix @ node_matrix(node)

        if "mesh" in node:
            mesh = gltf["meshes"][node["mesh"]]
            for primitive in mesh["primitives"]:
                if primitive.get("mode", 4) != 4:       # only triangle lists
                    continue
                positions = read_accessor(gltf, binary, primitive["attributes"]["POSITION"]).astype(float)
                if "indices" in primitive:
                    faces = read_accessor(gltf, binary, primitive["indices"]).reshape(-1, 3).astype(np.int64)
                else:
                    faces = np.arange(len(positions)).reshape(-1, 3)

                # apply the 4x4 transform to every vertex at once
                homogeneous = np.c_[positions, np.ones(len(positions))]
                world_positions = (homogeneous @ world.T)[:, :3]

                parts.append({
                    "name": node.get("name") or mesh.get("name") or f"part {len(parts) + 1}",
                    "vertices": world_positions,
                    "faces": faces,
                })

        for child in node.get("children", []):
            visit(child, world)

    scene = gltf["scenes"][gltf.get("scene", 0)]
    for root in scene["nodes"]:
        visit(root, np.eye(4))

    return parts


def normalize_parts(parts, target_size=2.0):
    """Center the whole model on the origin and scale its longest side to `target_size`."""
    all_vertices = np.vstack([p["vertices"] for p in parts])
    low, high = all_vertices.min(axis=0), all_vertices.max(axis=0)
    center = (low + high) / 2
    scale = target_size / (high - low).max()
    for p in parts:
        p["vertices"] = (p["vertices"] - center) * scale
    return parts


def model_stats(parts, path):
    """Small summary used on the landing page and the How-it-works page."""
    return {
        "parts": len(parts),
        "vertices": int(sum(len(p["vertices"]) for p in parts)),
        "triangles": int(sum(len(p["faces"]) for p in parts)),
        "file_mb": Path(path).stat().st_size / 1_000_000,
    }
