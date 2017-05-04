import bpy
import bmesh
import math
import mathutils
import json
import time
from mathutils import Vector, Matrix
import pdb as DBG

# exec(compile(open('/home/ilian/gitprojects/blender-shapetool/MatrixApproach.py').read(), '/home/ilian/gitprojects/blender-shapetool/MatrixApproach.py', 'exec'))


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


def define_new_group(group_name, obj):
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


class ControlPoints():
    """ Handle the control points

    """

    def __init__(self, control_set, height):
        self._control_set = control_set
        self.height = height
        self.curve_max = self.find_max()
        self.control_points_x = self.get_control_points_X()
        self.control_points_y = self.get_control_points_Y()
        self.control_points_limits = self.get_control_points_limits()

    def find_max(self):
        curve_data = []
        for curve in self._control_set:
            curve_data.append(1 - curve["start"]["position"]["y"])
            curve_data.append(1 - curve["end"]["position"]["y"])
            curve_data.append(1 - curve["start"]["control"]["y"])
            curve_data.append(1 - curve["end"]["control"]["y"])
        return max(curve_data)

    def get_control_points_Y(self):
        control_points = {}
        for indx, segment in enumerate(self._control_set):
            control_points[indx] = [((1 - segment["start"]["position"]["y"])/self.curve_max)*self.height]
            control_points[indx].append(((1 - segment["start"]["control"]["y"])/self.curve_max)*self.height)
            control_points[indx].append(((1 - segment["end"]["control"]["y"])/self.curve_max)*self.height)
            control_points[indx].append(((1 - segment["end"]["position"]["y"])/self.curve_max)*self.height)
        return control_points

    def get_control_points_X(self):
        control_points = {}
        for indx, segment in enumerate(self._control_set):
            control_points[indx] = [segment["start"]["position"]["x"]]
            control_points[indx].append(segment["start"]["control"]["x"])
            control_points[indx].append(segment["end"]["control"]["x"])
            control_points[indx].append(segment["end"]["position"]["x"])
        return control_points

    def get_control_points_limits(self):
        limits = {}
        for indx, segment in enumerate(self._control_set):
            limits[indx] = [min(self.control_points_x[indx])]
            limits[indx].append(max(self.control_points_x[indx]))
        return limits

BL_MAIN_OBJ_NAME = bpy.data.objects['ImportedMesh'].name
BL_SHAPE_TOOL_OBJ_NAME = bpy.data.objects['ShapeBezierCurve'].name
BL_SHAPE_PREVIEW_OBJ_NAME = BL_MAIN_OBJ_NAME

print("------------------------ TEST ------------------- ")

# class ApplyDrawnShapeOperator(bpy.types.Operator):
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


