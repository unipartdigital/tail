import time
import pickle
import csv
from random import uniform, gauss, randint, choice
import numpy

from tools import distance2points, trilaterate
from calculator import optimisation, nn_initial_guess_gen, get_opt_func, \
    original_data_initial_guess, simple_init_guess_gen
from simulate import points_gen, gen_distances




def simulate(kwarg):
    points = points_gen(**kwarg)
    data = gen_distances(points, **kwarg)
    f = get_opt_func(data, **kwarg)
    res = optimisation(data, **kwarg)
    return res.x

def get_points(filepath, file_id, **kwarg):
    return numpy.genfromtxt(filepath+'points'+file_id+'.csv', delimiter=',')

def get_links(filepath, file_id, **kwargs):
    return


def check_precision(kwarg):

    def point_inacuracy():
        point_errs = {}
        for dist in data:
            res_dist = distance2points(fixed_res[dist[0]], fixed_res[dist[1]])
            err = abs(res_dist - dist[2])
            point_a_errs = point_errs.setdefault(dist[0], [])
            point_a_errs.append(err)
            point_b_errs = point_errs.setdefault(dist[1], [])
            point_b_errs.append(err)
        return {key: sum(value) for key, value in point_errs.items()}

    def shake_point(points, index, error):
        # print(len(points))
        print(index*3, index*3 + 3)
        print(points[index*3: index*3 + 3])
        # print([randint(0, kwarg['xmax']), gauss(0, kwarg['ymax']), randint(0, kwarg['zmax'])])
        print(len(points), index)
        if index == -2:
            pass
            # shift all points in one direction keep the 0 static
        elif index == -1:
            points[0] = numpy.random.normal(0.0, error, 1)
        elif index == 0:
            points[1:3] =  numpy.random.normal(0.0, error, 2)
        else:
            points[index*3 - 2: index*3 + 1] = numpy.random.normal(0.0, error, 3)

    def shift2positive():
        min_x = min(fixed_res[:, 0])
        min_y = min(fixed_res[:, 1])
        min_z = min(fixed_res[:, 2])
        return numpy.add(fixed_res, numpy.array((-min_x, -min_y, -min_z)))

    points = points_gen(**kwarg)
    data = gen_distances(points, **kwarg)
    f = get_opt_func(data, kwarg['N'])
    init_guess = simple_init_guess_gen(kwarg['N'])
    # print(init_guess)
    while 1:
        # init_guess = original_data_initial_guess(points, 1)
        # init_guess = nn_initial_guess_gen(data, N, **kwarg)
        res = optimisation(f, init_guess, **kwarg)
        # print(data)
        print(res.success, len(res.x))
        # for point in res.x:
        #     print(point)
        fixed_res = numpy.concatenate(([0, 0, 0,
                                     res.x[0], 0, 0,
                                     res.x[1], res.x[2], 0],
                                     res.x[3:]))

        fixed_res = numpy.reshape(fixed_res, (-1, 3))
        # fixed_res = shift2positive()
        print('answers: ', len(fixed_res))
        # for point in fixed_res:
        #     print(point)

        comparison = []
        for dist in data:
            res_dist = distance2points(fixed_res[dist[0]], fixed_res[dist[1]])
            comparison.append((abs(res_dist - dist[2]), res_dist, dist[2]))
        print('distance comparison value: ',
              sum([row[0] for row in comparison]),
              sum([row[1] for row in comparison]),
              sum([row[2] for row in comparison]))
        for i, point in enumerate(points):
            print(distance2points(point, fixed_res[i]), point, fixed_res[i])
        print('com point error', sum((distance2points(point, fixed_res[i])
                  for i, point in enumerate(points))))
        print(numpy.shape(init_guess), numpy.shape(res))
        init_guess = res
        point_errs = point_inacuracy()
        print(sorted(point_errs.items(), reverse=True,
                                         key=lambda item: (item[1], item[0])))
        worst = 0
        for key, value in sorted(point_errs.items(), reverse=True,
                                 key=lambda item: (item[1], item[0])):
            if worst > 0 and key > 0:
                shake_point(init_guess, key-2, value)
                worst -= 1
                print("Shaked {}: {}".format(key, value))


