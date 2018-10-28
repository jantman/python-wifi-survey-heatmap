"""
The latest version of this package is available at:
<http://github.com/jantman/wifi-survey-heatmap>

##################################################################################
Copyright 2017 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

    This file is part of wifi-survey-heatmap, also known as wifi-survey-heatmap.

    wifi-survey-heatmap is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    wifi-survey-heatmap is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with wifi-survey-heatmap.  If not, see <http://www.gnu.org/licenses/>.

The Copyright and Authors attributions contained herein may not be removed or
otherwise altered, except to add the Author attribution of a contributor to
this work. (Additional Terms pursuant to Section 7b of the AGPL v3)
##################################################################################
While not legally required, I sincerely request that anyone who finds
bugs please submit them at <https://github.com/jantman/wifi-survey-heatmap> or
to me via email, and that you send any contributions or improvements
either as a pull request on GitHub, or to me via email.
##################################################################################

AUTHORS:
Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>
##################################################################################
"""

import sys
import argparse
import logging
import json

import csv
from collections import defaultdict
import numpy as np
import matplotlib.mlab as ml
import matplotlib.pyplot as pp
from mpl_toolkits.axes_grid1 import AxesGrid
from scipy.interpolate import Rbf
from pylab import imread, imshow
from matplotlib.offsetbox import AnchoredText
from matplotlib.patheffects import withStroke


FORMAT = "[%(asctime)s %(levelname)s] %(message)s"
logging.basicConfig(level=logging.WARNING, format=FORMAT)
logger = logging.getLogger()


