# Auto PyTabs

Automatically generate tabbed code examples for [mkdocs](https://www.mkdocs.org)
and [Sphinx](https://www.sphinx-doc.org) based documentations, 
making use of [pymdown tabs](https://facelessuser.github.io/pymdown-extensions/extensions/tabbed/) and
[Sphinx design](https://sphinx-design.readthedocs.io/en/latest/tabs.html) respectively.


# Work in progress

This library is work in progress. Approach with caution


## Usage


### Mkdocs

```yaml
site_name: My Docs
theme:
  name: material
markdown_extensions:
  - pymdownx.tabbed:
      alternate_style: true
  - pymdownx.snippets
  - auto_pytabs.markdown_ext:
      min_version: "3.7"  # optional
      max_version: "3.11" # optional
      tab_title_template: "Python {min_version}+"  # optional
```

### Sphinx

```python
extensions = ["auto_pytabs.sphinx_ext"]

auto_pytabs_min_version = (3, 7)  # optional
auto_pytabs_max_version = (3, 11)  # optional
auto_pytabs_tab_title_template = "Python {min_version}+"  # optional 
auto_pytabs_no_cache = True  # disabled file system cache
```

## Examples

### Markdown

**Input**

<pre>
```python
from typing import Optional, Dict

def foo(bar: Optional[str]) -> Dict[str, str]:
    ...
```
</pre>

**Generated markdown**

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

**Generated markdown**

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

    <!-- autopytabs: disable-block -->
    ```python
    from typing import Set, Optional
    
    def bar(baz: Optional[str]) -> Set[str]:
        ...
    ```

Or for whole sections / files

    <!-- autopytabs: disable -->
    everything after this will be ignored
    <!-- autopytabs: enable -->
    re-enables conversion again

### Compatibility with `pymdownx.snippets`

If the `pymdownx.snippets` extension is used, make sure that it runs **before** AutoPyTab

