"""
Versões suportadas
=====================
  0.x  Legacy        - formato antigo, so existe uma submesh
  1.x  Intermediaria - idêntica a v2 | talvez eu precise retrabalhar depos, mas não garanto nada
  2.x  Named ranges  - suporte para multipos submesh | depos eu tenho que erfatorar isso, para permitir a importação dessas mesh separadamente
  4.x  Full          - adiciona vertex types e bounding volumes

Flip
-------
  Apos o parsing os dados ainda estão no espaço do jogo
  Para converter pro espaço do Blender skn.flip()

    Isso faz:
        position.x *= -1
        normal.y *= -1
        normal.z *= -1
"""

import struct
from typing import List, Optional
from dataclasses import dataclass


# Constantes
# =============

SKN_MAGIC = 0x00112233

VERTEX_TYPE_BASIC = 0     # 52 bytes
VERTEX_TYPE_COLOR = 1     # 56 bytes
VERTEX_TYPE_TANGENT = 2   # 72 bytes


# Estruturas de dados
# ----------------------

@dataclass
class SKNSubmesh:
    name: str
    start_vertex: int
    vertex_count: int
    start_index: int
    index_count: int

    @property
    def face_count(self) -> int:
        return self.index_count // 3


@dataclass
class SKNVertex:
    position: tuple                   # (x, y, z)
    influences: bytes                 # u8[4] - bone indices
    weights: tuple                    # f32[4] - bone weights
    normal: tuple                     # (x, y, z)
    uv: tuple                         # (u, v)
    color: Optional[bytes] = None     # u8[4] RGBA  - vertex type 1+
    tangent: Optional[tuple] = None   # (x,y,z,w)  - vertex type 2


@dataclass
class SKNFile:
    version_major: int
    version_minor: int
    vertex_type: int
    submeshes: List[SKNSubmesh]
    indices: List[int]
    vertices: List[SKNVertex]
    flags: Optional[int] = None
    vertex_size: Optional[int] = None

    @property
    def version_str(self) -> str:
        return f"{self.version_major}.{self.version_minor}"

    @property
    def has_colors(self) -> bool:
        return self.vertex_type in (VERTEX_TYPE_COLOR, VERTEX_TYPE_TANGENT)

    @property
    def has_tangents(self) -> bool:
        return self.vertex_type == VERTEX_TYPE_TANGENT

    def flip(self):

        # Converte do espaço do jogo para o espaço do Blender
        for v in self.vertices:
            px, py, pz = v.position
            v.position = (-px, py, pz)
            if v.normal:
                nx, ny, nz = v.normal
                v.normal = (nx, -ny, -nz)


# Leitor binario
# -----------------

class _BS:
    # BinaryStream
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

    def read_uint16(self) -> int:
        v, = struct.unpack_from('<H', self.data, self.pos); self.pos += 2; return v

    def read_int32(self) -> int:
        v, = struct.unpack_from('<i', self.data, self.pos); self.pos += 4; return v

    def read_uint32(self) -> int:
        v, = struct.unpack_from('<I', self.data, self.pos); self.pos += 4; return v

    def read_float(self) -> float:
        v, = struct.unpack_from('<f', self.data, self.pos); self.pos += 4; return v

    def read_uint16_n(self, n: int) -> tuple:
        v = struct.unpack_from(f'<{n}H', self.data, self.pos); self.pos += 2*n; return v

    def read_uint32_n(self, n: int) -> tuple:
        v = struct.unpack_from(f'<{n}I', self.data, self.pos); self.pos += 4*n; return v

    def read_float_n(self, n: int) -> tuple:
        v = struct.unpack_from(f'<{n}f', self.data, self.pos); self.pos += 4*n; return v

    def read_vec2(self) -> tuple:
        v = struct.unpack_from('<2f', self.data, self.pos); self.pos += 8; return v

    def read_vec3(self) -> tuple:
        v = struct.unpack_from('<3f', self.data, self.pos); self.pos += 12; return v

    def read_vec4(self) -> tuple:
        v = struct.unpack_from('<4f', self.data, self.pos); self.pos += 16; return v

    def read_padded_ascii(self, n: int) -> str:
        raw = self.data[self.pos:self.pos + n]; self.pos += n
        return bytes(b for b in raw if b != 0).decode('ascii', errors = 'replace')


# Leitura de vertice por tipo
# ------------------------------

def _read_vertex(bs: _BS, vertex_type: int) -> SKNVertex:
    """
    Baseado no SKN.read() do lol_maya
    O Maya le position + influences + weights, pula normal (pad 12), le uv
    eu estou pegando a normal tbm para fazer alguns testes no Blender
    """
    position = bs.read_vec3()
    influences = bs.read_bytes(4)   # u8[4] bone indices
    weights = bs.read_float_n(4)    # f32[4] bone weights
    normal = bs.read_vec3()         # lido (maya faz pad)
    uv = bs.read_vec2()

    color = None
    tangent = None

    if vertex_type >= VERTEX_TYPE_COLOR:
        color = bs.read_bytes(4)   # u8[4] RGBA
    if vertex_type >= VERTEX_TYPE_TANGENT:
        tangent = bs.read_vec4()   # f32[4]

    return SKNVertex(
        position = position,
        influences = influences,
        weights = weights,
        normal = normal,
        uv = uv,
        color = color,
        tangent = tangent,
    )


