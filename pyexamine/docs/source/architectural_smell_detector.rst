Architectural Smell Detection
===========================

The Architectural Smell Detector identifies design and architectural issues in Python projects.

Detected Smells
-------------

* Hub-like Dependencies
* Scattered Functionality
* Cyclic Dependencies
* God Objects
* Unstable Dependencies
* Improper API Usage
* Redundant Abstractions

Usage
-----

Command Line
^^^^^^^^^^^

.. code-block:: bash

   analyze_code_quality /path/to/project --type architectural



API Reference
-----------

.. automodule:: code_quality_analyzer.architectural_smell_detector
   :members:
   :undoc-members:
   :show-inheritance: 