def execute():
    if BL_SHAPE_TOOL_OBJ_NAME not in bpy.data.objects.keys():
        return {'CANCELLED'}

    # hide manipulators
    # view3d_space = get_view3d_space()
    # view3d_space.transform_manipulators = set()
    # view3d_space.show_manipulator = False

    target_obj = select_object(target_objname)
    save_vertex_groups(target_obj)
    duplicate_target_obj = None

    # New stuff
    target_obj.hide = False
    for obj in bpy.data.objects:
        if 'Sphere' in obj.name:
            obj.hide = True
    # End of new stuff

    select_object(target_obj.name)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode='OBJECT')

    shape_obj = select_object(BL_SHAPE_TOOL_OBJ_NAME)
    # create copy of the shape
    bpy.ops.object.duplicate_move()
    duplicate_shape = bpy.context.object

    bpy.ops.object.convert(target="MESH")
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.vertices_smooth(repeat=2)

    bpy.ops.mesh.select_all(action="SELECT")
    define_new_group("shape_group", target_obj)
    bpy.ops.object.mode_set(mode='OBJECT')

    shape_obj = select_object(BL_SHAPE_TOOL_OBJ_NAME)
    bpy.ops.object.modifier_add(type='SHRINKWRAP')
    shape_obj.modifiers["Shrinkwrap"].target = bpy.data.objects[target_obj.name]
    shape_obj.modifiers["Shrinkwrap"].offset = 0.001
    shape_obj.modifiers["Shrinkwrap"].wrap_method = 'NEAREST_SURFACEPOINT'
    bpy.ops.object.modifier_apply(modifier="Shrinkwrap")

    unselect_all()
    duplicate_shape.select = True
    target_obj.select = True
    bpy.context.scene.objects.active = target_obj
    bpy.ops.object.join()

    select_object(target_obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)

    # -0.003 defines the amount of extrusion towards Origin
    bpy.ops.mesh.select_all(action='DESELECT')
    target_obj.vertex_groups.active_index = target_obj.vertex_groups['shape_group'].index
    bpy.ops.object.vertex_group_select()

    bm = bmesh.from_edit_mesh(target_obj.data)
    bm.verts.ensure_lookup_table()
    edges = [e for e in bm.edges if e.select]
    ret = bmesh.ops.extrude_edge_only(bm, edges=edges)
    for elm in ret['geom']:
        if isinstance(elm, bmesh.types.BMVert):
            elm.co += -0.003 * elm.normal
    bmesh.update_edit_mesh(target_obj.data)
    bpy.ops.object.vertex_group_select()

    bpy.ops.mesh.select_all(action='DESELECT')
    target_obj.vertex_groups.active_index = target_obj.vertex_groups['shape_group'].index
    bpy.ops.object.vertex_group_select()

    bpy.ops.mesh.intersect()
    bpy.ops.mesh.remove_doubles()

    define_new_group('shape_intersection_group', target_obj)

    bpy.ops.mesh.select_all(action='DESELECT')
    target_obj.vertex_groups.active_index = target_obj.vertex_groups['shape_group'].index
    bpy.ops.object.vertex_group_select()
    bpy.ops.mesh.delete(type='VERT')
    bpy.ops.object.vertex_group_remove(all=False)

    bpy.ops.mesh.select_all(action='DESELECT')
    target_obj.vertex_groups.active_index = target_obj.vertex_groups['shape_intersection_group'].index
    bpy.ops.object.vertex_group_select()

    bpy.ops.mesh.delete_loose()
    bpy.ops.object.vertex_group_select()

    print('Correcting shape loop over socket surface')
    clean_shape_loop(target_obj)

    bpy.ops.mesh.loop_to_region()
    define_new_group('modifier_group', target_obj)

    bpy.ops.mesh.region_to_loop()
    define_new_group('shape_intersection_group', target_obj)

    # New stuff from here
    curveXdata = [{'end': {'control': {'x': 0.25, 'y': 0.33},
                           'position': {'x': 0.5, 'y': 0.33}},
                   'start': {'control': {'x': 0, 'y': 0.75},
                             'position': {'x': 0, 'y': 1}}},
                  {'end': {'control': {'x': 1, 'y': 0.75},
                           'position': {'x': 1, 'y': 1}},
                   'start': {'control': {'x': 0.75, 'y': 0.33},
                             'position': {'x': 0.5, 'y': 0.33}}}]
    curveYdata = [{'end': {'control': {'x': 0.25, 'y': 0.33},
                           'position': {'x': 0.5, 'y': 0.33}},
                   'start': {'control': {'x': 0, 'y': 0.75},
                             'position': {'x': 0, 'y': 1}}},
                  {'end': {'control': {'x': 1, 'y': 0.75},
                           'position': {'x': 1, 'y': 1}},
                   'start': {'control': {'x': 0.75, 'y': 0.33},
                             'position': {'x': 0.5, 'y': 0.33}}}]

    time_start = time.time()
    shape_grid, middle_vertex_X, middle_vertex_Y = make_grid(target_obj)
    print("make_grid: %.4f sec" % (time.time() - time_start))

    extrude_values = blend_curves(target_obj, shape_grid, middle_vertex_X, middle_vertex_Y, curveXdata, curveYdata)

    # Extrude
    bm = bmesh.from_edit_mesh(target_obj.data)
    bm.verts.ensure_lookup_table()
    for indx, value in extrude_values.items():
        bm.verts[indx].co += bm.verts[indx].normal * value
    bmesh.update_edit_mesh(bpy.context.object.data)

    # Apply smooth modifier
    bpy.ops.object.modifier_add(type='SMOOTH')
    bpy.context.object.modifiers["Smooth"].vertex_group = "modifier_group"
    bpy.context.object.modifiers["Smooth"].iterations = 5
    bpy.context.object.modifiers["Smooth"].factor = 0.5
    bpy.ops.object.mode_set(mode="OBJECT")

    return {'FINISHED'}


