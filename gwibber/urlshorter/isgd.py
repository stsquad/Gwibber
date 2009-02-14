
"""

TinyURL.com interface for Gwibber
macno (Michele Azzolari) - 02/13/2008

"""

import urllib2

PROTOCOL_INFO = {

  "name": "is.gd",
  "version": 0.1,
  "fqdn" : "http://is.gd",
  
}

class URLShorter:

  def short(self, text):
    short = urllib2.urlopen("http://is.gd/api.php?longurl=%s" % urllib2.quote(text)).read()
    return short

