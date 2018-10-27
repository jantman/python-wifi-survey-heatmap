# Copyright (C) 2009-2012 Red Hat, Inc.
# Copyright (C) 2013-2014 Nathan Hoad.
#
# Interface with iwlib by Nathan Hoad <nathan@getoffmalawn.com>.
#
# This application is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation; version 2.
#
# This application is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.

import os

from .utils import _get_range_info, _parse_stats, _get_bytes, iwlib_socket
from ._iwlib import ffi, lib as iwlib


def scan(interface):
    """Perform a scan for access points in the area.

    Arguments:
        interface - device to use for scanning (e.g. eth1, wlan0).
    """
    interface = _get_bytes(interface)

    head = ffi.new('wireless_scan_head *')

    with iwlib_socket() as sock:
        range = _get_range_info(interface, sock=sock)

        if iwlib.iw_scan(sock, interface, range.we_version_compiled, head) != 0:
            errno = ffi.errno
            strerror = "Error while scanning: %s" % os.strerror(errno)
            raise OSError(errno, strerror)

    results = []

    scan = head.result

    buf = ffi.new('char []', 1024)

    while scan != ffi.NULL:
        parsed_scan = {}

        if scan.b.has_mode:
            parsed_scan['Mode'] = ffi.string(iwlib.iw_operation_mode[scan.b.mode])

        if scan.b.has_freq:
            parsed_scan['Frequency'] = scan.b.freq

        if scan.b.essid_on:
            parsed_scan['ESSID'] = ffi.string(scan.b.essid)
        else:
            parsed_scan['ESSID'] = b'Auto'

        if scan.has_ap_addr:
            iwlib.iw_ether_ntop(
                ffi.cast('struct ether_addr *', scan.ap_addr.sa_data), buf)
            if scan.b.has_mode and scan.b.mode == iwlib.IW_MODE_ADHOC:
                parsed_scan['Cell'] = ffi.string(buf)
            else:
                parsed_scan['Access Point'] = ffi.string(buf)

        if scan.has_maxbitrate:
            iwlib.iw_print_bitrate(buf, len(buf), scan.maxbitrate.value)
            parsed_scan['BitRate'] = ffi.string(buf)

        if scan.has_stats:
            parsed_scan['stats'] = _parse_stats(scan.stats)

        results.append(parsed_scan)
        scan = scan.next

    return results
