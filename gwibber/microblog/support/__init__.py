
"""

Microblog support methods
SegPhault (Ryan Paul) - 07/25/2008

"""

import re, os, facelib, locale, mx.DateTime

def parse_time(t):

  loc = locale.getlocale(locale.LC_TIME)
  locale.setlocale(locale.LC_TIME, 'C')
  result = mx.DateTime.Parser.DateTimeFromString(t)
  locale.setlocale(locale.LC_TIME, loc)
  return result 

LINK_PARSE = re.compile("(^(?:(?![^:@]+:[^:@\/]*@)([^:\/?#.]+):)?(?:\/\/)?((?:(([^:@]*):?([^:@]*))?@)?([^:\/?#]*)(?::(\d*))?)(((\/(?:[^?#](?![^?#\/]*\.[^?#\/.]+(?:[?#]|$)))*\/?)?([^?#\/]*))(?:\?([^#]*))?(?:#(.*))?))")
    
def linkify(t):
  return LINK_PARSE.sub('<a href="\\1">\\1</a>', t)

def highlight_search_results(t, q):
  pattern = re.compile(re.escape(q), re.I)
  return re.sub(pattern, ' <span class="searchresult">&nbsp;%s </span> ' % q, t)

def xml_escape(t):
  return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def generate_time_string(t):
  if isinstance(t, str): return t

  d = mx.DateTime.gmt() - t

  if d.seconds < 60: return "%d seconds ago" % d.seconds
  elif d.seconds < (60 * 60):  return "%d minutes ago" % (d.seconds / 60)
  elif d.seconds < (60 * 60 * 2): return "1 hour ago"
  elif d.days < 1: return "%d hours ago" % (d.seconds / 60 / 60)
  elif d.days == 1: return "1 day ago"
  elif d.days > 0: return "%d days ago" % d.days
  else: return "BUG: %s" % str(d)



