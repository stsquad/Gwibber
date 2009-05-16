<%def name="map(lat, long, w=175, h=80, maptype='mobile')">
  <a href="http://maps.google.com/maps?q=${lat},${long}">
    <img src="http://maps.google.com/staticmap?zoom=12&size=${w}x${h}&maptype=${maptype}&markers=${lat},${long}" />
  </a>
</%def>

<%def name="comment(data)">
  <p><a href="${data.profile_url}">${data.sender}</a>: ${data.text}</p>
</%def>

<%def name="msgclass(data, classes=['unread', 'reply', 'private'])">
  <% return " ".join(i for i in classes \
    if hasattr(data, "is_" + i) and getattr(data, "is_" + i)) %>
</%def>

<%def name="msgstyle(data)" filter="trim">
</%def>

<%def name="geo_position(data)">
  <div class="position">
    ${self.map(*data.geo_position)}
  </div>
</%def>

<%def name="liked_by(data)">
  <p class="likes">
    % for user in data.liked_by:
      <a href="${user[1]}">${user[0]}</a>
    % endfor
  </p> 
</%def>

<%def name="comments(data)">
  <div class="comments">
    % for c in data.comments[-3:]:
      ${self.comment(c)}
    % endfor
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

<%def name="fold(data, ops=['geo_position', 'liked_by', 'comments'])">
  <div class="fold">
    % for o in ops:
      % if hasattr(data, o):
        ${getattr(self, o)(data)}
      % endif
    % endfor
  </div>
</%def>
  
<%def name="timestring(data)" filter="trim">
  <a href="gwibber:read/${data.message_index}">${data.time_string}</a>
  % if hasattr(data, "reply_nick") and data.reply_nick:
    <a href="${data.reply_url}">${_("in reply to")} ${data.reply_nick}</a>
  % endif
</%def>

<%def name="title(data)">
  <span class="title">${data.title if hasattr(data, "title") else data.sender}</span>
</%def>

<%def name="sigil(data)">
  % if hasattr(data, "sigil"):
    <span class="sigil"><img src="${data.sigil}" /></span>
  % endif
</%def>

<%def name="content(data)">
  <p class="content">
    ${sigil(data)}   
    ${title(data)}
    <span class="time"> (${timestring(data)})</span><br />
    <span class="text">${data.html_string}</span>
  </p>
</%def>

<%def name="sidebar(data)">
  % if data.image:
    ${self.image(data)}
    <br />
  % endif

  % if data.protocol == "digg":
    ${self.diggbox(data)}
  % endif
</%def>

<%def name="messagebox(data)">
  <div id="${data.gId}" style="${self.msgstyle(data)}" class="message ${self.msgclass(data)}">
    ${caller.body()}
  </div>
</%def>

<%def name="user_header_message(data)">
  <%call expr="messagebox(data)">
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
  </%call>
</%def>

<%def name="toggledupe(data)">
  % if len(data.dupes) > 0:
    <div class="toggledupe"><img src="more.png" /></div>
  % endif
</%def>

<%def name="message(data)">
  <%call expr="messagebox(data)">
    ${toggledupe(data)}   
    <table>
      <tr>
        <td>
          ${self.sidebar(data)}
        </td>
        <td>
          ${self.content(data)}
          ${self.fold(data)}
        </td>
      </tr>
    </table>
    
    ${self.buttons(data)}
    ${self.dupes(data)}
  </%call>
</%def>

<%def name="messages(data)">
  <div class="header">
  </div>
  <div class="messages">
    % for m in data:
      % if hasattr(m, "is_user_header"):
        ${self.user_header_message(m)}
      % else:
        % if not m.is_duplicate:
          ${self.message(m)}
        % endif
      % endif
    % endfor
  </div>
</%def>
