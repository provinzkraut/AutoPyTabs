from auto_pytabs.markdown_ext import UpgradePreprocessor


def test_upgrade_single_version():
    ext = UpgradePreprocessor(min_version="3.9", max_version="3.11")
    source = """```python foo="bar"
from typing import Set

def bar(baz: str) -> Set[str]:
    ...
```
"""
    expected_output = """```python foo="bar"

def bar(baz: str) -> set[str]:
    ...
```"""

    output = "\n".join(ext.run(source.splitlines()))
    assert output == expected_output


def test_upgrade():
    ext = UpgradePreprocessor(min_version="3.7", max_version="3.11")
    source = """```python foo="bar"
from typing import Set, Optional

def bar(baz: Optional[str]) -> Set[str]:
    ...
```
"""

    expected_output = """=== "Python 3.7+"
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

=== "Python 3.10+"
    ```python foo="bar"
    
    def bar(baz: str | None) -> set[str]:
        ...
    ```"""

    output = "\n".join(ext.run(source.splitlines()))
    assert output == expected_output


def test_upgrade_custom_tab_title():
    ext = UpgradePreprocessor(
        min_version="3.7",
        max_version="3.11",
        tab_title_template="Python {min_version} and above",
    )
    source = """```python foo="bar"
from typing import Set

def bar(baz: Set[str]) -> Set[str]:
    ...
```
"""

    expected_output = """=== "Python 3.7 and above"
    ```python foo="bar"
    from typing import Set
    
    def bar(baz: Set[str]) -> Set[str]:
        ...
    ```

=== "Python 3.9 and above"
    ```python foo="bar"
    
    def bar(baz: set[str]) -> set[str]:
        ...
    ```"""

    output = "\n".join(ext.run(source.splitlines()))
    # breakpoint()
    assert output == expected_output


def test_nested_tabs():
    source = """=== "Level 1"
    === "Level 2"
        ```python
        from typing import List
        def func(x: List[str]) -> None:
            def inner():
                pass
        ```
"""

    expected_output = """=== "Level 1"
    === "Level 2"
        === "Python 3.7+"
            ```python
            from typing import List
            def func(x: List[str]) -> None:
                def inner():
                    pass
            ```
        
        === "Python 3.9+"
            ```python
            def func(x: list[str]) -> None:
                def inner():
                    pass
            ```"""

    ext = UpgradePreprocessor(min_version="3.7", max_version="3.11")
    output = "\n".join(ext.run(source.splitlines()))
    assert output == expected_output


def test_disable_block():
    source = """<!-- autopytabs: disable-block -->
```python
from typing import List
x: List[str]
```

```python
from typing import Set
y: Set[str]
```"""

    expected_output = """```python
from typing import List
x: List[str]
```

=== "Python 3.7+"
    ```python
    from typing import Set
    y: Set[str]
    ```

=== "Python 3.9+"
    ```python
    y: set[str]
    ```"""
    ext = UpgradePreprocessor(min_version="3.7", max_version="3.11")
    output = "\n".join(ext.run(source.splitlines()))
    assert output == expected_output


def test_disable_section():
    source = """<!-- autopytabs: disable -->
```python
from typing import List
x: List[str]
```

```python
from typing import Set
y: Set[str]
```

<!-- autopytabs: enable -->
```python
from typing import Dict
z: Dict[str, str]
```
"""

    expected_output = """```python
from typing import List
x: List[str]
```

```python
from typing import Set
y: Set[str]
```

=== "Python 3.7+"
    ```python
    from typing import Dict
    z: Dict[str, str]
    ```

=== "Python 3.9+"
    ```python
    z: dict[str, str]
    ```"""
    ext = UpgradePreprocessor(min_version="3.7", max_version="3.11")
    output = "\n".join(ext.run(source.splitlines()))
    assert output == expected_output


def test_ignore_fenced_block():
    source = """```json
{"foo": "bar"}
```"""

    ext = UpgradePreprocessor(min_version="3.7", max_version="3.11")
    output = "\n".join(ext.run(source.splitlines()))
    assert output == source
