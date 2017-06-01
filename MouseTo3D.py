import bpy
import bgl
import bmesh
from bpy_extras import view3d_utils
import mathutils
from mathutils import Vector

"""Functions for the mouse_coords_to_3D_view"""
def get_viewport():
    view = bgl.Buffer(bgl.GL_INT, 4)
    bgl.glGetIntegerv(bgl.GL_VIEWPORT, view)
    return view


def get_modelview_matrix():
    model_matrix = bgl.Buffer(bgl.GL_DOUBLE, [4, 4])
    bgl.glGetDoublev(bgl.GL_MODELVIEW_MATRIX, model_matrix)
    return model_matrix


def get_projection_matrix():
    proj_matrix = bgl.Buffer(bgl.GL_DOUBLE, [4, 4])
    bgl.glGetDoublev(bgl.GL_PROJECTION_MATRIX, proj_matrix)
    return proj_matrix


"""Function mouse_coords_to_3D_view"""
def mouse_coords_to_3D_view(x, y):
    depth = bgl.Buffer(bgl.GL_FLOAT, [0.0])
    bgl.glReadPixels(x, y, 1, 1, bgl.GL_DEPTH_COMPONENT, bgl.GL_FLOAT, depth)
    world_x = bgl.Buffer(bgl.GL_DOUBLE, 1, [0.0])
    world_y = bgl.Buffer(bgl.GL_DOUBLE, 1, [0.0])
    world_z = bgl.Buffer(bgl.GL_DOUBLE, 1, [0.0])
    view1 = get_viewport()
    model = get_modelview_matrix()
    proj = get_projection_matrix ()
    bgl.gluUnProject(x, y, depth[0],
                     model, proj,
                     view1,
                     world_x, world_y, world_z)
    return float(world_x[0]), float(world_y[0]), float(world_z[0])

"""drawing point OpenGL in mouse_coords_to_3D_view"""
def draw_callback_px(self, context):
    # mouse coordinates relative to 3d view
    x, y = self.mouse_path
    mx, my = self.mx, self.my #got from modal

    # mouse coordinates relative to Blender interface
    view = get_viewport()
    gmx = view[0] + x
    gmy = view[1] + y

    if False:
        #c= bgl.Buffer(bgl.GL_UNSIGNED_BYTE, [3,1])
        #bgl.glReadPixels(x, y, 1, 1, bgl.GL_RGB, bgl.GL_FLOAT, c)
        #c= bgl.Buffer(bgl.GL_SHORT, [3,1])
        c = bgl.Buffer(bgl.GL_FLOAT, [3,1])
        bgl.glReadPixels(gmx, gmy,1,1,bgl.GL_RGB,bgl.GL_FLOAT,c);
        draw_square_follow_cursor(c, gmx, gmy)
    else:
        draw_uv_sphere(mx, my, 0.5)


def draw_uv_sphere(mx, my, s):
    print("Draw uv sphere")
    ob = bpy.data.objects['Cube']
    v = ob.data.vertices[0].co
    mat = ob.matrix_world
    x,y,z = mouse_coords_to_3D_view(mx, my)
    mv = Vector((x, y, z))
    print(mv)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=42, ring_count=42, location=mat * mv, size=s)


def draw_square_follow_cursor(c, gmx, gmy):

    mouse3d = mouse_coords_to_3D_view(gmx, gmy)
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glColor3f(0.0,0.0,255.0)
    bgl.glPointSize(30)
    bgl.glBegin(bgl.GL_POINTS)
    bgl.glVertex3f(*(mouse3d))
    bgl.glVertex3f(mouse3d[0], mouse3d[1], mouse3d[2])
    bgl.glVertex2f(gmx,gmy)
    bgl.glEnd()

    # restore opengl defaults
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_BLEND)
    bgl.glColor4f(0.0, 0.0, 0.0, 1.0)

def draw_corner_square(c):
    for area in bpy.context.screen.areas:
        if area.type=='VIEW_3D':
            X= area.x
            Y= area.y
    dist= 100 #distancia del punto al cursor
    mouse3d = mouse_coords_to_3D_view(X+dist,Y+dist)
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glColor3f(c[0][0],c[1][0],c[2][0])
    bgl.glPointSize(30)
    bgl.glBegin(bgl.GL_POINTS)
    bgl.glVertex3f(mouse3d[0], mouse3d[1], mouse3d[2])
    bgl.glEnd()



    # restore opengl defaults
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_BLEND)
    bgl.glColor4f(0.0, 0.0, 0.0, 1.0)


def draw_square(c):
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glColor3f(c[0][0],c[1][0],c[2][0])
    bgl.glBegin(bgl.GL_POLYGON)
    bgl.glVertex2f(-0.5, -0.5)
    bgl.glVertex2f(-0.5, 0.5)
    bgl.glVertex2f(0.5, 0.5)
    bgl.glVertex2f(0.5, -0.5)
    bgl.glEnd( )

    # restore opengl defaults
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_BLEND)
    bgl.glColor4f(0.0, 0.0, 0.0, 1.0)

class ModalDrawOperator(bpy.types.Operator):
    """Draw a point with the mouse"""
    bl_idname = "view3d.modal_operator"
    bl_label = "Simple Modal View3D Operator"

    def modal(self, context, event):
        context.area.tag_redraw()

        if event.type == 'MOUSEMOVE':
            self.mouse_path = (event.mouse_region_x, event.mouse_region_y)
        elif event.type == 'LEFTMOUSE':
            self.mx, self.my= event.mouse_x, event.mouse_y
            return {'PASS_THROUGH'}
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            context.area.header_text_set()
            return {'CANCELLED'}


        return {'PASS_THROUGH'}


    def invoke(self, context, event):
        # the arguments we pass the the callback
        args = (self, context)
        # Add the region OpenGL drawing callback
        # draw in view space with 'POST_VIEW' and 'PRE_VIEW'
        self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, args, 'WINDOW', 'POST_VIEW')
        self.mouse_path = []
        #self.wx = bpy.context.window.width
        #self.wy = bpy.context.window.height
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


def register():
    bpy.utils.register_class(ModalDrawOperator)


def unregister():
    bpy.utils.unregister_class(ModalDrawOperator)


if __name__ == "__main__":
    register()