from math import sqrt
from datetime import datetime
import numpy
import matplotlib.pyplot as plt
import localization as lx
# from mpl_toolkits.mplot3d import Axes3D
from random import randint, uniform, gauss


def distance2points(p1, p2):
    """
    distane between two 3d points
    :param p1: (x, y, z)
    :param p2: (x, y, z)
    :return: r
    """
    return sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2 + (p1[2] - p2[2])**2)

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        serial = obj.isoformat()
        return serial
    return str(obj)

def plane_fit(points):
    """
    
    p, n = planeFit(points)

    Given an array, points, of shape (d,...)
    representing points in d-dimensional space,
    fit an d-dimensional plane to the points.
    Return a point, p, on the plane (the point-cloud centroid),
    and the normal, n.
    https://stackoverflow.com/questions/12299540/plane-fitting-to-4-or-more-xyz-points
    pts = np.diag((.1, 10)).dot(randn(2,1000)) + np.reshape((10, 100),(2,-1))
    
    The fit plane is very nearly at (10, 100) with a normal very nearly along the x axis.
    
    planeFit(pts)
        (array([ 10.00382471,  99.48404676]),
         array([  9.99999881e-01,   4.88824145e-04]))
    """

    from numpy.linalg import svd
    points = numpy.reshape(points, (numpy.shape(points)[0], -1)) # Collapse trialing dimensions
    assert points.shape[0] <= points.shape[1], "There are only {} points in {} dimensions.".format(points.shape[1], points.shape[0])
    ctr = points.mean(axis=1)
    x = points - ctr[:,numpy.newaxis]
    M = numpy.dot(x, x.T) # Could also use numpy.cov(x) here.
    return ctr, svd(M)[0][:,-1]

def plane_fit_v2():
    """Fixme/copypasted"""
    N_POINTS = 10
    TARGET_X_SLOPE = 2
    TARGET_y_SLOPE = 3
    TARGET_OFFSET = 5
    EXTENTS = 5
    NOISE = 5

    # create random data
    xs = [numpy.random.uniform(2 * EXTENTS) - EXTENTS for i in range(N_POINTS)]
    ys = [numpy.random.uniform(2 * EXTENTS) - EXTENTS for i in range(N_POINTS)]
    zs = []
    for i in range(N_POINTS):
        zs.append(xs[i] * TARGET_X_SLOPE + \
                  ys[i] * TARGET_y_SLOPE + \
                  TARGET_OFFSET + numpy.random.normal(scale=NOISE))

    # plot raw data
    plt.figure()
    ax = plt.subplot(111, projection='3d')
    ax.scatter(xs, ys, zs, color='b')

    # do fit
    tmp_A = []
    tmp_b = []
    for i in range(len(xs)):
        tmp_A.append([xs[i], ys[i], 1])
        tmp_b.append(zs[i])
    b = numpy.matrix(tmp_b).T
    A = numpy.matrix(tmp_A)
    fit = (A.T * A).I * A.T * b
    errors = b - A * fit

def trilaterate(anchors):
    """
    :param anchors: Dict with key=(location (x, y, z)
            and value distance 
    :return: (x, y, z)
    """
    P = lx.Project(mode='3D', solver='LSE')
    t, label = P.add_target()
    for location, distance in anchors.items():
        P.add_anchor(location, location)
        t.add_measure(location, distance)
    P.solve()
    return (t.loc.x, t.loc.y, t.loc.z)

def point_trilateration_test(point, N, limits, error, rand=uniform):
    res = {}
    for i in range(N):
        p = (
            rand(limits[0][0], limits[1][0]),
            rand(limits[0][1], limits[1][1]),
            rand(limits[0][2], limits[1][2])
        )
        print(p)
        res[p] = distance2points(point, p) + gauss(0, error)
    return res


if __name__ == "__main__":
    point = (1, 2, 3)
    # bbox = ((3, 4, 7), (9, 7, 9)) # point outside the bbox
    bbox = ((-3, -4, -7), (9, 7, 9)) # point inside the bbox
    anchors = point_trilateration_test(point, 4, bbox, 0.1)
    print(anchors)
    for i in range(1):
        t = trilaterate(anchors)
    print(t)