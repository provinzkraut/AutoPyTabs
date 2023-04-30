=== "Python 3.7+"
    ```python foo="bar"
    from typing import Set, Optional
    
    def bar(baz: Optional[str]) -> Set[str]:
        ...
    ```

=== "Python 3.9+"
    ```python foo="bar"
    from typing import Optional
    
    def bar(baz: Optional[str]) -> set[str]:
        ...
    ```

===+ "Python 3.10+"
    ```python foo="bar"
    
    def bar(baz: str | None) -> set[str]:
        ...
    ```