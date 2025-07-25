import os
import re
import importlib.util
from pathlib import Path
from reactpy_router import navigate, route, browser_router, use_params, use_search_params
from reactpy import component, vdom_to_html, html_to_vdom
from reactpy.backend.flask import configure, serve_development_app, use_request
from flask import Flask, request, jsonify, send_from_directory, make_response
from simple_websocket.aiows import asyncio
from flask_cors import CORS
import markdown

api_server = Flask(__name__)
CORS(api_server)

global parallel_routes
parallel_routes = {}


def use_parallel(func_name):
    for name in parallel_routes.keys():
        if name == func_name:
            return parallel_routes[name]()


def find_nearest_markdown(func_name, start_dir, route_root, markdown_files,
                          not_found):
    local_md_path = os.path.relpath(os.path.join(start_dir,
                                                 func_name + ".x.md"),
                                    start=route_root).replace("\\", "/")

    if local_md_path in markdown_files:
        return markdown_files[local_md_path]

    current_dir = Path(start_dir).resolve()
    route_root = Path(route_root).resolve()

    while True:
        markdown_folder = current_dir / "+markdown"
        if markdown_folder.exists() and markdown_folder.is_dir():
            md_file_path = os.path.relpath(
                markdown_folder / (func_name + ".x.md"),
                start=route_root).replace("\\", "/")

            if md_file_path in markdown_files:
                return markdown_files[md_file_path]

        if current_dir == route_root:
            break

        current_dir = current_dir.parent

    return not_found()


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
    private = re.compile(r'(?:^|/)\+_[^/]+')
    global layout
    layout = None
    not_found_route = None
    error_route = None
    err = None
    public_folder_path = None
    markdown_files = {}

    #  Collect all markdown files
    for root, dirs, files in os.walk(path, True):
        for md_file in Path(root).glob("*.x.md"):
            relative_md_path = os.path.relpath(md_file,
                                               start=path).replace("\\", "/")
            content = md_file.read_text(encoding="utf-8")
            markdown_files[relative_md_path] = markdown.markdown(content)

    for root, dirs, files in os.walk(path, True):
        relative_path = os.path.relpath(root, start=path)

        if relative_path == ".":
            relative_path = ""

        # handle private routes
        if private.search(relative_path):
            continue

        # Modify `dirs` to prevent descending into private subdirs
        dirs[:] = [
            d for d in dirs
            if not private.match(os.path.join(relative_path, d))
        ]

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

                    def make_api_route(handler):

                        def api_route():
                            return handler(request, make_response, jsonify)

                        return api_route

                    api_server.add_url_rule(
                        f"/{route_path_clean}",
                        endpoint=f"api_route_{route_path_clean}",
                        view_func=make_api_route(handler),
                        methods=method)

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

            # Handles protected routes
            elif "+<" and ">" in names:
                module_path = os.path.join(root, names)
                module_name = module_path.replace(
                    os.getcwd() + '/',
                    '').replace('/',
                                '.').replace('.x.py',
                                             '').replace("+<",
                                                         "").replace(">", "")

                spec = importlib.util.spec_from_file_location(
                    module_name, module_path)

                package = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(package)

                func_name = names.replace(".x.py",
                                          "").replace("+<",
                                                      "").replace(">", "")

                prot_func = getattr(package, func_name, None)

                if prot_func:
                    route_path_clean = os.path.join(
                        relative_path,
                        names.replace('.x.py', '').replace('_', '-')).replace(
                            "+<", "").replace(">", "")
                    route_path_clean = route_path_clean.replace("\\", "/")

                    @component
                    def goback(url):
                        return navigate(url)

                    @component
                    def protected():
                        return prot_func(use_request().cookies, goback)

                    r = route(f"/{route_path_clean}", protected())
                    routes.append(r)

                else:
                    print(f"Function '{func_name}' not found in {names}")

            # Handles markdown routes
            elif names.endswith(".md.x.py"):
                module_path = os.path.join(root, names)
                module_name = module_path.replace(os.getcwd() + '/',
                                                  '').replace('.md.x.py', '')
                spec = importlib.util.spec_from_file_location(
                    module_name, module_path)
                package = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(package)

                func_name = names.replace(".md.x.py", "")
                func_md = getattr(package, func_name, None)

                if func_md:
                    md_content = find_nearest_markdown(func_name, root, path,
                                                       markdown_files,
                                                       not_found_route)

                    route_path_clean = os.path.join(
                        relative_path,
                        names.replace('.md.x.py',
                                      '').replace('_',
                                                  '-')).replace("\\", "/")

                    @component
                    def md():
                        return html_to_vdom(md_content)

                    r = route(f"/{route_path_clean}", func_md(md()))
                    routes.append(r)

            # Handles parallel routes
            elif "+@" in names:
                module_path = os.path.join(root, names)
                module_name = module_path.replace(
                    os.getcwd() + '/',
                    "").replace('/', '.').replace('.x.py',
                                                  '').replace("+@", "")
                spec = importlib.util.spec_from_file_location(
                    module_name, module_path)
                package = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(package)
                func_name = names.replace(".x.py", "").replace("+@", "")
                func = getattr(package, func_name, None)
                if func:
                    parallel_routes[func_name] = func

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
