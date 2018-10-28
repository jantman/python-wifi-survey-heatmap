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
import os
import wx

from wifi_survey_heatmap.collector import Collector

FORMAT = "[%(asctime)s %(levelname)s] %(message)s"
logging.basicConfig(level=logging.WARNING, format=FORMAT)
logger = logging.getLogger()


class FloorplanPanel(wx.Panel):

    def __init__(self, parent, img_path):
        super(FloorplanPanel, self).__init__(self, parent=parent)
        self.img_path = img_path


class MainFrame(wx.Frame):

    def __init__(self, img_path, *args, **kw):
        super(MainFrame, self).__init__(*args, **kw)
        self.pnl = wx.Panel(self)
        self.img_path = img_path
        """
        self.bitmap = wx.Bitmap(img_path)
        self.canvas = wx.MemoryDC(self.bitmap)
        text = 'whatever'
        w, h = self.canvas.GetSize()
        tw, th = self.canvas.GetTextExtent(text)
        self.canvas.DrawText(text, (w - tw) / 2, (h - th) / 2)
        self.static_bitmap = wx.StaticBitmap(self, -1, self.bitmap)
        """

        # create a menu bar
        self.makeMenuBar()

        # and a status bar
        self.CreateStatusBar()
        self.SetStatusText("Welcome to wxPython!")
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.pnl.Bind(wx.EVT_LEFT_UP, self.onClick)

    def _set_background(self):
        self.dc = wx.ClientDC(self.pnl)
        bmp = wx.Bitmap(self.img_path)
        self.dc.DrawBitmap(bmp, 500, 500)

    def OnEraseBackground(self, evt):
        """
        Add a picture to the background
        """
        # yanked from ColourDB.py
        dc = evt.GetDC()

        if not dc:
            dc = wx.ClientDC(self.pnl)
            rect = self.pnl.GetUpdateRegion().GetBox()
            dc.SetClippingRect(rect)
        dc.Clear()
        bmp = wx.Bitmap(self.img_path)
        dc.DrawBitmap(bmp, 0, 0)

    def onClick(self, event):
        pos = event.GetPosition()
        print('Got click at: %s' % pos)
        print('Frame size: %s; panel size: %s' % (self.GetSize(), self.pnl.GetSize()))
        self.SetStatusText('Got click.')
        """
        self.canvas.SetBrush(wx.Brush(wx.Colour(255, 0, 0)))
        self.canvas.DrawCircle(pos[0], pos[1], 50)
        self.static_bitmap = wx.StaticBitmap(self, -1, self.bitmap)
        """
        self.dc = wx.ClientDC(self.pnl)
        self.dc.SetBrush(wx.Brush('BLUE', wx.SOLID))
        x, y = pos
        self.dc.DrawCircle(x, y, 3)

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
    p = argparse.ArgumentParser(description='Sample python script skeleton.')
    p.add_argument('-v', '--verbose', dest='verbose', action='count', default=0,
                   help='verbose output. specify twice for debug-level output.')
    p.add_argument('INTERFACE', type=str, help='Wireless interface name')
    p.add_argument('SERVER', type=str, help='iperf3 server IP or hostname')
    p.add_argument('IMAGE', type=str, help='Path to background image')
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
    frm = MainFrame(args.IMAGE, None, title='wifi-survey')
    frm.Show()
    frm.Maximize(True)
    frm.SetStatusText('%s' % frm.pnl.GetSize())
    #frm._set_background()
    app.MainLoop()


if __name__ == '__main__':
    main()
