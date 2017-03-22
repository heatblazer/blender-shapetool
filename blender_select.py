import bpy
import bmesh
import math
import mathutils
import json
from mathutils import Vector, Matrix


def delete_object(obj, select=True):
    """ Deletes an object (if exists) from the scene """
    if select:
        obj = select_object(obj)
    else:
        if obj not in bpy.data.objects.keys():
            return False
        obj = bpy.data.objects[obj]

    if obj:
        if obj.mode != "OBJECT" and select:
            bpy.ops.object.mode_set(mode="OBJECT")

        if not DISABLE_SHAPEKEYS and select:
            try:
                # deleting existing shape keys before deleting the object
                # is required to actually clean up the shape keys register
                bpy.ops.object.shape_key_remove(all=True)
            except RuntimeError:
                pass

        bpy.context.scene.objects.unlink(obj)
        try:
            bpy.data.objects.remove(obj)
        except:
            # blender 2.77
            if obj.users:
                obj.user_clear()
            bpy.data.objects.remove(obj)
        return True
    else:
        # object does not exist
        return False

def delete_all_spheres():
    """ deletes all bezier control spheres """
    for obj in bpy.data.objects:
        if obj.name == "ConnectorControlSphere":
            continue
        if "Sphere" in obj.name:
            delete_object(obj)

def duplicate_object(obj, target_name, select=False, copy_vertex_groups=False, copy_custom_props=False, keep_transform=False):
    """ Creates duplicate of an object
    """

    if copy_vertex_groups:
        copyobj = select_object(obj)
        bpy.ops.object.duplicate()
        new_obj = bpy.context.object
        if new_obj.parent:
            if keep_transform:
                bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
            else:
                bpy.ops.object.parent_clear(type='CLEAR')
        new_obj.name = target_name
        if select:
            select_object(target_name)
        if copy_custom_props:
            for key in copyobj.keys():
                new_obj[key] = copyobj[key]
        return new_obj
    else:
        scene = bpy.context.scene
        copyobj = select_object(obj)

        # Create new mesh
        mesh = bpy.data.meshes.new(target_name)

        # Create new object associated with the mesh
        ob_new = bpy.data.objects.new(target_name, mesh)

        # Copy data block from the old object into the new object
        ob_new.data = copyobj.data.copy()
        ob_new.scale = copyobj.scale
        ob_new.location = copyobj.location
        # Link new object to the given scene and select it
        for key in copyobj.keys():
            ob_new[key] = copyobj[key]

        scene.objects.link(ob_new)

        if select:
            select_object(ob_new)

    return ob_new


def define_new_group(group_name,obj):
    """ Define a new group

        Input: group name, mesh object
        Output:

    """

    if group_name in obj.vertex_groups.keys():
        obj.vertex_groups.remove(obj.vertex_groups[group_name])

    bpy.ops.object.vertex_group_add()
    bpy.ops.object.vertex_group_assign()
    bpy.context.object.vertex_groups[-1].name = group_name

def mesh_objects():
    """ Returns the list of mesh objects on the scene. """
    objects = []

    for obj in bpy.data.objects:
        if isinstance(obj.data, bpy.types.Mesh):
            objects.append(obj)

    return objects

def save_vertex_groups(mesh):
    """ Saves the coordinates of all zone arrow and aligning vertex groups """
    print('saving Zones vertex groups')
    current_object = bpy.context.object
    current_mode = bpy.context.mode
    mesh.update_from_editmode()
    vgroup_names = {vgroup.index: vgroup.name for vgroup in mesh.vertex_groups}
    for v in mesh.data.vertices:
        for g in v.groups:
            vg_name = vgroup_names.get(g.group, None)
            if not vg_name:
                continue
            co = None
            if vg_name.startswith('ZVG') or vg_name.startswith("ALIGN_"):
                co = ";".join([str(v.co[0]), str(v.co[1]), str(v.co[2])])
                mesh[vg_name] = co
    select_object(current_object.name)
    if current_mode == 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    elif current_mode == 'EDIT_MESH':
        bpy.ops.object.mode_set(mode='EDIT')

def unselect_all():
    """ Unselects every object. """
    if not mesh_objects():
        return

    for ob in bpy.data.objects.values():
        ob.select = False

    # selection in edit mode needs special clearing
    if bpy.context.scene.objects.active and bpy.context.scene.objects.active.mode == "EDIT":
        bpy.ops.object.mode_set(mode="OBJECT")

    bpy.context.scene.objects.active = None


def select_object(obj, select=True):
    """ Selects an object on the scene """
    unselect_all()

    if isinstance(obj, str):
        # object passed by name
        try:
            obj = bpy.data.objects[obj]
        except KeyError:
            # object with name not found
            return None

    bpy.context.scene.objects.active = obj

    # make object selectable
    obj.hide_select = False
    if select:
        obj.select = True
    return obj

#########################################################################
BREAK_POINT = True
BL_MAIN_OBJ_NAME = bpy.data.objects['ImportedMesh'].name
BL_SHAPE_PREVIEW_OBJ_NAME = bpy.data.objects['ShapeBezierCurve'].name
BL_SHAPE_TOOL_OBJ_NAME = BL_MAIN_OBJ_NAME

print("------------------------ TEST ------------------- ")

