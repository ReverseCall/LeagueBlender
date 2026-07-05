import struct
from typing import List, Optional
from dataclasses import dataclass

# Constantes
# =============

SCB_MAGIC = b"r3d2Mesh"

# Flags do campo flags no header
SCB_FLAG_HAS_VCP = 1 << 0   # core face por vértice
SCB_FLAG_HAS_LOCAL_ORIGIN_LOCATOR_PIVOT = 1 << 1   # pivô


# Estruturas de dados
# ----------------------

@dataclass
class SCBVertex:
    position: tuple


@dataclass
class SCBFace:
    indices: tuple
    material: str
    uvs: tuple
    vcp: Optional[tuple] = None


def flip_point(x: float, y: float, z: float) -> tuple:
    return (-x, -z, y)


def unflip_point(x: float, y: float, z: float) -> tuple:
    return (-x, z, -y)


def invert_winding(indices: tuple) -> tuple:

    # Inverte o winding das faces para manter as normais corretas
    i0, i1, i2 = indices
    return (i0, i2, i1)


@dataclass
class SCBFile:
    version_major: int
    version_minor: int
    name: str
    flags: int
    bounding_box: tuple
    central_point: tuple
    vertices: List[SCBVertex]
    faces: List[SCBFace]
    vertex_colors: Optional[List[tuple]] = None

    @property
    def version_str(self) -> str:
        return f"{self.version_major}.{self.version_minor}"

    @property
    def has_vertex_colors(self) -> bool:
        return self.vertex_colors is not None

    @property
    def has_vcp(self) -> bool:
        return bool(self.flags & SCB_FLAG_HAS_VCP)

    def flip(self):

        # Converte do espaço do jogo para o espaço do Blender
        for v in self.vertices:
            v.position = flip_point(*v.position)

        # central_point usa a mesma conversão de eixos que os vertices
        self.central_point = flip_point(*self.central_point)

    def unflip(self):

        # Converte do espaço do Blender de volta para o espaço do jogo.
        for v in self.vertices:
            v.position = unflip_point(*v.position)

        self.central_point = unflip_point(*self.central_point)


# BinaryStream
# ---------------

class _BS:
    __slots__ = ('data', 'pos')

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def pad(self, n: int):
        self.pos += n

    def read_bytes(self, n: int) -> bytes:
        b = self.data[self.pos:self.pos + n]
        self.pos += n
        return b

    def read_uint8(self) -> int:
        v = self.data[self.pos]; self.pos += 1; return v

    def read_uint16(self) -> int:
        v, = struct.unpack_from('<H', self.data, self.pos); self.pos += 2; return v

    def read_int32(self) -> int:
        v, = struct.unpack_from('<i', self.data, self.pos); self.pos += 4; return v

    def read_uint32(self) -> int:
        v, = struct.unpack_from('<I', self.data, self.pos); self.pos += 4; return v

    def read_float(self) -> float:
        v, = struct.unpack_from('<f', self.data, self.pos); self.pos += 4; return v

    def read_vec2(self) -> tuple:
        v = struct.unpack_from('<2f', self.data, self.pos); self.pos += 8; return v

    def read_vec3(self) -> tuple:
        v = struct.unpack_from('<3f', self.data, self.pos); self.pos += 12; return v

    def read_uint32_n(self, n: int) -> tuple:
        v = struct.unpack_from(f'<{n}I', self.data, self.pos); self.pos += 4*n; return v

    def read_float_n(self, n: int) -> tuple:
        v = struct.unpack_from(f'<{n}f', self.data, self.pos); self.pos += 4*n; return v

    def read_padded_ascii(self, n: int) -> str:
        raw = self.data[self.pos:self.pos + n]; self.pos += n
        return bytes(b for b in raw if b != 0).decode('ascii', errors='replace')


# Ponto de entrada publico
# ---------------------------

