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
import errno

from .utils import _parse_stats, _get_bytes, iwlib_socket
from ._iwlib import ffi, lib as iwlib


def get_iwconfig(interface):
    """
    Retrieve the current configuration of a given interface

    Arguments:
        interface - device to work on (e.g. eth1, wlan0).
    """
    with iwlib_socket() as sock:
        return _get_iwconfig(interface, sock)


def _get_iwconfig(interface, sock):
    interface = _get_bytes(interface)

    wrq = ffi.new('struct iwreq*')

    iwconfig = {}

    def get_ext(flag):
        return iwlib.iw_get_ext(sock, interface, flag, wrq) >= 0

    if not get_ext(iwlib.SIOCGIWNAME):
        wrq.ifr_ifrn = interface[:iwlib.IFNAMSIZ-1]
        wrq.ifr_ifrn[iwlib.IFNAMSIZ-1] = b'\0'

        if iwlib.ioctl(sock, iwlib.SIOCGIFFLAGS, wrq) < 0:
            err = errno.ENODEV
        else:
            err = errno.ENOTSUP

        strerror = os.strerror(err)

        raise OSError(err, "Could not get config for '%s': %s" % (interface.decode('utf8'), strerror))

    if not get_ext(iwlib.SIOCGIWNWID):
        if wrq.u.nwid.disabled:
            iwconfig['NWID'] = b"Auto"
        else:
            iwconfig['NWID'] = ('%x' % (wrq.u.nwid.value)).encode('utf8')

    buf = ffi.new('char []', 1024)

    if get_ext(iwlib.SIOCGIWFREQ):
        freq = iwlib.iw_freq2float(ffi.addressof(wrq.u.freq))
        iwlib.iw_print_freq_value(buf, len(buf), freq)
        iwconfig['Frequency'] = ffi.string(buf)

    if get_ext(iwlib.SIOCGIWAP):
        iwlib.iw_ether_ntop(ffi.cast('struct ether_addr *', wrq.u.ap_addr.sa_data), buf)
        mode = wrq.u.mode
        has_mode = 0 <= mode < iwlib.IW_NUM_OPER_MODE
        if has_mode and mode == iwlib.IW_MODE_ADHOC:
            iwconfig['Cell'] = ffi.string(buf)
        else:
            iwconfig['Access Point'] = ffi.string(buf)

    if get_ext(iwlib.SIOCGIWRATE):
        iwlib.iw_print_bitrate(buf, len(buf), wrq.u.bitrate.value)
        iwconfig['BitRate'] = ffi.string(buf)

    if get_ext(iwlib.SIOCGIWRATE):
        iwlib.iw_print_bitrate(buf, len(buf), wrq.u.bitrate.value)
        iwconfig['BitRate'] = ffi.string(buf)

    buf = ffi.new('char []', 1024)
    wrq.u.data.pointer = buf
    wrq.u.data.length = iwlib.IW_ENCODING_TOKEN_MAX
    wrq.u.data.flags = 0
    if get_ext(iwlib.SIOCGIWENCODE):
        flags = wrq.u.data.flags
        key_size = wrq.u.data.length

        if flags & iwlib.IW_ENCODE_DISABLED or not key_size:
            iwconfig['Key'] = b'off'
        else:
            key = ffi.new('char []', 1024)
            iwlib.iw_print_key(key, len(key), buf, key_size, flags)
            iwconfig['Key'] = ffi.string(key)

    essid = ffi.new('char []', iwlib.IW_ESSID_MAX_SIZE+1)
    wrq.u.essid.pointer = essid
    wrq.u.essid.length = iwlib.IW_ESSID_MAX_SIZE + 1
    wrq.u.essid.flags = 0
    if get_ext(iwlib.SIOCGIWESSID):
        iwconfig['ESSID'] = ffi.string(ffi.cast('char *', (wrq.u.essid.pointer)))
        wrq.u.essid.length = iwlib.IW_ESSID_MAX_SIZE + 1
        wrq.u.essid.flags = 0

    if get_ext(iwlib.SIOCGIWMODE):
        mode = wrq.u.mode
        has_mode = 0 <= mode < iwlib.IW_NUM_OPER_MODE
        if has_mode:
            iwconfig['Mode'] = ffi.string(iwlib.iw_operation_mode[mode])

    stats = ffi.new('iwstats *')
    range = ffi.new('iwrange *')

    has_range = int(iwlib.iw_get_range_info(sock, interface, range) >= 0)
    if iwlib.iw_get_stats(sock, interface, stats, range, has_range) >= 0:
        iwconfig['stats'] = _parse_stats(stats)

    return iwconfig


def set_essid(interface, essid):
    """
    Set the ESSID of a given interface

    Arguments:
        interface - device to work on (e.g. eth1, wlan0).
        essid - ESSID to set. Must be no longer than IW_ESSID_MAX_SIZE (typically 32 characters).

    """
    interface = _get_bytes(interface)
    essid = _get_bytes(essid)

    wrq = ffi.new('struct iwreq*')

    with iwlib_socket() as sock:
        if essid.lower() in (b'off', b'any'):
            wrq.u.essid.flags = 0
            essid = b''
        elif essid.lower() == b'on':
            buf = ffi.new('char []', iwlib.IW_ESSID_MAX_SIZE+1)
            wrq.u.essid.pointer = buf
            wrq.u.essid.length = iwlib.IW_ESSID_MAX_SIZE + 1
            wrq.u.essid.flags = 0
            if iwlib.iw_get_ext(sock, interface, iwlib.SIOCGIWESSID, wrq) < 0:
                raise ValueError("Error retrieving previous ESSID: %s" % (os.strerror(ffi.errno)))
            wrq.u.essid.flags = 1
        elif len(essid) > iwlib.IW_ESSID_MAX_SIZE:
            raise ValueError("ESSID '%s' is longer than the maximum %d" % (essid, iwlib.IW_ESSID_MAX_SIZE))
        else:
            wrq.u.essid.pointer = ffi.new_handle(essid)
            wrq.u.essid.length = len(essid)
            wrq.u.essid.flags = 1

        if iwlib.iw_get_kernel_we_version() < 21:
            wrq.u.essid.length += 1

        if iwlib.iw_set_ext(sock, interface, iwlib.SIOCSIWESSID, wrq) < 0:
            errno = ffi.errno
            strerror = "Couldn't set essid on device '%s': %s" % (interface.decode('utf8'), os.strerror(errno))
            raise OSError(errno, strerror)
