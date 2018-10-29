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
import matplotlib.cm as cm
import matplotlib.pyplot as pp
from mpl_toolkits.axes_grid1 import AxesGrid
from scipy.interpolate import Rbf
from pylab import imread, imshow
from matplotlib.offsetbox import AnchoredText
from matplotlib.patheffects import withStroke
import matplotlib


FORMAT = "[%(asctime)s %(levelname)s] %(message)s"
logging.basicConfig(level=logging.WARNING, format=FORMAT)
logger = logging.getLogger()


class HeatMapGenerator(object):

    def __init__(self, image_path, title):
        self._image_path = image_path
        self._title = title
        logger.debug(
            'Initialized HeatMapGenerator; image_path=%s title=%s',
            self._image_path, self._title
        )
        self._layout = imread(self._image_path)
        self._image_width = len(self._layout[0])
        self._image_height = len(self._layout) - 1
        logger.debug(
            'Loaded image with width=%d height=%d',
            self._image_width, self._image_height
        )
        with open('%s.json' % self._title, 'r') as fh:
            self._data = json.loads(fh.read())
        logger.info('Loaded %d measurement points', len(self._data))

    def generate(self):
        a = defaultdict(list)
        for row in self._data:
            a['x'].append(row['x'])
            a['y'].append(row['y'])
            a['rssi'].append(row['result']['iwconfig']['stats']['level'])
        for x, y in [
            (0, 0), (0, self._image_height),
            (self._image_width, 0), (self._image_width, self._image_height)
        ]:
            a['x'].append(x)
            a['y'].append(y)
            a['rssi'].append(min(a['rssi']))
        logger.debug('a=%s', a)
        num_x = int(self._image_width / 4)
        num_y = int(num_x / (self._image_width / self._image_height))
        logger.debug('num_x=%d num_y=%s', num_x, num_y)
        x = np.linspace(0, self._image_width, num_x)
        y = np.linspace(0, self._image_height, num_y)
        gx, gy = np.meshgrid(x, y)
        gx, gy = gx.flatten(), gy.flatten()
        self._plot(
            a, 'rssi', 'RSSI (level)', gx, gy, num_x, num_y
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

    def _plot(self, a, key, title, gx, gy, num_x, num_y):
        pp.rcParams['figure.figsize'] = (
            self._image_width / 300, self._image_height / 300
        )
        pp.title(title)
        # Interpolate the data
        rbf = Rbf(
            a['x'], a['y'], a[key], function='linear'
        )
        z = rbf(gx, gy)
        z = z.reshape((num_y, num_x))
        # Render the interpolated data to the plot
        pp.axis('off')
        # begin color mapping
        norm = matplotlib.colors.Normalize(
            vmin=min(a[key]), vmax=max(a[key]), clip=True
        )
        mapper = cm.ScalarMappable(norm=norm, cmap='RdYlBu_r')
        # end color mapping
        image = pp.imshow(
            z,
            extent=(0, self._image_width, self._image_height, 0),
            cmap='RdYlBu_r', alpha=0.5, zorder=100
        )
        pp.colorbar(image)
        pp.imshow(self._layout, interpolation='bicubic', zorder=1, alpha=1)
        # begin plotting points
        for idx in range(0, len(a['x'])):
            pp.plot(
                a['x'][idx], a['y'][idx],
                marker='o', markeredgecolor='black', markeredgewidth=1,
                markerfacecolor=mapper.to_rgba(a[key][idx]), markersize=6
            )
        # end plotting points
        fname = '%s_%s.png' % (key, self._title)
        logger.info('Writing plot to: %s', fname)
        #pp.savefig(fname, dpi=300)
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
