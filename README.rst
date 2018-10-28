python-wifi-survey-heatmap
==========================

A Python application for Linux machines to perform WiFi site surveys and present
the results as a heatmap overlayed on a floorplan.

Very alpha.

Dependencies
------------

* The Python `iwlib <https://pypi.org/project/iwlib/>`_ package, which needs cffi and the Linux ``wireless_tools`` package.
* The Python `iperf3 <https://pypi.org/project/iperf3/>`_ package, which needs `iperf3 <http://software.es.net/iperf/>`_ installed on your system.
* `wxPython Phoenix <https://wiki.wxpython.org/How%20to%20install%20wxPython>`_, which unfortunately must be installed using OS packages or built from source.
* An iperf3 server running on another system on the LAN, as described below.

Data Collection
---------------

At each survey location, data collection should take 45-60 seconds. The data collected is currently:

* 10-second iperf3 measurement, TCP, client (this app) sending to server, default iperf3 options
* 10-second iperf3 measurement, TCP, server sending to client, default iperf3 options
* 10-second iperf3 measurement, UDP, client (this app) sending to server, default iperf3 options
* 10-second iperf3 measurement, UDP, server sending to client, default iperf3 options
* ``iwconfig`` capture for current AP/ESSID/BSSID, frequency, bitrate, and quality/level/noise stats
* ``iwlist`` scan of all visible access points

Usage
-----

Server Setup
++++++++++++

On the system you're using as the ``iperf3`` server, run ``iperf3 -s`` to start iperf3 in server mode in the foreground.
By default it will use TCP and UDP ports 5201 for communication, and these must be open in your firewall (at least from the client machine).
Ideally, you should be running the same exact iperf3 version on both machines.
