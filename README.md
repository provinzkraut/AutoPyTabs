# AutoPyTabs

Tooling to automatically generate tabbed code examples for different Python versions in
[mkdocs](https://www.mkdocs.org) or [Sphinx](https://www.sphinx-doc.org) based documentations, or a plain
[markdown](https://python-markdown.github.io/) workflow, making use of the
[pymdown "tabbed"](https://facelessuser.github.io/pymdown-extensions/extensions/tabbed/) markdown extension for markdown,
and [sphinx{design} tabs](https://sphinx-design.readthedocs.io/en/latest/tabs.html) for Sphinx.

## Motivation

Writing and maintaining documentation can be tedious, especially the task of including
code snippets for different versions of Python. AutoPyTabs aims to solve this problem
by automatically generating those "versioned snippets" at build-time, which means
there's only *one* file to maintain, and to be checked into VCS.

## Table of contents

1. [Usage with mkdocs / markdown](#usage-markdown)
   1. [Configuration](#markdown-config)
   2. [Examples](#markdown-examples)
   3. [Selectively disable](#selectively-disable)
   4. [Compatibility with `pymdownx.snippets`](#compatibility-with-pymdownxsnippets)
2. [Usage with Sphinx](#usage-with-sphinx)
   1. [Configuration](#sphinx-config)
   2. [Directives](#directives)
   3. [Examples](#sphinx-examples)
   4. [Compatibility with other extensions](#compatibility-with-other-extensions)

## Installation

For mkdocs: `pip install auto-pytabs[mkdocs]`
For markdown: `pip install auto-pytabs[markdown]`
For sphinx: `pip install auto-pytabs[sphinx]`

<h2 id="usage-markdown">Usage with mkdocs / markdown</h2>

<h3 id="markdown-config">Configuration</h3>

**Mkdocs plugin**

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

**Markdown extension**

```python
import markdown

md = markdown.Markdown(
    extensions=["auto_pytabs"],
    extension_configs={
        "auto_pytabs": {
            "min_version": "3.7",  # optional
            "max_version": "3.11",  # optional
            "tab_title_template": "Python {min_version}+",  # optional
            "no_cache": False,  # optional
        }
    },
)
```

### Mkdocs plugins vs markdown extension

AutoPyTabs ships as both a markdown extension and an mkdocs plugin, both of which can be used in mkdocs. The only difference
between them is that the mkdocs plugin performs automatic cache-eviction of unused files. This is not easily possible with
a markdown extension since it does not have a clearly defined build phase with which an extension could interact, meaning an
extension does not know when the build is "done", and therefore also not if a cache file is truly unused.

If you are using mkdocs, the mkdocs plugin is recommended. If you have caching disabled, there will be no difference either way.

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

## Usage with Sphinx

AutPyTabs provides a Sphinx extension `auto_pytabs.sphinx_ext`, enabling its functionality
for the `.. code-block` and `.. literalinclude` directives.

<h3 id="sphinx-config">Configuration</h3>

```python
extensions = ["auto_pytabs.sphinx_ext", "sphinx_design"]

auto_pytabs_min_version = (3, 7)  # optional
auto_pytabs_max_version = (3, 11)  # optional
auto_pytabs_tab_title_template = "Python {min_version}+"  # optional 
auto_pytabs_no_cache = True  # disabled caching
```

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
mode. To enable it, simply use the `auto_pytabs.sphinx_ext_compat` extension instead of
`auto_pytabs.sphinx_ext`. Now, only content within `.. pytabs-` directives will be upgraded.

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
