import struct
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# Estruturas de Dados
# ======================

@dataclass
class SKLJoint:
    name: str = ""
    parent: int = -1
    hash: int = 0
    radius: float = 2.0
    
    # Trasformações locais
    local_translation: Tuple[float, float, float] = (0, 0, 0)
    local_scale: Tuple[float, float, float] = (1, 1, 1)
    local_rotation: Tuple[float, float, float, float] = (0, 0, 0, 1) # (x, y, z, w)
    
    # Inverse Bind Pose
    iglobal_translation: Optional[Tuple[float, float, float]] = None
    iglobal_scale: Optional[Tuple[float, float, float]] = None
    iglobal_rotation: Optional[Tuple[float, float, float, float]] = None
    
    # Global Matrix
    global_matrix: Optional[List[float]] = None


@dataclass
class SKLFile:
    version: int = 0
    joints: List[SKLJoint] = field(default_factory = list)
    influences: List[int] = field(default_factory = list)

    def flip(self):

        # Converte do espaço LoL (Y-up) para (Z-up) do Blender
        for j in self.joints:

            # ___ local ___
            tx, ty, tz = j.local_translation
            j.local_translation = (-tx, ty, tz)
            rx, ry, rz, rw = j.local_rotation
            j.local_rotation = (rx, -ry, -rz, rw)
            
            # ___ Global Inversa ___
            if j.iglobal_translation is not None:
                ix, iy, iz = j.iglobal_translation
                j.iglobal_translation = (-ix, iy, iz)
                irx, iry, irz, irw = j.iglobal_rotation
                j.iglobal_rotation = (irx, -iry, -irz, irw)


# Assistente de fluxo binario
# ------------------------------

class _BS:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def read(self, fmt: str):
        size = struct.calcsize(fmt)
        v = struct.unpack_from(fmt, self.data, self.pos)
        self.pos += size
        return v[0] if len(v) == 1 else v

    def seek(self, pos: int): self.pos = pos
    def tell(self) -> int: return self.pos
    def pad(self, n: int): self.pos += n

    def read_vec3(self): return self.read('<3f')
    def read_quat(self): return self.read('<4f')
    def read_ascii(self, length: int):
        raw = self.data[self.pos:self.pos + length]
        self.pos += length
        return raw.split(b'\x00')[0].decode('ascii', errors = 'ignore')

    def read_char_until_zero(self):
        s = []
        while self.pos < len(self.data):
            c = self.data[self.pos]
            self.pos += 1
            if c == 0: break
            s.append(chr(c))
        return "".join(s)


# Parser
# ---------

def read_skl(path: str) -> SKLFile:
    with open(path, 'rb') as f:
        data = f.read()
    
    bs = _BS(data)
    skl = SKLFile()
    
    # Cabeçalho: 4 bytes de tamanho do recursp + 4 bytes para o identificador do formato "magic/token"
    bs.pad(4) 
    magic = bs.read('<I')
    
    if magic == 0x22FD4FC3:

        # ___ SKL Morderno ___
        skl.version = bs.read('<I')
        bs.pad(2)
        joint_count = bs.read('<H')
        influence_count = bs.read('<I')
        joints_offset = bs.read('<i')
        bs.pad(4)
        influences_offset = bs.read('<i')
        bs.pad(32)

        if joints_offset > 0 and joint_count > 0:
            bs.seek(joints_offset)
            for i in range(joint_count):
                j = SKLJoint()
                bs.pad(4)
                j.parent = bs.read('<h')
                bs.pad(2)
                j.hash = bs.read('<I')
                j.radius = bs.read('<f')
                j.local_translation = bs.read_vec3()
                j.local_scale = bs.read_vec3()
                j.local_rotation = bs.read_quat()
                j.iglobal_translation = bs.read_vec3()
                j.iglobal_scale = bs.read_vec3()
                j.iglobal_rotation = bs.read_quat()
                
                name_offset = bs.read('<i')
                ret = bs.tell()
                bs.seek(ret - 4 + name_offset)
                j.name = bs.read_char_until_zero()
                if i == 0 and j.name == "": # Hack root
                    bs.pad(1)
                    j.name = bs.read_char_until_zero()
                if not j.name: j.name = f"Joint_{j.hash:08X}"
                
                bs.seek(ret)
                skl.joints.append(j)

        if influences_offset > 0 and influence_count > 0:
            bs.seek(influences_offset)
            skl.influences = list(struct.unpack_from(f'<{influence_count}H', data, bs.tell()))

    else:

        # ___ Legacy SKL ___
        """
        isso esta aqui so para evitar erros!
        pelo oq eu vi não tem mais nem um SKL legado mas no jogo. mas eu posso esta errado.
        o unico que eu sabia de cabeça era o do Aatrox, e esse ja foi atualizado depos da troca dos arquivos 
        DDS para TEX :)
        (nota: acho que aatrox na verdade não era legado, e sim major=1)
        """
        bs.seek(0)
        magic_str = bs.read_ascii(8)
        if magic_str != "r3d2sklt":
            raise ValueError(f"Formato SKL invalido: {magic_str}")
        
        skl.version = bs.read('<I')
        bs.pad(4)
        joint_count = bs.read('<I')
        
        for i in range(joint_count):
            j = SKLJoint()
            j.name = bs.read_ascii(32)
            j.parent = bs.read('<i')
            bs.pad(4)

            # Matriz 3x4 (Global)
            mat_data = bs.read('<12f')

            # Armazena como lista para conversão posterior se necessario
            j.global_matrix = list(mat_data)
            skl.joints.append(j)
            
        if skl.version == 1:
            skl.influences = list(range(joint_count))
        elif skl.version == 2:
            count = bs.read('<I')
            skl.influences = list(struct.unpack_from(f'<{count}I', data, bs.tell()))

    return skl


