"""
The latest version of this package is available at:
<http://github.com/jantman/wifi-survey-heatmap>

##################################################################################
Copyright 2020 Dominik DL6ER <dl6er@dl6er.de>

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

This code was inspired by the examples in https://github.com/DL6ER/libnl
but is heavily rewritten to be a lot more general.

AUTHORS:
Dominik DL6ER <dl6er@dl6er.de>
##################################################################################
"""

import logging
import ctypes
import fcntl
import logging
import math
import os
import signal
import socket
import struct
import sys
import time
import datetime

# For scanning access points in the vicinity
import libnl.handlers
from libnl.attr import nla_data, nla_get_string, nla_get_u8, nla_get_u16, nla_get_u32, nla_parse, nla_put_u32, nla_parse, nla_parse_nested, nla_put, nla_put_nested
from libnl.error import errmsg
from libnl.genl.ctrl import genl_ctrl_resolve, genl_ctrl_resolve_grp
from libnl.genl.genl import genl_connect, genlmsg_attrdata, genlmsg_attrlen, genlmsg_put
from libnl.linux_private.genetlink import genlmsghdr
from libnl.linux_private.netlink import NLM_F_DUMP
from libnl.msg import nlmsg_alloc, nlmsg_data, nlmsg_hdr
from libnl.nl import nl_recvmsgs, nl_send_auto, nl_recvmsgs_default
from libnl.nl80211 import nl80211
from libnl.nl80211.helpers import parse_bss
from libnl.nl80211.iw_scan import bss_policy
from libnl.socket_ import nl_socket_add_membership, nl_socket_alloc, nl_socket_drop_membership, nl_socket_modify_cb
from libnl.handlers import NL_CB_CUSTOM, NL_CB_VALID, NL_SKIP
from ctypes import c_int32

logger = logging.getLogger(__name__)


