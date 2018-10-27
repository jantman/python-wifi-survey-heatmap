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

from wifi_survey_heatmap.vendor.iwlib.iwconfig import get_iwconfig
from wifi_survey_heatmap.vendor.iwlib.iwlist import scan

logger = logging.getLogger(__name__)


class Collector(object):

    def __init__(self, interface_name, server_addr):
        super().__init__()
        logger.debug(
            'Initializing Collector for interface: %s; iperf server: %s',
            interface_name, server_addr
        )
        self._interface_name = interface_name
        self._iperf_server = server_addr

    def _run_iperf(self):
        res = {}
        return res

    def run(self):
        res = {
            'iperf': self._run_iperf()
        }
        logger.debug('Getting iwconfig...')
        res['config'] = get_iwconfig(self._interface_name)
        logger.debug('iwconfig result: %s', res['config'])
        logger.debug('Scanning...')
        res['scan'] = scan(self._interface_name)
        logger.debug('scan result: %s', res['scan'])
        return res
