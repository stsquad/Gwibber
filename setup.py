#!/usr/bin/env python
#
# setup.py for gnuConcept

from distutils.core import setup
from DistUtilsExtra.command import *
from glob import glob

setup(name="gwibber",
      version="1.0.2",
      author="Ryan Paul",
      author_email="segphault@arstechnica.com",
      url="http://cixar.com/~segphault",
      license="GNU General Public License (GPL)",
      packages=['gwibber', 'gwibber.microblog',
          'gwibber.microblog.support', 'gwibber.urlshorter'],
      data_files=[
    ('share/gwibber/ui/', glob("ui/*.glade")),
    ('share/gwibber/ui/', glob("ui/*.png")),
    ('share/gwibber/ui/themes/default', glob("ui/themes/default/*")),
    ('share/gwibber/ui/themes/defaultsmall', glob("ui/themes/defaultsmall/*")),
    ('share/gwibber/ui/themes/funkatron', glob("ui/themes/funkatron/*")),
    ('share/gwibber/ui/themes/shine', glob("ui/themes/shine/*")),
    ('share/gwibber/ui', ['ui/progress.gif']),
    ('share/gwibber/ui', ['ui/gwibber.svg']),
    ('share/pixmaps', ['ui/gwibber.svg'])
    ],
      scripts=['bin/gwibber'],
      cmdclass = { "build" :  build_extra.build_extra,
                   "build_i18n" :  build_i18n.build_i18n,
                   "build_help" :  build_help.build_help,
                   "build_icons" :  build_icons.build_icons
                 }
)
