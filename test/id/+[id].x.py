from reactpy import html, component


@component
def id(params):
    return html.div([
        html.h1(f"Dynamic Content for ID: {params['id']}"),
        html.p("This page dynamically renders content based on the slug."),
    ])
