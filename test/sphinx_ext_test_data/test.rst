=====
Index
=====

code-block
----------

.. code-block:: python
    :caption: test caption

    from typing import Dict, Union, List, Optional

    def foo(x: Union[Dict[str, str], List[str]]) -> Optional[List[int]]:
        pass


code-block no upgrade
---------------------

.. code-block:: python
    :caption: test caption
    :no-upgrade:

    from typing import Dict, Union, List, Optional

    def foo(x: Union[Dict[str, str], List[str]]) -> Optional[List[int]]:
        pass


code-block non-python
----------------------

.. code-block:: javascript

    const x = "hello"


code-block no language
----------------------

.. code-block::

    this is something


literalinclude
--------------

.. literalinclude:: example.py
    :language: python
    :caption: test caption


literalinclude non-python
--------------------------

.. literalinclude:: example.js
    :language: javascript


literalinclude no language
---------------------------

.. literalinclude:: example.js