def blend_curves(target_obj, shape_grid, middle_vertex_X, middle_vertex_Y, curveXdata=[], curveYdata=[]):
    """ Blend the user defined (X,Y) curves and store each vertex value in a dictionary.

        Input: mesh object
        Output: dict{BMVert.index : extrude_value}
    """

    # curveXdata = json.loads(self.x_displacement)
    # curveYdata = json.loads(self.y_displacement)
    height = 15

    # Handle the no curves case
    if not(curveXdata and curveYdata):
        extrude_values = {}
        for v_index, data in shape_grid.items():
            extrude_values[v_index] = height/1000

        # restore state and selection
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action='DESELECT')
        target_obj.vertex_groups.active_index = target_obj.vertex_groups['shape_intersection_group'].index
        bpy.ops.object.vertex_group_select()

        return extrude_values

    # separate the curve data
    curveX = ControlPoints(curveXdata, height)
    curveY = ControlPoints(curveYdata, height)

    # caluclate the extrusion
    columnData_extruded = calculate_extrusion(shape_grid, curveX, 'row', middle_vertex_X)
    rowData_extruded = calculate_extrusion(shape_grid, curveY, 'column', middle_vertex_Y)

    bm = bmesh.from_edit_mesh(target_obj.data)
    bm.verts.ensure_lookup_table()
    # blend the extruded values by doing weighted average (consider revision) and store the result in a dictionary
    extrude_values = {}
    for v_index, value in columnData_extruded.items():
        if bm.verts[v_index].tag:
            continue
        else:
            extrude_values[v_index] = value/1000
            if v_index == middle_vertex_X['vertex'].index:
                bm.verts[v_index].tag = True

    for v_index, value in rowData_extruded.items():
        if bm.verts[v_index].tag:
            continue
        else:
            extrude_values[v_index] = (extrude_values[v_index] + value/1000)/2

    bmesh.update_edit_mesh(bpy.context.object.data)

    # restore state and selection
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action='DESELECT')
    target_obj.vertex_groups.active_index = target_obj.vertex_groups['shape_intersection_group'].index
    bpy.ops.object.vertex_group_select()

    return extrude_values


