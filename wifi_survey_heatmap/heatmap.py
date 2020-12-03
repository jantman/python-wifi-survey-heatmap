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

from collections import defaultdict
import numpy as np
import matplotlib.cm as cm
import matplotlib.pyplot as pp
from scipy.interpolate import Rbf
from pylab import imread, imshow
from matplotlib.offsetbox import AnchoredText
from matplotlib.patheffects import withStroke
from matplotlib.font_manager import FontManager
import matplotlib


FORMAT = "[%(asctime)s %(levelname)s] %(message)s"
logging.basicConfig(level=logging.WARNING, format=FORMAT)
logger = logging.getLogger()


WIFI_CHANNELS = {
    # center frequency to (channel, bandwidth MHz)
    2412.0: (1, 20.0),
    2417.0: (2, 20.0),
    2422.0: (3, 20.0),
    2427.0: (4, 20.0),
    2432.0: (5, 20.0),
    2437.0: (6, 20.0),
    2442.0: (7, 20.0),
    2447.0: (8, 20.0),
    2452.0: (9, 20.0),
    2457.0: (10, 20.0),
    2462.0: (11, 20.0),
    2467.0: (12, 20.0),
    2472.0: (13, 20.0),
    2484.0: (14, 20.0),
    5160.0: (32, 20.0),
    5170.0: (34, 40.0),
    5180.0: (36, 20.0),
    5190.0: (38, 40.0),
    5200.0: (40, 20.0),
    5210.0: (42, 80.0),
    5220.0: (44, 20.0),
    5230.0: (46, 40.0),
    5240.0: (48, 20.0),
    5250.0: (50, 160.0),
    5260.0: (52, 20.0),
    5270.0: (54, 40.0),
    5280.0: (56, 20.0),
    5290.0: (58, 80.0),
    5300.0: (60, 20.0),
    5310.0: (62, 40.0),
    5320.0: (64, 20.0),
    5340.0: (68, 20.0),
    5480.0: (96, 20.0),
    5500.0: (100, 20.0),
    5510.0: (102, 40.0),
    5520.0: (104, 20.0),
    5530.0: (106, 80.0),
    5540.0: (108, 20.0),
    5550.0: (110, 40.0),
    5560.0: (112, 20.0),
    5570.0: (114, 160.0),
    5580.0: (116, 20.0),
    5590.0: (118, 40.0),
    5600.0: (120, 20.0),
    5610.0: (122, 80.0),
    5620.0: (124, 20.0),
    5630.0: (126, 40.0),
    5640.0: (128, 20.0),
    5660.0: (132, 20.0),
    5670.0: (134, 40.0),
    5680.0: (136, 20.0),
    5690.0: (138, 80.0),
    5700.0: (140, 20.0),
    5710.0: (142, 40.0),
    5720.0: (144, 20.0),
    5745.0: (149, 20.0),
    5755.0: (151, 40.0),
    5765.0: (153, 20.0),
    5775.0: (155, 80.0),
    5785.0: (157, 20.0),
    5795.0: (159, 40.0),
    5805.0: (161, 20.0),
    5825.0: (165, 20.0)
}


