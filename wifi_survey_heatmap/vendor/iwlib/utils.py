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

import contextlib
import errno
import os

from ._iwlib import ffi, lib as iwlib


@contextlib.contextmanager
def iwlib_socket(sock=None):
    if sock is None:
        closing = True
        sock = iwlib.iw_sockets_open()
    else:
        closing = False

    if sock < 0:
        raise OSError(ffi.errno, os.strerror(ffi.errno))

    try:
        yield sock
    finally:
        if closing:
            iwlib.iw_sockets_close(sock)


def get_max_quality(interface):
    """
    Return max quality of an interface. Useful for working out percentages of
    quality results from `iwconfig.scan()`.
    """
    range = _get_range_info(interface)
    return range.max_qual.qual


def supports_scanning(interface):
    """
    Check if an interface supports scanning.
    Returns true if the device supports scanning. False otherwise.
    """
    try:
        _get_range_info(interface)
    except OSError:
        return False
    else:
        return True


def _get_range_info(interface, sock=None):
    interface = _get_bytes(interface)
    range = ffi.new('struct iw_range *')

    with iwlib_socket(sock=sock) as sock:
        has_range = iwlib.iw_get_range_info(sock, interface, range) >= 0

    if not has_range or range.we_version_compiled < 14:
        err = errno.ENOTSUP
        raise OSError(err, os.strerror(err))
    return range


def _parse_stats(stats):
    return {
        'quality': stats.qual.qual,
        'level': stats.qual.level,
        'noise': stats.qual.noise,
        'updated': stats.qual.updated,
    }


def _get_bytes(s):
    if isinstance(s, bytes):
        return s
    return s.encode('utf8')
