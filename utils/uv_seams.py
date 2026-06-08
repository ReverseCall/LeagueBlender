"""
Detecção e aplicação de UV seams a partir de dados brutos do SKN.
"""

import bpy
from collections import defaultdict

from ..formats.skn import SKNFile


# Precisão para agrupar vertices por posição
_POS_ROUND = 3


def compute_seam_edges(skn: SKNFile) -> set:
    """
    Detecta arestas de seam a partir dos dados brutos do SKN.

    O SKN ja vem com vertices duplicados nas costuras: mesma posição 3D,
    indices diferentes, UVs diferentes. A aresta de seam passa entre
    esses pares de split verts.

    Algoritmo:
        1. Agrupa vertices por posição (arredondada a _POS_ROUND casas)
        2. Grupos com 2+ vertices e UVs distintas = split verts (costuras)
        3. Uma aresta e seam se AMBOS os seus vertices são split verts
           (se so um e split, e um canto de ilha, não uma costura)

    Retorna um set de (v_min, v_max) com os indices dos vertices do SKN.
    """
    pos_groups: dict = defaultdict(list)
    for vi, v in enumerate(skn.vertices):
        key = (
            round(v.position[0], _POS_ROUND),
            round(v.position[1], _POS_ROUND),
            round(v.position[2], _POS_ROUND),
        )
        pos_groups[key].append(vi)

    split_verts: set = set()
    for vis in pos_groups.values():
        if len(vis) < 2:
            continue
        unique_uvs = {
            (round(skn.vertices[vi].uv[0], 5), round(skn.vertices[vi].uv[1], 5))
            for vi in vis
        }
        if len(unique_uvs) > 1:
            split_verts.update(vis)

    if not split_verts:
        return set()

    seam_edges: set = set()
    for i in range(0, len(skn.indices), 3):
        tri = (skn.indices[i], skn.indices[i + 1], skn.indices[i + 2])
        for k in range(3):
            v0 = tri[k]
            v1 = tri[(k + 1) % 3]
            if v0 in split_verts and v1 in split_verts:
                seam_edges.add((min(v0, v1), max(v0, v1)))

    return seam_edges


def apply_seams(mesh: bpy.types.Mesh, seam_edges: set):
    """Marca as arestas correspondentes no mesh do Blender como seam."""
    if not seam_edges:
        return

    edge_map = {
        (min(e.vertices[0], e.vertices[1]),
         max(e.vertices[0], e.vertices[1])): e.index
        for e in mesh.edges
    }

    for key in seam_edges:
        idx = edge_map.get(key)
        if idx is not None:
            mesh.edges[idx].use_seam = True