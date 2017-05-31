import bpy
import bmesh


def rotFaces(rotval, arrsel, bme):
    for f in arrsel:
        f.select = True
    print('faces in array: ', arrsel)
    for f in bme.faces:
        print('Test selected index:', f.index, f.select)
    # bpy.ops.object.mode_set(mode = 'EDIT', toggle = False)
    #    bpy.ops.mesh.split()
    #    bpy.ops.transform.rotate(value=(rotval), axis=(0,0,1))
    #    bpy.ops.object.mode_set(mode = 'OBJECT', toggle = False)
    for f in bme.faces:
        f.select = False


ob = bpy.context.active_object
me = ob.data
bm = bmesh.new()
bm.from_mesh(me)
bm.normal_update()
print('selected bmesh:', bm)

bpy.ops.object.mode_set(mode='EDIT', toggle=False)
bpy.ops.mesh.select_all(action='DESELECT')
bpy.context.scene.tool_settings.mesh_select_mode = (False, False, True)
bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

for f in bm.faces:
    print('face index:', f.index, ' and face normal:', f.normal)

#xminus = []
#yminus = []
#yplus = []

#for f in bm.faces:
#    if f.normal[0] < 0:
#        xminus.append(f)

#for f in bm.faces:
#    if f.normal[1] < 0:
#        yminus.append(f)

#for f in bm.faces:
#    if f.normal[1] > 0:
#        yplus.append(f)

#print('xminus: ', xminus)
#print('yminus: ', yminus)
#print('yplus: ', yplus)

#rotv = 3.141529
#rotFaces(rotv, xminus, bm)
#bm.to_mesh(me)
#rotv = 3.141529 / 2
#rotFaces(rotv, yminus, bm)
#bm.to_mesh(me)
#rotv = -3.141529 / 2
#rotFaces(rotv, yplus, bm)
#bm.to_mesh(me)