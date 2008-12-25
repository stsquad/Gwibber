#!/usr/bin/env python
#
# setup.py for gnuConcept

import subprocess
from distutils.core import setup
from DistUtilsExtra.command import *
from glob import glob

# Need this to create .desktop file otherwise it will not find it
# during install
cmd = "intltool-merge -d -u po/ gwibber.desktop.in gwibber.desktop".split(" ")
proc = subprocess.Popen(cmd)
proc.wait()

setup(name="gwibber",
      version="0.7",
      author="Ryan Paul",
      author_email="segphault@arstechnica.com",
      url="http://cixar.com/~segphault",
      license="GNU General Public License (GPL)",
      packages=['gwibber', 'gwibber.microblog', 'gwibber.microblog.support'],
      data_files=[
    ('share/gwibber/ui/', glob("ui/*.glade")),
    ('share/gwibber/ui/', glob("ui/*.png")),
    ('share/gwibber/ui/themes/default', glob("ui/themes/default/*")),
    ('share/gwibber/ui/themes/shine', glob("ui/themes/shine/*")),
    ('share/gwibber/ui', ['ui/progress.gif']),
    ('share/gwibber/ui', ['ui/gwibber.svg']),
    ('share/pixmaps', ['ui/gwibber.svg']),
    ('share/applications/',['gwibber.desktop'])
    ],
      scripts=['bin/gwibber'],
      cmdclass = { "build" :  build_extra.build_extra,
                   "build_i18n" :  build_i18n.build_i18n,
                   "build_help" :  build_help.build_help,
                   "build_icons" :  build_icons.build_icons
                 }
)
