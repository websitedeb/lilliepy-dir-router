# Lilliepy-dir-router
a router that uses folders and files to create routes for reactpy files (is used in the lilliepy framework)

## Dependencies
* reactpy
* reactpy router
* pathlib
* importlib
* os
* re

## Setup
if you are using the lilliepy framework, then this part should be already dont for you, if not, then read this

```python
# your_python_file.py
from lilliepy_dir_router import FileRouter

FileRouter("/path/to/your/pages/folder", verbose=True) # verbose, if set to true, will print out the routes and status of the router
```

## Syntax

there are 3 special types of files/directories to use in this current release

### Folders

#### Silent Folders

silent folders are denoted as ([FOLDER_NAME]), these folders are only for grouping files together, they wont be added to said file's route

##### e.g :-
```
├── pages
│   ├── (files)
│   │   ├── file.x.py
```
* the url for ```file.x.py``` will be /file, notice how it isnt /files/file

### Files

#### Regular Files

regular files must end in a ```.x.py``` extenstion if you want it to render, if there are functions of python files you dont want to render or want to make components that you want to import to other ```.x.py``` files and it said component shouldnt have its own route, then use the regular ```.py``` extension.
* NOTE: the router will ignore files that are not in ```.x.py``` extenstion

##### Syntax
```python
# main.x.py

from reactpy import component, html # import component (to make function a component), and html (to make html), you can also import hooks from here if you want


@component # makes function component
def main(): # NOTE: FUNCTION'S NAME MUST BE THE SAME AS THE FILE'S NAME (THIS IS CASE SENSITIVE TOO)
  return html.h1("yo") # returns <h1>yo</h1>

@component
def test(): # this wont render in this file as it's name isnt the same as the file's name, however, you can use this function in your component (the functions that has the same name as the file's name)
  return html.h1("Test")

```
* again, note, function's name MUST be the same name as the file's name if you want it to render, you can create helper functions and/or import them into the render-ing component

#### ```+root.x.py```

this special file is the root file, it will render in the root of an url, and if it kept in the first dir, then it will render in "/"

##### e.g :-
```
├── pages
│   ├── +root.x.py     <-- this will render in "/"
│   ├── files
│   │   ├── +root.x.py  <-- this will render in "/files", notice it renders in the root folder
│   │   ├── file.x.py
│   ├── another_example
│   │   ├── +root.x.py  <-- this will render in "/another_example", notice it renders in the root folder
│   │   ├── file_two.x.py
│   │   ├── nested_folder
│   │   │   ├── +root.x.py    <-- this will render in "/another_example/nested_folder"
│   │   ├── nested_folder_two
│   │   │   ├── (folder)
│   │   │   │   ├── +root.x.py  <-- this will render in "/another_example/nested_folder", as the parent folder for +root.x.py is a silent folder, so it is neglected
```
* so in simpler terms, the ```+root.x.py``` file will render in the parent folder root dir url
* NOTE: it will not render in "/[PARENT_FOLDER_OF_+ROOT.X.PY_FILE]/", as this is a completely different route
* NOTE: if the parent folder is a slient folder, the +root.x.py file wont be the root file for the silent folder, it will be the root folder for the parent folder of the silent folder

##### Syntax :-
```python
# +root.x.py

from reactpy import component, html

@component
def root(): # the render-ing function for a +root.x.py file MUST be called "root" (LOWER CASE, NOT UPPPER CASE)
  return html.h1("home")
```

#### Slug Files

these are files which take in value(s) from the url, they are made by saying +[(FILE_NAME)].x.py

##### e.g :-
```
├── pages
│   ├── +[name].x.py
│   ├── id
│   │   ├── +[id].x.py
```

##### Syntax :-
```python
# +[id].x.py

from reactpy import html, component


@component
# function's name must be the same as the name given inbetween the two brackets in the file's name
def id(params): # 1 parameter must be given so that this function can access the value(s) in the url, the parameter's name MUST be called params if you want it to be a slug (this is to help differeciate between slug params and other params)
    return html.div([
        html.h1(f"Dynamic Content for ID: {params['id']}"), #params is a dictionary, trust me, knowing that helps you alot
        html.p("This page dynamically renders content based on the slug."),
    ])
```

### When to use ```.x.py``` and ```.py```

you should use ```.x.py``` when:
  * you want the file to render
  * it dosnt contain sensitive backend code
  * it dosnt have parameters other than the slug file's ```params``` parameter

you should use ```.py``` when:
  * you want to make a component that you want to import and not have a url of its own
  * you want to do backend code
  * you have more parameters than just the slug's ```params``` parameter

you could think of ```.x.py``` as the client components and ```.py``` as the server components in reactjs