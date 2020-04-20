"""
The latest version of this package is available at:
<http://github.com/jantman/wifi-survey-heatmap>

##################################################################################
Copyright 2017 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

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

import sys
import argparse
import logging
import wx
import json
import os

from wifi_survey_heatmap.collector import Collector

FORMAT = "[%(asctime)s %(levelname)s] %(message)s"
logging.basicConfig(level=logging.WARNING, format=FORMAT)
logger = logging.getLogger()


RESULT_FIELDS = [
    'error',
    'time',
    'timesecs',
    'protocol',
    'num_streams',
    'blksize',
    'omit',
    'duration',
    'sent_bytes',
    'sent_bps',
    'received_bytes',
    'received_bps',
    'sent_kbps',
    'sent_Mbps',
    'sent_kB_s',
    'sent_MB_s',
    'received_kbps',
    'received_Mbps',
    'received_kB_s',
    'received_MB_s',
    'retransmits',
    'bytes',
    'bps',
    'jitter_ms',
    'kbps',
    'Mbps',
    'kB_s',
    'MB_s',
    'packets',
    'lost_packets',
    'lost_percent',
    'seconds'
]


class SurveyPoint(object):

    def __init__(self, parent, x, y):
        self.parent = parent
        self.x = x
        self.y = y
        self.is_finished = False
        self.is_failed = False
        self.result = {}

    def set_result(self, res):
        self.result = res

    @property
    def as_dict(self):
        return {
            'x': self.x,
            'y': self.y,
            'result': self.result,
            'failed': self.is_failed
        }

    def set_is_failed(self):
        self.is_failed = True

    def set_is_finished(self):
        self.is_finished = True

    def draw(self, dc):
        color = 'green'
        if not self.is_finished:
            color = 'yellow'
        if self.is_failed:
            color = 'red'
        dc.SetBrush(wx.Brush(color, wx.SOLID))

        window_size = dc.GetSize()
        relposx = self.x * window_size[0]
        relposy = self.y * window_size[1]

        dc.DrawCircle(relposx, relposy, 20)


class SafeEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, type(b'')):
            return obj.decode()
        return json.JSONEncoder.default(self, obj)


class FloorplanPanel(wx.Panel):

    def __init__(self, parent):
        super(FloorplanPanel, self).__init__(parent)
        self.parent = parent
        self.img_path = parent.img_path
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.Bind(wx.EVT_LEFT_UP, self.onClick)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.survey_points = []
        self.data_filename = '%s.json' % self.parent.survey_title
        if os.path.exists(self.data_filename):
            self._load_file(self.data_filename)
        self.collector = Collector(self.parent.interface, self.parent.server)
        self.parent.SetStatusText("Ready.")

    def _load_file(self, fpath):
        with open(fpath, 'r') as fh:
            raw = fh.read()
        data = json.loads(raw)
        for point in data:
            p = SurveyPoint(self, point['x'], point['y'])
            p.set_result(point['result'])
            p.set_is_finished()
            self.survey_points.append(p)

    def OnEraseBackground(self, evt):
        """Add a picture to the background"""
        dc = evt.GetDC()
        if not dc:
            dc = wx.ClientDC(self)
            rect = self.GetUpdateRegion().GetBox()
            dc.SetClippingRect(rect)
        dc.Clear()
        
        bmp = wx.Bitmap(self.img_path)
        window_size = self.GetSize()
        image = wx.Bitmap.ConvertToImage(bmp)
        image = image.Scale(window_size[0], window_size[1], wx.IMAGE_QUALITY_HIGH)
        bmp = wx.Bitmap(image)

        dc.DrawBitmap(bmp, 0, 0)

    def onClick(self, event):
        pos = event.GetPosition()
        self.parent.SetStatusText('Got click at: %s' % pos)
        window_size = self.GetSize()
        relposx = (pos[0] / window_size[0])
        relposy = (pos[1] / window_size[1])
        self.survey_points.append(SurveyPoint(self, relposx, relposy))
        
        self.Refresh()
        res = {}
        count = 0
        for protoname, udp in {'tcp': False, 'udp': True}.items():
            for suffix, reverse in {'': False, '-reverse': True}.items():
                if udp and reverse:
                    logger.warning('Skipping reverse UDP; always fails')
                    continue
                count += 1
                tmp = self.run_iperf(count, udp, reverse)
                if tmp is None:
                    # bail out; abort this survey point
                    del self.survey_points[-1]
                    self.parent.SetStatusText('Aborted; ready to retry...')
                    self.Refresh()
                    return
                # else success
                res['%s%s' % (protoname, suffix)] = {
                    x: getattr(tmp, x, None) for x in RESULT_FIELDS
                }
        self.parent.SetStatusText('Running iwconfig...')
        self.Refresh()
        res['iwconfig'] = self.collector.run_iwconfig()
        self.parent.SetStatusText('Running iwscan...')
        self.Refresh()
        res['iwscan'] = self.collector.run_iwscan()
        self.survey_points[-1].set_result(res)
        self.survey_points[-1].set_is_finished()
        self.parent.SetStatusText(
            'Saving to: %s' % self.data_filename
        )
        self.Refresh()
        res = json.dumps(
            [x.as_dict for x in self.survey_points],
            cls=SafeEncoder
        )
        with open(self.data_filename, 'w') as fh:
            fh.write(res)
        self.parent.SetStatusText(
            'Saved to %s; ready...' % self.data_filename
        )
        self.Refresh()

    def warn(self, message, caption='Warning!'):
        dlg = wx.MessageDialog(self.parent, message, caption,
                               wx.OK | wx.ICON_WARNING)
        dlg.ShowModal()
        dlg.Destroy()

    def YesNo(self, question, caption='Yes or no?'):
        dlg = wx.MessageDialog(self.parent, question, caption,
                               wx.YES_NO | wx.ICON_QUESTION)
        result = dlg.ShowModal() == wx.ID_YES
        dlg.Destroy()
        return result

    def run_iperf(self, count, udp, reverse):
        self.parent.SetStatusText(
            'Running iperf %d/3 (udp=%s, reverse=%s)' % (count, udp, reverse)
        )
        self.Refresh()
        tmp = self.collector.run_iperf(udp, reverse)
        if tmp.error is None:
            return tmp
        # else this is an error
        if tmp.error.startswith('unable to connect to server'):
            self.warn(
                'ERROR: Unable to connect to iperf server. Aborting.'
            )
            return None
        if self.YesNo('iperf error: %s. Retry?' % tmp.error):
            self.Refresh()
            return self.run_iperf(count, udp, reverse)
        # else bail out
        return tmp

    def on_paint(self, event=None):
        dc = wx.ClientDC(self)
        for p in self.survey_points:
            p.draw(dc)


class MainFrame(wx.Frame):

    def __init__(
            self, img_path, interface, server, survey_title,
            *args, **kw
    ):
        super(MainFrame, self).__init__(*args, **kw)
        self.img_path = img_path
        self.interface = interface
        self.server = server
        self.survey_title = survey_title
        self.CreateStatusBar()
        self.pnl = FloorplanPanel(self)
        self.makeMenuBar()

    def makeMenuBar(self):
        fileMenu = wx.Menu()
        fileMenu.AppendSeparator()
        exitItem = fileMenu.Append(wx.ID_EXIT)
        menuBar = wx.MenuBar()
        menuBar.Append(fileMenu, "&File")
        self.SetMenuBar(menuBar)
        self.Bind(wx.EVT_MENU, self.OnExit,  exitItem)

    def OnExit(self, event):
        """Close the frame, terminating the application."""
        self.Close(True)


def parse_args(argv):
    """
    parse arguments/options

    this uses the new argparse module instead of optparse
    see: <https://docs.python.org/2/library/argparse.html>
    """
    p = argparse.ArgumentParser(description='wifi survey data collection UI')
    p.add_argument('-v', '--verbose', dest='verbose', action='count', default=0,
                   help='verbose output. specify twice for debug-level output.')
    p.add_argument('INTERFACE', type=str, help='Wireless interface name')
    p.add_argument('SERVER', type=str, help='iperf3 server IP or hostname')
    p.add_argument('IMAGE', type=str, help='Path to background image')
    p.add_argument(
        'TITLE', type=str, help='Title for survey (and data filename)'
    )
    args = p.parse_args(argv)
    return args


def set_log_info():
    """set logger level to INFO"""
    set_log_level_format(logging.INFO,
                         '%(asctime)s %(levelname)s:%(name)s:%(message)s')


def set_log_debug():
    """set logger level to DEBUG, and debug-level output format"""
    set_log_level_format(
        logging.DEBUG,
        "%(asctime)s [%(levelname)s %(filename)s:%(lineno)s - "
        "%(name)s.%(funcName)s() ] %(message)s"
    )


def set_log_level_format(level, format):
    """
    Set logger level and format.

    :param level: logging level; see the :py:mod:`logging` constants.
    :type level: int
    :param format: logging formatter format string
    :type format: str
    """
    formatter = logging.Formatter(fmt=format)
    logger.handlers[0].setFormatter(formatter)
    logger.setLevel(level)


def main():
    args = parse_args(sys.argv[1:])

    # set logging level
    if args.verbose > 1:
        set_log_debug()
    elif args.verbose == 1:
        set_log_info()

    app = wx.App()
    frm = MainFrame(
        args.IMAGE, args.INTERFACE, args.SERVER, args.TITLE,
        None, title='wifi-survey: %s' % args.TITLE
    )
    frm.Show()
    frm.Maximize(True)
    frm.SetStatusText('%s' % frm.pnl.GetSize())
    app.MainLoop()


if __name__ == '__main__':
    main()
