<%namespace name="base" file="base.mako">
  <%def name="msgstyle(data)">
    background: -webkit-gradient(linear, left top, left 220%, from(rgba(
      ${data.bgcolor_rgb["red"]},
      ${data.bgcolor_rgb["green"]},
      ${data.bgcolor_rgb["blue"]}, 0.6)), to(black));
  </%def>
</%namespace>

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
    ${base.messages(message_store)}
  </body>
</html>
