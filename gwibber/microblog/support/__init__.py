#!/usr/bin/env python

"""

Microblog support methods
SegPhault (Ryan Paul) - 07/25/2008

"""

import re, os, facelib, simplejson

LINK_PARSE = re.compile("(https?://[^ )\n]+)")
IMG_CACHE_DIR = "%s/.gwibber/imgcache" % os.path.expanduser("~")

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

def image_cache(url, cache_dir = IMG_CACHE_DIR):
  if not os.path.exists(cache_dir): os.makedirs(cache_dir)
  encoded_url = base64.encodestring(url)[:-1]
  if len(encoded_url) > 200: encoded_url = encoded_url[::-1][:200]
  img_path = os.path.join(cache_dir, encoded_url).replace("\n","")

  if not os.path.exists(img_path):
    output = open(img_path, "w+")
    output.write(urllib2.urlopen(url).read())
    output.close()

  return img_path
