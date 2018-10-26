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

from iwlib.iwlist import scan
from iwlib.iwconfig import get_iwconfig
import NetworkManager

logger = logging.getLogger(__name__)


class Collector(object):

    def __init__(self, interface_name):
        super().__init__()
        logger.debug('Initializing Collector for interface: %s', interface_name)
        self._interface_name = interface_name

    def run(self):
        res = {}
        logger.debug('Getting iwconfig...')
        res['config'] = get_iwconfig(self._interface_name)
        logger.debug('iwconfig result: %s', res['config'])
        """
        logger.debug('Scanning...')
        res['scan'] = scan(self._interface_name)
        logger.debug('scan result: %s', res['scan'])
        """
        logger.debug('Finding APs via NetworkManager')
        res['nm_aps'] = {}
        """
        for dev in NetworkManager.Device.all():
            if dev.DeviceType == NetworkManager.NM_DEVICE_TYPE_WIFI:
        """
        for ap in NetworkManager.AccessPoint.all():
            try:
                res['nm_aps'][ap.object_path] = {
                    'ssid': ap.Ssid,
                    'mac': ap.HwAddress,
                    'frequency': ap.Frequency,
                    'strength': ap.Strength
                }
                logger.debug('AP: %s', vars(ap))
                logger.debug(dir(ap))
            except NetworkManager.ObjectVanished:
                pass
        logger.debug(
            'Found %d APs from NetworkManager: %s',
            len(res['nm_aps']), res['nm_aps']
        )
        return res
