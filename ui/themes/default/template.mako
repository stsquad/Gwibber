<%def name="timestring(data)">
  <a href="gwibber:read/${data.message_index}">${data.time_string}</a>
  % if hasattr(data, "reply_nick") and hasattr(data, "reply"):
    <a href="${data.reply_url}">${data.reply} ${data.reply_nick}</a>
  % endif
</%def>

<%def name="bgstyle(r,g,b)">
background: -webkit-gradient(linear, left top, left 220%, from(rgba(${r}, ${g}, ${b}, 0.6)), to(black));
</%def>

<%def name="message(data)">
<div id="${data.gId}" class="message ${(hasattr(data, "username") and data.username or "") + data.protocol}"
  style="${self.bgstyle(data.bgcolor_rgb["red"], data.bgcolor_rgb["green"], data.bgcolor_rgb["blue"])}">
  <table>
    <tr>
      % if data.image:
        <td class="imagecolumn">
          <a href="${data.profile_url}">
            <div class="imgbox" title="${data.sender_nick}" style="background-image: url(${data.image});"></div>
          </a>
          <br />
          <div class="diggbox"></div>
        </td>
      % endif
      <td>
        <p class="content">
          <span class="title">${data.title if hasattr(data, "title") else data.sender}</span>
          <span class="time"> (${self.timestring(data)})</span><br />
          <span class="text">${data.html_string}</span>
        </p>
      </td>
    </tr>
  </table>
  <div class="toggledupe"><img src="add.png" /></div>
  <div class="dupes"></div>
  <div class="replybutton">
    % if hasattr(data, "can_thread"):
      <a href="gwibber:/thread/${data.message_index}"><img src="thread.png" /></a>
      <a href="gwibber:/reply/${data.message_index}"><img src="reply.png" /></a>
    % endif   
  </div>  
</div>
</%def>

<%def name="messages(msgs)">
  % for m in msgs:
    ${self.message(m)}
  % endfor
</%def>

<html>
  <head>
    <link rel="stylesheet" type="text/css" href="theme.css" />
  </head>
  <body>
    <div class="header">
    </div>
    <div class="messages">
      ${self.messages(message_store)}
    </div>
  </body>
</html>
