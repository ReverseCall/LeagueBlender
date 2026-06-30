
# Configurações compartilhadas entre arquivos SKN e SCB (mesh)
# ===============================================================


import bpy
import bmesh


# Cor cinza padrao do LeagueBlender
# ------------------------------------

def srgb_to_linear(c: float) -> float:
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


# Referencia usado pela cor cinza
DEFAULT_GRAY_LINEAR = srgb_to_linear(0.158220)


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
        
