from collections import UserDict
from math import sqrt
from random import randint, random, uniform
import cProfile
import time
import numpy
import numba
from scipy.optimize import root


# has to be changed with the actual c of radiowave in air at room temperature
C = 299792458


#should be optimised
@numba.jit(cache=True)
def point_in_bbox(bbox):#, bbox_int):
    return [uniform(bbox[i], bbox[i+1]) for i in range(int(len(bbox)/2))]


#should be optimised and made to work for !=3d
def in_bbox(point, bbox):
    if (bbox[0] <= point[0] <= bbox[1]) \
        and (bbox[2] <= point[1] <= bbox[3]) \
        and (bbox[4] <= point[2] <= bbox[5]):
        return True


class Anchor(object):
    def __init__(self, id, point):
        self.id = id
        self.point = point
        self.neighbor = None
        self.neighbor_distance = 10e22

    def coordinates(self):
        return self.point.position()

    def distance2anchor(self, anchor):
        return self.point.distance2point(anchor.point)

    def update_neighbor(self, distance, friend):
        if distance < self.neighbor_distance:
            self.neighbor_distance = distance
            self.heighbor = friend

    # should be fixed ...
    def half_way2neighbor(self):
        return self.neighbor_distance / 2


class AnchorMesh(dict):
    def __init__(self, *args, **kwargs):
        self.update(*args, **kwargs)

    def __getitem__(self, key):
        val = dict.__getitem__(self, key)
        return val

    def __setitem__(self, key, val):
        dict.__setitem__(self, key, val)

    def __repr__(self):
        dictrepr = dict.__repr__(self)
        return '%s(%s)' % (type(self).__name__, dictrepr)

    def update(self, *args, **kwargs):
        for k, v in dict(*args, **kwargs).items():
            if not type(v) == Anchor:
                raise TypeError
            self.update_closest_neighbors(v)
            self[k] = v
        self.make_anchors_array()
        self.make_blank_tdoa_array()
        self.make_blank_bbox_array()

    def update_closest_neighbors(self, anchor):
        # distances = dict()
        for friend in self.values():
            distance = anchor.distance2anchor(friend)
            anchor.update_neighbor(distance, friend)
            friend.update_neighbor(distance, anchor)


    def make_anchors_array(self):
        self.anchors_indexing = {}
        self.anchors_array = self.make_blank_anchors_array()
        for i, anchor in enumerate(self.values()):
            self.anchors_indexing.update({anchor.id: i})
            self.anchors_array[i:] = anchor.point
        return self.anchors_indexing, self.anchors_array

    def make_blank_anchors_array(self):
        for pick_one in self.values():
            self.blank_anchors_array = numpy.zeros((len(self),
                                                    len(pick_one.point)))
            return self.blank_anchors_array

    def make_blank_bbox_array(self):
        for pick_one in self.values():
            self.blank_bbox_array = numpy.zeros((len(self),
                                                 len(pick_one.point)*2))
            return self.blank_bbox_array

    def make_blank_tdoa_array(self):
        self.blank_tdoa_array = numpy.empty((len(self),))
        return self.blank_tdoa_array

    def add_anchor(self, anchor):
        self[anchor.id] = anchor

    #################################
    # linear bbox based initial guess
    #################################
    def prepare_f_linear(self, sensor):
        tdoa_array = numpy.array(self.blank_tdoa_array)
        for tdoa in sensor.tdoas.values():
            tdoa_array[self.anchors_indexing[tdoa.anchor.id]] = tdoa.distance

        self.ex_bbox_array = numpy.array(self.blank_bbox_array)
        for i in range(int(self.ex_bbox_array.shape[1]/2)):
            self.ex_bbox_array[:, i * 2] = \
                self.anchors_array[:, i] - tdoa_array
            self.ex_bbox_array[:, i * 2 + 1] = \
                self.anchors_array[:, i] + tdoa_array

    def f_linear(self, zero_time):
        res = []
        for i in range(int(self.ex_bbox_array.shape[1] / 2)):
            res.append(numpy.nanmax(self.ex_bbox_array[:, i * 2]
                                    - zero_time))
            res.append(numpy.nanmin(self.ex_bbox_array[:, i * 2 + 1]
                                    + zero_time))
        res =numpy.prod([abs(res[i] - res[i+1])
                               for i in range(int(len(res)/2))])
        return res

    def find_sensor_position_linear(self, sensor):
        guess = numpy.array([sensor.base_anchor.half_way2neighbor()])
        self.prepare_f_linear(sensor)
        position = root(self.f_linear, guess, jac=False, method='lm',
                        options={
                            'col_deriv': True,
                            'maxiter': 10000,
                            # 'epsfcn': 1,
                            'factor': 0.01,
                            'xtol': 1E-25,
                            'ftol': 1E-25
                        })
        return self.get_linear_result(position.x)

    def get_linear_result(self, zero_time):
        bbox_ex = []
        bbox_in = []
        for i in range(int(self.ex_bbox_array.shape[1] / 2)):
            bbox_ex.append(numpy.nanmax(self.ex_bbox_array[:, i * 2]
                                        - zero_time))
            bbox_ex.append(numpy.nanmin(self.ex_bbox_array[:, i * 2 + 1]
                                        + zero_time))
        p = point_in_bbox(bbox_ex)
        return numpy.array((*p, zero_time))

    ############
    # non-linear
    ############
    def prepare_f_nonlinear(self, sensor):
        self.current_tdoa_array = numpy.array(self.blank_tdoa_array)
        for tdoa in sensor.tdoas.values():
            self.current_tdoa_array[
                self.anchors_indexing[tdoa.anchor.id]] = tdoa.distance
        self.current_base_anchor = numpy.array(sensor.base_anchor.point)
        # print('anchor point expanded', self.anchors_array)

    # @numba.jit(nopython=False, cache=True)
    def f_non_linear(self, x):
        # XXX: remove the sqrts when it starts working
        base = numpy.sqrt(numpy.sum(numpy.square(
                self.current_base_anchor - x[1:]))) + x[0]
        expanded_base = numpy.expand_dims(base, 2)
        expanded_base = numpy.tile(expanded_base,
                                   self.anchors_array.shape[0]).T
        expanded_coords = numpy.expand_dims(x[1:], 2)
        expanded_coords = numpy.tile(expanded_coords,
                                     self.anchors_array.shape[0]).T
        res = numpy.sqrt(numpy.sum(numpy.square(self.anchors_array
                                                - expanded_coords), 1)) \
              - self.current_tdoa_array - expanded_base
        return res # , jac

    def find_sensor_position_non_linear(self, sensor):
        guess = self.find_sensor_position_linear(sensor)
        self.prepare_f_nonlinear(sensor)
        position = root(self.f_non_linear, guess, jac=False, method='lm',
                        options={
                            'col_deriv': True,
                            'maxiter': 1000,
                            # 'epsfcn': 1,
                            'factor': 0.1,
                            'xtol': 1e-10,
                            'ftol': 1e-10
                        })
        return position

