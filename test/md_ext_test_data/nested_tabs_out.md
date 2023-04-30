=== "Level 1"
    === "Level 2"
        === "Python 3.7+"
            ```python
            from typing import List
            def func(x: List[str]) -> None:
                def inner():
                    pass
            ```
        
        ===+ "Python 3.9+"
            ```python
            def func(x: list[str]) -> None:
                def inner():
                    pass
            ```