import os
import re
import importlib.util
from pathlib import Path
from reactpy_router import route, browser_router, use_params
from reactpy import component, run, vdom_to_html, html_to_vdom
from sanic import Sanic
import sanic.response as res
import threading

t1 = threading.Thread(target=Sanic, args=("server", ))
@t1.get(r"/")
#...

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

    for root, dirs, files in os.walk(path, True):
        relative_path = os.path.relpath(root, start=path)
        if relative_path == ".":
            relative_path = ""

        # Handle silent routes (grouping routes)
        if silent.search(relative_path):
            relative_path = ""

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
                        return function(params=vals).render()

                    r = route(f"/{route_path_cleaner}", slug_shot())
                    routes.append(r)
                else:
                    print(f"Function '{func_name}' not found in {names}, slug")

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

                if handler:
                    pass

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

                t2 = threading.Thread(target=api_server.run, args=(
                    "0.0.0.0", 8080, ))
                t1.start()
                t2.start()
            else:

                @component
                def root():
                    return layout(browser_router(*routes))

                t2 = threading.Thread(target=api_server.run, args=(
                    "0.0.0.0", 8080, ))
                t1.start()
                t2.start()
        else:
            if verbose:
                print(*routes)

                @component
                def root():
                    return browser_router(*routes)

                t2 = threading.Thread(target=api_server.run, args=(
                    "0.0.0.0", 8080, ))
                t1.start()
                t2.start()
            else:

                @component
                def root():
                    return browser_router(*routes)

                t2 = threading.Thread(target=api_server.run, args=(
                    "0.0.0.0", 8080, ))
                t1.start()
                t2.start()
