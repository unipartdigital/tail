import time
from random import randint
import copy
import numpy
from scipy.optimize import root
import numba
from tools import distance2points


def opt_func_gen(data, N):
    f = ''
    # f += '@numba.jit(nopython=True)\n'
    f += 'def f(input):\n'
    # f += '    print("length of input data: ", len(x))\n'
    # f += '    x = numpy.concatenate(([0, 0, 0, x[0], 0, 0, x[1], x[2], 0], x[3:]))\n'
    # f += '    print(x)\n'
    f += '    x = numpy.zeros(len(input) + 6)\n'
    f += '    x[3] = input[0]\n'
    f += '    x[6] = input[1]\n'
    f += '    x[7] = input[2]\n'
    f += '    x[9:] = input[3:]\n'
    f += '    f = numpy.array((\n'
    df = '    df = numpy.array((\n'
    # optimisation: calculate x[n]**2 here
    # and then apply it to the set of equations
    blank_jac_line = ['0' for i in range(N * 3)]
    for line in data:
        # print(line)
        m = line[0]
        n = line[1]
        error = line[3]
        line = [m*3, n*3,
                m*3 + 1, n*3 + 1,
                m*3 + 2, n*3 + 2,
                line[2]**2]
        f += '        (x[{}] - x[{}])**2 + (x[{}]- x[{}])**2' \
             ' + (x[{}] - x[{}])**2 - {}, \n'.format(*line)
        # print(f)
        jacobian_line = copy.copy(blank_jac_line)
        dstr = '2*(x[{}] - x[{}])'
        jacobian_line[m*3] = dstr.format(m*3, n*3)
        jacobian_line[n*3] = dstr.format(n*3, m*3)
        jacobian_line[m*3 + 1] = dstr.format(m*3 + 1, n*3 + 1)
        jacobian_line[n*3 + 1] = dstr.format(n*3 + 1, m*3 + 1)
        jacobian_line[m*3 + 2] = dstr.format(m*3 + 2, n*3 + 2)
        jacobian_line[n*3 + 2] = dstr.format(n*3 + 2, m*3 + 2)
        for i in [8, 5, 4, 2, 1, 0]:
            jacobian_line.pop(i)
        # print(len(jacobian_line))
        df += '        (' + ', '.join(jacobian_line) + '),\n'
    f += '    ))\n' + df + '    ))\n' \
         '    return f, df.transpose()'
    # ~ print f
    with open('func_code.py', 'w') as file:
        file.writelines(f)
    return f


def simple_init_guess_gen(N, **kwarg):
    """
    Generates a simplified (random) initial guess of the locations of the points
    :param N: Number of points
    :param kwarg: 
    :return: flat numpy.array of points
    """
    mid = 100
    # Todo replace with numpy.random.randn(N*3-6)
    a = [randint(0, 150) for i in range((N)*3-6)]
    a[:9] = [0, 0, 0, mid, 0, 0, mid, mid, 0]
    # print('Guess gen number of variables: ', len(a))
    return numpy.array(a, dtype=numpy.float64)

def complex_initial_guess(data):
    ### Remove
    # def
    for line in data:
        if line[0] == 0 and line[1] == 1:
            d1 = line[3]
        elif line[0] == 0 and line[1] == 2:
            d2 = line[3]
        elif line[0] == 1 and line[1] == 2:
            d3 = line[3]
        elif line[0] == 1 and line[1] == 2:
            d4 = line[3]
    points = []
    points.append((0, 0, 0))
    points.append((d1, 0, 0))
    points.append((0, d2, 0))

def nn_initial_guess_gen(data, N, **kwarg):
    import initial_guess_nn
    print(data)
    x = numpy.zeros((1, 50, 50), dtype=numpy.float32)
    for dist in data:
        # print(dist)
        x[0][dist[0], dist[1]] = dist[2]
    model = initial_guess_nn.load_model('test_model1')
    return numpy.ravel(model.predict(x))[: N*3-6]

def original_data_initial_guess(points, noise=0.0, **kwarg):
    res = [coord for point in points for coord in point]
    for i in [8, 5, 4, 2, 1, 0]:
        res.pop(i)
    return numpy.random.normal(numpy.array(res, dtype=numpy.float64), noise)


def optimisation(f, guess, **kwarg):
    """
    Generalised optimisation function that generates the f(x) from data and 
    makes an initial guess and applies them to scipy.optimize.root
    :param data: 
    :param N: Number of points
    :param kwarg: 
    :return: flat numpy.array of resulting point coordinates if the 
    """
    # exec(opt_func_gen_old(data, N), globals())
    # while 1:

    # print(len(guess), guess)
    # print(f(guess))
    #~ print('f sample:', f(guess))
    t = time.time()
    sol = root(f, guess, jac=True, method='lm', options={
        'col_deriv': True,
        'maxiter':10000,
        # 'epsfcn': 1,
        'factor': 10,
        'xtol': 1E-25,
        'ftol': 1E-25
    })

        # fixed_res = numpy.concatenate(([0, 0, 0,
        #                              sol.x[0], 0, 0,
        #                              sol.x[1], sol.x[2], 0],
        #                             sol.x[3:]))
        # fixed_res = numpy.reshape(fixed_res, (-1, 3))
        # # print('answers: ', len(fixed_res))
        # # for point in fixed_res:
        # #     print(point)
        # comparison = []
        # for dist in data:
        #     res_dist = distance2points(fixed_res[dist[0]], fixed_res[dist[1]])
        #     # ~ print res_dist, dist[2]
        #     comparison.append((abs(res_dist - dist[2]), res_dist, dist[2], dist[3]))
        # print('error', sum([abs(row[3]) for row in comparison]))
        # if sum([row[0] for row in comparison]) < 500:
        #     return sol
        # # print('distance comparison value: ',
        # #       sum([row[0] for row in comparison]),
        # #       sum([row[1] for row in comparison]),
        # #       sum([row[2] for row in comparison]))
        # # for i, point in enumerate(points):
        # #     print(distance2points(point, fixed_res[i]), point, fixed_res[i])
        # # print('com point error', sum((distance2points(point, fixed_res[i])
        # #                               for i, point in enumerate(points))))

    print('optimisation time: ', time.time() - t, 's')
    return sol

def get_opt_func(data, N):
    exec(opt_func_gen(data, N), globals())
    return f

