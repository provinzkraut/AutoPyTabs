# AutoPyTabs

Automatically generate code examples for different Python versions in
[mkdocs](https://www.mkdocs.org) or [Sphinx](https://www.sphinx-doc.org) based documentations, or a plain
[markdown](https://python-markdown.github.io/) workflow, making use of the
[pymdown "tabbed"](https://facelessuser.github.io/pymdown-extensions/extensions/tabbed/) markdown extension for markdown,
and [sphinx{design} tabs](https://sphinx-design.readthedocs.io/en/latest/tabs.html) for Sphinx.

## Rationale

### The problem

Python project documentation typically include code examples. Given that most of the time, a project will support
multiple versions of Python, it would be ideal to showcase the adjustments that can or need to be made for different
Python versions. This can be achieved by including several versions of the example code, conveniently displayed using
the [pymdown "tabbed"](https://facelessuser.github.io/pymdown-extensions/extensions/tabbed/) extension for markdown, or
[sphinx{design} tabs](https://sphinx-design.readthedocs.io/en/latest/tabs.html) for Sphinx.

This, however, raises several problems:

1. Maintaining multiple versions of a single example is tedious and error-prone as they can easily
   become out of sync
2. Figuring out which examples need to be changed for which specific Python version is a labour intensive task
3. Dropping or adding support for Python versions requires revisiting every example in the documentation
4. Checking potentially ~4 versions of a single example into VCS creates unnecessary noise

Given those, it's no surprise that the current standard is to only show examples for the lowest  supported version of Python.

### The solution

**AutoPyTabs** aims to solve all of these problems by automatically generating versions of code examples, targeting different
Python versions **at build-time**, based on a base version (the lowest supported Python version).
This means that:

1. There exists only one version of each example: The lowest supported version becomes the source of truth,
   therefore preventing out-of-sync examples and reducing maintenance burden
2. Dropping or adding support for Python versions can be done via a simple change in a configuration file

<hr>

## Table of contents

1. [Usage with mkdocs / markdown](#usage-markdown)
   1. [Configuration](#markdown-config)
   2. [Differences between the mkdocs plugin vs markdown extension](#differences-between-the-mkdocs-plugin-and-markdown-extension)
   3. [Examples](#markdown-examples)
   4. [Selectively disable](#selectively-disable)
   5. [Compatibility with `pymdownx.snippets`](#compatibility-with-pymdownxsnippets)
2. [Usage with Sphinx](#usage-with-sphinx)
   1. [Configuration](#sphinx-config)
   2. [Directives](#directives)
   3. [Examples](#sphinx-examples)
   4. [Compatibility with other extensions](#compatibility-with-other-extensions)

<hr> 

## Installation

For mkdocs: `pip install auto-pytabs[mkdocs]`
For markdown: `pip install auto-pytabs[markdown]`
For sphinx: `pip install auto-pytabs[sphinx]`

<h2 id="usage-markdown">Usage with mkdocs / markdown</h2>

<h3 id="markdown-config">Configuration</h3>

#### Mkdocs plugin

```yaml
site_name: My Docs
markdown_extensions:
  - pymdownx.tabbed:
plugins:
  - auto_pytabs:
      min_version: "3.7"  # optional
      max_version: "3.11" # optional
      tab_title_template: "Python {min_version}+"  # optional
      no_cache: false  # optional
```

*Available configuration options*

| Name                 | Default                   | Description                 |
| -------------------- | ------------------------- | --------------------------- |
| `min_version`        | `(3, 7)`                  | Minimum python version      |
| `max_version`        | `(3, 7)`                  | Maximum python version      |
| `tab_title_template` | `"Python {min_version}+"` | Template for tab titles     |
| `no_cache`           | `False`                   | Disable file system caching |

#### Markdown extension

```python
import markdown

md = markdown.Markdown(
    extensions=["auto_pytabs"],
    extension_configs={
        "auto_pytabs": {
            "min_version": "3.7",  # optional
            "max_version": "3.11",  # optional
            "tab_title_template": "Python {min_version}+",  # optional
        }
    },
)
```

*Available configuration options*

| Name                 | Default                   | Description                                 |
| -------------------- | ------------------------- | ------------------------------------------- |
| `min_version`        | `(3, 7)`                  | Minimum python version to generate code for |
| `max_version`        | `(3, 7)`                  | Maximum python version to generate code for |
| `tab_title_template` | `"Python {min_version}+"` | Template for tab titles                     |

### Differences between the mkdocs plugin and markdown extension

AutoPyTabs ships as a markdown extension and an mkdocs plugin, both of which can be used in mkdocs. The only difference
between them is that the mkdocs plugin supports caching, which can make subsequent builds faster (i.e. when using `mkdocs serve`).
The reason why the markdown extension does not support caching is that `markdown` does not have clearly defined build
steps with wich an extension could interact (like mkdocs [plugin events](https://www.mkdocs.org/dev-guide/plugins/#events)),
making it impossible to know when to persist cached items to disk / evict unused items.

**If you are using mkdocs, the mkdocs plugin is recommended**. If you have caching disabled, there will be no difference either way.

Should you wish to integrate the markdown extension into a build process where you can manually persist the cache after the build,
you can explicitly pass it a cache:

```python
import markdown
from auto_pytabs.core import Cache

cache = Cache()

md = markdown.Markdown(
    extensions=["auto_pytabs"],
    extension_configs={
        "auto_pytabs": {
           "cache": cache
        }
    },
)


def build_markdown() -> None:
    md.convertFile("document.md", "document.html")
    cache.persist()
```

<h3 id="markdown-examples">Examples</h3>

**Input**

<pre>
```python
from typing import Optional, Dict

def foo(bar: Optional[str]) -> Dict[str, str]:
    ...
```
</pre>

**Equivalent markdown**

<pre>
=== "Python 3.7+"
    ```python
    from typing import Optional, Dict

    def foo(bar: Optional[str]) -> Dict[str, str]:
        ...
    ```

=== "Python 3.9+"
    ```python
    from typing import Optional
    
    
    def foo(bar: Optional[str]) -> dict[str, str]:
        ...
    ```

==== "Python 3.10+"
    ```python
    def foo(bar: str | None) -> dict[str, str]:
        ...
    ```
</pre>

#### Nested blocks

Nested tabs are supported as well:

**Input**

<pre>
=== "Level 1-1"

    === "Level 2-1"

        ```python
        from typing import List
        x: List[str]
        ```

    === "Level 2-2"
    
        Hello, world!

=== "Level 1-2"

    Goodbye, world!
</pre>

**Equivalent markdown**

<pre>
=== "Level 1-1"

    === "Level 2-1"

        === "Python 3.7+"
            ```python
            from typing import List
            x: List[str]
            ```
        
        === "Python 3.9+"
            ```python
            x: list[str]
            ```

    === "Level 2-2"

        Goodbye, world!

=== "Level 1-2"
    Hello, world!
    
</pre>

### Selectively disable

You can disable conversion for a single code block:

````
<!-- autopytabs: disable-block -->
```python
from typing import Set, Optional

def bar(baz: Optional[str]) -> Set[str]:
    ...
```
````

Or for whole sections / files

```
<!-- autopytabs: disable -->
everything after this will be ignored
<!-- autopytabs: enable -->
re-enables conversion again
```

### Compatibility with `pymdownx.snippets`

If the `pymdownx.snippets` extension is used, make sure that it runs **before** AutoPyTab

<hr>

## Usage with Sphinx

AutPyTabs provides a Sphinx extension `auto_pytabs.sphinx_ext`, enabling its functionality
for the `.. code-block` and `.. literalinclude` directives.

<h3 id="sphinx-config">Configuration</h3>

#### Example configuration

```python
extensions = ["auto_pytabs.sphinx_ext", "sphinx_design"]

auto_pytabs_min_version = (3, 7)  # optional
auto_pytabs_max_version = (3, 11)  # optional
auto_pytabs_tab_title_template = "Python {min_version}+"  # optional 
# auto_pytabs_no_cache = True  # disabled file system caching
# auto_pytabs_compat_mode = True  # enable compatibility mode
```

#### Available configuration options

| Name                             | Default                   | Description                                      |
| -------------------------------- | ------------------------- | ------------------------------------------------ |
| `auto_pytabs_min_version`        | `(3, 7)`                  | Minimum python version to generate code for      |
| `auto_pytabs_max_version`        | `(3, 7)`                  | Maximum python version to generate code for      |
| `auto_pytabs_tab_title_template` | `"Python {min_version}+"` | Template for tab titles                          |
| `auto_pytabs_no_cache`           | `False`                   | Disable file system caching                      |
| `auto_pytabs_compat_mode`        | `False`                   | Enable [compatibility mode](#compatibility-mode) |

<h3 id="sphinx-examples">Examples</h3>

**Input**

```rst
.. code-block:: python

   from typing import Optional, Dict
   
   def foo(bar: Optional[str]) -> Dict[str, str]:
       ...
```

**Equivalent ReST**

```rst
.. tab-set::

   .. tab-item:: Python 3.7+
   
       .. code-block:: python
       
          from typing import Optional, Dict
      
          def foo(bar: Optional[str]) -> Dict[str, str]:
              ...

   .. tab-item:: Python 3.9+
   
      .. code-block:: python
      
          from typing import Optional
          
          
          def foo(bar: Optional[str]) -> dict[str, str]:
              ...

   .. tab-item:: Python 3.10+
   
      .. code-block:: python
      
          def foo(bar: str | None) -> dict[str, str]:
              ...

```

### Directives

AutoPyTabs overrides the built-in `code-block` and `literal-include` directives,
extending them with auto-upgrade and tabbing functionality, which means no special
directives, and therefore changes to existing documents are needed.

Additionally, a `:no-upgrade:` option is added to the directives, which can be used to
selectively fall back the default behaviour.

Two new directives are provided as well:

- `.. pytabs-code-block::`
- `.. pytabs-literalinclude::`

which by default act exactly like `.. code-block` and `.. literalinclude` respectively,
and are mainly to provide AutoPyTab's functionality in [compatibility mode](#compatibility-mode).

### Compatibility mode

If you don't want the default behaviour of directive overrides, and instead wish to use the
`.. pytabs-` directives manually (e.g. because of compatibility issues with other extensions
or because you only want to apply it to select code blocks) you can make use AutoPyTabs' compatibility
mode. To enable it, simply use the `auto_pytabs_compat_mode = True` in `conf.py`. Now, only content within `.. pytabs-`
directives will be upgraded.

### Compatibility with other extensions

Normally the directive overrides don't cause any problems and are very convenient,
since no changes to existing documents have to be made. However, if other extensions are included,
which themselves override one of those directives, one of them will inadvertently override the other,
depending on the order they're defined in `extensions`.

To combat this, you can use the [compatibility mode](#compatibility-mode) extension instead, which
only includes the new directives.

If you control the conflicting overrides, you can alternatively inherit from
`auto_py_tabs.sphinx_ext.CodeBlockOverride` and `auto_py_tabs.sphinx_ext.LiteralIncludeOverride`
instead of `sphinx.directives.code.CodeBlock` and `sphinx.directives.code.LiteralInclude` respectively.
