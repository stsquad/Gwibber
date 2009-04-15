
"""

tr.im interface for Gwibber
macno (Michele Azzolari) - 02/13/2008

"""

import urllib2

PROTOCOL_INFO = {

  "name": "tr.im",
  "version": 0.1,
  "fqdn" : "http://tr.im",
  
}

class URLShorter:

  def short(self, text):
    short = urllib2.urlopen("http://tr.im/api/trim_simple?url=%s" % urllib2.quote(text)).read().rstrip("\n")
    return short

