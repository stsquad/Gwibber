<%!
import time
%>

<%def name="timestring(data)" filter="trim">
  <a href="gwibber:read/${data.message_index}">${data.time_string}</a>
  % if hasattr(data, "reply_nick") and hasattr(data, "reply"):
    <a href="${data.reply_url}">${data.reply} ${data.reply_nick}</a>
  % endif
</%def>

<%def name="bgstyle(r,g,b, data)">
% if hasattr(data, "is_reply") and data.is_reply:
  background: -webkit-gradient(linear, left top, left 150%, from(rgba(${r}, ${g}, ${b}, 0.6)), to(white));
% elif hasattr(data, "is_private") and data.is_private:
  background: -webkit-gradient(linear, left top, left 350%, from(rgba(${r}, ${g}, ${b}, 1)), to(black));
% else:
  background: -webkit-gradient(linear, left top, left 350%, from(rgba(${r}, ${g}, ${b}, 0.1)), to(black));
% endif
</%def>

<%def name="map(lat, long, w=175, h=80, maptype='mobile')">
  <a href="http://maps.google.com/maps?q=${lat},${long}">
    <img src="http://maps.google.com/staticmap?zoom=12&size=${w}x${h}&maptype=${maptype}&markers=${lat},${long}" />
  </a>
</%def>

<%def name="comment(data)">
  <p><a href="${data.profile_url}">${data.sender}</a>: ${data.text}</p>
</%def>

<%def name="msgclass(data)">
  <% return " ".join(i for i in ["unread", "reply", "private"] \
    if hasattr(data, "is_" + i) and getattr(data, "is_" + i)) %>
</%def>

<%def name="dupes(data)">
  % if len(data.dupes) > 0:
    <div class="dupes">
      % for d in data.dupes:
        ${self.message(d)}
      % endfor
    </div>
  % endif
</%def>

<%def name="buttons(data)">
  <div class="replybutton">
    % if hasattr(data, "can_thread"):
      <a href="gwibber:thread/${data.message_index}"><img src="thread.png" /></a>
    % endif   
    <a href="gwibber:reply/${data.message_index}"><img src="reply.png" /></a>
  </div>
</%def>

<%def name="user_header_message(data)">
<div id="${data.gId}" class="message ${self.msgclass(data)}"
  style="${self.bgstyle(data.bgcolor_rgb["red"], data.bgcolor_rgb["green"], data.bgcolor_rgb["blue"], data)}">
  <center>
	  <p class="content">
			<span class="title">${data.sender}</span><br />
			% if hasattr(data, "sender_followers_count"):
        <span class="text">${data.sender_followers_count} followers</span><br />
        <span class="text">${data.sender_location}</span><br />
      % endif
			<span class="text"><a href="${data.external_profile_url}">${data.external_profile_url}</a></span>
		</p>
  </center>
</div>
</%def>

<%def name="diggbox(data)">
  <div class="diggbox">
    <p><span class="diggcount">${data.diggs}</span><br /><small>diggs</small></p>
  </div>
</%def>

<%def name="image(data)">
  <a href="${data.profile_url}">
    <div class="imgbox" title="${data.sender_nick}" style="background-image: url(${data.image});"></div>
  </a>
</%def>

<%def name="message(data)">
<div id="${data.gId}" class="message ${self.msgclass(data)}"
  style="${self.bgstyle(data.bgcolor_rgb["red"], data.bgcolor_rgb["green"], data.bgcolor_rgb["blue"], data)}">
  
  % if len(data.dupes) > 0:
    <div class="toggledupe"><img src="more.png" /></div>
  % endif

  <table>
    <tr>
      <td>
      % if data.image:
        ${self.image(data)}
        <br />
      % endif

      % if data.protocol == "digg":
        ${self.diggbox(data)}
      % endif
      </td>
      <td>
        <p class="content">
          % if hasattr(data, "sigil"):
            <span class="sigil"><img src="${data.sigil}" /></span>
          % endif
          <span class="title">${data.title if hasattr(data, "title") else data.sender}</span>
          <span class="time"> (${self.timestring(data)})</span><br />
          <span class="text">${data.html_string}</span>
        </p>
        <div class="fold">
          % if hasattr(data, "geo_position"):
            ${self.map(*data.geo_position)}<br />
          % endif

          % if hasattr(data, "liked_by"):
            <p class="likes">
              % for user in data.liked_by:
                <a href="${user[1]}">${user[0]}</a>
              % endfor
            </p> 
          % endif

          % if hasattr(data, "comments"):
            <div class="comments">
              % for c in data.comments[-3:]:
                ${comment(c)}
              % endfor
            </div>
          % endif
        </div>
      </td>
    </tr>
  </table>
  ${self.buttons(data)}
  ${self.dupes(data)}
</div>
</%def>

<html>
  <head>
    <link rel="stylesheet" type="text/css" href="theme.css" />
    <script src="jquery.js"></script>
    <script>
      $(document).ready(function() {
        $(".message").hover(
          function() {$(this).find(".replybutton").fadeIn(100)},
          function() {$(this).find(".replybutton").hide(0)});

        $(".toggledupe").show(0).unbind().toggle(
          function() {$(this).parent().find(".dupes").show(100)},
          function() {$(this).parent().find(".dupes").hide(100)});
      });
    </script>
  </head>
  <body>
    <div class="header">
    </div>
    <div class="messages">
      % for m in message_store:
        % if hasattr(m, "is_user_header"):
          ${self.user_header_message(m)}
        % else:
          % if not m.is_duplicate:
            ${self.message(m)}
          % endif
        % endif
      % endfor
    </div>
  </body>
</html>