def make_grid(obj):
    """ Create a 2D map of the shape vertices, where each vertex has a unique column and row.
        Add "boundaries" which will outline the shape
    """

    # Find the first quadrant and first vertex that lays in this first quadrant
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    verts = [v for v in bm.verts if v.select]


    shape_min, shape_max = get_shape_limits(verts)

    for v in verts:
        v.tag = True
    bmesh.update_edit_mesh(bpy.context.object.data)

    obj.vertex_groups.active_index = obj.vertex_groups['modifier_group'].index
    bpy.ops.object.vertex_group_select()

    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    verts = [v for v in bm.verts if v.select]

    # Create an initial map of all vertices based on the shape limits
    time_start = time.time()
    sorted_initial_vert_map = create_shape_vertex_map(shape_min, shape_max, verts)
    print("create_shape_vertex_map: %.4f sec" % (time.time() - time_start))

    bmesh.update_edit_mesh(bpy.context.object.data)
    bpy.ops.mesh.select_all(action='DESELECT')
    obj.vertex_groups.active_index = obj.vertex_groups['shape_intersection_group'].index
    bpy.ops.object.vertex_group_select()

    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()

    # Create the shape grid and sort by x-coordinate first
    shape_grid = {}
    inner_columns = {}
    outer_columns = {}

    step = 0
    for quadrant in sorted_initial_vert_map:
        for indx, v in enumerate(quadrant):
            if bm.verts[v].select:
                shape_grid[v] = {"vertex": bm.verts[v],
                                 "column": (indx+step),
                                 "border_vertex": True}
                outer_columns[(indx+step)] = {"vertex": bm.verts[v].index}
                #print("Outer columns: {}".format(indx+step))
            else:
                shape_grid[v] = {"vertex": bm.verts[v],
                                 "column": (indx+step),
                                 "inner_vertex": True}
                inner_columns[(indx+step)] = {"vertex": bm.verts[v].index}
                #print("Inner columns: {}".format(indx+step))
        step += (indx + 1)


    # Sort by z-coordinate
    verts_z = {v.index: v.co.z for v in verts}
    sorted_verts_z = sorted(verts_z, key=(lambda k: verts_z[k]), reverse=True)

    inner_rows = {}
    outer_rows = {}

    for indx, v in enumerate(sorted_verts_z):
        if bm.verts[v].tag:
            shape_grid[v].update(row=indx)
            outer_rows[indx] = {"vertex": bm.verts[v].index}
        else:
            shape_grid[v].update(row=indx)
            inner_rows[indx] = {"vertex": bm.verts[v].index}

    bmesh.update_edit_mesh(bpy.context.object.data)

    # Add boundaries to the new 2D grid by looping through the shape loop vertices.
    # First sort which of the edge vertices is larger (row/column wise) and find the
    # vertices that have row/column between these two edge vertices. Then take either
    # column/row value as the boundary for the vertex's row/column.
    bpy.ops.mesh.select_all(action='DESELECT')
    obj.vertex_groups.active_index = obj.vertex_groups['shape_intersection_group'].index
    bpy.ops.object.vertex_group_select()

    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    edges = [e for e in bm.edges if e.select]
    for v in bm.verts:
        v.select = False
    for e in edges:
        column_A = shape_grid[e.verts[0].index]['column']
        column_B = shape_grid[e.verts[1].index]['column']
        if column_A > column_B:
            column_B, column_A = column_A, column_B
        row_A = shape_grid[e.verts[0].index]['row']
        row_B = shape_grid[e.verts[1].index]['row']
        if row_A > row_B:
            row_B, row_A = row_A, row_B
        middle_columns = [column for column in range(column_A + 1, column_B)]
        middle_rows = [row for row in range(row_A + 1, row_B)]

        visited = []
        for column in middle_columns:
            try:
                vertex = shape_grid[inner_columns[column]['vertex']]
                visited.append(vertex['vertex'].index)
            except KeyError:
                pass
            else:
                row_1 = shape_grid[outer_columns[column_A]['vertex']]['row']
                row_2 = shape_grid[outer_columns[column_B]['vertex']]['row']
                if 'column_rows' in vertex.keys():
                    vertex['column_rows'].append(row_1)
                else:
                    vertex.update(column_rows=[row_1])
                    vertex['vertex'].select = True
        for row in middle_rows:
            try:
                vertex = shape_grid[inner_rows[row]['vertex']]
            except KeyError:
                pass
            else:
                column_1 = shape_grid[outer_rows[row_A]['vertex']]['column']
                column_2 = shape_grid[outer_rows[row_B]['vertex']]['column']
                if 'row_columns' in vertex.keys():
                    vertex['row_columns'].append(column_1)
                else:
                    vertex.update(row_columns=[column_1])

    # Leave only the closest boundary rows/columns to the current vertex
    for v in shape_grid.keys():
        if 'border_vertex' not in shape_grid[v].keys():
            vertex = shape_grid[v]
            row_A = min(vertex['row_columns'])
            row_B = max(vertex['row_columns'])
            try:
                column_A = min(vertex['column_rows'])
                column_B = max(vertex['column_rows'])
            except KeyError:
                print('ERROR')
                print(vertex)
                raise
            for column in vertex['row_columns']:
                if column > vertex['column'] and column <= row_B:
                    row_B = column
                elif column < vertex['column'] and column >= row_A:
                    row_A = column
            for row in vertex['column_rows']:
                if row > vertex['row'] and row <= column_B:
                    column_B = row
                elif row < vertex['row'] and row >= column_A:
                    column_A = row
            vertex['row_columns'] = (row_A, row_B)
            vertex['column_rows'] = (column_A, column_B)

    try:
        middle_vertex_Y = shape_grid[inner_columns[round(len(shape_grid)/2)]['vertex']]
    except KeyError:
        middle_vertex_Y = shape_grid[outer_columns[round(len(shape_grid)/2)]['vertex']]
    try:
        middle_vertex_X = shape_grid[inner_rows[round(len(shape_grid)/2)]['vertex']]
    except KeyError:
        middle_vertex_X = shape_grid[outer_rows[round(len(shape_grid)/2)]['vertex']]

    bmesh.update_edit_mesh(bpy.context.object.data)

    return shape_grid, middle_vertex_X, middle_vertex_Y


