
"""

Zi.ma interface for Gwibber
macno (Michele Azzolari) - 02/20/2008

"""

import urllib2

PROTOCOL_INFO = {

  "name": "zi.ma",
  "version": 0.1,
  "fqdn" : "http://zi.ma",
  
}

class URLShorter:

  def short(self, text):
    short = urllib2.urlopen("http://zi.ma/?module=ShortURL&file=Add&mode=API&url=%s" % urllib2.quote(text)).read()
    return short

