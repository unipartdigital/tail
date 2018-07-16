#!/usr/bin/python3

import argparse
import glob

import numpy
from scipy import stats
import matplotlib.pyplot as plt
import probscale
import allantools

class PlotWrapper(object):
    def __init__(self, no_display=False, fig=None, ax=None):
        self.__class__ = allantools.Plot
        if (fig != None) & (ax != None):
            self.plt = plt
            self.fig = fig
            self.ax = ax
            self.ax.set_xscale("log")
            self.ax.set_yscale("log")
        else:
            allantools.Plot.__init__(self=self, no_display=no_display)

def main():
    parser = argparse.ArgumentParser(usage=__doc__)
    parser.add_argument('--col', nargs=1, type=int, default=1, help='which field to use as a column index (starting from 0)')
    parser.add_argument('--row', nargs=1, type=int, default=0, help='which field to use as a row index (starting from 0)')
    parser.add_argument('--min', nargs=1, type=float, default=None, help='minimum y value to show on graph')
    parser.add_argument('--max', nargs=1, type=float, default=None, help='maximum y value to show on graph')
    parser.add_argument('--skip', nargs=1, type=int, default=None, help='Skip n lines from the beginning of the data')
    parser.add_argument('--filter', nargs=1, type=float, default=None, help='filter by nth percentile')
    parser.add_argument('--prob', default=False, action='store_true', help='draw a probability plot')
    parser.add_argument('--allan', default=False, action='store_true', help='draw Allan plot')
    parser.add_argument('--log', default=False, action='store_true', help='use a log scale for the data')
    parser.add_argument('--bestfit', default=False, action='store_true', help='draw a best fit line')
    parser.add_argument('--ci', default=False, action='store_true', help='draw 95% confidence interval')
    parser.add_argument('--filename', nargs=1, default="result-2.csv", help='Name of file to read within directory')
    parser.add_argument('--marker', nargs=1, default=',', help='Marker for plotting points')
    parser.add_argument('basename', nargs=1, help='base name of directories in which to search for results')
    parser.add_argument('fields', nargs='*', help='names of fields to plot')
    args = parser.parse_args()
    fields = list(map(int, args.fields))
    
    values = []
    basename = args.basename[0]
    filename = args.filename
    marker = args.marker[0]
    ymin = float(args.min[0]) if args.min != None else None
    ymax = float(args.max[0]) if args.max != None else None
    #print(ymin)
    #print(ymax)
    skip = int(args.skip[0]) if args.skip != None else None
    #print(skip)

    dirs = glob.glob(basename + '-*')
    slen = len(basename) + 1
    for dir in dirs:
        s = dir[slen:]
        params = dir[slen:].split('-')
#        print("Found " + s)
        for p in range(0,len(params)):
#            print("Param "+str(p+1)+" is "+params[p])
            while p >= len(values):
                values.append(dict())
            values[p][params[p]] = 1

    for p in range(0,len(values)):
        n = 0
        for v in sorted(values[p].keys()):
            values[p][v] = n
            n+=1

    #print(values)

    rindex = args.row
    cindex = args.col
    if rindex < len(values):
        rmax = len(values[rindex])
    else:
        rmax = 1

    if cindex < len(values):
        cmax = len(values[cindex])
    else:
        cmax = 1

    fig = plt.figure(figsize=(30,20), dpi=72)

    for dir in dirs:
        s = dir[slen:]
        params = dir[slen:].split('-')
        if rindex < len(values):
            row = values[rindex][params[rindex]]
        else:
            row = 1
        if cindex < len(values):
            col = values[cindex][params[cindex]]
        else:
            col = 1
#        print(rmax)
#        print(cmax)
#        print(row)
#        print(col)
        axes = plt.subplot(rmax, cmax, 1+row*cmax+col)
        axes.set_ylim(bottom=ymin, top=ymax, auto=True if (ymax == None and ymin == None) else False)
        plt.title(dir)
        try:
            data = numpy.genfromtxt(dir + '/' + filename, delimiter=',', usecols=fields, names=True)
            data = data[skip:]
#            print(data.dtype.names)
#            print(data)
            if args.prob:
                for name in data.dtype.names:
                    d = data[name]
                    if args.filter != None:
                        d = d[abs(d) < numpy.percentile(abs(d),args.filter)]
                    if args.log:
                        d = list(map(abs, d))
                        # 0 values won't work on a logarithmic scale, so filter them out to avoid errors
                        d = [x for x in d if x != 0]
                    probscale.probplot(d, ax=axes, plottype='prob', probax='y', datascale='log' if args.log else 'linear', scatter_kws=dict(linestyle='none', marker=marker, label=name), bestfit=args.bestfit, estimate_ci=args.ci)
                    plt.legend(loc='lower right', frameon=False)
            elif args.allan:
                if args.filter != None:
                    data = data[abs(data[data.dtype.names[1]]) < numpy.percentile(abs(data[data.dtype.names[1]]),args.filter)]
                xfield = data.dtype.names[0]
                for name in data.dtype.names:
                    a = allantools.Dataset(data=data[name])
                    a.compute("mdev")
                    b = PlotWrapper(fig=fig, ax=axes)
                    b.plot(a, errorbars=True, grid=True)
            else:
                if args.log:
                    axes.set_yscale('log')
                if args.filter != None:
                    data = data[abs(data[data.dtype.names[1]]) < numpy.percentile(abs(data[data.dtype.names[1]]),args.filter)]
                xfield = data.dtype.names[0]
                for name in data.dtype.names[1:]:
                    plt.plot(data[xfield], data[name], label=name, linestyle='none', marker=marker)
                    plt.legend(loc='upper right', frameon=False)
        except IOError:
            print("Unable to read file " + dir + '/' + filename)

    plt.show()


if __name__ == "__main__":
    main()
