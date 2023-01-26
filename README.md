# AutoPyTabs

Tooling to automatically generate tabbed code examples for different Python versions in
[mkdocs](https://www.mkdocs.org) or [Sphinx](https://www.sphinx-doc.org) based documentations, or a plain
[markdown](https://python-markdown.github.io/) workflow, making use of the
[pymdown "tabbed"](https://facelessuser.github.io/pymdown-extensions/extensions/tabbed/) markdown extension for markdown,
and [sphinx{design} tabs](https://sphinx-design.readthedocs.io/en/latest/tabs.html) for Sphinx.

# Work in progress

This library is work in progress. Approach with caution

## Table of contents

1. [markdown / mkdocs](#mkdocs-markdown)
   1. [Configuration](#mkdocs-config)
   1. [Examples](#mkdocs-examples)
   1. [Selectively disable](#selectively-disable)
   1. [Compatibility with `pymdownx.snippets`](#compatibility-with-pymdownxsnippets)
1. [Sphinx](#sphinx)
   1. [Configuration](#sphinx-config)
   1. [Directives](#directives)
   1. [Examples](#sphinx-examples)
   1. [Compatibility with other extensions](#compatibility-with-other-extensions)

# Usage

<h2 id="mkdocs-markdown">Mkdocs / markdown</h2>

### Installation

`pip install auto-pytabs[markdown]`

<h3 id="mkdocs-config">Configuration</h3>

**Markdown extension in mkdocs**

```yaml
site_name: My Docs
markdown_extensions:
  - pymdownx.tabbed:
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
    extensions=["auto_pytabs.markdown_ext"],
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

<h3 id="mkdocs-examples">Examples</h3>

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

## Sphinx

AutPyTabs provides a Sphinx extension `auto_pytabs.sphinx_ext`, enabling its functionality
for the `.. code-block` and `.. literalinclude` directives.

### Installation

`pip install auto-pytabs[sphinx]`

### Usage

<h4 id="sphinx-config">Configuration</h4>

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
