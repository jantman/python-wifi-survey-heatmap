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

from time import sleep
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
        self._connection_names = conn_names

    @property
    def _device(self):
        for dev in NetworkManager.NetworkManager.GetDevices():
            if dev.Interface == self._interface_name:
                return dev
        raise RuntimeError('ERROR: No device "%s" found.' % interface_name)

    @property
    def _connections(self):
        connections = dict([
            (
                x.GetSettings()['connection']['id'], x
            ) for x in NetworkManager.Settings.ListConnections()
        ])
        return {
            x: connections[x] for x in connections
            if x in self._connection_names
        }

    def _get_current_stats(self):
        res = {}
        logger.debug('Getting iwconfig...')
        res['config'] = get_iwconfig(self._interface_name)
        logger.debug('iwconfig result: %s', res['config'])
        logger.debug('Finding APs via NetworkManager')
        res['nm_aps'] = {}
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
        return res

    @property
    def _active_connections(self):
        try:
            return dict([
                (x.Connection.GetSettings()['connection']['id'], x)
                for x in NetworkManager.NetworkManager.ActiveConnections
            ])
        except Exception:
            return {}

    def _deactivate(self):
        for cname, conn in self._active_connections.items():
            if cname not in self._connection_names:
                continue
            try:
                logger.debug('Deactivating connection: %s', cname)
                NetworkManager.NetworkManager.DeactivateConnection(conn)
            except Exception as ex:
                logger.debug('Unable to deactivate: %s', ex, exc_info=True)
            for i in range(0, 100):
                s = self._device.State
                if s == NetworkManager.NM_DEVICE_STATE_DISCONNECTED:
                    logger.debug('Device is disconnected.')
                    return
                logger.debug(
                    'Device is in state %s; sleep 2s',
                    NetworkManager.const('device_state', s)
                )
            raise RuntimeError('ERROR: Device never disconnected.')

    def _activate(self, conn_name, conn):
        logger.debug('Activating %s', conn_name)
        NetworkManager.NetworkManager.ActivateConnection(
            conn, self._device, "/"
        )
        for i in range(0, 100):
            if conn_name in self._active_connections.keys():
                logger.debug('Activated connection %s', conn_name)
                return
            logger.debug('Connection %s not active yet; sleep 2s', conn_name)
            sleep(2)
        raise RuntimeError('ERROR: Connection never activated.')

    def run(self):
        res = {}
        if self._device.ActiveConnection is not None:
            logger.info(
                'Getting stats for current connection: %s',
                self._device.ActiveConnection.Id
            )
            res[self._device.ActiveConnection.Id] = self._get_current_stats()
        for conn_name, conn in self._connections.items():
            if conn_name in res.keys():
                continue
            self._deactivate()
            logger.info(
                'Connecting to and getting stats for connection: %s',
                conn_name
            )
            self._activate(conn_name, conn)
            res[conn_name] = self._get_current_stats()
        return res