# Hash de nome de joint
# -----------------------

def elf_hash(s: str) -> int:

    # ELF hash usado pelo LoL para identificar joints pelo nome
    s = s.lower()
    h = 0
    for c in s:
        h = (h << 4) + ord(c)
        t = h & 0xF0000000
        if t != 0:
            h ^= (t >> 24)
        h &= ~t
    return h & 0xFFFFFFFF


# Serialização binaria
# ----------------------

def write_skl_binary_modern(joints: list, influences: list, path: str):

    # Escreve o SKL no formato magic = 0x22FD4FC3, version = 0
    n = len(joints)
    m = len(influences)

    # ___ Offsets das seções ___
    joints_offset = 64
    joint_indices_offset = joints_offset + n * 100
    influences_offset = joint_indices_offset + n * 8
    joint_names_offset = influences_offset + m * 2

    with open(path, 'wb') as f:

        # ___ Cabeçalho (64 bytes) ___
        f.write(struct.pack('<I', 0))
        f.write(struct.pack('<I', 0x22FD4FC3))
        f.write(struct.pack('<I', 0))
        f.write(struct.pack('<HH', 0, n))
        f.write(struct.pack('<I', m))
        f.write(struct.pack('<i', joints_offset))
        f.write(struct.pack('<i', joint_indices_offset))
        f.write(struct.pack('<i', influences_offset))
        f.write(struct.pack('<i', 0))
        f.write(struct.pack('<i', 0))
        f.write(struct.pack('<i', joint_names_offset))
        f.write(struct.pack('<5I', 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF))

        # ___ Strings de nomes ___
        # Escritas primeiro para calcular os offsets relativos nos joints
        f.seek(joint_names_offset)
        joint_name_file_offsets = {}
        for i, j in enumerate(joints):
            joint_name_file_offsets[i] = f.tell()
            f.write(j["name"].encode('ascii', errors='ignore') + b'\x00')

        # ___ Joints (100 bytes cada) ___
        f.seek(joints_offset)
        for i, j in enumerate(joints):
            pos_before = f.tell()

            f.write(struct.pack('<HH', 0, i))
            f.write(struct.pack('<h', j["parent"]))
            f.write(struct.pack('<H', 0))
            f.write(struct.pack('<I', j["hash"]))
            f.write(struct.pack('<f', j["radius"]))

            f.write(struct.pack('<3f', *j["local_t"]))
            f.write(struct.pack('<3f', *j["local_s"]))
            f.write(struct.pack('<4f', *j["local_r"]))

            f.write(struct.pack('<3f', *j["ig_t"]))
            f.write(struct.pack('<3f', *j["ig_s"]))
            f.write(struct.pack('<4f', *j["ig_r"]))

            # Offset relativo para a string do nome
            name_rel = joint_name_file_offsets[i] - f.tell()
            f.write(struct.pack('<i', name_rel))

            written = f.tell() - pos_before
            assert written == 100, f"Joint {i} escreveu {written} bytes (esperado 100)"

        # ___ Joint Indices (8 bytes cada) ___
        f.seek(joint_indices_offset)
        for i, j in enumerate(joints):
            f.write(struct.pack('<HH', i, 0))
            f.write(struct.pack('<I', j["hash"]))

        # ___ Influences (2 bytes cada) ___
        f.seek(influences_offset)
        for idx in influences:
            f.write(struct.pack('<H', idx))

        # ___ Resource size ___
        file_size = f.tell()
        f.seek(0)
        f.write(struct.pack('<I', file_size))