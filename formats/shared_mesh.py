
# Configurações compartilhadas entre arquivos SKN e SCB (mesh)
# ===============================================================


import bpy
import bmesh

from ..i18n import t


# Cor cinza padrao do LeagueBlender
# ------------------------------------

def srgb_to_linear(c: float) -> float:
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


# Referencia usado pela cor cinza
DEFAULT_GRAY_LINEAR = srgb_to_linear(0.158220)


# Validações de pre-exportação
# -------------------------------
# Compartilhadas entre export_skn.py e export_scb.py

_MAX_MATERIAL_NAME_LEN = 63


def validate_material_slots(
    mesh_obj: bpy.types.Object,
    *,
    no_material_key: str = "msg_export_no_material",
    empty_slot_key: str = "msg_export_empty_material_slot",
) -> tuple[bool, str]:

    # Verificação de materiais para evitar erros
    if len(mesh_obj.material_slots) == 0:
        return False, t(no_material_key, mesh_obj.name)

    for i, slot in enumerate(mesh_obj.material_slots):
        if slot.material is None:
            return False, t(empty_slot_key, mesh_obj.name, i)

    return True, ""


def enforce_material_name_limit(mesh_obj: bpy.types.Object, warnings: list) -> None:

    # Corrige nomes de materiais maiores que 63 caracteres
    for slot in mesh_obj.material_slots:
        mat = slot.material
        if mat is None:
            continue

        if len(mat.name) <= _MAX_MATERIAL_NAME_LEN:
            continue

        old_name = mat.name
        new_name = old_name[:_MAX_MATERIAL_NAME_LEN]

        # Evita colisao com outro material/datablock que ja tenha esse nome truncado
        if new_name in bpy.data.materials and bpy.data.materials[new_name] != mat:
            mat.name = new_name  # bpy resolve o conflito sozinho
        else:
            mat.name = new_name

        warnings.append(t("msg_material_renamed", old_name, len(old_name), _MAX_MATERIAL_NAME_LEN, mat.name))


# Triangulação para exportação
# -------------------------------

def triangulate_to_temp_mesh(mesh_obj: bpy.types.Object, temp_name: str, *, quad_method: str = 'BEAUTY', ngon_method: str = 'BEAUTY') -> bpy.types.Mesh:

    # Triangula mesh_obj.data numa mesh temporaria nova
    bm = bmesh.new()
    bm.from_mesh(mesh_obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces, quad_method=quad_method, ngon_method=ngon_method)

    temp_mesh = bpy.data.meshes.new(temp_name)
    bm.to_mesh(temp_mesh)
    bm.free()
    temp_mesh.update()

    return temp_mesh


# UV
# -----

def flip_uv(u: float, v: float) -> tuple:

    # Flip vertical (V). convenção compartilhada entre SKN e SCB
    return (u, 1.0 - v)


# Material base
# ----------------

def make_base_material(mat_name: str, uv_layer_name: str | None = None, use_gray: bool = True) -> bpy.types.Material:

    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (600, 0)

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (200, 0)

    if use_gray:
        color = (DEFAULT_GRAY_LINEAR, DEFAULT_GRAY_LINEAR, DEFAULT_GRAY_LINEAR, 1.0)
    else:
        color = (0.8, 0.8, 0.8, 1.0)  # Padrao do Blender

    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["Metallic"].default_value = 0.0

    if uv_layer_name is not None:
        uv_node = nodes.new("ShaderNodeUVMap")
        uv_node.location = (-200, -200)
        uv_node.uv_map = uv_layer_name

    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    mat.diffuse_color = color
    return mat


# Tris -> Quads
# ----------------

def convert_to_quads(mesh: bpy.types.Mesh):

    # Converter triangulos em quads
    bm = bmesh.new()
    bm.from_mesh(mesh)
    try:
        bmesh.ops.join_triangles(
            bm,
            faces=bm.faces,
            angle_face_threshold=0.698132,
            angle_shape_threshold=0.698132,
        )
    except Exception:
        pass
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()


# WeightedNormal
# -----------------

def apply_weighted_normal(obj: bpy.types.Object):

    # Aplica o modificador WeightedNormal ao objeto
    wn = obj.modifiers.new(name="WeightedNormal", type='WEIGHTED_NORMAL')
    try:
        if hasattr(wn, "weighting_mode"):
            wn.weighting_mode = 'FACE_AREA'
        elif hasattr(wn, "mode"):
            wn.mode = 'FACE_AREA'

        wn.weight = 50

        if hasattr(wn, "thresh"):
            wn.thresh = 0.01
        elif hasattr(wn, "threshold"):
            wn.threshold = 0.01
    except Exception as e:
        print(f"Aviso: Não foi possivel configurar todas as opções do WeightedNormal: {e}")


# Vertex Color
# ---------------
"""
Converte as cores dos vértices entre o formato dos arquivos (SCB e SKN) e as color attributes do Blender

As cores dos arquivos são armazenadas em bytes BGRA (255). O alpha não fica na color attribute principal,
pois o Vertex Paint so permite pintar RGB. Assim a cor principal e sempre opaca (A=1.0) e o alpha real e armazenado na
color attribute "Alpha" (ver create_alpha_attribute()).

color_srgb e usado para preservar exatamente os valores originais dos bytes
Diferente de .color, ele não aplica conversão de espaço de cor, evitando perda
de informação durante a leitura e escrita.
"""

