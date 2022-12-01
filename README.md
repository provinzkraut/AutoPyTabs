# Auto PyTabs

A markdown extension to automatically generate 
[pymdown tabs](https://facelessuser.github.io/pymdown-extensions/extensions/tabbed/)
for different Python versions.

## Example

**Input**

<pre>
```python
from typing import Optional, Dict

def foo(bar: Optional[str]) -> Dict[str, str]:
    ...
```
</pre>

**Output**

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

**Output**

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

## Per-block disable
You can disable conversion for a single code block:


    <!-- autopytabs: disable-block -->
    ```python
    from typing import Set, Optional
    
    def bar(baz: Optional[str]) -> Set[str]:
        ...
    ```



## Section disable
Or for whole sections / files


    <!-- autopytabs: disable -->
    everything after this will be ignored
    <!-- autopytabs: enable -->
    re-enables conversion again