def read_scb(path: str) -> "SCBFile":
    
    # Le um arquivo SCB e retorna um SCBFile V2.1/3.2
    with open(path, 'rb') as f:
        data = f.read()

    bs = _BS(data)

    # Magic (8 bytes)
    magic = bs.read_bytes(8)
    if magic != SCB_MAGIC:
        raise ValueError(f"Magic inválido: {magic!r} (esperado {SCB_MAGIC!r})")

    version_major = bs.read_uint16()
    version_minor = bs.read_uint16()

    if version_major == 2:
        pass
    elif not (version_major == 3 and version_minor == 2):
        raise ValueError(f"Versão SCB não suportada: {version_major}.{version_minor}. Suportadas: 2.x e 3.2.")

    mesh_name = bs.read_padded_ascii(128)
    vertex_count = bs.read_int32()
    face_count = bs.read_int32()
    flags = bs.read_uint32()

    # Bounding box - 2x Vec3 (min, max)
    bb_min = bs.read_vec3()
    bb_max = bs.read_vec3()
    bounding_box = (bb_min, bb_max)

    # Extensão da versão 3.2
    has_vertex_colors_flag = False
    if version_major == 3 and version_minor == 2:
        has_vertex_colors_flag = bool(bs.read_uint32())

    # Vértices
    vertices: List[SCBVertex] = []
    for _ in range(vertex_count):
        pos = bs.read_vec3()
        vertices.append(SCBVertex(position=pos))

    # Cores de vértice por array
    vertex_colors: Optional[List[tuple]] = None
    if has_vertex_colors_flag:
        vertex_colors = []
        for _ in range(vertex_count):
            b = bs.read_uint8()
            g = bs.read_uint8()
            r = bs.read_uint8()
            a = bs.read_uint8()
            vertex_colors.append((b, g, r, a))

    # Ponto central
    central_point = bs.read_vec3()

    # ___ Faces ___
    has_vcp = bool(flags & SCB_FLAG_HAS_VCP)
    faces: List[SCBFace] = []
    for _ in range(face_count):
        indices = bs.read_uint32_n(3)
        material = bs.read_padded_ascii(64)

        u0, u1, u2, v0, v1, v2 = bs.read_float_n(6)
        uvs = ((u0, v0), (u1, v1), (u2, v2))

        faces.append(SCBFace(
            indices = indices,
            material = material,
            uvs = uvs,
            vcp = None,
        ))

    # ___ VCP ___
    if has_vcp:
        for face in faces:
            c0 = (bs.read_uint8(), bs.read_uint8(), bs.read_uint8())
            c1 = (bs.read_uint8(), bs.read_uint8(), bs.read_uint8())
            c2 = (bs.read_uint8(), bs.read_uint8(), bs.read_uint8())
            face.vcp = (c0, c1, c2)

    return SCBFile(
        version_major = version_major,
        version_minor = version_minor,
        name = mesh_name,
        flags = flags,
        bounding_box = bounding_box,
        central_point = central_point,
        vertices = vertices,
        faces = faces,
        vertex_colors = vertex_colors,
    )


# Serialização binaria
# ----------------------

def _no_negative_zero(vec: tuple) -> tuple:

    # Normaliza -0.0 para 0.0 (evita diferença de bits sem diferença de valor)
    return tuple(0.0 if c == 0.0 else c for c in vec)


def write_scb_binary(
    vertices: List[tuple],
    faces: List[dict],
    path: str,
    *,
    central_point: tuple = (0.0, 0.0, 0.0),
    flags: int = SCB_FLAG_HAS_LOCAL_ORIGIN_LOCATOR_PIVOT,
    vertex_colors: Optional[List[tuple]] = None,
    name: str = "",
):

    # Escreve um SCB v3.2; "name" (128 bytes) preserva o nome da color attribute entre import/export.
    vertex_count = len(vertices)
    face_count = len(faces)

    # Bounding box recalculada a partir dos vertices (ja em espaço de jogo)   | futuramente volta aqui para fazer melhorias visual para o usuario
    if vertex_count > 0:
        xs = [v[0] for v in vertices]
        ys = [v[1] for v in vertices]
        zs = [v[2] for v in vertices]
        bb_min = (min(xs), min(ys), min(zs))
        bb_max = (max(xs), max(ys), max(zs))
    else:
        bb_min = (0.0, 0.0, 0.0)
        bb_max = (0.0, 0.0, 0.0)

    has_vertex_colors = vertex_colors is not None
    has_vcp = bool(flags & SCB_FLAG_HAS_VCP)

    with open(path, 'wb') as f:

        # ___ Cabeçalho ___
        f.write(SCB_MAGIC)
        f.write(struct.pack('<HH', 3, 2))

        name_bytes = name.encode('ascii', errors='ignore')[:127]
        f.write(name_bytes + b'\x00' * (128 - len(name_bytes)))

        f.write(struct.pack('<iiI', vertex_count, face_count, flags))

        f.write(struct.pack('<3f', *bb_min))
        f.write(struct.pack('<3f', *bb_max))

        f.write(struct.pack('<I', 1 if has_vertex_colors else 0))

        # ___ Vertices ___
        for v in vertices:
            f.write(struct.pack('<3f', *_no_negative_zero(v)))

        # Cores de vértice (array por vertice)
        if has_vertex_colors:
            for c in vertex_colors:
                f.write(bytes(c))  # b, g, r, a

        # ___ Ponto central ___
        f.write(struct.pack('<3f', *_no_negative_zero(central_point)))

        # ___ Faces ___
        for face in faces:
            f.write(struct.pack('<3I', *face["indices"]))

            mat_bytes = face["material"].encode('ascii', errors='ignore')[:63]
            f.write(mat_bytes + b'\x00' * (64 - len(mat_bytes)))

            (u0, v0), (u1, v1), (u2, v2) = face["uvs"]
            f.write(struct.pack('<6f', u0, u1, u2, v0, v1, v2))

        # ___ VCP ___
        if has_vcp:
            for face in faces:
                vcp = face.get("vcp") or ((255, 255, 255), (255, 255, 255), (255, 255, 255))
                for c in vcp:
                    f.write(bytes(c))