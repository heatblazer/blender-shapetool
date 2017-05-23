import bpy
import bmesh
from bpy_extras.object_utils import world_to_camera_view

def main(self, context):
    sce = context.scene
    cam = sce.camera
    ob = context.object
    me = ob.data
    mat = ob.matrix_world

    if not me.is_editmode:
        bpy.ops.object.mode_set(mode='EDIT')

    bm = bmesh.from_edit_mesh(me)

    if not self.extend:
        bpy.ops.mesh.select_all(action='DESELECT')

    for v in bm.verts:
        x, y, z = world_to_camera_view(sce, cam, mat * v.co)
        if (0.0 <= x <= 1.0 and
            0.0 <= y <= 1.0 and
            (not self.clip or cam.data.clip_start < z < cam.data.clip_end)):
            v.select = True

    bm.select_flush(True)


class MESH_OT_select_view_frustum(bpy.types.Operator):
    """Select geometry in view frustum (uses active object and scene camera)"""
    bl_idname = "mesh.select_view_frustum"
    bl_label = "Select View Frustum"
    bl_options = {'REGISTER', 'UNDO'}

    clip = bpy.props.BoolProperty(
        name="Clip",
        description="Take camera near and far clipping distances into account",
        default=True
    )

    extend = bpy.props.BoolProperty(
        name="Extend",
        description="Extend the current selection",
        default=False
    )

    @classmethod
    def poll(cls, context):
        return (context.object is not None and
                context.object.type == 'MESH' and
                context.scene.camera is not None)

    def execute(self, context):
        main(self, context)
        return {'FINISHED'}


def register():
    bpy.utils.register_class(MESH_OT_select_view_frustum)


def unregister():
    bpy.utils.unregister_class(MESH_OT_select_view_frustum)


if __name__ == "__main__":
    register()