class HeatMapGenerator(object):

    def __init__(self, image_path, title):
        self._image_path = image_path
        self._image_width = 2544
        self._image_height = 1691
        self._title = title
        logger.debug(
            'Initialized HeatMapGenerator; image_path=%s title=%s',
            self._image_path, self._title
        )
        with open('%s.json' % self._title, 'r') as fh:
            self._data = json.loads(fh.read())
        logger.info('Loaded %d measurement points', len(self._data))

    def generate(self):
        layout = imread(self._image_path)
        s_beacons = ['2e:20', 'f6:70', '5b:30', '74:c0', 'f5:90', '16:a0']
        g_beacons = ['14:a1', 'f6:71', '5b:31', '74:c1', 'f5:91', '16:a1']
        a = defaultdict(list)
        self._rows = []
        with open('%s.csv' % self._title, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                self._rows.append(row)
                rssis = []
                for k, v in row.items():
                    a[k].append(int(v))
                    if k in s_beacons:
                        rssis.append(int(v))
                a['max_rssi'].append(max(rssis))

        grid_width = 797
        grid_height = 530

        num_x = int(self._image_width / 4)
        num_y = int(num_x / (self._image_width / self._image_height))

        x = np.linspace(0, grid_width, num_x)
        y = np.linspace(0, grid_height, num_y)

        gx, gy = np.meshgrid(x, y)
        gx, gy = gx.flatten(), gy.flatten()

        levels = [-85, -80, -75, -70, -65, -60, -55, -50, -45, -40, -35, -30,
                  -25]

        interpolate = True
        """
        self._grid_plots(
            s_beacons, interpolate, gx, gy, num_x, num_y, a, x, y, levels,
            layout
        )
        """
        self._max_plot(
            a, s_beacons, interpolate, gx, gy, num_x, num_y, x, y, levels,
            layout
        )

    def _add_inner_title(self, ax, title, loc, size=None, **kwargs):
        if size is None:
            size = dict(size=pp.rcParams['legend.fontsize'])
        at = AnchoredText(
            title, loc=loc, prop=size, pad=0., borderpad=0.5, frameon=False,
            **kwargs
        )
        at.set_zorder(200)
        ax.add_artist(at)
        at.txt._text.set_path_effects(
            [withStroke(foreground="w", linewidth=3)]
        )
        return at

    def _grid_plots(
        self, s_beacons, interpolate, gx, gy, num_x, num_y, a, x, y, levels,
            layout
    ):
        f = pp.figure()
        f.suptitle("Individual AP RSSI")
        # Adjust the margins and padding
        f.subplots_adjust(
            hspace=0.1, wspace=0.1, left=0.05, right=0.95, top=0.85,
            bottom=0.15
        )

        # Create a grid of subplots using the AxesGrid helper
        image_grid = AxesGrid(
            f, 111, nrows_ncols=(2, 3), axes_pad=0.1, label_mode="1",
            share_all=True, cbar_location="right", cbar_mode="single",
            cbar_size="3%"
        )

        for beacon, i in zip(s_beacons, range(len(s_beacons))):
            # Hide the axis labels
            image_grid[i].xaxis.set_visible(False)
            image_grid[i].yaxis.set_visible(False)

            if interpolate:
                # Interpolate the data
                rbf = Rbf(
                    a['Drawing X'], a['Drawing Y'], a[beacon], function='linear'
                )
                z = rbf(gx, gy)
                z = z.reshape((num_y, num_x))

                # Render the interpolated data to the plot
                image = image_grid[i].imshow(
                    z, vmin=-85, vmax=-25,
                    extent=(0, self._image_width, self._image_height, 0),
                    cmap='RdYlBu_r', alpha=1
                )
                # c = image_grid[i].contourf(z, levels, alpha=0.5)
                # c = image_grid[i].contour(z, levels, linewidths=5, alpha=0.5)
            else:
                z = ml.griddata(
                    a['Drawing X'], a['Drawing Y'], a[beacon], x, y
                )
                c = image_grid[i].contourf(x, y, z, levels, alpha=0.5)
            image_grid[i].imshow(
                layout, interpolation='bicubic', zorder=100
            )

        # Setup the data for the colorbar and its ticks
        image_grid.cbar_axes[0].colorbar(image)
        image_grid.cbar_axes[0].set_yticks(levels)

        # Add inset titles to each subplot
        for ax, im_title in zip(image_grid, s_beacons):
            t = self._add_inner_title(ax, "Beacon %s" % im_title, loc=3)
            t.patch.set_alpha(0.5)
        pp.show()

    def _max_plot(
        self, a, s_beacons, interpolate, gx, gy, num_x, num_y, x, y, levels,
            layout
    ):
        # Get the maximum RSSI seen for each beacon
        #max_rssi = [max(i) for i in a[s_beacons]]
        """
        max_rssi = []
        for row in self._rows:
            max_rssi.append(max([row[bcn] for bcn in s_beacons]))
        """
        max_rssi = a['max_rssi']
        logger.debug('Max RSSIs: %s', a['max_rssi'])
        pp.title("Maximum RSSI seen for each beacon")
        if interpolate:
            # Interpolate the data
            rbf = Rbf(
                a['Drawing X'], a['Drawing Y'], max_rssi, function='linear'
            )
            z = rbf(gx, gy)
            z = z.reshape((num_y, num_x))
            # Render the interpolated data to the plot
            image = pp.imshow(
                z, vmin=-85, vmax=-25,
                extent=(0, self._image_width, self._image_height, 0),
                cmap='RdYlBu_r', alpha=1
            )
            # pp.contourf(z, levels, alpha=0.5)
            # pp.contour(z, levels, linewidths=5, alpha=0.5)
        else:
            z = ml.griddata(a['Drawing X'], a['Drawing Y'], max_rssi, x, y)
            pp.contourf(x, y, z, levels, alpha=0.5)
        pp.colorbar(image)
        pp.imshow(layout, interpolation='bicubic', zorder=100)
        pp.show()


def parse_args(argv):
    """
    parse arguments/options

    this uses the new argparse module instead of optparse
    see: <https://docs.python.org/2/library/argparse.html>
    """
    p = argparse.ArgumentParser(description='wifi survey heatmap generator')
    p.add_argument('-v', '--verbose', dest='verbose', action='count', default=0,
                   help='verbose output. specify twice for debug-level output.')
    p.add_argument('IMAGE', type=str, help='Path to background image')
    p.add_argument(
        'TITLE', type=str, help='Title for survey (and data filename)'
    )
    args = p.parse_args(argv)
    return args


def set_log_info():
    """set logger level to INFO"""
    set_log_level_format(logging.INFO,
                         '%(asctime)s %(levelname)s:%(name)s:%(message)s')


def set_log_debug():
    """set logger level to DEBUG, and debug-level output format"""
    set_log_level_format(
        logging.DEBUG,
        "%(asctime)s [%(levelname)s %(filename)s:%(lineno)s - "
        "%(name)s.%(funcName)s() ] %(message)s"
    )


def set_log_level_format(level, format):
    """
    Set logger level and format.

    :param level: logging level; see the :py:mod:`logging` constants.
    :type level: int
    :param format: logging formatter format string
    :type format: str
    """
    formatter = logging.Formatter(fmt=format)
    logger.handlers[0].setFormatter(formatter)
    logger.setLevel(level)


def main():
    args = parse_args(sys.argv[1:])

    # set logging level
    if args.verbose > 1:
        set_log_debug()
    elif args.verbose == 1:
        set_log_info()

    HeatMapGenerator(args.IMAGE, args.TITLE).generate()


if __name__ == '__main__':
    main()
