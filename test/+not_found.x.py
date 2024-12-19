from reactpy import component, html


@component
def not_found():
  return html.h1("Not found")
