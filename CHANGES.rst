Changelog
=========

2.0.0 (2024-12-08)
------------------

* Bump base Docker image from Buster to Bullseye.
* Merge `PR 34 <https://github.com/jantman/python-wifi-survey-heatmap/pull/34>`_ to include plot failure exception in logging, thanks to `josephw <https://github.com/josephw>`_.
* README - include link to similar project for MacOS.
* Massive contribution from `byteit101 <https://github.com/byteit101>`_ in `PR 38 <https://github.com/jantman/python-wifi-survey-heatmap/pull/38>`_ to move the UI processing to a thread, resolve duplicate point plotting issues, better handle sudo, and many other fixes.

1.2.0 (2022-06-05)
------------------

* Merge `PR 26 <https://github.com/jantman/python-wifi-survey-heatmap/pull/26>`_ to add documentation on ``Couldn't connect to accessibility bus`` error, thanks to `hnykda <https://github.com/hnykda>`__.
* Fix ``TypeError`` in ``wifi-heatmap-thresholds`` entrypoint.
* Update all Python dependencies.
* Update Docker image to latest Debian Buster.

1.1.0 (2022-04-05)
------------------

* Merge `PR 24 <https://github.com/jantman/python-wifi-survey-heatmap/pull/24>`_ to fix `Issue 22 <https://github.com/jantman/python-wifi-survey-heatmap/issues/22>`_ where APs were being plotted with SSID instead of BSSID, and therefore wifi-heatmap `--ap-names` option was not working.

1.0.0 (2022-02-19)
------------------

* Merge `PR 4 <https://github.com/jantman/python-wifi-survey-heatmap/pull/4>`_ and `PR 6 <https://github.com/jantman/python-wifi-survey-heatmap/pull/6>`_ containing a massive number of improvements by `DL6ER <https://github.com/DL6ER>`__

    * Migrate from iwconfig to iw-nl80211 (communicate directly with the kernel over sockets using PyRIC)
    * Add new optional parameter "wifi-survey -d 10" to support changing the duration of the iperf3 test runs. Often enough, 10 seconds did not result in reliable results if far away from the AP (it needs some "ramp up" time)
    * Modify wifi-heatmap to support new data in the JSON container
    * Add option "wifi-heatmap --show-points" to show points (hidden now by default as they are distracting without providing additional information on sufficiently dense measurements)
    * Add frequency_TITLE.png heatmap to show band-steering effects.
    * Add channel\_{rx,tx}\_bitrate_TITLE.png heatmap to show advertised channel capacity.
    * Add Quick Start to README (pointing more prominently towards docker) and other minor tweaks for the README
    * Use stead nlsocket for improved performance
    * Put try-except block around iwscan as it may fail with "OSError: [Errno 16] Error while scanning: Device or resource busy"
    * Show progress labels in survey circles
    * Ensure PEP8 compliance of all changes
    * RX and TX bandwidths are identical (channel-property), chose one of them (often only one value is available)
    * Reenable Download (UDP) test and use received_Mbps (instead of sent_Mbps) as measure for the most realistic bitrate
    * Add option for controling the colormap more easily
    * Finish transition from iwtools to nl80211
    * Update wifi-heatmap to read new data from JSON file
    * Don't interpolate uniform data to avoid interpolation artifacts for uniform data
    * Rename nl_scan to libnl, PEP8 formatting and allow to make a survey without an iperf3 server
    * Implement relative scaling of the window
    * Draw a red point if a survey failed. Remove failed points when starting a new survey.
    * Do not start maximized. This makes sense now that we support image scaling.
    * Change color of moving point from red to lightblue as we're now using red to indicate failure.
    * Make SERVER an optional property to easily skip iperf3 tests in case there is no suitable server. Also disable scanning by default as it takes quite some time and does not give all that much information in the end. Finally, update the README to reflect these changes
    * Add frequency graph and differentiate
    * Update Dockerfile to use patched version of libnl
    * Allow starting wifi-survey without any mandatory arguments. Missing items will be asked for in an interactive manner.
    * Store used image filename in JSON file so wifi-heatmaps works with TITLE alone. This can still be overwritten when explicitly specifying an image.
    * Add optional argument --contours N to draw N contours in the image (with inline labels)
    * Ensure survey points are drawn on top of everything else when they are used and that contour lines are omitted for uniform data.
    * Only try to plot for what we have data in the JSON file
    * Allow iperf3 server to be specified as ip:port

* `PR 15 <https://github.com/jantman/python-wifi-survey-heatmap/pull/15>`_ from `chris-reeves <https://github.com/chris-reeves>`__ - Handle missing data points
* Update Dockerfile
* Fix `Issue 17 <https://github.com/jantman/python-wifi-survey-heatmap/issues/17>`_ - AttributeError when scanning APs, caused by unset/NoneType interface_name.
* Update examples in README
* Fix `Issue 18 <https://github.com/jantman/python-wifi-survey-heatmap/issues/18>`_ - AttributeError in ``wifi-heatmap`` entrypoint - 'HeatMapGenerator' object has no attribute '_image_path'.
* Switch from using DL6ER's libnl fork to `libnl3 <https://pypi.org/project/libnl3/>`__
* Fix `Issue 19 <https://github.com/jantman/python-wifi-survey-heatmap/issues/19>`_ - BSSID option was intermittently not working. This has been fixed.
* Add command-line option to toggle libnl debug-level logging on or off (off by default).
* Fix for non-integer screen positions when scaling.

0.2.1 (2020-08-11)
------------------

* Fix heatmap generation error if ``wifi-survey`` is run with ``-S`` / ``--no-scan`` option to disable ``iwlist scan``.
* Implement ``-b`` / ``--bssid`` option to ensure that scan is against a specified BSSID.
* Implement ``--ding`` option to play a short audio file (i.e. a ding) when measurement is finished.
* ``wifi-heatmap`` - accept either title or filename as argument

0.2.0 (2020-08-09)
------------------

* Package via Docker, for easier usage without worrying about dependencies.
* Optional AP name/band annotations on heatmap.
* Add CLI option to disable iwlist scans.
* Add ability to remove survey points.
* Add ability to drag (move) survey points.

0.1.0 (2018-10-30)
------------------

* Initial release
