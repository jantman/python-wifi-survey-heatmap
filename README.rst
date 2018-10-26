python-wifi-survey-heatmap
==========================

A Python application for Linux machines running NetworkManager to perform WiFi
site surveys and present the results as a heatmap overlayed on a floorplan.

Very alpha.

Dependencies
------------

* This relies on the Python `iwlib <https://pypi.org/project/iwlib/>`_ package, which needs cffi and the Linux ``wireless_tools`` package.
* This relies on the ``python-networkmanager`` package. That in turn relies on ``dbus-python`` which may work better via OS packages (virtualenv with ``--system-site-packages``).
