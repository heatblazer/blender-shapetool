import bpy
import bmesh

class SimpleOperator(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.simple_operator"
    bl_label = "Simple Object Operator"

    @classmethod
    def poll(cls, context):
        return (context.object is not None and
                context.object.type == 'MESH' and
                context.object.data.is_editmode)

    def invoke(self, context, event):
        print("SimpleOperator")
        me = context.object.data
        bm = bmesh.from_edit_mesh(me)
        verts_sel = [v.select for v in bm.verts]
        edges_sel = [e.select for e in bm.edges]
        faces_sel = [f.select for f in bm.faces]

        loc = event.mouse_region_x, event.mouse_region_y
        print(loc)

        try:
            geom = bm.select_history[-1]
        except IndexError:
            geom = None

        ret = bpy.ops.view3d.select(extend=True, location=loc)
        if ret == {'PASS_THROUGH'}:
            self.report({'INFO'}, "no close-by geom")
            return {'CANCELLED'}

        try:
            geom2 = bm.select_history[-1]
            print("geom2 sel 1st", geom2.select)
        except IndexError:
            geom2 = None

        if geom is None:
            geom = geom2

        if isinstance(geom, bmesh.types.BMVert):
            geom_sel = verts_sel
            bm_geom = bm.verts
        elif isinstance(geom, bmesh.types.BMEdge):
            geom_sel = edges_sel
            bm_geom = bm.edges
        elif isinstance(geom, bmesh.types.BMFace):
            geom_sel = faces_sel
            bm_geom = bm.faces

        for sel, g in zip(geom_sel, bm_geom):
            if sel != g.select:
                g.select_set(True)
                bm.select_history.remove(g)
                bm.select_flush_mode()
                break


        self.report({'INFO'}, repr(geom))
        return {'FINISHED'}


def register():
    bpy.utils.register_class(SimpleOperator)


def unregister():
    bpy.utils.unregister_class(SimpleOperator)


if __name__ == "__main__":
    print("Start main")
    register()