ALPHA_ATTR_NAME = "Alpha"


def _clamp_255(c: float) -> int:
    return max(0, min(255, round(c * 255)))


def find_alpha_attribute(mesh: bpy.types.Mesh) -> bpy.types.Attribute | None:

    # Busca a color attribute de alpha por nome, ignorando caixa alta/baixa
    for c in mesh.color_attributes:
        if c.name.lower() == ALPHA_ATTR_NAME.lower():
            return c
    return None


def create_vertex_color_layer(mesh: bpy.types.Mesh, name: str, colors_bgra: list) -> bpy.types.Attribute:

    # Cria uma color attribute por vertice (domain POINT) a partir de uma lista (b, g, r, a)
    layer = mesh.color_attributes.new(name = name, type = 'BYTE_COLOR', domain = 'POINT')

    for vi, (b, g, r, a) in enumerate(colors_bgra):
        if vi >= len(layer.data):
            break
        layer.data[vi].color_srgb = (r / 255.0, g / 255.0, b / 255.0, 1.0)

    # Deixa ela ativa/selecionada na aba de Vertex Paint
    mesh.color_attributes.active_color_index = len(mesh.color_attributes) - 1

    return layer


def create_alpha_attribute(mesh: bpy.types.Mesh, alphas_0_255: list) -> bpy.types.Attribute:

    """
    Cria a color attribute "Alpha" (domain POINT), armazenando o alpha de cada vertice como um tom de cinza
    (R=G=B=alpha, A=1.0), permitindo sua edição pelo Vertex Paint. e FLOAT_COLOR e usado apenas para evitar
    uma quantização extra
    """
    layer = mesh.color_attributes.new(name = ALPHA_ATTR_NAME, type = 'FLOAT_COLOR', domain = 'POINT')

    for vi, a in enumerate(alphas_0_255):
        if vi >= len(layer.data):
            break
        v = a / 255.0
        layer.data[vi].color_srgb = (v, v, v, 1.0)

    return layer


def find_main_color_attribute(mesh: bpy.types.Mesh) -> bpy.types.Attribute | None:

    # Acha a color attribute "principal"
    active = mesh.color_attributes.active_color
    if active is not None and active.name.lower() != ALPHA_ATTR_NAME.lower():
        return active
    return next((c for c in mesh.color_attributes if c.name.lower() != ALPHA_ATTR_NAME.lower()), None)


def read_vertex_color_layer(mesh: bpy.types.Mesh, layer: bpy.types.Attribute = None) -> list | None:

    # Lê a color attribute principal da malha e retorna uma lista de (b, g, r, a), (255) na ordem de mesh.vertices
    # Aceita layers nos domains POINT ou CORNER
    if layer is None:
        layer = find_main_color_attribute(mesh)

    if layer is None:
        return None

    def to_bgra(c) -> tuple:
        r, g, b, a = c
        return (_clamp_255(b), _clamp_255(g), _clamp_255(r), _clamp_255(a))

    if layer.domain == 'POINT':
        return [to_bgra(layer.data[i].color_srgb) for i in range(len(mesh.vertices))]

    # CORNER. mapeia a primeira loop encontrada de cada vertice
    vert_to_color = {}
    for loop in mesh.loops:
        if loop.vertex_index not in vert_to_color:
            vert_to_color[loop.vertex_index] = layer.data[loop.index].color_srgb

    default = (1.0, 1.0, 1.0, 1.0)
    return [to_bgra(vert_to_color.get(vi, default)) for vi in range(len(mesh.vertices))]


def read_alpha_attribute(mesh: bpy.types.Mesh) -> list | None:

    # Le a color attribute "Alpha" (se existir) e devolve uma lista de valores 255 por vertice
    layer = find_alpha_attribute(mesh)
    if layer is None:
        return None

    def to_alpha_byte(c) -> int:
        r, g, b, _a = c
        return _clamp_255((r + g + b) / 3.0)

    if layer.domain == 'POINT':
        return [to_alpha_byte(layer.data[i].color_srgb) for i in range(len(mesh.vertices))]

    # ___ CORNER ___
    vert_to_color = {}
    for loop in mesh.loops:
        if loop.vertex_index not in vert_to_color:
            vert_to_color[loop.vertex_index] = layer.data[loop.index].color_srgb

    default = (1.0, 1.0, 1.0, 1.0)
    return [to_alpha_byte(vert_to_color.get(vi, default)) for vi in range(len(mesh.vertices))]


def merge_alpha(vertex_colors_bgra: list, alphas_0_255: list) -> list:

    # Substitui o canal alpha de vertex_colors_bgra usando alphas_0_255 na ordem dos vértices.
    merged = []
    for i, (b, g, r, a) in enumerate(vertex_colors_bgra):
        a_new = alphas_0_255[i] if i < len(alphas_0_255) else a
        merged.append((b, g, r, a_new))
    return merged


