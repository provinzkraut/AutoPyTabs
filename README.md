# Auto PyTabs

A markdown extension to automatically generate 
[pymdown tabs](https://facelessuser.github.io/pymdown-extensions/extensions/tabbed/)
for different Python versions using [pyupgrade](https://github.com/asottile/pyupgrade).

## Usage

From python

```python
from markdown import markdown
from auto_pytabs import UpgradeExtension

markdown("...", extensions=[UpgradeExtension(min_version="3.8"), "pymdownx.tabbed"])
```

Integrated in mkdocs:

```yaml
site_name: My Docs
theme:
  name: material
markdown_extensions:
  - pymdownx.tabbed:
      alternate_style: true
  - pymdownx.snippets
  - auto_pytabs:
      min_version: "3.8"
```

## Example

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


### Nested blocks

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

## Selectively disable

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

## Compatibility with `pymdownx.snippets`

If the `pymdownx.snippets` extension is used, make sure that it runs **before** AutoPyTab

## Configuration

|                                                         |                                             |
|---------------------------------------------------------|---------------------------------------------|
| min_version (default: `3.7`)                            | Minimum Python version to support           |
| max_version (default: `3.11`)                           | Maximum Python version to support           |
| tab_title_template (default: `"Python {min_version}+"`) | Python format string to generate tab titles |