# Ponto de entrada publico
# ---------------------------

def read_skn(path: str) -> SKNFile:
    """
    Lê um arquivo SKN e retorna um SKNFile
    SKN.read() do lol_maya
    Aceita major em (0, 1, 2, 4) - versão 1 tratada igual a 2. (coisa a se trabalhar melhor - depos)
    """
    with open(path, 'rb') as f:
        data = f.read()

    bs = _BS(data)

    magic = bs.read_uint32()
    if magic != SKN_MAGIC:
        raise ValueError(
            f"Magic invalido: 0x{magic:08X} (esperado 0x{SKN_MAGIC:08X})"
        )

    major = bs.read_uint16()
    minor = bs.read_uint16()

    # Maya) if major not in (0, 2, 4) and minor != 1 -> erro
    # Tratamos tambem major=1 (testado por engenharia "Reverse" pegou? kk)
    if major not in (0, 1, 2, 4):
        raise ValueError(
            f"Versão SKN não suportada: {major}.{minor}. "
            "Suportadas: 0, 1, 2 e 4."
        )

    vertex_type = VERTEX_TYPE_BASIC
    submeshes: List[SKNSubmesh] = []
    flags: Optional[int] = None

    if major == 0:
        # version 0 = sem submeshes - 1 submesh implicita "Base"
        index_count = bs.read_uint32()
        vertex_count = bs.read_uint32()
        submeshes = [SKNSubmesh('Base', 0, vertex_count, 0, index_count)]

    else:
        # major 1, 2, 4: lê submeshes
        submesh_count = bs.read_uint32()
        for _ in range(submesh_count):
            name = bs.read_padded_ascii(64)
            vs, vc, si, ic = bs.read_uint32_n(4)
            submeshes.append(SKNSubmesh(name, vs, vc, si, ic))

        if major == 4:
            flags = bs.read_uint32()   # flags

        index_count = bs.read_uint32()
        vertex_count = bs.read_uint32()

        if major == 4:
            bs.pad(4)    # vertex size
            vertex_type = bs.read_uint32()
            bs.pad(24)   # bounding box (2x vec3)
            bs.pad(16)   # bounding sphere (vec3 + float)

    # Valida
    if index_count % 3 != 0:
        raise ValueError(f"Contagem de indices invalida: {index_count}")

    # Indices - o Maya filtra faces degeneradas (3 indices iguais)
    # Essa parte faz o mesmo
    raw_faces = [bs.read_uint16_n(3) for _ in range(index_count // 3)]
    indices: List[int] = []
    for f in raw_faces:
        if not (f[0] == f[1] or f[1] == f[2] or f[2] == f[0]):
            indices.extend(f)

    # Vertices
    vertices = [_read_vertex(bs, vertex_type) for _ in range(vertex_count)]

    return SKNFile(
        version_major = major,
        version_minor = minor,
        vertex_type = vertex_type,
        submeshes = submeshes,
        indices = indices,
        vertices = vertices,
        flags = flags,
    )


# Serialização binaria
# ----------------------

def write_skn_binary_v1(submeshes: list, path: str):

    # Escreve o SKN (magic = 0x00112233, major = 1, minor = 1)
    all_verts = []
    all_idxs = []
    sm_headers = []

    # ___ Concatena todas as submeshes em buffers unicos ___
    for sm in submeshes:
        v_start = len(all_verts)
        i_start = len(all_idxs)
        all_idxs.extend([idx + v_start for idx in sm["indices"]])
        all_verts.extend(sm["verts"])
        sm_headers.append({
            "name": sm["name"],
            "v_start": v_start,
            "v_count": len(sm["verts"]),
            "i_start": i_start,
            "i_count": len(sm["indices"]),
        })

    with open(path, 'wb') as f:

        # ___ Cabeçalho + submesh headers ___
        f.write(struct.pack('<I', 0x00112233))
        f.write(struct.pack('<HH', 1, 1))
        f.write(struct.pack('<I', len(sm_headers)))
        for h in sm_headers:
            name_bytes = h["name"].encode('ascii', errors='ignore')[:63]
            f.write(name_bytes + b'\x00' * (64 - len(name_bytes)))
            f.write(struct.pack('<IIII',
                h["v_start"], h["v_count"],
                h["i_start"], h["i_count"]))

        # ___ Indices ___
        f.write(struct.pack('<II', len(all_idxs), len(all_verts)))
        for idx in all_idxs:
            f.write(struct.pack('<H', idx))

        # Vertices (52 bytes)
        for v in all_verts:
            f.write(struct.pack('<3f', *v["position"]))
            f.write(v["influences"])
            f.write(struct.pack('<4f', *v["weights"]))
            f.write(struct.pack('<3f', *v["normal"]))
            f.write(struct.pack('<2f', *v["uv"]))
