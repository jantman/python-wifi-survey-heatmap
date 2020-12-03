"""
The latest version of this package is available at:
<http://github.com/jantman/wifi-survey-heatmap>

##################################################################################
Copyright 2018 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

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

import logging
from time import sleep

from wifi_survey_heatmap.vendor.iwlib.iwlist import scan
import pyric
import pyric.pyw as pyw
import pyric.utils as wireless_utils

import iperf3

logger = logging.getLogger(__name__)


class Collector(object):

    def __init__(self, interface_name, server_addr, scan=True):
        super().__init__()
        logger.debug(
            'Initializing Collector for interface: %s; iperf server: %s',
            interface_name, server_addr
        )
        # ensure interface_name is a wireless interfaces
        self._wifi_card = self.get_wifi_card(interface_name)
        self._interface_name = interface_name
        self._iperf_server = server_addr
        self._scan = scan

    def get_wifi_card(self, interface_name):
        # Check if this is a wireless device
        wifaces = pyw.winterfaces()
        if interface_name not in wifaces:
            logger.error("Device {0} is not a valid wireless interface, use one of {1}".format(interface_name, wifaces))
            exit(1)

        # Get WiFi card handle
        card = pyw.getcard(interface_name)
        linfo = pyw.link(card)
        logger.debug('Connected to AP with SSID "%s"', linfo['ssid'])
        return card

    def run_iperf(self, udp=False, reverse=False):
        client = iperf3.Client()
        client.server_hostname = self._iperf_server
        client.port = 5201
        client.protocol = 'udp' if udp else 'tcp'
        client.reverse = reverse
        logger.debug(
            'Running iperf to %s; udp=%s reverse=%s', self._iperf_server,
            udp, reverse
        )
        for retry in range(0, 4):
            res = client.run()
            if res.error is None:
                break
            logger.error('iperf error: %s; retrying', res.error)
        logger.debug('iperf result: %s', res)
        return res

    def _run_all_iperf(self):
        res = {'tcp': {}, 'udp': {}}
        for proto_name, udp in {'tcp': False, 'udp': True}.items():
            for dest_name, reverse in {
                'client_to_server': False,
                'server_to_client': True
            }.items():
                tmp = self.run_iperf(udp, reverse)
                if 'end' in tmp.json:
                    tmp = tmp.json['end']
                res[proto_name][dest_name] = tmp
                logger.debug('Sleeping 2s before next iperf run')
                sleep(2)
        return res

    def check_associated(self):
        logger.debug('Checking association with AP...')
        linfo = pyw.link(self._wifi_card)
        if not "stat" in linfo or not linfo["stat"] == "associated":
            logger.warning('Not associated to an AP')
            return False
        else:
            logger.debug("OK")
            return True

    def get_bssid(self):
        logger.debug('Getting BSSID...')
        linfo = pyw.link(self._wifi_card)
        res = linfo['bssid']
        logger.debug('BSSID is %s', res)
        return res

    def get_ssid(self):
        logger.debug('Getting SSID...')
        linfo = pyw.link(self._wifi_card)
        res = linfo['ssid']
        logger.debug('SSID is %s', res)
        return res

    def get_rss(self):
        logger.debug('Getting received signal strength (RSS)...')
        linfo = pyw.link(self._wifi_card)
        res = linfo['rss']
        logger.debug('RSS is %s', res)
        return res

    def get_freq(self):
        logger.debug('Getting frequency...')
        linfo = pyw.link(self._wifi_card)
        res = linfo['freq']
        logger.debug('Frequency is %s', res)
        return res

    def get_channel(self, freq):
        logger.debug('Getting channel from frequency...')
        res = wireless_utils.channels.rf2ch(freq)
        logger.debug('Channel is %s', res)
        return res

    def get_channel_width(self):
        logger.debug('Getting channel width...')
        linfo = pyw.link(self._wifi_card)
        res = linfo['chw']
        logger.debug('Channel width is %s MHz', res)
        return res

    def get_bitrate(self):
        res = {}
        logger.debug('Getting bitrate width...')
        linfo = pyw.link(self._wifi_card)
        if 'bitrate' in linfo['rx'] and 'rate' in linfo['rx']['bitrate']:
            res['rx'] = linfo['rx']['bitrate']['rate']
        else:
            res['rx'] = -1.0
        if 'bitrate' in linfo['tx'] and 'rate' in linfo['tx']['bitrate']:
            res['tx'] = linfo['tx']['bitrate']['rate']
        else:
            res['tx'] = -1.0
        logger.debug('Bitrate is %.1f / %.1f MBit/s (RX / TX)', res['rx'], res['tx'])
        return res

    def scan_access_points(self):
        logger.debug('Scanning network for available access points...')
        wifi_scanner = get_scanner()
        res = wifi_scanner.get_access_points()
        logger.debug('Found %d access points', len(res))
        return res

    def run_iwscan(self):
        logger.debug('Scanning...')
        res = scan(self._interface_name)
        logger.debug('scan result: %s', res)
        return res