def create_shape_vertex_map(shape_min, shape_max, verts):
    """ Create an initial vertices map of the shape, taking into account
        the shape limits (shape_min, shape_max). Can handle up to three quadrants.

    """

    initial_vert_map = {}
    verts_x_q1 = {v.index: v.co.x for v in verts if v.co.x > 0 and v.co.y > 0}
    sorted_verts_x_q1 = sorted(verts_x_q1, key=(lambda k: verts_x_q1[k]), reverse=True)
    initial_vert_map['Q1'] = sorted_verts_x_q1

    verts_x_q2 = {v.index: v.co.x for v in verts if v.co.x < 0 and v.co.y > 0}
    sorted_verts_x_q2 = sorted(verts_x_q2, key=(lambda k: verts_x_q2[k]), reverse=True)
    initial_vert_map['Q2'] = sorted_verts_x_q2

    verts_x_q3 = {v.index: v.co.x for v in verts if v.co.x < 0 and v.co.y < 0}
    sorted_verts_x_q3 = sorted(verts_x_q3, key=(lambda k: verts_x_q3[k]))
    initial_vert_map['Q3'] = sorted_verts_x_q3

    verts_x_q4 = {v.index: v.co.x for v in verts if v.co.x > 0 and v.co.y < 0}
    sorted_verts_x_q4 = sorted(verts_x_q4, key=(lambda k: verts_x_q4[k]))
    initial_vert_map['Q4'] = sorted_verts_x_q4

    shape_coverage = [key for key in initial_vert_map.keys() if len(initial_vert_map[key])]

    sorted_initial_vert_map = []
    visited = []
    for limit in [shape_min, shape_max]:
        for quadrant in shape_coverage:
            if limit.index in initial_vert_map[quadrant]:
                sorted_initial_vert_map.append(initial_vert_map[quadrant])
                visited.append(quadrant)

    for quadrant in shape_coverage:
        if quadrant not in visited:
            sorted_initial_vert_map.insert(1, initial_vert_map[quadrant])

    return sorted_initial_vert_map


def get_shape_limits(verts):
    """ Find the shape "beginning" and "end" in XY plane.

        If the shape is contained in one quadrant only, look for x-coordinate min and max
        If the shape is in two quadrants - look for min/max of x-coordinate or y-coordinate, depending on the shape position
        If the hape is in three quadrants - look for min or max in x-coordinate or y-coordinate
        Shapes in four quadrants are not handled
    """

    # helper mapper class to map a vertex to specific angle
    # then sort by criteria and return the appropriate vtx
    class VtxAngleMap(object):
        def __init__(self, bmv, angle, idx):
            self.bmvert = bmv
            self.angle = angle
            self.index = idx

    # dummy bubble sort - will work with it to qsort or if there is python way
    def __sort(data): # works only for the VtxAnlgeMaps....
        i, j = 0, 0
        while i < len(data):
            j = i
            while j < len(data):
                if data[i].angle > data[j].angle:
                    tmp = data[i]
                    data[i] = data[j]
                    data[j] = tmp
                j += 1
            i +=1

    # get an angle of a point in 2D by origin (0, 0)
    def get_vertex_angle2(y, x):
        theta_rad = atan2(y, x)
        deg_fix = 0
        if theta_rad < 0:
            deg_fix = 360 # fix for negative degrees
        theta_deg = (theta_rad / math.pi *180) + (deg_fix)
        return theta_deg


    sorted_verts=[] # returned sorted verts by begin and end
    vtxmap=[] # list of mapped values, helper for the sort and other checks

    for v in verts: # organize vtxmap with bmvert, angle and optional index
        vtxmap.append(VtxAngleMap(v, get_vertex_angle2(v.co.y, v.co.x), v.index))

    __sort(vtxmap) # sort by the angle

    # find the gap - it's gap if the difference between 2 angles is more than 2 (hardcoded for now)
    for i in range(0, len(vtxmap)-1):
        if vtxmap[i+1].angle - vtxmap[i].angle > 2: # it's a gap
            # do the list vertex that starts the gap
            # will be the start of the new list
            # and the second vertex will be at the end
            j = i
            h = j
            while j >=0:
                sorted_verts.append(vtxmap[j].bmvert)
                j -= 1
            j = len(vtxmap)-1
            while j > h:
                sorted_verts.append(vtxmap[j].bmvert)
                j -= 1
            break

    return sorted_verts


