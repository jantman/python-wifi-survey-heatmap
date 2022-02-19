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

from wifi_survey_heatmap.libnl import Scanner

import iperf3

logger = logging.getLogger(__name__)


class Collector(object):

    def __init__(self, server_addr, duration, scanner, scan=True):
        super().__init__()
        logger.debug(
            'Initializing Collector for interface: %s; iperf server: %s',
            scanner.interface_name, server_addr
        )
        # ensure interface_name is a wireless interfaces
        self._iperf_server = server_addr
        self._scan = scan
        self._duration = duration
        self.scanner = scanner

    def run_iperf(self, udp=False, reverse=False):
        client = iperf3.Client()
        client.duration = self._duration

        server_parts = self._iperf_server.split(":")
        if len(server_parts) == 2:
            client.server_hostname = server_parts[0]
            client.port = int(server_parts[1])
        else:
            client.server_hostname = self._iperf_server
            client.port = 5201 # substitute some default port

        client.protocol = 'udp' if udp else 'tcp'
        client.reverse = reverse
        logger.info(
            'Running iperf to %s; udp=%s reverse=%s', self._iperf_server,
            udp, reverse
        )
        for retry in range(0, 4):
            res = client.run()
            if res.error is None:
                break
            logger.error('iperf error %s; retrying', res.error)
        logger.debug('iperf result: %s', res)
        return res

    def check_associated(self):
        logger.debug('Checking association with AP...')
        if self.scanner.get_current_bssid() is None:
            logger.warning('Not associated to an AP')
            return False
        else:
            logger.debug("OK")
            return True

    def get_metrics(self):
        return self.scanner.get_iface_data()

    def scan_all_access_points(self):
        logger.debug('Scanning...')
        res = self.scanner.scan_all_access_points()
        logger.debug('Found {} access points during scan'.format(len(res)))
        return res
