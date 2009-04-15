
"""

Cli.gs interface for Gwibber
macno (Michele Azzolari) - 02/20/2008

"""

import urllib2

PROTOCOL_INFO = {

  "name": "cli.gs",
  "version": 0.1,
  "fqdn" : "http://cli.gs",
  
}

class URLShorter:

  def short(self, text):
    short = urllib2.urlopen("http://cli.gs/api/v1/cligs/create?appid=gwibber&url=%s" % urllib2.quote(text)).read()
    return short

