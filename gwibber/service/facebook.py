#!/usr/bin/env python

"""
Facebook Status Update
SegPhault (Ryan Paul) - 05/22/2007

Based on code by Rudolf Olah
http://web2point0.groups.vox.com/library/post/6a00d414257d066a4700cd972544814cd5.html
"""

import urllib2, re, sys

class Client:
  def __init__(self, user, passwd):
    self.user = user
    self.passwd = passwd

  def update_status(self, message):
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
    urllib2.install_opener(opener)

    urllib2.urlopen(urllib2.Request(
      "https://login.facebook.com/login.php?m&amp;next=http%3A%2F%2Fm.facebook.com%2Fhome.php",
      "email=%s&pass=%s&login=Login" % (self.user, self.passwd)))

    connection = urllib2.urlopen("http://m.facebook.com/")
    form_id = re.findall('name="post_form_id" value="(\w+)"', connection.read())[0]

    opener.open(urllib2.Request("http://m.facebook.com/home.php",
      "post_form_id=%s&status=%s&update=Update" % (form_id, message)))
