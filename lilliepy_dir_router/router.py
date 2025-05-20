import os
import re
import importlib.util
from pathlib import Path
from reactpy_router import route, browser_router, use_params, use_search_params
from reactpy import component, vdom_to_html, html_to_vdom
from reactpy.backend.flask import configure, serve_development_app
from flask import Flask, request, jsonify, send_from_directory
from simple_websocket.aiows import asyncio
from flask_cors import CORS

api_server = Flask(__name__)
CORS(api_server)


def get_parents_until_specific_folder(file_path, target_folder):
    file_path = Path(file_path).resolve()

    parent_folders = []

    while file_path != file_path.parent:
        file_path, current_folder = file_path.parent, file_path.name
        parent_folders.append(current_folder)

        if current_folder == target_folder:
            parent_folders.reverse()
            parent_folders.remove("+root.x.py")
            break

    parent_folders = [
        folder for folder in parent_folders
        if not (folder.startswith('(') and folder.endswith(')'))
    ]

    if parent_folders and parent_folders[-1] == target_folder:
        return "/"

    parent_folders.remove(f"{target_folder}")
    return "/" + "/".join(parent_folders)


def FileRouter(route_path, verbose=False):
    path = os.path.join(os.getcwd(), route_path)

    if verbose:
        print(path)

    routes = []
    silent = re.compile(r'\([^\)]*\)')
    global layout
    layout = None
    not_found_route = None
    error_route = None
    err = None
    public_folder_path = None

    for root, dirs, files in os.walk(path, True):
        relative_path = os.path.relpath(root, start=path)

        if relative_path == ".":
            relative_path = ""

        # Handle silent routes (grouping routes)
        if silent.search(relative_path):
            relative_path = ""

        # Handles Asset Routes
        if "+public" in relative_path:
            public_folder_path = os.path.join(root)
            if public_folder_path:

                @api_server.route("/public/<path:filename>")
                def serve_public_file(filename):
                    return send_from_directory(public_folder_path, filename)

        for names in files:

            #Handle non .x.py files
            if not names.endswith(".x.py"):
                continue

            # Handle +root.x.py (main route)
            if names == "+root.x.py":
                module_path = os.path.join(root, names)
                root_route = get_parents_until_specific_folder(
                    module_path, route_path)
                module_name = module_path.replace(os.getcwd() + '/',
                                                  '').replace('/',
                                                              '.').replace(
                                                                  '.x.py', '')
                spec = importlib.util.spec_from_file_location(
                    module_name, module_path)
                package = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(package)

                func_name = names.replace(".x.py", "").replace("+", "")
                func = getattr(package, func_name, None)

                if func:
                    r = route(f"{root_route}", func())
                    routes.append(r)
                else:
                    print(f"Function '{func_name}' not found in {names}")

            # Handle +not_found.x.py (404 route)
            elif names == "+not_found.x.py":
                module_path = os.path.join(root, names)
                module_name = module_path.replace(os.getcwd() + '/',
                                                  '').replace('/',
                                                              '.').replace(
                                                                  '.x.py', '')
                spec = importlib.util.spec_from_file_location(
                    module_name, module_path)
                package = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(package)

                func_name = names.replace(".x.py", "").replace("+", "")
                func_n = getattr(package, func_name, None)

                if func_n:
                    not_found_route = func_n
                else:
                    print(f"Function '{func_name}' not found in {names}")

            # Handle +error.x.py
            elif names == "+error.x.py":
                module_path = os.path.join(root, names)
                module_name = module_path.replace(os.getcwd() + '/',
                                                  '').replace('/',
                                                              '.').replace(
                                                                  '.x.py', '')
                spec = importlib.util.spec_from_file_location(
                    module_name, module_path)
                package = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(package)

                func_name = names.replace(".x.py", "").replace("+", "")
                func = getattr(package, func_name, None)
                errorCode = getattr(package, 'errorCode', None)

                if func and errorCode:
                    error_route = func
                    err = errorCode

            # Handle slug routes (with dynamic parameters)
            elif "+[" and "]" in names:
                module_path = os.path.join(root, names)
                module_name = module_path.replace(
                    os.getcwd() + '/',
                    '').replace('/',
                                '.').replace('.x.py',
                                             '').replace("+[",
                                                         "").replace("]", "")

                spec = importlib.util.spec_from_file_location(
                    module_name, module_path)
                package = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(package)

                func_name = names.replace(
                    ".x.py", "").removeprefix("+[").removesuffix("]")
                function = getattr(package, func_name, None)

                route_path_clean = os.path.join(
                    relative_path,
                    names.replace('.x.py', '').replace('_', '-')).replace(
                        "+[", "{").replace("]", "}")
                route_path_cleaner = route_path_clean.replace("\\", "/")

                if function:

                    @component
                    def slug_shot():
                        vals = use_params()
                        return function(params=vals)

                    r = route(f"/{route_path_cleaner}", slug_shot())
                    routes.append(r)
                else:
                    print(f"Function '{func_name}' not found in {names}, slug")

            # Handle slug routes (with search parameters)
            elif "+{" and "}" in names:  # e.g: /age/age?age=18
                module_path2 = os.path.join(root, names)
                module_name2 = module_path2.replace(
                    os.getcwd() + '/',
                    '').replace('/',
                                '.').replace('.x.py',
                                             '').replace("+{",
                                                         "").replace("}", "")

                spec2 = importlib.util.spec_from_file_location(
                    module_name2, module_path2)
                package2 = importlib.util.module_from_spec(spec2)
                spec2.loader.exec_module(package2)

                func_name2 = names.replace(
                    ".x.py", "").removeprefix("+{").removesuffix("}")
                function2 = getattr(package2, func_name2, None)

                route_path_clean2 = os.path.join(
                    relative_path,
                    names.replace('.x.py',
                                  '').replace('_', '-')).replace("+{", "{")
                route_path_cleaner = route_path_clean2.replace("\\", "/")

                if function2:

                    @component
                    def dy():
                        val = use_search_params()
                        return function2(params=val)

                    ro = route(f"/{route_path_cleaner}", dy())
                    routes.append(ro)
                else:
                    print(
                        f"Function '{func_name2}' not found in {names}, slug")

            # Handles api routes
            elif ".api.x.py" in names:
                module_path = os.path.join(root, names)
                module_name = module_path.replace(os.getcwd() + '/',
                                                  '').replace('/',
                                                              '.').replace(
                                                                  '.x.py', '')

                spec = importlib.util.spec_from_file_location(
                    module_name, module_path)
                package = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(package)

                handler = getattr(package, 'handler', None)
                method = getattr(package, 'method', None)

                if handler and method:
                    route_path_clean = os.path.join(
                        relative_path,
                        names.replace('.api.x.py', '').replace('_', '-'))
                    route_path_clean = route_path_clean.replace("\\", "/")

                    @api_server.route(f"/{route_path_clean}", methods=method)
                    def api_route():
                        return handler(request, jsonify)

            # Handles server components
            elif ".server.x.py" in names:
                module_path = os.path.join(root, names)
                module_name = module_path.replace(
                    os.getcwd() + '/',
                    '').replace('/',
                                '.').replace('.server.x.py',
                                             '').replace("+[",
                                                         "").replace("]", "")
                spec = importlib.util.spec_from_file_location(
                    module_name, module_path)

                package = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(package)

                func_name = names.replace(".server.x.py", "")
                func_s = getattr(package, func_name, None)

                if func_s:
                    route_path_clean = os.path.join(
                        relative_path,
                        names.replace('.server.x.py', '').replace('_', '-'))
                    route_path_clean = route_path_clean.replace("\\", "/")

                    def create_dehydrate(func_s):

                        @component
                        def dehydrate():
                            try:
                                rendered_vdom = func_s().render()
                                rendered_html = vdom_to_html(rendered_vdom)
                                return html_to_vdom(rendered_html)
                            except Exception as e:
                                return html_to_vdom(
                                    f"<h1>Error rendering component: {str(e)}</h1>"
                                )

                        return dehydrate

                    unique_dehydrate = create_dehydrate(func_s)
                    r = route(f"/{route_path_clean}", unique_dehydrate())
                    routes.append(r)
                else:
                    print(
                        f"Function '{func_name}' not found in {names}, server")

            # Handles +layout.x.py
            elif "+layout.x.py" in names:
                module_path = os.path.join(root, names)
                module_name = module_path.replace(os.getcwd() + '/',
                                                  '').replace('/',
                                                              '.').replace(
                                                                  '.x.py', '')
                spec = importlib.util.spec_from_file_location(
                    module_name, module_path)
                package = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(package)

                func_name = names.replace(".x.py", "").replace("+", "")
                func = getattr(package, func_name, None)

                if func:
                    layout = func

            # Handle normal routes
            else:
                module_path = os.path.join(root, names)
                module_name = module_path.replace(os.getcwd() + '/',
                                                  '').replace('/',
                                                              '.').replace(
                                                                  '.x.py', '')

                spec = importlib.util.spec_from_file_location(
                    module_name, module_path)
                package = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(package)

                func_name = names.replace(".x.py", "")
                func = getattr(package, func_name, None)

                if func:
                    route_path_clean = os.path.join(
                        relative_path,
                        names.replace('.x.py', '').replace('_', '-'))
                    route_path_clean = route_path_clean.replace("\\", "/")

                    r = route(f"/{route_path_clean}", func())
                    routes.append(r)
                else:
                    print(f"Function '{func_name}' not found in {names}")

    if not_found_route:

        @component
        def not_found():
            return not_found_route()

        routes.append(route("{404:any}", not_found()))

    if error_route and err:

        @component
        def error():
            return error_route()

        routes.append(route("{" + str(err) + "}" + ":any", error()))

    if routes:

        if layout:
            if verbose:
                print(*routes)

                @component
                def root():
                    return layout(browser_router(*routes))

                configure(api_server, root)
                asyncio.run(serve_development_app(api_server, "0.0.0.0", 8080))
            else:

                @component
                def root():
                    return layout(browser_router(*routes))

                configure(api_server, root)
                asyncio.run(serve_development_app(api_server, "0.0.0.0", 8080))
        else:
            if verbose:
                print(*routes)

                @component
                def root():
                    return browser_router(*routes)

                configure(api_server, root)
                asyncio.run(serve_development_app(api_server, "0.0.0.0", 8080))
            else:

                @component
                def root():
                    return browser_router(*routes)

                configure(api_server, root)
                asyncio.run(serve_development_app(api_server, "0.0.0.0", 8080))