class Point(list):
    @property
    def position(self):
        return (time * C for time in self)

    def distance2point(self, point):
        if len(self) == len(point):
            return sqrt(sum([(self[i] - point[i]) ** 2
                             for i in range(len(self))]))
        raise AttributeError


class Sensor(object):
    def __init__(self, tdoas=None, point=Point(), test_point=Point()):
        self.tdoas = tdoas if tdoas else {}
        self.point = point
        self.test_point = test_point
        self.base_anchor = None
        if self.base_anchor:
            self.get_base_tdoa()

    # should be much faster
    def get_base_tdoa(self):
        for tdoa in self.tdoas.values():
            # float error - must get improved
            if tdoa.distance <= 1e-11:
                self.base_anchor = tdoa.anchor

    def __repr__(self):
        return '{}(point={}, test_point={})'.format(type(self).__name__,
                                                    self.point, self.test_point)


class TDOA(object):
    def __init__(self, anchor, distance, error):
        self.anchor = anchor
        self.distance = distance
        self.error = error

    def __repr__(self):
        return '{}(anchor={}, r={})'.format(type(self).__name__,
                                            self.anchor.id, self.distance)


################
# test functions
################

def distance2points(p1, p2):
    """
    distane between two 3d points
    :param p1: (x, y, z)
    :param p2: (x, y, z)
    :return: r
    """
    return sqrt(
            (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2 + (p1[2] - p2[2]) ** 2)


def get_sensor_tdoas(sensor, mesh):
    toas = {}
    min_toa = 10e25
    closest_anchor = None
    for id, anchor in mesh.items():
        toas[id] = sensor.test_point.distance2point(anchor.point)
        if toas[id] < min_toa:
            min_toa = toas[id]
            closest_anchor = anchor
    for id, toa in toas.items():
        sensor.tdoas.update({id: TDOA(mesh[id],
                                      toa - min_toa,
                                      random())})
    sensor.get_base_tdoa()

def try_tdoa(N_attampts, mesh):
    sensors = []
    all_error = 0
    max_error = 0
    for i in range(N_attampts):
        sensor = Sensor(point=Point(), test_point=randpoint())
        sensors.append(sensor)
        get_sensor_tdoas(sensor, mesh)
        # print('tp', sensor.test_point)
        position = mesh.find_sensor_position_non_linear(sensor)
        # print('position', position.x)
        error = distance2points(position.x[1:], sensor.test_point)
        # print('error', error)
        all_error += error
        if error > max_error:
            max_error = error
    print(N_attampts, ' sensors on average took ',
          (time.time() - start_time)/N_attampts, 's')
    print('average error= ', all_error/N_attampts)
    print('maxerror= ', max_error)

if __name__ == '__main__':

    # get some random anchors
    a, b, c = 100, 200, 50


    def randpoint():
        return Point((randint(0, a), randint(0, b), randint(0, c)))

    # test_coords = [
    #     [70, 142, 26],
    #     [69, 103, 49],
    #     [68, 182, 49],
    #     [56, 112, 25],
    #     [21, 70, 5],
    #     [88, 102, 40],
    #     [5, 148, 2],
    # ]

    N_anchors = 7
    mesh = AnchorMesh()
    for i in range(N_anchors):
        p = randpoint()
        anch = Anchor(str(i), p)
        mesh.update({anch.id: anch})
    # print(mesh.keys(), mesh.values())

    # key_iter, mesh_array = mesh.anchors_array()
    # print(key_iter, mesh_array)

    # generate some sensors to test with
    start_time = time.time()
    N_attampts = 10000

    cProfile.run('try_tdoa({}, mesh)'.format(N_attampts))