def clean_shape_loop(obj):
    """ Clean shape - edges at tight places, faces at sharp corners and
        hole pairs in the loop.

        Extensive debug messaging added as this is a key moment.

        Input:
        Output:
    """

    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    faces = [f for f in bm.faces if f.select]

    # Handle faces - dissolve if any and then loop to see if some are left.
    # If this is true, connect vertices with edges to split the faces
    if faces:
        print('Correcting {} faces'.format(len(faces)))
        bmesh.ops.dissolve_faces(bm, faces=faces)
        faces = [f for f in bm.faces if f.select]
        for face in faces:
            vs = [v for v in face.verts]
            bmesh.ops.connect_vert_pair(bm, verts=vs)

    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()

    # Loop over the vertices in the shape loop and count how many edges are
    # linked to each vertice.
    # Based on this count, we will try to find 'holes' in the shape loop.

    indx = 0
    vertices = [[v, indx] for v in bm.verts if v.select]
    edges = [e for e in bm.edges if e.select]

    for v in vertices:
        for e in edges:
            if v[0] in e.verts:
                v[1] += 1

    # If there is just one edge connected to a vertice then there is a gap
    # (vers_at_limit). However, if there are more than two, there is a
    # bridge between a tight spot at the shape loop and the edges
    # connecting them will be dissolved.  If there is a single hole,
    # connect the two vertices, if there are more than two (and even), loop
    # over the vertices at the holes and look for the min distance. Based
    # on this connect the vertice pairs.
    # NOTE: bmesh.ops.connect_vert_pair sometimes finishes without output
    # results (or error) - this usually happens when the vertices are
    # inside a face (not lying on the borders)

    verts_at_limit = [v[0] for v in vertices if v[1] < 2]
    verts_at_shortcuts = [v[0] for v in vertices if v[1] > 2]

    if verts_at_limit:
        print('Number of vertices at shape loop gap: {}'.format(len(verts_at_limit)))
        if len(verts_at_limit) == 1:
            print('[Unhandled] Number of vertices at shape loop gap: {}'.format(len(verts_at_limit)))
        elif len(verts_at_limit) == 2:
            cEdges = bmesh.ops.connect_vert_pair(bm, verts=verts_at_limit)
            if not cEdges['edges']:
                print("Empty result, expecting bad geometry: {}, vertices {}".format(cEdges, verts_at_limit))
            else:
                for edge in cEdges['edges']:
                    edge.select = True
            bm.edges.ensure_lookup_table()
        else:
            pairs = []
            for v in verts_at_limit:
                min_dist = [calc_distance(v.co, Vector((0.0, 0.0, 0.0))), v]
                verts_at_limit_copy = [vd for vd in verts_at_limit if vd != v]
                for vc in verts_at_limit_copy:
                    if vc not in [vert for e in v.link_edges for vert in e.verts]:
                        dist = calc_distance(v.co, vc.co)
                        if min_dist[0] > dist:
                            min_dist[0] = dist
                            min_dist[1] = vc
                pairs.append((v, min_dist[1]))
            for pair in pairs:
                cEdges = bmesh.ops.connect_vert_pair(bm, verts=pair)
                if not cEdges['edges']:
                    print("Empty result, expecting bad geometry: {}, vertices: ".format(cEdges, pair))
                else:
                    for edge in cEdges['edges']:
                        edge.select = True
                bm.edges.ensure_lookup_table()
    if verts_at_shortcuts:
        print('Number of vertices at faces/shortcuts: {}'.format(len(verts_at_shortcuts)))
        edges_at_faces = []
        for e in edges:
            if e.verts[0] in verts_at_shortcuts and e.verts[1] in verts_at_shortcuts:
                edges_at_faces.append(e)

        bmesh.ops.dissolve_edges(bm, edges=edges_at_faces)

    bmesh.update_edit_mesh(obj.data)