def check_precision2(kwarg):

    def point_inacuracy():
        point_errs = {}
        for dist in data:
            # print(dist)
            p1 = dist[0]
            p2 = dist[1]
            distance = dist[2]
            res_dist = distance2points(fixed_res[p1], fixed_res[p2])
            err = abs(res_dist - distance)
            point_a_errs = point_errs.setdefault(p1, [[], {}])
            point_a_errs[0].append(err)
            point_a_errs[1].update({tuple(fixed_res[p2]): distance})
            point_b_errs = point_errs.setdefault(p2, [[], {}])
            point_b_errs[0].append(err)
            point_b_errs[1].update({tuple(fixed_res[p1]): distance})
        return {key: (sum(dist), anchors) for key, (dist, anchors)
                in point_errs.items()}

    def relocate_point(index, val):
        x, y, z = trilaterate(val)
        if index == 0:
            return (0, 0, 0)
            # shift all points to their trilaterated position; keep the 0 static
        elif index == 1:
            # print(init_guess[0])
            init_guess[0] = x
            # print(init_guess[0])
            return (x, 0, 0)
        elif index == 2:
            # print(init_guess[1:3])
            init_guess[1:3] =  [y, z]
            # print(init_guess[1:3])
            return (0, y, z)
        else:
            # print(init_guess[(index-2) * 3 : (index-1) * 3 ])
            init_guess[(index-2) * 3 : (index-1) * 3 ] = [x, y, z]
            # print(init_guess[(index-2) * 3 : (index-1) * 3 ])
            return (x, y, z)

    points = points_gen(**kwarg)
    data = gen_distances(points, **kwarg)
    f = get_opt_func(data, kwarg['N'])
    best_dist_diff = 10e6
    while 1:
        init_guess = simple_init_guess_gen(kwarg['N'])
        print('CASE {}: RESET INITIAL GUESS'.format(kwarg['case']))
        # print(init_guess)
        for i in range(5):
            res = optimisation(f, init_guess, **kwarg)
            # print(res.success, len(res.x))
            fixed_res = numpy.concatenate(([0, 0, 0,
                                         res.x[0], 0, 0,
                                         res.x[1], res.x[2], 0],
                                         res.x[3:]))

            fixed_res = numpy.reshape(fixed_res, (-1, 3))
            # print('answers: ', len(fixed_res))

            comparison = []
            for dist in data:
                res_dist = distance2points(fixed_res[dist[0]], fixed_res[dist[1]])
                comparison.append((abs(res_dist - dist[2]), res_dist, dist[2]))
            dist_diff = sum([row[0] for row in comparison])

            print('distance comparison value: ',
                  dist_diff,
                  sum([row[1] for row in comparison]),
                  sum([row[2] for row in comparison]))
            # for i, point in enumerate(points):
            #     print(distance2points(point, fixed_res[i]), point, fixed_res[i])
            # print('com point error', sum((distance2points(point, fixed_res[i])
            #           for i, point in enumerate(points))))

            if dist_diff < best_dist_diff:
                best_dist_diff = dist_diff
                result = fixed_res
            if best_dist_diff < 1e-4:
                return result
            init_guess = res.x
            point_errs = point_inacuracy()
            worst = 100
            # print(init_guess)
            # print(fixed_res)
            for key, value in sorted(point_errs.items(), reverse=True,
                                     key=lambda item: (item[1], item[0])):
                if worst > 0 and value[0] > 1e-5:
                    # print('kv ', key, value)
                    # initial = numpy.array(fixed_res[key])
                    relocated = relocate_point(key, value[1])
                    worst -= 1
                    # print("Shaked {}: {} from {} to {}".format(
                    #         key, value[0], initial, relocated))




def try_nn(kwarg):
    points = points_gen(**kwarg)
    data = gen_distances(points, **kwarg)
    guess = nn_initial_guess_gen(data, **kwarg)
    print(len(guess), guess)

if __name__ == '__main__':
    """
    If number of links with a point < 4 the calculation is 
    impossible for that point and it should be 
    discarded together with all of its links.


    """
    settings = {
        'xmax': 500,
        'ymax': 150,
        'zmax': 5,
        'N': 25,
        'con_perc': 30,
        'width': 1,
        'dist_factor': 0.02,
        'max_dist': 350,
        'min_dist': 20,
        'etalon_points': (),
        # 'etalon_points': ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)),
        'iter_limit': 150,
        'filepath': 'c:\\code\\tail\\mesh\\',
        'file_id': '125',
        'save_points': True,
    }

    # try_nn(settings)


    time_start = time.time()
    # points = points_gen(**settings)
    # points = get_points(**settings)
    # print(points)
    N = 100
    for i in range(N):
        # ~ print('result: ', simulate(settings))
        # print('result: ', check_precision(settings))
        settings['case'] = i
        print('result: ', check_precision2(settings))
    print('The process takes {} seconds on average.'.format(
            (time.time() - time_start) / N))