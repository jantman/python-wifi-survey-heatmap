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

    def __init__(self, interface_name, conn_names):
        super().__init__()
        logger.debug(
            'Initializing Collector for interface: %s with connections: %s',
            interface_name, conn_names
        )
        self._interface_name = interface_name
        self._device = None
        for dev in NetworkManager.NetworkManager.GetDevices():
            if dev.Interface == interface_name:
                self._device = dev
        if self._device is None:
            raise RuntimeError('ERROR: No device "%s" found.' % interface_name)
        self._connection_names = conn_names
        connections = dict([
            (
                x.GetSettings()['connection']['id'], x
            ) for x in NetworkManager.Settings.ListConnections()
        ])
        self._connections = {
            x: connections[x] for x in connections if x in conn_names
        }

    def _activate_connection(self, name):
        conn = self._connections[name]
        NetworkManager.NetworkManager.ActivateConnection(
            conn, self._device, "/"
        )

    def _get_active_connection_name(self):
        for conn in NetworkManager.NetworkManager.ActiveConnections:
            if conn in self._connections.values():
                return conn.Connection.GetSettings()['connection']['id']
        return None

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
            except NetworkManager.ObjectVanished:
                pass
        logger.debug(
            'Found %d APs from NetworkManager: %s',
            len(res['nm_aps']), res['nm_aps']
        )
        # BEGIN DEBUG
        print("Available network devices")
        print("%-10s %-19s %-20s %s" % ("Name", "State", "Driver", "Managed?"))
        for dev in NetworkManager.NetworkManager.GetDevices():
            print("%-10s %-19s %-20s %s" % (
            dev.Interface, NetworkManager.const('device_state', dev.State), dev.Driver,
            dev.Managed))

        print("")

        print("Available connections")
        print("%-30s %s" % ("Name", "Type"))
        for conn in NetworkManager.Settings.ListConnections():
            settings = conn.GetSettings()['connection']
            print("%-30s %s" % (settings['id'], settings['type']))

        print("")

        print("Active connections")
        print("%-30s %-20s %-10s %s" % ("Name", "Type", "Default", "Devices"))
        for conn in NetworkManager.NetworkManager.ActiveConnections:
            settings = conn.Connection.GetSettings()['connection']
            print("%-30s %-20s %-10s %s" % (
            settings['id'], settings['type'], conn.Default,
            ", ".join([x.Interface for x in conn.Devices])))
        print('############## Device %s' % self._interface_name)
        print(self._device)
        print(NetworkManager.const('device_state', self._device.State))
        print(self._device.ActiveConnection.Id)
        # END DEBUG
        return res
