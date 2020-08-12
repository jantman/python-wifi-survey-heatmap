Changelog
=========

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
