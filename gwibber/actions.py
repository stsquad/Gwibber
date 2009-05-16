import gtk, microblog, gintegration

class MessageAction:
  icon = None
  label = None

  @classmethod
  def get_icon_path(self, size=16):
    theme = gtk.icon_theme_get_default()
    finfo = theme.lookup_icon(self.icon, size, 0)
    return finfo.get_filename() if finfo else None

  @classmethod
  def include(self, client, msg):
    return True

  @classmethod
  def action(self, w, client, msg):
    pass

class Reply(MessageAction):
  icon = "mail_reply"
  label = "_Reply"

  @classmethod
  def include(self, client, msg):
    return msg.account.supports(microblog.can.REPLY)

  @classmethod
  def action(self, w, client, msg):
    client.reply(msg)

class Retweet(MessageAction):
  icon = "mail_forward"
  label = "R_etweet"

class Like(MessageAction):
  icon = "bookmark_add"
  label = "_Like this message"

class Tomboy(MessageAction):
  icon = "tomboy"
  label = "Save to _Tomboy"

  @classmethod
  def action(self, w, client, msg):
    gintegration.create_tomboy_note(
      "%s message from %s at %s\n\n%s" % (
        msg.account["protocol"].capitalize(),
        msg.sender, msg.time, msg.text))

  @classmethod
  def include(self, client, msg):
    return gintegration.service_is_running("org.gnome.Tomboy")

MENU_ITEMS = [Reply, Retweet, Like, Tomboy]
