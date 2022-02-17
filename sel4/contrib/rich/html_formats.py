from sel4.conf import settings

CONSOLE_HTML_FORMAT = """\
<!DOCTYPE html>
<head>
<meta charset="UTF-8">
<style>
{stylesheet}
body {{
    color: {foreground};
    background-color: {background};
    max-width: """+settings.HTML_WIDTH+"""
}}
pre {{
    white-space: pre-wrap;       /* Since CSS 2.1 */
    white-space: -moz-pre-wrap;  /* Mozilla, since 1999 */
    white-space: -pre-wrap;      /* Opera 4-6 */
    white-space: -o-pre-wrap;    /* Opera 7 */
    word-wrap: break-word;       /* Internet Explorer 5.5+ */
}}
::-moz-selection {{ /* Code for Firefox */
  background: #44475a;
}}

::selection {{
  background: #44475a;
}}

</style>
</head>
<html>
<body>
    <code>
        <pre style="font-family:ui-monospace,'Fira Code',Menlo,'DejaVu Sans Mono',consolas,'Courier New',monospace">{code}</pre>
    </code>
</body>
</html>
"""