class ApplyDrawnShapeOperator(bpy.types.Operator):
    """Apply the custom drawn shape to the mesh """
    bl_idname = "debug.apply_drawn_shape"
    bl_label = "Apply drawn shape"
    bl_options = {'REGISTER', 'UNDO'}

    target_objname = BL_MAIN_OBJ_NAME

    height = bpy.props.FloatProperty(name="Height amount in mm", default=2)
    smooth_amount = bpy.props.IntProperty(name="Smooth amount", default=100)
    x_displacement = bpy.props.StringProperty(name="X displacement amounts", default="")
    y_displacement = bpy.props.StringProperty(name="Y displacement amounts", default="")
    preview = bpy.props.BoolProperty(name="Only preview shape", default=True)

    def execute(self, context):
        if BL_SHAPE_TOOL_OBJ_NAME not in bpy.data.objects.keys():
            return {'CANCELLED'}

        # hide manipulators
        #view3d_space = get_view3d_space()
        #view3d_space.transform_manipulators = set()
        #view3d_space.show_manipulator = False

        target_obj = select_object(self.target_objname)
        save_vertex_groups(target_obj)
        duplicate_target_obj = None
        if self.preview:
            # do not really apply, just preview, so work on a duplicate copy
            print("Only previewing shape on a copy of %s" % target_obj.name)
            duplicate_target_obj = duplicate_object(
                target_obj, BL_SHAPE_PREVIEW_OBJ_NAME, select=True, copy_vertex_groups=True)
            duplicate_target_obj.hide = True
            duplicate_target_obj.hide_select = True  # unselectable
        else:
            # show the object in case it was hidden because of preview mode
            target_obj.hide = False

        select_object(target_obj.name)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.object.mode_set(mode='OBJECT')

        shape_obj = select_object(BL_SHAPE_TOOL_OBJ_NAME)
        # create copy of the shape
        bpy.ops.object.duplicate_move()
        duplicate_shape = bpy.context.object

        if "Shrinkwrap" not in duplicate_shape.modifiers:
            # no shape was added
            delete_all_spheres()
            delete_object(duplicate_shape)
            return {'FINISHED'}

        bpy.ops.object.convert(target="MESH")
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.vertices_smooth()
        bpy.ops.mesh.vertices_smooth()

        bpy.ops.mesh.select_all(action="SELECT")
        define_new_group("shape_group",target_obj)
        bpy.ops.object.mode_set(mode='OBJECT')

        shape_obj = select_object(BL_SHAPE_TOOL_OBJ_NAME)
        bpy.ops.object.modifier_add(type='SHRINKWRAP')
        shape_obj.modifiers["Shrinkwrap"].target = bpy.data.objects[target_obj.name]
        shape_obj.modifiers["Shrinkwrap"].offset = 0.001
        shape_obj.modifiers["Shrinkwrap"].wrap_method = 'NEAREST_SURFACEPOINT'
        bpy.ops.object.modifier_apply(modifier="Shrinkwrap")

        # -0.003 defines the amount of extrusion towards Origin
        extrude_value = self.calc_shape_normal(duplicate_shape)
        extrude_value = -0.003*(extrude_value/extrude_value.magnitude)

        unselect_all()
        duplicate_shape.select = True
        target_obj.select = True
        bpy.context.scene.objects.active = target_obj
        bpy.ops.object.join()

        select_object(target_obj)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action='DESELECT')
        target_obj.vertex_groups.active_index = target_obj.vertex_groups['shape_group'].index
        bpy.ops.object.vertex_group_select()

        bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": extrude_value.to_tuple()})

        bpy.ops.mesh.select_all(action='DESELECT')
        target_obj.vertex_groups.active_index = target_obj.vertex_groups['shape_group'].index
        bpy.ops.object.vertex_group_select()

        bpy.ops.mesh.intersect()

        define_new_group('shape_intersection_group',target_obj)

        bpy.ops.mesh.select_all(action='DESELECT')
        target_obj.vertex_groups.active_index = target_obj.vertex_groups['shape_group'].index
        bpy.ops.object.vertex_group_select()
        bpy.ops.mesh.delete(type='VERT')
        bpy.ops.object.vertex_group_remove(all=False)

        bpy.ops.mesh.select_all(action='DESELECT')
        target_obj.vertex_groups.active_index = target_obj.vertex_groups['shape_intersection_group'].index
        bpy.ops.object.vertex_group_select()

        bpy.ops.mesh.remove_doubles()

        bpy.ops.mesh.delete_loose()
        bpy.ops.object.vertex_group_select()

        print('Correcting shape loop over socket surface')
        self.clean_shape_loop(target_obj)

        bpy.ops.mesh.loop_to_region()
        bpy.ops.mesh.fill_holes()
        define_new_group('modifier_group',target_obj)

        bpy.ops.object.mode_set(mode='OBJECT')

        # Add a grid object and project the shape over it
        target_obj_shape_verts = [v.co for v in target_obj.data.vertices if v.select]
        shape_median_point = sum(target_obj_shape_verts, Vector()) / len(target_obj_shape_verts)
        bpy.ops.mesh.primitive_grid_add(radius=0.075, view_align=False, enter_editmode=False, location=Vector((0.0,0.0,0.0)))

        grid_proj_obj = bpy.context.object
        nv = self.calc_shape_normal(target_obj).to_tuple()
        print("Shape normal vector: {}".format(nv))
        sign = lambda number: (number>0) - (number<0)

        #Rotate the grid object
        #1.Rotate the grid horizontally to point in the direction of the shape
        shape_to_origin_vector = math.sqrt(shape_median_point[0]**2 + shape_median_point[1]**2)
        initial_angle = abs(math.asin(shape_median_point[1]/shape_to_origin_vector))

        if shape_median_point[0] > 0 and shape_median_point[1] < 0:
            initial_angle = math.radians(180) - initial_angle
        elif shape_median_point[0] > 0 and shape_median_point[1] > 0:
            initial_angle = math.radians(180) + initial_angle
        elif shape_median_point[0] < 0 and shape_median_point[1] >0:
            initial_angle = math.radians(360) - initial_angle

        initial_rot_angle = math.degrees(initial_angle)
        print("Angle of rotation: {} degrees or {} radians".format(initial_rot_angle,initial_angle))
        if initial_angle > math.radians(360)/2:
            bpy.ops.transform.rotate(value=initial_angle/2, axis=(0.0, 0.0, 1.0), constraint_axis=(False, False, True), constraint_orientation='LOCAL')
            bpy.ops.transform.rotate(value=initial_angle/2, axis=(0.0, 0.0, 1.0), constraint_axis=(False, False, True), constraint_orientation='LOCAL')
        else:
            bpy.ops.transform.rotate(value=initial_angle, axis=(0.0, 0.0, 1.0), constraint_axis=(False, False, True), constraint_orientation='LOCAL')

        #2.Rotate the grid vertically, accounting for the change of volume towards the distal end
        shape_median_point_comp = shape_median_point.copy()
        shape_median_point_comp += Vector((nv))*1.1
        shape_to_origin_vector_comp = math.sqrt((shape_median_point[0] - shape_median_point_comp[0])**2 + (shape_median_point[2] - shape_median_point_comp[2])**2)
        inclination_angle = (math.asin((shape_median_point[2] - shape_median_point_comp[2])/shape_to_origin_vector_comp))

        if shape_median_point[0] > 0 and shape_median_point[2] < 0:
            initial_angle =  math.radians(90) - inclination_angle
            print("Angle before compensation: {} ,compensation angle: {}".
                         format(math.degrees(math.radians(90)),math.degrees(inclination_angle)))
        elif shape_median_point[0] < 0 and shape_median_point[2] < 0:
            initial_angle =  math.radians(-90) - inclination_angle
            print("Angle before compensation: {} ,compensation angle: {}".
                         format(math.degrees(math.radians(-90)),math.degrees(inclination_angle)))
        else:
            initial_angle =  math.radians(90)
            inclination_angle = 0.0

        bpy.ops.transform.rotate(value=initial_angle, axis=(0.0, 1.0, 0.0), constraint_axis=(False, True, False), constraint_orientation='LOCAL')
        grid_proj_obj.location = shape_median_point

        #add a custom rotation axis to compensate the inclination
        bpy.ops.object.duplicate_move(OBJECT_OT_duplicate={"linked":False, "mode":'TRANSLATION'},
                                      TRANSFORM_OT_translate={"value":(0, 0.05, 0), "constraint_axis":(False, True, False), "constraint_orientation":'LOCAL'})
        grid_proj_dup_verts = [v.co for v in bpy.context.object.data.vertices if v.select]
        grid_proj_dup_median_point = sum(grid_proj_dup_verts, Vector()) / len(grid_proj_dup_verts)
        rot_axis = shape_median_point - (bpy.context.object.matrix_world * grid_proj_dup_median_point)
        bpy.ops.object.delete(use_global=False)
        select_object(grid_proj_obj)
        #End of grid rotation

        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.subdivide()
        bpy.ops.mesh.subdivide()
        bpy.ops.mesh.subdivide()

        define_new_group('grid_group',grid_proj_obj)
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.transform.translate(value=(sign(nv[0])*0.05,sign(nv[1])*0.05,sign(nv[2])*0.05),constraint_axis=(True,True,True),constraint_orientation='GLOBAL')

        bpy.ops.object.select_all(action='DESELECT')

        select_object(target_obj)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action='DESELECT')
        target_obj.vertex_groups.active_index = target_obj.vertex_groups['shape_intersection_group'].index
        bpy.ops.object.vertex_group_select()
        bpy.ops.mesh.duplicate_move(TRANSFORM_OT_translate={"value":(0.0,0.0,0.0),
                                                            "constraint_axis":(True,True,True),"constraint_orientation":'GLOBAL'})
        #magic number below is amount of extrusion
        define_new_group('shape_outline',target_obj)
        bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value":(sign(nv[0])*0.1,sign(nv[1])*0.1,sign(nv[2])*0.1),
                                                                 "constraint_axis":(True,True,True),"constraint_orientation":'GLOBAL'})
        target_obj.vertex_groups.active_index = target_obj.vertex_groups['shape_intersection_group'].index
        bpy.ops.object.vertex_group_select()

        bpy.ops.object.mode_set(mode="OBJECT")
        unselect_all()

        target_obj.select = True
        grid_proj_obj.select = True
        bpy.context.scene.objects.active = target_obj
        bpy.ops.object.join()

        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.intersect(mode='SELECT', use_separate=True, threshold=1e-06)
        define_new_group('grid_intersection_group',target_obj)
        bpy.ops.mesh.remove_doubles()

        bpy.ops.mesh.select_all(action='DESELECT')
        target_obj.vertex_groups.active_index = target_obj.vertex_groups['shape_outline'].index
        bpy.ops.object.vertex_group_select()
        bpy.ops.mesh.delete(type='VERT')
        bpy.ops.object.vertex_group_remove(all=False)

        target_obj.vertex_groups.active_index = target_obj.vertex_groups['grid_intersection_group'].index
        bpy.ops.object.vertex_group_select()
        bpy.ops.mesh.delete_loose()
        bpy.ops.object.vertex_group_select()

        print('Correcting shape loop over grid surface')
        self.clean_shape_loop(target_obj)

        bpy.ops.mesh.loop_to_region()
        bpy.ops.object.vertex_group_assign()

        target_obj.vertex_groups.active_index = target_obj.vertex_groups['grid_group'].index
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.vertex_group_remove(all=False)

        target_obj.vertex_groups.active_index = target_obj.vertex_groups['grid_intersection_group'].index
        bpy.ops.object.vertex_group_deselect()
        bpy.ops.mesh.delete(type='VERT')

        #Floating unconnected vertices remain sometimes, remove them
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.delete_loose()

        #Extrude only the inner part
        target_obj.vertex_groups.active_index = target_obj.vertex_groups['grid_intersection_group'].index
        bpy.ops.object.vertex_group_select()

        bpy.ops.mesh.region_to_loop()
        bpy.ops.mesh.delete(type='VERT')

        target_obj.vertex_groups.active_index = target_obj.vertex_groups['grid_intersection_group'].index
        bpy.ops.object.vertex_group_select()
        bpy.ops.mesh.delete_loose()
        bpy.ops.object.vertex_group_select()

        extrude_values = self.blendCurves(target_obj,rot_axis,inclination_angle,initial_rot_angle)

        bm = bmesh.from_edit_mesh(target_obj.data)
        bm.verts.ensure_lookup_table()
        shape_obj_verts = [v.co for v in bm.verts if v.select]
        shape_obj_median_point = sum(shape_obj_verts, Vector()) / len(shape_obj_verts)

        translate_value = self.calc_distance(shape_obj_median_point,shape_median_point)
        bmesh.update_edit_mesh(bpy.context.object.data)

        print("translate_value: {}".format(translate_value))
        bpy.ops.mesh.extrude_edges_move(TRANSFORM_OT_translate={"value":(sign(nv[0])*-translate_value,sign(nv[1])*-translate_value,sign(nv[2])*-translate_value),
                                                                "constraint_axis":(True,True,True),"constraint_orientation":'GLOBAL'})
        define_new_group('grid_intersection_group_extruded',target_obj)

        target_obj.vertex_groups.active_index = target_obj.vertex_groups['grid_intersection_group'].index
        bpy.ops.object.vertex_group_select()
        target_obj.vertex_groups.active_index = target_obj.vertex_groups['grid_intersection_group_extruded'].index
        bpy.ops.object.vertex_group_deselect()
        define_new_group('grid_intersection_group',target_obj)

        target_obj.vertex_groups.active_index = target_obj.vertex_groups['grid_intersection_group'].index
        bpy.ops.object.vertex_group_select()
        target_obj.vertex_groups.active_index = target_obj.vertex_groups['grid_intersection_group_extruded'].index
        bpy.ops.object.vertex_group_select()
        bpy.ops.mesh.delete_loose()

        self.correctShapeSurface(target_obj)

        target_obj.vertex_groups.active_index = target_obj.vertex_groups['intersection'].index
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.vertex_group_remove()
        target_obj.vertex_groups.active_index = target_obj.vertex_groups['intersection_corrected'].index
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.vertex_group_remove()
        target_obj.vertex_groups.active_index = target_obj.vertex_groups['modifier_group'].index
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.vertex_group_remove()
        target_obj.vertex_groups.active_index = target_obj.vertex_groups['shape_intersection_group'].index
        bpy.ops.object.vertex_group_deselect()
        bpy.ops.mesh.delete(type='VERT')

        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.mesh.select_all(action='DESELECT')

        #Do the extrusion
        bm = bmesh.from_edit_mesh(target_obj.data)
        bm.verts.ensure_lookup_table()
        for indx,value in extrude_values.items():
            bm.verts[indx].co += bm.verts[indx].normal * value
        bmesh.update_edit_mesh(bpy.context.object.data)

        target_obj.vertex_groups.active_index = target_obj.vertex_groups['grid_intersection_group'].index
        bpy.ops.object.vertex_group_select()
        bpy.ops.mesh.subdivide()
        bpy.ops.mesh.region_to_loop()

        target_obj.vertex_groups.active_index = target_obj.vertex_groups['shape_intersection_group'].index
        bpy.ops.object.vertex_group_select()

        bpy.ops.mesh.bridge_edge_loops()
        bpy.ops.mesh.subdivide()
        bpy.ops.mesh.select_all(action='DESELECT')

        target_obj.vertex_groups.active_index = target_obj.vertex_groups['grid_intersection_group'].index
        bpy.ops.object.vertex_group_select()
        bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
        target_obj.vertex_groups.active_index = target_obj.vertex_groups['shape_intersection_group'].index
        bpy.ops.object.vertex_group_select()

        define_new_group('shape_group',target_obj)

        #Make the mesh surrounding the shape finer
        bpy.ops.mesh.select_all(action='DESELECT')
        target_obj.vertex_groups.active_index = target_obj.vertex_groups['shape_intersection_group'].index
        bpy.ops.object.vertex_group_select()
        bpy.ops.mesh.select_more()
        bpy.ops.mesh.select_more()
        target_obj.vertex_groups.active_index = target_obj.vertex_groups['grid_intersection_group'].index
        bpy.ops.object.vertex_group_deselect()
        bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
        bpy.ops.mesh.subdivide()
        bpy.ops.mesh.subdivide()

        #Apply smooth modifier
        bpy.ops.object.modifier_add(type='SMOOTH')
        bpy.context.object.modifiers["Smooth"].vertex_group = "shape_group"
        bpy.context.object.modifiers["Smooth"].iterations = self.smooth_amount
        bpy.context.object.modifiers["Smooth"].factor = 0.5
        bpy.ops.object.mode_set(mode="OBJECT")

        shape_obj.hide = True
        delete_all_spheres()

        if duplicate_target_obj:
            target_obj.name += "_tmp"
            duplicate_target_obj.name = BL_MAIN_OBJ_NAME
            target_obj.name = BL_SHAPE_PREVIEW_OBJ_NAME


        return {'FINISHED'}


    def calc_shape_normal(self,obj):
        """ Calculate the shape normal vector

            Input: mesh object (select object vertices in EDIT mode first)
            Output: mathutils.Vector

        """
        verts = [v for v in obj.data.vertices if v.select]

        nv = None
        count = 0
        for vertex in verts:
            if nv is None:
                nv = vertex.normal
            else:
                nv += vertex.normal
            count += 1

        nv /= count

        return nv

    def clean_shape_loop(self,obj):
        """ Clean shape - edges at tight places, single hole from intersection, faces at sharp corners.

            Extensive debug messaging added as this is a key moment.

            Input:
            Output:
        """

        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        faces = [f for f in bm.faces if f.select]

        if faces:
            print('Correcting {} faces'.format(len(faces)))
            bmesh.ops.dissolve_faces(bm,faces = faces)
            faces = [f for f in bm.faces if f.select]
            for face in faces:
                vs = [v for v in face.verts]
                bmesh.ops.connect_vert_pair(bm, verts = vs)

        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()

        indx = 0
        vertices = [[v,indx] for v in bm.verts if v.select]
        edges = [e for e in bm.edges if e.select]

        for v in vertices:
            for e in edges:
                if v[0] in e.verts:
                    v[1] += 1

        verts_at_limit = [v[0] for v in vertices if v[1] < 2]
        verts_at_shortcuts = [v[0] for v in vertices if v[1] > 2]

        if verts_at_limit:
            print('Number of vertices at shape loop gap: {}'.format(len(verts_at_limit)))
            if len(verts_at_limit) == 1:
                print('[Unhandled] Number of vertices at shape loop gap: {}'.format(len(verts_at_limit)))
            elif len(verts_at_limit) == 2:
                cEdges = bmesh.ops.connect_vert_pair(bm, verts = verts_at_limit)
                if not cEdges['edges']:
                    print("Empty result, expecting bad geometry: {}, vertices {}".format(cEdges,verts_at_limit))
                else:
                    for edge in cEdges['edges']:
                        edge.select = True
                bm.edges.ensure_lookup_table()
            else:
                pairs = []
                verts_at_limit_copy = verts_at_limit.copy()
                for _ in range(round(len(verts_at_limit)/2)):
                    v = verts_at_limit_copy.pop()
                    min_dist = [self.calc_distance(v.co,Vector((0.0,0.0,0.0))),v]
                    for vc in verts_at_limit_copy:
                        dist = self.calc_distance(v.co,vc.co)
                        if min_dist[0] > dist:
                            min_dist[0] = dist
                            min_dist[1] = vc
                    pairs.append((v,min_dist[1]))
                    verts_at_limit_copy.remove(min_dist[1])
                for pair in pairs:
                    cEdges = bmesh.ops.connect_vert_pair(bm, verts = pair)
                    if not cEdges['edges']:
                        print("Empty result, expecting bad geometry: {}, vertices: ".format(cEdges,pair))
                    else:
                        for edge in cEdges['edges']:
                            edge.select = True
                    bm.edges.ensure_lookup_table()
        if verts_at_shortcuts:
            logger.debug('Number of vertices at faces/shortcuts: {}'.format(len(verts_at_shortcuts)))
            edges_at_faces = []
            for e in edges:
                if e.verts[0] in verts_at_shortcuts and e.verts[1] in verts_at_shortcuts:
                    edges_at_faces.append(e)

            bmesh.ops.dissolve_edges(bm,edges = edges_at_faces)

        bmesh.update_edit_mesh(obj.data)

    def calc_distance(self,origin,vert):
        """ Calculate Euclidean distance between two points

            Input:  mathutils.Vector
            Output: float
        """

        return math.sqrt((vert[0] - origin[0])**2 + (vert[1] - origin[1])**2 + (vert[2] - origin[2])**2)


    def blendCurves(self,target_obj,rot_axis,inclination_angle,initial_rot_angle):
        """ Blend the user defined (X,Y) curves and store each vertex value in a dictionary.

            Input: mesh object
            Output: dict{BMVert.index : extrude_value}
        """

        curveX = json.loads(self.x_displacement)
        curveY = json.loads(self.y_displacement)
        if ilian_debug():
            print(json.dumps(curveX, indent=4, sort_keys=True))
            print(json.dumps(curveY, indent=4, sort_keys=True))


        if bpy.context.scene.objects.active.mode == "EDIT":
            bpy.ops.object.mode_set(mode="OBJECT")

        #Store the original shape vertex locations
        orig_locs = {v.index: v.co.copy() for v in target_obj.data.vertices if v.select}

        #Compensate the inclination
        rot_mat = Matrix.Rotation(-inclination_angle,3,rot_axis)
        print("Rotation_axis: {}, inclination_angle: {}, rotation matrix: {}".format(rot_axis,inclination_angle,rot_mat))

        target_obj_shape_verts = [v for v in target_obj.data.vertices if v.select]
        for v in target_obj_shape_verts:
            v.co = rot_mat * v.co

        #Flatten the shape by pointing the normal in Y direction

        if initial_rot_angle <= 90:
            comp_angle = 90 - initial_rot_angle
        elif initial_rot_angle > 90 and initial_rot_angle <= 180:
            comp_angle = -(initial_rot_angle - 90)
        elif initial_rot_angle > 180 and initial_rot_angle <= 270:
            comp_angle = 270 - initial_rot_angle
        elif initial_rot_angle > 270 and initial_rot_angle <= 360:
            comp_angle = -(initial_rot_angle - 270)

        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.transform.rotate(value=math.radians(comp_angle), axis=(0.0, 0.0, 1.0), constraint_axis=(False, False, True), constraint_orientation='GLOBAL')

        bm = bmesh.from_edit_mesh(bpy.context.object.data)
        verts = [v for v in bm.verts if v.select]
        for v in verts:
            v.co.y = 0.0
        bmesh.update_edit_mesh(bpy.context.object.data)

        #Find the min,max in X,Z and use these in the shape traversal
        bpy.ops.object.mode_set(mode="OBJECT")
        verts_x = {v.index: v.co.x for v in target_obj.data.vertices if v.select}
        verts_z = {v.index: v.co.z for v in target_obj.data.vertices if v.select}

        min_X = min(verts_x.keys(), key=(lambda k: verts_x[k]))
        max_X = max(verts_x.keys(), key=(lambda k: verts_x[k]))
        min_Z = min(verts_z.keys(), key=(lambda k: verts_z[k]))
        max_Z = max(verts_z.keys(), key=(lambda k: verts_z[k]))


        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action='DESELECT')

        bm = bmesh.from_edit_mesh(target_obj.data)
        bm.verts.ensure_lookup_table()

        #Put the shape vertices in rows and column (matrix)
        rowData,columnData = self.getRowColumnData(bm,min_X,max_Z)

        #Handle the no curves case
        if not(curveX and curveY):
            extrude_values = {}
            for key,verts in rowData.items():
                for v in verts:
                    extrude_values[v.index] = self.height/1000
            bmesh.update_edit_mesh(bpy.context.object.data)

            #restore the original shape vertex locations
            bpy.ops.object.mode_set(mode="OBJECT")
            for key,value in orig_locs.items():
                target_obj.data.vertices[key].co = orig_locs[key]

            #restore state and selection
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action='DESELECT')
            target_obj.vertex_groups.active_index = target_obj.vertex_groups['grid_intersection_group'].index
            bpy.ops.object.vertex_group_select()

            return extrude_values

        #Separate the curves data in useful dicts
        cPointsX_X = {}
        cPointsX_Y = {}
        cPointsX_X_limits = {}

        cPointsY_X = {}
        cPointsY_Y = {}
        cPointsY_X_limits = {}

        #update
        curveXmaxY = max(max([1 - curve["start"]["position"]["y"] for curve in curveX]),max([1 - curve["end"]["position"]["y"] for curve in curveX]),
                         max([1 - curve["start"]["control"]["y"] for curve in curveX]),max([1 - curve["end"]["control"]["y"] for curve in curveX]))
        curveYmaxY = max(max([1 - curve["start"]["position"]["y"] for curve in curveY]),max([1 - curve["end"]["position"]["y"] for curve in curveY]),
                         max([1 - curve["start"]["control"]["y"] for curve in curveY]),max([1 - curve["end"]["control"]["y"] for curve in curveY]))
        curveMax = max(curveXmaxY,curveYmaxY)

        for indx,segment in enumerate(curveX):
            cPointsX_Y[indx] = [((1 - segment["start"]["position"]["y"])/curveMax)*self.height]
            cPointsX_Y[indx].append(((1 - segment["start"]["control"]["y"])/curveMax)*self.height)
            cPointsX_Y[indx].append(((1 - segment["end"]["control"]["y"])/curveMax)*self.height)
            cPointsX_Y[indx].append(((1 - segment["end"]["position"]["y"])/curveMax)*self.height)

            cPointsX_X[indx] = [segment["start"]["position"]["x"]]
            cPointsX_X[indx].append(segment["start"]["control"]["x"])
            cPointsX_X[indx].append(segment["end"]["control"]["x"])
            cPointsX_X[indx].append(segment["end"]["position"]["x"])

            cPointsX_X_limits[indx] = [min(cPointsX_X[indx])]
            cPointsX_X_limits[indx].append(max(cPointsX_X[indx]))


        for indx,segment in enumerate(curveY):
            cPointsY_Y[indx] = [((1 - segment["start"]["position"]["y"])/curveMax)*self.height]
            cPointsY_Y[indx].append(((1 - segment["start"]["control"]["y"])/curveMax)*self.height)
            cPointsY_Y[indx].append(((1 - segment["end"]["control"]["y"])/curveMax)*self.height)
            cPointsY_Y[indx].append(((1 - segment["end"]["position"]["y"])/curveMax)*self.height)

            cPointsY_X[indx] = [segment["start"]["position"]["x"]]
            cPointsY_X[indx].append(segment["start"]["control"]["x"])
            cPointsY_X[indx].append(segment["end"]["control"]["x"])
            cPointsY_X[indx].append(segment["end"]["position"]["x"])

            cPointsY_X_limits[indx] = [min(cPointsY_X[indx])]
            cPointsY_X_limits[indx].append(max(cPointsY_X[indx]))

        # get the middle column, middle vertex of middle column and "middle row"
        # TODO - maybe consider the case when the middle column is not continuous
        column_count = len({key for key in columnData.keys() if len(key.split('-')) == 1})
        if column_count % 2:
            middle_column = str(round(column_count/2))
        else:
            middle_column = str(round(column_count/2))

        middle_column_rows = len([v for v in columnData[middle_column]])
        if middle_column_rows % 2:
            middle_vertex = columnData[middle_column][int(round(middle_column_rows/2))]
        else:
            middle_vertex = columnData[middle_column][int(middle_column_rows/2)]

        for row,values in rowData.items():
            if middle_vertex in values:
                middle_row = row
                break

        #caluclate the extrusion
        columnData_extruded = self.calculate_extrusion(columnData,curveX,middle_column,cPointsX_X_limits,cPointsX_Y)
        rowData_extruded = self.calculate_extrusion(rowData,curveY,middle_row,cPointsY_X_limits,cPointsY_Y)

        #blend the extruded values by doing weighted average (consider revision) and store the result in a dictionary
        extrude_values = {}
        for key,values in columnData_extruded.items():
            key_tmp = int(key.split('-')[0])
            for value in values:
                if value[0].tag:
                    continue
                else:
                    extrude_values[value[0].index] = value[1]/1000
                    if key_tmp == middle_column:
                        value[0].tag = True

        for key,values in rowData_extruded.items():
            key_tmp = int(key.split('-')[0])
            for value in values:
                if value[0].tag:
                    continue
                else:
                    extrude_values[value[0].index] = (extrude_values[value[0].index] + value[1]/1000)/2
                    if key_tmp == middle_row:
                        value[0].tag = True

        bmesh.update_edit_mesh(bpy.context.object.data)

        #restore the original shape vertex locations
        bpy.ops.object.mode_set(mode="OBJECT")
        for key,value in orig_locs.items():
            target_obj.data.vertices[key].co = orig_locs[key]

        #restore state and selection
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action='DESELECT')
        target_obj.vertex_groups.active_index = target_obj.vertex_groups['grid_intersection_group'].index
        bpy.ops.object.vertex_group_select()

        return extrude_values


    def getRowColumnData(self,bm,cVertZ,cVertX):
        """ Return a column and row representation of the shape data
            input: bmesh, tolerance, start value
            output: dict{column: list(BMVerts)}, dict{row: list(BMVerts)}

        """

        rows = dict()
        columns = dict()

        #clean up the tags
        for v in bm.verts:
            v.tag = False

        rows =  self.traverseShape(bm,cVertX,rows,'rows')
        print('Row count: {}'.format(len(rows)))
        #clean up the tags
        for v in bm.verts:
            v.tag = False

        columns =  self.traverseShape(bm,cVertZ,columns,'columns')
        print('Column count: {}'.format(len(columns)))

        #sort each column/row by the vertex co values
        for key in columns.keys():
            columns[key].sort(key = lambda value:value.co.z)
        for key in rows.keys():
            rows[key].sort(key = lambda value:value.co.x)

        rows = self.splitSequence(rows)
        columns = self.splitSequence(columns)

        #clean up the tags
        for v in bm.verts:
            v.tag = False

        return rows, columns


    def traverseShape(self,bm,cVert,sequence,seq_type,cIndx = 0,EPS = 0.002):
        """ Recursive traversal of the shape

        EPS - define the tolerance in coordinate difference

        output: dict{sequence: list(BMVerts)}
        """
        if seq_type == 'rows':
            seq_co = 2
        else:
            seq_co = 0

        if not sequence:
            # This is the initial case
            cIndx = 0
            sequence[str(cIndx)] = [bm.verts[cVert]]
        else:
            if abs(bm.verts[cVert].co[seq_co] - sequence[str(cIndx)][0].co[seq_co]) < EPS:
                sequence[str(cIndx)].append(bm.verts[cVert])
            else:
                for elem in range(len(sequence)):
                    if abs(bm.verts[cVert].co[seq_co] - sequence[str(elem)][0].co[seq_co]) < EPS:
                        sequence[str(elem)].append(bm.verts[cVert])
                        break
                else:
                    cIndx = len(sequence)
                    sequence[str(cIndx)] = [bm.verts[cVert]]

        bm.verts[cVert].tag = True
        for l_edge in bm.verts[cVert].link_edges:
            if not l_edge.other_vert(bm.verts[cVert]).tag:
                other = l_edge.other_vert(bm.verts[cVert])
                self.traverseShape(bm,other.index,sequence,seq_type,cIndx)
        else:
            return sequence


    def splitSequence(self,sequence):
        """ Split the rows or columns if a gap (geometry) exists/continuous

            input: sequence of rows/columns
            output: dict{sequence: list(BMVerts)}
        """
        new_seq = dict()
        for key,seq in sequence.items():
            for indx,v in enumerate(seq):
                for l_edge in v.link_edges:
                    if l_edge.other_vert(v) in seq:
                        if key not in new_seq.keys():
                            new_seq[key] = [v]
                            break
                        elif l_edge.other_vert(v) in new_seq[key]:
                            continue
                        else:
                            new_seq[key].append(v)
                            break
                    elif indx == len(seq) - 1:
                        new_seq[key].append(v)
                        break
                else:
                    key = key + '-' + str(1)
                    if key not in new_seq.keys():
                        new_seq[key] = [v]
                    else:
                        new_seq[key].append(v)
        return new_seq


    def calculate_extrusion(self,data,curve,middle,cPoints_X_limits,cPoints_Y):
        """ Calculate the extrusion for each row/column by applying linear interpolation.

            input: dict{},list(),dict[],list(),list()
            output: dict{sequence: list(BMVerts)}
        """
        data_extruded = {}
        for indx in data.keys():
            per_segment  = (len(data[indx]) - (len(curve) - 1))/len(curve)
            residual =  (len(data[indx]) - (len(curve) - 1)) % (len(curve))
            extrude_value = []

            for segment in range(len(curve)):
                if residual:
                    #Distribute the residual
                    cSegment  = math.ceil(per_segment)
                    residual -= 1
                else:
                    cSegment = max(math.floor(per_segment),1)

                #In UV space the coordinates change in range 0-1, this requires doubling of the step.
                #We have n-columns between start and end of a segment, hence n+1 is the end/start.
                step = 2*(cPoints_X_limits[segment][1] - cPoints_X_limits[segment][0])/(cSegment + 1)
                U = [u*step for u in range(1,math.ceil(cSegment) + 1)]

                if not indx == middle:
                    cPoints = []
                    for cPoint in cPoints_Y[segment]:
                        indx_tmp = int(indx.split('-')[0])
                        middle_tmp = int(middle)
                        if indx_tmp > middle_tmp:
                            index = middle_tmp - (indx_tmp - middle_tmp)
                        else:
                            index = indx_tmp
                        cPoints.append(index*cPoint/middle_tmp)

                extrude_value.extend(self.bezierCurve(cPoints_Y[segment],U))

                if not segment == len(curve) - 1:
                    #Append the control point value at the end of each segment
                    extrude_value.append(cPoints_Y[segment][-1])

            data_extruded[indx] = self.extrude(extrude_value,data[indx])

        return data_extruded


    def extrude(self,extrusion_value,data):
        """ Complemetary function to calculate extrusion

        """
        res = list()
        for indx,vertex in enumerate(data):
            res.append((vertex,extrusion_value[int(indx)]))

        return res


    def bezierCurve(self,cPoints,grid):
        """ Calculate cubic bezier curve between two points
            input: control points, step
            output: list

        """
        curve = []
        for u in grid:
            curve.append(cPoints[0]*((1-u)**3) + cPoints[1]*3*u*((1-u)**2) + cPoints[2]*(3*u**2)*(1-u) + cPoints[3]*(u**3))

        return curve


    def correctShapeSurface(self,target_obj):
        """ Move the gridded shape onto the surface of the mesh by calculating the closest intersection between a line of two vertices and the shape faces

            Input: mesh object
            Output:

        """

        target_obj.vertex_groups.active_index = target_obj.vertex_groups['grid_intersection_group'].index
        bpy.ops.object.vertex_group_select()
        target_obj.vertex_groups.active_index = target_obj.vertex_groups['grid_intersection_group_extruded'].index
        bpy.ops.object.vertex_group_select()
        target_obj.vertex_groups.active_index = target_obj.vertex_groups['modifier_group'].index
        bpy.ops.object.vertex_group_select()
        bpy.ops.mesh.intersect(mode='SELECT', use_separate=True, threshold=1e-06)
        bpy.ops.mesh.remove_doubles()

        define_new_group('intersection',target_obj)
        bpy.ops.mesh.select_all(action='DESELECT')

        target_obj.vertex_groups.active_index = target_obj.vertex_groups['grid_intersection_group_extruded'].index
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.vertex_group_remove()
        bpy.ops.mesh.delete(type='VERT')

        target_obj.vertex_groups.active_index = target_obj.vertex_groups['grid_intersection_group'].index
        bpy.ops.object.vertex_group_select()

        bm = bmesh.from_edit_mesh(target_obj.data)
        bm.verts.ensure_lookup_table()
        verts = [v for v in bm.verts if v.select]

        duplicates = []
        for v in verts:
            max_length = 0
            for l_edge in v.link_edges:
                edge_length = l_edge.calc_length()
                if max_length <= edge_length:
                    max_length = edge_length
                    other_v = l_edge.other_vert(v)
            duplicates.append((v.index,other_v.index))

        for line in duplicates:
            bm.verts[line[0]].select = False
            bm.verts[line[1]].select = True

        bmesh.update_edit_mesh(bpy.context.object.data)

        define_new_group('intersection_corrected',target_obj)

        bm = bmesh.from_edit_mesh(target_obj.data)
        bm.verts.ensure_lookup_table()
        for line in duplicates:
            bm.verts[line[0]].co = bm.verts[line[1]].co
        bmesh.update_edit_mesh(bpy.context.object.data)
    
    def modal(self, context, event):
        self.execute(context)
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

def register():
    bpy.utils.register_class(ApplyDrawnShapeOperator)
    bpy.ops.debug.apply_drawn_shape('INVOKE_DEFAULT')

def unregister():
    bpy.utils.unregister_class(ApplyDrawnShapeOperator)


if __name__ == "__main__":
    register()