class Scanner(object):

    def __init__(self, interface_name=None, scan=True):
        super().__init__()
        logger.debug(
            'Initializing Scanner for interface: %s',
            interface_name
        )
        self.interface_name = interface_name
        self._scan = scan
        self.iface_data = {}

        self._nl_sock = None

        # Get all interfaces of this machine
        self.if_idx = None
        self.iface_names = self.list_all_interfaces()

    def set_interface(self, interface_name):
        for idx in self.iface_data:
            if self.iface_data[idx]['name'] == interface_name:
                self.if_idx = idx
                self.interface_name = interface_name
                break
        if self.if_idx == None:
            logger.error("Device {0} is not a valid interface, use"
                        " one of {1}".format(interface_name, self.iface_names))
            exit(1)

    def list_all_interfaces(self):
        self.update_iface_details(nl80211.NL80211_CMD_GET_INTERFACE)
        iface_names = []
        for idx in self.iface_data:
            if 'name' in self.iface_data[idx]:
                iface_names.append(self.iface_data[idx]['name'])
        return iface_names

    def _error_handler(self, _, err, arg):
        """Update the mutable integer `arg` with the error code."""
        arg.value = err.error
        return libnl.handlers.NL_STOP

    def _ack_handler(self, _, arg):
        """Update the mutable integer `arg` with 0 as an acknowledgement."""
        arg.value = 0
        return libnl.handlers.NL_STOP

    def _callback_trigger(self, msg, arg):
        # Called when the kernel is done scanning. Only signals if it was
        # successful or if it failed. No other data.
        #
        # Positional arguments:
        # msg -- nl_msg class instance containing the data sent by the kernel.
        # arg -- mutable integer (ctypes.c_int()) to update with results.
        #
        # Returns:
        # An integer, value of NL_SKIP. It tells libnl to stop calling other
        # callbacks for this message and proceed with processing the next kernel
        # message.
        gnlh = genlmsghdr(nlmsg_data(nlmsg_hdr(msg)))
        if gnlh.cmd == nl80211.NL80211_CMD_SCAN_ABORTED:
            arg.value = 1  # The scan was aborted for some reason.
        elif gnlh.cmd == nl80211.NL80211_CMD_NEW_SCAN_RESULTS:
            # The scan completed successfully. `callback_dump` will collect the results later.
            arg.value = 0
        return libnl.handlers.NL_SKIP

    def _callback_dump(self, msg, results):
        # Here is where SSIDs and their data is decoded from the binary data
        # sent by the kernel. This function is called once per SSID. Everything
        # in `msg` pertains to just one SSID.
        #
        # Positional arguments:
        # msg -- nl_msg class instance containing the data sent by the kernel.
        # results -- dictionary to populate with parsed data.
        bss = dict()  # To be filled by nla_parse_nested().

        # First we must parse incoming data into manageable chunks and check for errors.
        gnlh = genlmsghdr(nlmsg_data(nlmsg_hdr(msg)))
        tb = dict((i, None) for i in range(nl80211.NL80211_ATTR_MAX + 1))
        nla_parse(tb, nl80211.NL80211_ATTR_MAX, genlmsg_attrdata(
            gnlh, 0), genlmsg_attrlen(gnlh, 0), None)
        if not tb[nl80211.NL80211_ATTR_BSS]:
            logger.warning('BSS info missing for an access point.')
            return libnl.handlers.NL_SKIP
        if nla_parse_nested(bss, nl80211.NL80211_BSS_MAX,
                            tb[nl80211.NL80211_ATTR_BSS], bss_policy):
            logger.warning(
                'Failed to parse nested attributes for an access point!')
            return libnl.handlers.NL_SKIP
        if not bss[nl80211.NL80211_BSS_BSSID]:
            logger.warning('No BSSID detected for an access point!')
            return libnl.handlers.NL_SKIP
        if not bss[nl80211.NL80211_BSS_INFORMATION_ELEMENTS]:
            logger.warning(
                'No additional information available for an access point!')
            return libnl.handlers.NL_SKIP

        # Further parse and then store. Overwrite existing data for BSSID if scan is run multiple times.
        bss_parsed = parse_bss(bss)
        results[bss_parsed['bssid']] = bss_parsed
        return libnl.handlers.NL_SKIP

    def _do_scan_trigger(self, if_index, driver_id, mcid):
        # Issue a scan request to the kernel and wait for it to reply with a
        # signal.
        #
        # This function issues NL80211_CMD_TRIGGER_SCAN which requires root
        # privileges. The way NL80211 works is first you issue
        # NL80211_CMD_TRIGGER_SCAN and wait for the kernel to signal that the
        # scan is done. When that signal occurs, data is not yet available. The
        # signal tells us if the scan was aborted or if it was successful (if
        # new scan results are waiting). This function handles that simple
        # signal. May exit the program (sys.exit()) if a fatal error occurs.
        #
        # Positional arguments:
        # self._nl_sock -- nl_sock class instance (from nl_socket_alloc()).
        # if_index -- interface index (integer).
        # driver_id -- nl80211 driver ID from genl_ctrl_resolve() (integer).
        # mcid -- nl80211 scanning group ID from genl_ctrl_resolve_grp() (integer).
        #
        # Returns:
        # 0 on success or a negative error code.

        # First get the "scan" membership group ID and join the socket to the group.
        logger.debug('Joining group %d.', mcid)
        # Listen for results of scan requests (aborted or new results).
        ret = nl_socket_add_membership(self._nl_sock, mcid)
        if ret < 0:
            return ret

        # Build the message to be sent to the kernel.
        msg = nlmsg_alloc()
        # Setup which command to run.
        genlmsg_put(msg, 0, 0, driver_id, 0, 0,
                    nl80211.NL80211_CMD_TRIGGER_SCAN, 0)
        # Setup which interface to use.
        nla_put_u32(msg, nl80211.NL80211_ATTR_IFINDEX, if_index)
        ssids_to_scan = nlmsg_alloc()
        nla_put(ssids_to_scan, 1, 0, b'')  # Scan all SSIDs.
        # Setup what kind of scan to perform.
        nla_put_nested(msg, nl80211.NL80211_ATTR_SCAN_SSIDS, ssids_to_scan)

        # Setup the callbacks to be used for triggering the scan only.
        # Used as a mutable integer to be updated by the callback function.
        # Signals end of messages.
        err = ctypes.c_int(1)
        # Signals if the scan was successful (new results) or aborted, or not
        # started.
        results = ctypes.c_int(-1)
        cb = libnl.handlers.nl_cb_alloc(libnl.handlers.NL_CB_DEFAULT)
        libnl.handlers.nl_cb_set(cb, libnl.handlers.NL_CB_VALID,
                                 libnl.handlers.NL_CB_CUSTOM, self._callback_trigger, results)
        libnl.handlers.nl_cb_err(
            cb, libnl.handlers.NL_CB_CUSTOM, self._error_handler, err)
        libnl.handlers.nl_cb_set(
            cb, libnl.handlers.NL_CB_ACK, libnl.handlers.NL_CB_CUSTOM, self._ack_handler, err)
        libnl.handlers.nl_cb_set(cb, libnl.handlers.NL_CB_SEQ_CHECK, libnl.handlers.NL_CB_CUSTOM,
                                 lambda *_: libnl.handlers.NL_OK, None)  # Ignore sequence checking.

        # Now we send the message to the kernel, and retrieve the
        # acknowledgement. The kernel takes a few seconds to finish scanning for
        # access points.
        logger.debug('Sending NL80211_CMD_TRIGGER_SCAN...')
        ret = nl_send_auto(self._nl_sock, msg)
        if ret < 0:
            return ret
        while err.value > 0:
            logger.debug(
                'Retrieving NL80211_CMD_TRIGGER_SCAN acknowledgement...')
            ret = nl_recvmsgs(self._nl_sock, cb)
            if ret < 0:
                return ret
        if err.value < 0:
            logger.warning('Unknown error {0} ({1})'.format(
                err.value, errmsg[abs(err.value)]))

        # Block until the kernel is done scanning or aborted the scan.
        while results.value < 0:
            logger.debug(
                'Retrieving NL80211_CMD_TRIGGER_SCAN final response...')
            ret = nl_recvmsgs(self._nl_sock, cb)
            if ret < 0:
                return ret
        if results.value > 0:
            logger.warning('The kernel aborted the scan.')

        # Done, cleaning up.
        logger.debug('Leaving group %d.', mcid)
        # No longer need to receive multicast messages.
        return nl_socket_drop_membership(self._nl_sock, mcid)

    def _do_scan_results(self, if_index, driver_id, results):
        # Retrieve the results of a successful scan (SSIDs and data about them).
        # This function does not require root privileges. It eventually calls a
        # callback that actually decodes data about SSIDs but this function
        # kicks that off. May exit the program (sys.exit()) if a fatal error
        # occurs.
        #
        # Positional arguments:
        # self._nl_sock -- nl_sock class instance (from nl_socket_alloc()).
        # if_index -- interface index (integer).
        # driver_id -- nl80211 driver ID from genl_ctrl_resolve() (integer).
        # results -- dictionary to populate with results. Keys are BSSIDs (MAC
        #            addresses) and values are dicts of data.
        # Returns:
        # 0 on success or a negative error code.

        msg = nlmsg_alloc()
        genlmsg_put(msg, 0, 0, driver_id, 0, NLM_F_DUMP,
                    nl80211.NL80211_CMD_GET_SCAN, 0)
        nla_put_u32(msg, nl80211.NL80211_ATTR_IFINDEX, if_index)
        cb = libnl.handlers.nl_cb_alloc(libnl.handlers.NL_CB_DEFAULT)
        libnl.handlers.nl_cb_set(cb, libnl.handlers.NL_CB_VALID,
                                 libnl.handlers.NL_CB_CUSTOM, self._callback_dump, results)
        logger.debug('Sending NL80211_CMD_GET_SCAN...')
        ret = nl_send_auto(self._nl_sock, msg)
        if ret >= 0:
            logger.debug('Retrieving NL80211_CMD_GET_SCAN response...')
            ret = nl_recvmsgs(self._nl_sock, cb)
        return ret

    def scan_all_access_points(self):
        # Scan for access points within reach

        # First get the wireless interface index.
        pack = struct.pack('16sI', self.interface_name.encode('ascii'), 0)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            info = struct.unpack('16sI', fcntl.ioctl(
                sock.fileno(), 0x8933, pack))
        except OSError:
            return logger.warning(
                'Wireless interface {0}\
                    does not exist.'.format(self.interface_name))
        finally:
            sock.close()
        if_index = int(info[1])

        # Next open a socket to the kernel and bind to it. Same one used for
        # sending and receiving.
        self._nl_sock = nl_socket_alloc()  # Creates an `nl_sock` instance.
        genl_connect(self._nl_sock)  # Create file descriptor and bind socket.
        logger.debug('Finding the nl80211 driver ID...')
        driver_id = genl_ctrl_resolve(self._nl_sock, b'nl80211')
        logger.debug('Finding the nl80211 scanning group ID...')
        mcid = genl_ctrl_resolve_grp(self._nl_sock, b'nl80211', b'scan')

        # Scan for access points 1 or more (if requested) times.
        results = dict()
        for i in range(2, -1, -1):  # Three tries on errors.
            ret = self._do_scan_trigger(if_index, driver_id, mcid)
            if ret < 0:
                logger.debug('do_scan_trigger() returned {0},'
                             'retrying in 5 seconds({1}).'.format(ret, i))
                time.sleep(5)
            ret = self._do_scan_results(if_index, driver_id, results)
            if ret < 0:
                logger.debug('do_scan_results() returned {0},'
                             'retrying in 5 seconds ({1}).'.format(ret, i))
                time.sleep(5)
                continue
            break
        if not results:
            logger.debug('No access points detected.')
            return []

        logger.debug('Found {0} access points:'.format(len(results)))

        # Convert timedelta to integer to avoid
        #    TypeError: Object of type timedelta is not JSON serializable
        for ap in results:
            for prop in results[ap]:
                if isinstance(results[ap][prop], datetime.timedelta):
                    results[ap][prop] = int(
                        results[ap][prop].microseconds)/1000

        return results

    def _iface_callback(self, msg, _):
        # Callback function called by libnl upon receiving messages from the
        # kernel.
        #
        # Positional arguments:
        # msg -- nl_msg class instance containing the data sent by the kernel.
        #
        # Returns:
        # An integer, value of NL_SKIP. It tells libnl to stop calling other
        # callbacks for this message and proceed with processing the next kernel
        # message.

        # First convert `msg` into something more manageable.
        gnlh = genlmsghdr(nlmsg_data(nlmsg_hdr(msg)))

        # Partially parse the raw binary data and place them in the `tb`
        # dictionary. Need to populate dict with all possible keys.
        tb = dict((i, None) for i in range(nl80211.NL80211_ATTR_MAX + 1))
        nla_parse(tb, nl80211.NL80211_ATTR_MAX, genlmsg_attrdata(
            gnlh, 0), genlmsg_attrlen(gnlh, 0), None)

        # Now it's time to grab the data, we start with the interface index as
        # universal identifier
        if tb[nl80211.NL80211_ATTR_IFINDEX]:
            if_index = nla_get_u32(tb[nl80211.NL80211_ATTR_IFINDEX])
        else:
            return NL_SKIP

        # Create new interface dict if this interface is not yet known
        if if_index in self.iface_data:
            iface_data = self.iface_data[if_index]
        else:
            iface_data = {}

        if tb[nl80211.NL80211_ATTR_IFNAME]:
            iface_data['name'] = nla_get_string(
                tb[nl80211.NL80211_ATTR_IFNAME]).decode('ascii')

        if tb[nl80211.NL80211_ATTR_IFTYPE]:
            iftype = nla_get_u32(tb[nl80211.NL80211_ATTR_IFTYPE])

            if iftype == nl80211.NL80211_IFTYPE_UNSPECIFIED:
                typestr = 'UNSPECIFIED'
            elif iftype == nl80211.NL80211_IFTYPE_ADHOC:
                typestr = 'ADHOC'
            elif iftype == nl80211.NL80211_IFTYPE_STATION:
                typestr = 'STATION'
            elif iftype == nl80211.NL80211_IFTYPE_AP:
                typestr = 'AP'
            elif iftype == nl80211.NL80211_IFTYPE_AP_VLAN:
                typestr = 'AP_VLAN'
            elif iftype == nl80211.NL80211_IFTYPE_WDS:
                typestr = 'WDS'
            elif iftype == nl80211.NL80211_IFTYPE_MONITOR:
                typestr = 'MONITOR'
            elif iftype == nl80211.NL80211_IFTYPE_MESH_POINT:
                typestr = 'MESH_POINT'
            elif iftype == nl80211.NL80211_IFTYPE_P2P_CLIENT:
                typestr = 'P2P_CLIENT'
            elif iftype == nl80211.NL80211_IFTYPE_P2P_GO:
                typestr = 'P2P_GO'
            elif iftype == nl80211.NL80211_IFTYPE_P2P_DEVICE:
                typestr = 'P2P_DEVICE'

            iface_data['type'] = typestr

        if tb[nl80211.NL80211_ATTR_WIPHY]:
            wiphy_num = nla_get_u32(tb[nl80211.NL80211_ATTR_WIPHY])
            iface_data['wiphy'] = 'phy#{0}'.format(wiphy_num)

        if tb[nl80211.NL80211_ATTR_MAC]:
            mac_raw = nla_data(tb[nl80211.NL80211_ATTR_MAC])[:6]
            mac_address = ':'.join(format(x, '02x') for x in mac_raw)
            iface_data['mac'] = mac_address

        if tb[nl80211.NL80211_ATTR_GENERATION]:
            generation = nla_get_u32(tb[nl80211.NL80211_ATTR_GENERATION])
            # Do not overwrite the generation for excessively large values
            if generation < 100:
                iface_data['generation'] = generation

        if tb[nl80211.NL80211_ATTR_WIPHY_TX_POWER_LEVEL]:
            iface_data['tx_power'] = nla_get_u32(
                tb[nl80211.NL80211_ATTR_WIPHY_TX_POWER_LEVEL])/100  # mW

        if tb[nl80211.NL80211_ATTR_CHANNEL_WIDTH]:
            iface_data['ch_width'] = nla_get_u32(
                tb[nl80211.NL80211_ATTR_CHANNEL_WIDTH])

        if tb[nl80211.NL80211_ATTR_CENTER_FREQ1]:
            iface_data['frequency'] = nla_get_u32(
                tb[nl80211.NL80211_ATTR_CENTER_FREQ1])

        # Station infos
        if tb[nl80211.NL80211_ATTR_STA_INFO]:
            # Need to unpack the data
            sinfo = dict((i, None)
                         for i in range(nl80211.NL80211_STA_INFO_MAX))
            rinfo = dict((i, None)
                         for i in range(nl80211.NL80211_STA_INFO_TX_BITRATE))

            # Extract data
            nla_parse_nested(sinfo, nl80211.NL80211_STA_INFO_MAX,
                             tb[nl80211.NL80211_ATTR_STA_INFO], None)

            # Extract info about signal strength (= quality)
            if sinfo[nl80211.NL80211_STA_INFO_SIGNAL]:
                iface_data['signal'] = 100 + \
                    nla_get_u8(sinfo[nl80211.NL80211_STA_INFO_SIGNAL])
                # Compute quality (formula found in iwinfo_nl80211.c and largely
                # simplified)
                iface_data['quality'] = iface_data['signal'] + 110
                iface_data['quality_max'] = 70

            # Extract info about negotiated bitrate
            if sinfo[nl80211.NL80211_STA_INFO_TX_BITRATE]:
                nla_parse_nested(rinfo, nl80211.NL80211_RATE_INFO_MAX,
                                 sinfo[nl80211.NL80211_STA_INFO_TX_BITRATE],
                                 None)
                if rinfo[nl80211.NL80211_RATE_INFO_BITRATE]:
                    iface_data['bitrate'] = nla_get_u16(
                        rinfo[nl80211.NL80211_RATE_INFO_BITRATE])/10

        # BSS info
        if tb[nl80211.NL80211_ATTR_BSS]:
            # Need to unpack the data
            binfo = dict((i, None) for i in range(nl80211.NL80211_BSS_MAX))
            nla_parse_nested(binfo, nl80211.NL80211_BSS_MAX,
                             tb[nl80211.NL80211_ATTR_BSS], None)

            # Parse BSS section (if complete)
            try:
                bss = parse_bss(binfo)

                # Remove duplicated information blocks
                if 'beacon_ies' in bss:
                    del bss['beacon_ies']
                if 'information_elements' in bss:
                    del bss['information_elements']
                if 'supported_rates' in bss:
                    del bss['supported_rates']

                # Convert timedelta objects for later JSON encoding
                for prop in bss:
                    if isinstance(bss[prop], datetime.timedelta):
                        bss[prop] = int(bss[prop].microseconds)/1000

                # Append BSS data to general object
                iface_data = {**iface_data, **bss}
            except Exception as e:
                logger.warning("Obtaining BSS data failed: {}".format(e))
                pass

        # Append data to global structure
        self.iface_data[if_index] = iface_data

        return NL_SKIP

    def update_iface_details(self, cmd):
        # Send a command specified by CMD to the kernel and attach a callback to
        # process the returned values into our own datastructure

        self._nl_sock = nl_socket_alloc()  # Creates an `nl_sock` instance.
        # Create file descriptor and bind socket.
        ret = genl_connect(self._nl_sock)
        if ret < 0:
            reason = errmsg[abs(ret)]
            logger.error(
                'genl_connect() returned {0} ({1})'.format(ret, reason))
            return {}

        # Now get the nl80211 driver ID. Handle errors here.
        # Find the nl80211 driver ID.
        driver_id = genl_ctrl_resolve(self._nl_sock, b'nl80211')
        if driver_id < 0:
            reason = errmsg[abs(driver_id)]
            logger.error(
                'genl_ctrl_resolve() returned {0} ({1})'.format(driver_id,
                                                                reason))
            return {}

        # Setup the Generic Netlink message.
        msg = nlmsg_alloc()  # Allocate a message.
        if self.if_idx == None:
            # Ask kernel to send info for all wireless interfaces.
            genlmsg_put(msg, 0, 0, driver_id, 0, NLM_F_DUMP,
                        nl80211.NL80211_CMD_GET_INTERFACE, 0)
        else:
            genlmsg_put(msg, 0, 0, driver_id, 0, NLM_F_DUMP, cmd, 0)
            # This is the interface we care about.
            nla_put_u32(msg, nl80211.NL80211_ATTR_IFINDEX, self.if_idx)
            #nla_put_u32(msg, nl80211.NL80211_ATTR_MAC, 2199023255552)

        # Add the callback function to the self._nl_sock.
        nl_socket_modify_cb(self._nl_sock, NL_CB_VALID,
                            NL_CB_CUSTOM, self._iface_callback, False)

        # Now send the message to the kernel, and get its response,
        # automatically calling the callback.
        ret = nl_send_auto(self._nl_sock, msg)
        if ret < 0:
            reason = errmsg[abs(ret)]
            logger.error(
                'nl_send_auto() returned {0} ({1})'.format(ret, reason))
            return {}
        logger.debug('Sent {0} bytes to the kernel.'.format(ret))
        # Blocks until the kernel replies. Usually it's instant.
        ret = nl_recvmsgs_default(self._nl_sock)
        if ret < 0:
            reason = errmsg[abs(ret)]
            logger.error(
                'nl_recvmsgs_default() returned {0} ({1})'.format(ret, reason))
            return {}

    def get_iface_data(self, update=False):
        if(update):
            logger.debug("Updating WiFi interface data ...")
            self.update_iface_details(nl80211.NL80211_CMD_GET_STATION)
            self.update_iface_details(nl80211.NL80211_CMD_GET_SCAN)

        return self.iface_data[self.if_idx]
