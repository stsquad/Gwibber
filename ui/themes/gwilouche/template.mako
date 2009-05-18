<%namespace name="base" file="base.mako">
  <%def name="msgstyle(data)">
    background: -webkit-gradient(linear, left top,
      left ${"150%" if hasattr(data, "is_reply") and data.is_reply else "350%"},
      from(rgba(${data.color.rgb}, 0.1)),
      to(${"white" if hasattr(data, "is_reply") and data.is_reply else "black"}));
  </%def>
</%namespace>

<html>
  <head>
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
    <style>
      <%include file="theme.css" /> 
    </style>
  </head>
  <body>
    ${base.messages(message_store)}
  </body>
</html>
