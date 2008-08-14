#!/usr/bin/env python

"""

Microblog support methods
SegPhault (Ryan Paul) - 07/25/2008

"""

import re, os, facelib, datetime, time

LINK_PARSE = re.compile("(https?://[^ )\n]+)")

def linkify(t):
  return LINK_PARSE.sub('<a href="\\1">\\1</a>', t)

def generate_time_string(t):
  if isinstance(t, str): return t
  d = datetime.datetime(*time.gmtime()[0:6]) - t

  if d.seconds < 60: return "%d seconds ago" % d.seconds
  elif d.seconds < (60 * 60):  return "%d minutes ago" % (d.seconds / 60)
  elif d.seconds < (60 * 60 * 2): return "1 hour ago"
  elif d.days < 1: return "%d hours ago" % (d.seconds / 60 / 60)
  elif d.days == 1: return "1 day ago"
  elif d.days > 0: return "%d days ago" % d.days
  else: return "BUG: %s" % str(d)


