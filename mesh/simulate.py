from math import sqrt
import csv
import json
from random import uniform, gauss, randint, choice
from tools import distance2points, json_serial
from pprint import pprint


def points_gen(xmax, ymax, zmax, N, min_dist, iter_limit, filepath,
               etalon_points=((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)),
               **kwarg):
    """
        creating N (if possible) random points with X, Y and Z coordinates
        
        :param xmax: float/int (bbox X size)
        :param ymax: float/int (bbox Y size)
        :param zmax: float/int (bbox Z size)
        :param N: desired Number of points (may be impossible to achieve 
        depending on the min_distance and iter_limit) 
        :param min_dist: minimal distance between any two points
        :param iter_limit: iteration attempts for the production of random 
        points at a distance larger than that set by min_distance
        :param etalon_points: set/list/touple of 4 points that define the 
        coordinate system. i.e. ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1))
        :return: list of points
    """

    def gen_point():
        return uniform(0, xmax), uniform(0, ymax), uniform(0, zmax)

    def export():
        with open(filepath+'points'+ str(len(ancor_points)) + '.csv', 'w') as file:
            pointwriter = csv.writer(file, delimiter=',',
                                     quotechar='|', quoting=csv.QUOTE_MINIMAL)
            pointwriter.writerows(ancor_points)

    def check_distance():
        """Check if the current point is too close to any other point"""
        for point in ancor_points:
            if not (abs(x - point[0]) > min_dist
                    or abs(y - point[1]) > min_dist
                    or abs(z - point[2]) > min_dist
                    or sqrt((x - point[0])**2 +
                            (y - point[1])**2 +
                            (z - point[2])**2) > min_dist):
                return False
        return True

    ancor_points = []
    ancor_points.extend(etalon_points)
    failed_iter = 0
    while True:
        x, y, z = gen_point()
        if check_distance():
            ancor_points.append((x, y, z))
            failed_iter = 0
        else:
            failed_iter += 1
        if failed_iter == iter_limit or len(ancor_points) >= N:
            # print(ancor_points)
            # export()
            return ancor_points
    # print(ancor_points)
    # export()
    return ancor_points


def gen_distances(points, con_perc, width, dist_factor, max_dist, **kwarg):
    """
    calculating distances between points, 
    adding error, discarting long or short connections, 
    vaguely adjusting for connection percentage
    :param points: set of generated points for which we generate distances
    :param con_perc: percentage of connections that work (are available)
    :param width: 
    :param dist_factor: 
    :param max_dist: maximal distance at which the connection exists
    :return: [index p1, index p2, distance between p1 and p2, simmulated error,
    (p1 coordinates, p2 coordinates)]
    """
    data = []
    for i, point1 in enumerate(points[: -1]):
        for j, point2 in enumerate(points[i+1: ]):
            dist = distance2points(point1, point2)
            # discarting connections that are too far
            # reducing the array only to working connections (con_perc)
            if dist < max_dist and randint(0, 100) < con_perc:
                error = gauss(0, width) + choice([-1, 1]) * dist_factor*dist
                # data.append([i, j+i+1, dist, error, (point1, point2)])
                data.append([i, j+i+1, dist, error])
    check = {}
    for line in data:
        check.setdefault(line[0], 0)
        check[line[0]] += 1
        check.setdefault(line[1], 0)
        check[line[1]] += 1
    if 0 in check.values() or 1 in check.values() \
            or 2 in check.values() or 3 in check.values():
        try:
            return gen_distances(points, con_perc, width,
                                 dist_factor, max_dist, **kwarg)
        except:
            return data
    # print(check)
    return data


def gen_points_sets(points_sets_n, **kwargs):
    res = []
    for i in range(points_sets_n):
        res.append(points_gen(**kwargs))
    # print(res)
    return res


def gen_distances_sets(points, distances_sets_n, **kwargs):
    distances_sets = []
    for i in range(distances_sets_n):
        distances = gen_distances(points, **kwargs)
        distances_sets.append(distances)
    return distances_sets


def generate_dataset(kwargs):
    res = []
    points_sets = gen_points_sets(**kwargs)
    for points in points_sets:
        for distances in gen_distances_sets(points, **kwargs):
            res.append({'points': points, 'distances': distances})
            # print(len(distances))
    # pprint(res)
    return res


def variate_test_cases(kwargs):
    pass

def save_data(data, filename):
    with open(filename, 'w') as file:
        file.write(json.dumps(data))

def gen_dataset():
    settings = {
        'xmax': randint(100, 500),
        'ymax': randint(50, 200),
        'zmax': randint(10, 100),
        'N': randint(15,50),
        'con_perc': randint(20, 100),
        'width': 1,
        'dist_factor': 0.02,
        'max_dist': 350,
        'min_dist': 20,
        # 'etalon_points': None,
        'etalon_points': choice([((0, 0, 0), (1, 0, 0),
                                  (0, 1, 0), (0, 0, 1)),
                                 None]),
        'iter_limit': 150,
        'filepath': 'c:\\code\\tail\\mesh\\',
        'file_id': '125',
        'save_points': True,
        'points_sets_n': 20,
        'distances_sets_n': 20,
    }

    data = generate_dataset(settings)
    save_data(data, 'train.json')
    save_data(data, 'test.json')
    print('Dataset generated, N=', settings['N'])

if __name__ == '__main__':
    settings = {
        'xmax': 500,
        'ymax': 150,
        'zmax': 10,
        'N': 45,
        'con_perc': 30,
        'width': 1,
        'dist_factor': 0.02,
        'max_dist': 350,
        'min_dist': 20,
        # 'etalon_points': None,
        'etalon_points': ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)),
        'iter_limit': 150,
        'filepath': 'c:\\code\\tail\\mesh\\',
        'file_id': '125',
        'save_points': True,
        'points_sets_n': 20,
        'distances_sets_n': 20,
    }

    data = generate_dataset(settings)
    save_data(data, 'train.json')
    save_data(data, 'test.json')