def calc_distance(origin, vert):
    """ Calculate Euclidean distance between two points

        Input:  mathutils.Vector
        Output: float
    """

    return math.sqrt((vert[0] - origin[0])**2 + (vert[1] - origin[1])**2 + (vert[2] - origin[2])**2)


def calculate_extrusion(data, curve, seq_type, middle_vertex):
    """ Calculate the extrusion for each row/column by applying linear interpolation.

        input: dict{},list(),dict[],list(),list()
        output: dict{sequence: list(BMVerts)}
    """

    data_extruded = {}
    for vertex_index, vertex in data.items():
        if 'border_vertex' not in vertex.keys():
            # The curves can be seen as consisting of segments. Between each
            # segment, there is a cubic bezier fitted. Get the position of the
            # vertex in this context and calculate the necessary extrusion

            if seq_type == 'column':
                data_length = vertex['row_columns'][1] - vertex['row_columns'][0]
                seq_range = 'row_columns'
            elif seq_type == 'row':
                data_length = vertex['column_rows'][1] - vertex['column_rows'][0]
                seq_range = 'column_rows'

            if data_length:
                segment_length = (data_length - (len(curve._control_set) - 1))/len(curve._control_set)
                residual = (data_length - (len(curve._control_set) - 1)) % (len(curve._control_set))
                vertex_position = vertex[seq_type] - vertex[seq_range][0]

                segments = []
                for segment in range(len(curve._control_set)):
                    if residual:
                        # Distribute the residual, by adding an extra row/column
                        current_segment = math.ceil(segment_length)
                        residual -= 1
                        segments.append(current_segment)
                    else:
                        current_segment = segment_length
                        segments.append(current_segment)
                    if vertex_position <= sum(segments):
                        # We have found the segment which vertex_position belongs to
                        # Use this "segment" then
                        break

                # Cubic beziers are calculated in UV space, where the coordinate system limits are in the range 0-1.
                # Calculate a step based on this, by doubling the difference between the x - limits.
                # We have n-columns between start and end of a segment, hence n+1 is the end/start.
                step = 2 * (curve.control_points_limits[segment][1] - curve.control_points_limits[segment][0])/(current_segment + 1)
                U = step * (segments[segment] - (sum(segments) - vertex_position))
                if not vertex_index == middle_vertex['vertex'].index:
                    control_points = []
                    if vertex[seq_type] > middle_vertex[seq_type]:
                        index = middle_vertex[seq_type] - (vertex[seq_type] - middle_vertex[seq_type])
                    else:
                        index = middle_vertex[seq_type]

                    for control_point in curve.control_points_y[segment]:
                        # This forms the extrusion value, based on the distance between the middle and current column/row. Linear interpolation.
                        control_points.append(index*control_point / middle_vertex[seq_type])
                    data_extruded[vertex_index] = bezierCurve(control_points, U)
                else:
                    data_extruded[vertex_index] = bezierCurve(curve.control_points_y[segment], U)
            else:
                # This vertex lying on the border
                data_extruded[vertex_index] = 0.0
    return data_extruded


def bezierCurve(cPoints, u):
    """ Calculate cubic bezier curve between two points
        input: control points, vertex_location in the 2D map
        output: list

    """

    return (cPoints[0]*((1-u)**3) + cPoints[1]*3*u*((1-u)**2) + cPoints[2]*(3*u**2)*(1-u) + cPoints[3]*(u**3))


#def register():
#    bpy.utils.register_class(ApplyDrawnShapeOperator)
#    bpy.ops.debug.apply_drawn_shape('INVOKE_DEFAULT')

#def unregister():
#    bpy.utils.unregister_class(ApplyDrawnShapeOperator)


#if __name__ == "__main__":
#    #register()
#    DBG.run('register()')




