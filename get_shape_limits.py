    def get_shape_limits(self, verts):
        """ Find the shape "beginning" and "end" in XY plane.

            If the shape is contained in one quadrant only, look for x-coordinate min and max
            If the shape is in two quadrants - look for min/max of x-coordinate or y-coordinate, depending on the shape position
            If the hape is in three quadrants - look for min or max in x-coordinate or y-coordinate
            Shapes in four quadrants are not handled
        """

        boundary_vertex_map = {}
        boundary_vertex_map['Q1'] = {v.index: v.co.x for v in verts if v.co.x > 0 and v.co.y > 0}
        boundary_vertex_map['Q2'] = {v.index: v.co.x for v in verts if v.co.x < 0 and v.co.y > 0}
        boundary_vertex_map['Q3'] = {v.index: v.co.x for v in verts if v.co.x < 0 and v.co.y < 0}
        boundary_vertex_map['Q4'] = {v.index: v.co.x for v in verts if v.co.x > 0 and v.co.y < 0}

        shape_coverage = set([key for key in boundary_vertex_map.keys() if len(boundary_vertex_map[key])])

        if len(shape_coverage) == 1:
            shape_min = min(verts, key=lambda v: v.co.x)
            shape_max = max(verts, key=lambda v: v.co.x)
        elif len(shape_coverage) == 2:
            if shape_coverage.issubset(set(['Q1', 'Q2'])):
                shape_min = max(verts, key=lambda v: v.co.x)
                shape_max = min(verts, key=lambda v: v.co.x)
            elif shape_coverage.issubset(set(['Q3', 'Q4'])):
                shape_min = min(verts, key=lambda v: v.co.x)
                shape_max = max(verts, key=lambda v: v.co.x)
            elif shape_coverage.issubset(set(['Q4', 'Q1'])):
                shape_min = min(verts, key=lambda v: v.co.y)
                shape_max = max(verts, key=lambda v: v.co.y)
            else:
                shape_min = max(verts, key=lambda v: v.co.y)
                shape_max = min(verts, key=lambda v: v.co.y)
        elif len(shape_coverage) == 3:
            if shape_coverage.issubset(set(['Q3', 'Q4', 'Q1'])):
                shape_min = min(filter(lambda v: v.co.x < 0.0 and v.co.y < 0.0, verts), key=lambda v: v.co.x)
                shape_max = max(filter(lambda v: v.co.x > 0.0 and v.co.y > 0.0, verts), key=lambda v: v.co.y)
            elif shape_coverage.issubset(set(['Q1', 'Q2', 'Q3'])):
                shape_min = max(filter(lambda v: v.co.x > 0.0 and v.co.y > 0.0, verts), key=lambda v: v.co.x)
                shape_max = min(filter(lambda v: v.co.x < 0.0 and v.co.y < 0.0, verts), key=lambda v: v.co.y)
            elif shape_coverage.issubset(set(['Q4', 'Q1', 'Q2'])):
                shape_min = min(filter(lambda v: v.co.x > 0.0 and v.co.y < 0.0, verts), key=lambda v: v.co.y)
                shape_max = min(filter(lambda v: v.co.x < 0.0 and v.co.y > 0.0, verts), key=lambda v: v.co.x)
            else:
                shape_min = max(filter(lambda v: v.co.x < 0.0 and v.co.y > 0.0, verts), key=lambda v: v.co.y)
                shape_max = max(filter(lambda v: v.co.x > 0.0 and v.co.y < 0.0, verts), key=lambda v: v.co.x)
        else:
            logger.error("Cannot handle shapes in four quadrants yet")

        return shape_min, shape_max



#get the vertex angle between 2 vertices
def get_vertex_angle(vtx1=(), vtx2=()):
    def __dot(v1=(), v2=()):
        return  (v1[0] * v2[0]) + (v1[1] * v2[1])
    def __len(v1=()):
        return  sqrt((v1[0] **2) + (v1[1] **2))

    def __norm(v1=()):
        v = (v1[0] / __len(v1), v1[1] / __len(v1))
        return  v

    if len(vtx1) != len(vtx2) and len(vtx1) != 2:
        raise Exception("Error vector operation: Different lengths!")

    angle = acos(__dot(__norm(vtx1), __norm(vtx2)))
    degs = angle * 180 / math.pi
    return degs