class HeatMapGenerator(object):

    graphs = {
        'rss': 'RSS (received signal strength) [dBm]',
        'tcp_upload_Mbps': 'TCP Upload [MBit/s]',
        'tcp_download_Mbps': 'TCP Download [MBit/s]',
        'udp_upload_Mbps': 'UDP Upload [MBit/s]',
        'jitter': 'UDP Jitter [ms]',
        'frequency': 'Wi-Fi frequency [MHz]',
        'channel_rx_bitrate': 'Advertised channel bandwidth (RX) [MBit/s]',
        'channel_tx_bitrate': 'Advertised channel bandwidth (TX) [MBit/s]',
    }

    def __init__(
        self, image_path, title, showpoints, ignore_ssids=[], aps=None, thresholds=None
    ):
        self._ap_names = {}
        if aps is not None:
            with open(aps, 'r') as fh:
                self._ap_names = {
                    x.upper(): y for x, y in json.loads(fh.read()).items()
                }
        self._image_path = image_path
        self._layout = None
        self._image_width = 0
        self._image_height = 0
        self._corners = [(0, 0), (0, 0), (0, 0), (0, 0)]
        self._title = title
        self._showpoints = showpoints
        if not self._title.endswith('.json'):
            self._title += '.json'
        self._ignore_ssids = ignore_ssids
        logger.debug(
            'Initialized HeatMapGenerator; image_path=%s title=%s',
            self._image_path, self._title
        )
        with open(self._title, 'r') as fh:
            self._data = json.loads(fh.read())
        logger.info('Loaded %d measurement points', len(self._data))
        self.thresholds = {}
        if thresholds is not None:
            logger.info('Loading thresholds from: %s', thresholds)
            with open(thresholds, 'r') as fh:
                self.thresholds = json.loads(fh.read())
            logger.debug('Thresholds: %s', self.thresholds)

    def load_data(self):
        a = defaultdict(list)
        for row in self._data:
            a['x'].append(row['x'])
            a['y'].append(row['y'])
            a['rss'].append(row['result']['rss'])
            a['tcp_upload_Mbps'].append(row['result']['tcp']['sent_Mbps'])
            a['tcp_download_Mbps'].append(
                row['result']['tcp-reverse']['received_Mbps']
            )
            a['udp_upload_Mbps'].append(row['result']['udp']['Mbps'])
            a['jitter'].append(row['result']['udp']['jitter_ms'])
            a['frequency'].append(row['result']['freq'])
            a['channel_rx_bitrate'].append(row['result']['bitrate']['rx'])
            a['channel_tx_bitrate'].append(row['result']['bitrate']['tx'])
            ap = self._ap_names.get(
                row['result']['ssid'].upper(),
                row['result']['ssid']
            )
            if row['result']['freq'] < 5:
                a['ap'].append(ap + '_2.4GHz')
            else:
                a['ap'].append(ap + '_5GHz')
        return a

    def _load_image(self):
        self._layout = imread(self._image_path)
        self._image_width = len(self._layout[0])
        self._image_height = len(self._layout) - 1
        self._corners = [
            (0, 0), (0, self._image_height),
            (self._image_width, 0), (self._image_width, self._image_height)
        ]
        logger.debug(
            'Loaded image with width=%d height=%d',
            self._image_width, self._image_height
        )

    def generate(self):
        self._load_image()
        a = self.load_data()
        for x, y in self._corners:
            a['x'].append(x)
            a['y'].append(y)
            for k in a.keys():
                if k in ['x', 'y', 'ap']:
                    continue
                a['ap'].append(None)
                a[k] = [0 if x is None else x for x in a[k]]
                a[k].append(min(a[k]))
        self._channel_graphs()
        num_x = int(self._image_width / 4)
        num_y = int(num_x / (self._image_width / self._image_height))
        x = np.linspace(0, self._image_width, num_x)
        y = np.linspace(0, self._image_height, num_y)
        gx, gy = np.meshgrid(x, y)
        gx, gy = gx.flatten(), gy.flatten()
        for k, ptitle in self.graphs.items():
            self._plot(
                a, k, '%s - %s' % (self._title, ptitle), gx, gy, num_x, num_y
            )

    def _channel_to_signal(self):
        """
        Return a dictionary of 802.11 channel number to combined "quality" value
        for all APs seen on the given channel. This includes interpolation to
        overlapping channels based on channel width of each channel.
        """
        # build a dict of frequency (GHz) to list of quality values
        channels = defaultdict(list)
        for row in self._data:
            for scan in row['result']['iwscan']:
                if scan['ESSID'] in self._ignore_ssids:
                    continue
                channels[scan['Frequency'] / 1000000].append(
                    scan['stats']['quality']
                )
        # collapse down to dict of frequency (GHz) to average quality (float)
        for freq in channels.keys():
            channels[freq] = sum(channels[freq]) / len(channels[freq])
        # build the full dict of frequency to quality for all channels
        freq_qual = {x: 0.0 for x in WIFI_CHANNELS.keys()}
        # then, update to account for full bandwidth of each channel
        for freq, qual in channels.items():
            freq_qual[freq] += qual
            for spread in range(
                int(freq - (WIFI_CHANNELS[freq][1] / 2.0)),
                int(freq + (WIFI_CHANNELS[freq][1] / 2.0) + 1.0)
            ):
                if spread in freq_qual and spread != freq:
                    freq_qual[spread] += qual
        return {
            WIFI_CHANNELS[x][0]: freq_qual[x] for x in freq_qual.keys()
        }

    def _plot_channels(self, names, values, title, fname, ticks):
        pp.rcParams['figure.figsize'] = (
            self._image_width / 300, self._image_height / 300
        )
        fig, ax = pp.subplots()
        ax.set_title(title)
        ax.bar(names, values)
        ax.set_xlabel('Channel')
        ax.set_ylabel('Mean Quality')
        ax.set_xticks(ticks)
        #ax.set_xticklabels(names)
        logger.info('Writing plot to: %s', fname)
        pp.savefig(fname, dpi=300)
        pp.close('all')

    def _channel_graphs(self):
        try:
            c2s = self._channel_to_signal()
        except KeyError:
            return
        names24 = []
        values24 = []
        names5 = []
        values5 = []
        for ch, val in c2s.items():
            if ch < 15:
                names24.append(ch)
                values24.append(val)
            else:
                names5.append(ch)
                values5.append(val)
        self._plot_channels(
            names24, values24, '2.4GHz Channel Utilization',
            '%s_%s.png' % ('channels24', self._title),
            names24
        )
        ticks5 = [
            38, 46, 54, 62, 102, 110, 118, 126, 134, 142, 151, 159
        ]
        self._plot_channels(
            names5, values5, '5GHz Channel Utilization',
            '%s_%s.png' % ('channels5', self._title),
            ticks5
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
        logger.debug('Plotting: %s', key)
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
        if 'min' in self.thresholds.get(key, {}):
            vmin = self.thresholds[key]['min']
            logger.debug('Using min threshold from thresholds: %s', vmin)
        else:
            vmin = min(a[key])
            logger.debug('Using calculated min threshold: %s', vmin)
        if 'max' in self.thresholds.get(key, {}):
            vmax = self.thresholds[key]['max']
            logger.debug('Using max threshold from thresholds: %s', vmax)
        else:
            vmax = max(a[key])
            logger.debug('Using calculated max threshold: %s', vmax)
        norm = matplotlib.colors.Normalize(vmin=vmin, vmax=vmax, clip=True)
        mapper = cm.ScalarMappable(norm=norm, cmap='RdYlBu_r')
        # end color mapping
        image = pp.imshow(
            z,
            extent=(0, self._image_width, self._image_height, 0),
            cmap='RdYlBu_r', alpha=0.5, zorder=100,
            vmin=vmin, vmax=vmax
        )
        pp.colorbar(image)
        pp.imshow(self._layout, interpolation='bicubic', zorder=1, alpha=1)
        labelsize = FontManager.get_default_size() * 0.4
        if(self._showpoints):
            # begin plotting points
            for idx in range(0, len(a['x'])):
                if (a['x'][idx], a['y'][idx]) in self._corners:
                    continue
                pp.plot(
                    a['x'][idx], a['y'][idx],
                    marker='o', markeredgecolor='black', markeredgewidth=1,
                    markerfacecolor=mapper.to_rgba(a[key][idx]), markersize=6
                )
                pp.text(
                    a['x'][idx], a['y'][idx] - 30,
                    a['ap'][idx], fontsize=labelsize,
                    horizontalalignment='center'
                )
            # end plotting points
        fname = '%s_%s.png' % (key, self._title)
        logger.info('Writing plot to: %s', fname)
        pp.savefig(fname, dpi=300)
        pp.close('all')


def parse_args(argv):
    """
    parse arguments/options

    this uses the new argparse module instead of optparse
    see: <https://docs.python.org/2/library/argparse.html>
    """
    p = argparse.ArgumentParser(description='wifi survey heatmap generator')
    p.add_argument('-v', '--verbose', dest='verbose', action='count', default=0,
                   help='verbose output. specify twice for debug-level output.')
    p.add_argument('-i', '--ignore', dest='ignore', action='append',
                   default=[], help='SSIDs to ignore from channel graph')
    p.add_argument('-t', '--thresholds', dest='thresholds', action='store',
                   type=str, help='thresholds JSON file path')
    p.add_argument('-a', '--ap-names', type=str, dest='aps', action='store',
                   default=None,
                   help='If specified, a JSON file mapping AP MAC/BSSID to '
                        'a string to label each measurement with, showing '
                        'which AP it was connected to. Useful when doing '
                        'multi-AP surveys.')
    p.add_argument('IMAGE', type=str, help='Path to background image')
    p.add_argument(
        'TITLE', type=str, help='Title for survey (and data filename)'
    )
    p.add_argument('-s', '--show-points', dest='showpoints', action='count', default=0,
                   help='show measurement points in file')
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

    showpoints = True if args.showpoints > 0 else False

    HeatMapGenerator(
        args.IMAGE, args.TITLE, showpoints, ignore_ssids=args.ignore, aps=args.aps,
        thresholds=args.thresholds
    ).generate()


if __name__ == '__main__':
    main()
