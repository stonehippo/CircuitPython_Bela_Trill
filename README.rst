Introduction
============

A CircuitPython driver for the `Bela.io Trill touch sensors <https://bela.io/products/trill/>`_

Dependencies
============

This driver depends on:

* `Adafruit CircuitPython <https://github.com/adafruit/circuitpython>`_
* `Adafruit Bus Device <https://github.com/adafruit/Adafruit_CircuitPython_BusDevice>`_

Please ensure all dependencies are available on the CircuitPython filesystem.
This is easily achieved by downloading
`the Adafruit library and driver bundle <https://github.com/adafruit/Adafruit_CircuitPython_Bundle>`_.

Usage Example
=============

Setting up a single Trill touch sensor is straightforward, when using the defualt I2C addresss and scan settings.

.. code-block:: python

  import board
  import time
  import bela_trill

  trill_bar = bela_trill.Bar(board.I2C())

  while True:
    trill_bar.read()
    for i in range(trill_bar.number_of_touches()):
      touch = trill_bar.touches[i]
      print(f"touch{i}: location_x: {touch.location_x} size: {touch.size")
    time.sleep(0.05)
