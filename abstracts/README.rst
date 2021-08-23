
abstracts
=========

Abstract class and interface definitions.

Create an ``abstract.Abstraction``
----------------------------------

An ``Abstraction`` is a ``metaclass`` for defining abstract classes.

Let's define an abstract ``AFoo`` class and give it an abstract ``do_foo``
method.

Like any python class, an ``Abstraction`` can have any name, but it may
be helpful to distinguish abstract classes from others by prefixing their
name with ``A``.

.. code-block:: python

   >>> import abc
   >>> import abstracts

   >>> class AFoo(metaclass=abstracts.Abstraction):
   ...
   ...     @abc.abstractmethod
   ...     def do_foo(self):
   ...         raise NotImplementedError

Abstract classes **cannot** be instantiated directly.

.. code-block:: python

   >>> AFoo()
   Traceback (most recent call last):
   ...
   TypeError: Can't instantiate abstract class AFoo with abstract method... do_foo


Create an ``implementer`` for an ``abstract.Abstraction``
---------------------------------------------------------

In order to make use of ``AFoo``, we need to create an implementer for it.

.. code-block:: python

   >>> @abstracts.implementer(AFoo)
   ... class Foo:
   ...     pass

The implementer **must** implement all of the abstract methods,
defined by its abstract classes.

.. code-block:: python

   >>> Foo()
   Traceback (most recent call last):
   ...
   TypeError: Can't instantiate abstract class Foo with abstract method... do_foo

   >>> @abstracts.implementer(AFoo)
   ... class Foo2:
   ...
   ...     def do_foo(self):
   ...         return "DID FOO"

   >>> Foo2()
   <__main__.Foo2 object at ...>


An implementer inherits from its ``Abstractions``
-------------------------------------------------

An ``implementer`` class is a subclass of its ``Abstraction``.

.. code-block:: python

   >>> issubclass(Foo2, AFoo)
   True

Likewise an instance of an implementer is an instance of its ``Abstraction``

.. code-block:: python

   >>> isinstance(Foo2(), AFoo)
   True

The ``Abstraction`` class can be seen in the class ``bases``, and the
methods of the ``Abstraction`` can be invoked by the implementer.

.. code-block:: python

   >>> import inspect
   >>> AFoo in inspect.getmro(Foo2)
   True


Create an ``implementer`` that implements multiple ``Abstraction`` s.
---------------------------------------------------------------------

An implementer can implement multiple abstractions.

Let's create a second abstraction.

.. code-block:: python

   >>> class ABar(metaclass=abstracts.Abstraction):
   ...
   ...     @abc.abstractmethod
   ...     def do_bar(self):
   ...         raise NotImplementedError

And now we can create an implementer that implememts both the ``AFoo`` and ``ABar``
``Abstraction`` s.

.. code-block:: python

   >>> @abstracts.implementer((AFoo, ABar))
   ... class FooBar:
   ...
   ...     def do_foo(self):
   ...         return "DID FOO"
   ...
   ...     def do_bar(self):
   ...         return "DID BAR"

   >>> FooBar()
   <__main__.FooBar object at ...>


Defining abstract properties
----------------------------

Properties can be defined in an abstract class, and just like with normal
methods, they must be implemented by any implementers.

.. code-block:: python

   >>> class AMover(metaclass=abstracts.Abstraction):
   ...
   ...     @property
   ...     @abc.abstractmethod
   ...     def speed(self):
   ...         return 5
   ...
   ...     @property
   ...     @abc.abstractmethod
   ...     def direction(self):
   ...         return "forwards"


Calling ``super()`` on an ``abstractmethod``
--------------------------------------------

Just like with pythons "Abstract Base Classes" you can call ``super()``
in an ``abstractmethod``, to invoke an abstract implementation.

.. code-block:: python

   >>> @abstracts.implementer(AMover)
   ... class Mover:
   ...
   ...     @property
   ...     def direction(self):
   ...         return "backwards"
   ...
   ...     @property
   ...     def speed(self):
   ...         return super().speed

This custom implementation of ``AMover`` **must** implement both ``speed`` and
``direction``, even if its implementation invokes the abstract implementation.

In this case it uses the default/abstract implementation of ``speed`` while providing
its own implementation of ``direction``.

.. code-block:: python

   >>> mover = Mover()
   >>> mover
   <__main__.Mover object at ...>

   >>> mover.speed
   5
   >>> mover.direction
   'backwards'


Defining an ``abstracts.Interface`` class
-----------------------------------------

An ``Interface`` is much like an ``Abstraction``, but with a few differences.

An ``Interface`` can only define methods with the ``@interfacemethod`` decorator.

It cannot define normal methods or methods with the ``@abstractmethod``, only methods
with ``@interfacemethod``.

An ``@interfacemethod`` if invoked will always raise an ``NotImplementedError``, and
therefore cannot be used as an abstract implementation.

Lets add an ``Interface`` class that we can use.

In the way that it may be helpful to distinguish an ``Abstraction`` from other
types of classes, it may be also useful to distinguish an ``Interface`` by
using an ``I`` prefix when naming them.

.. code-block:: python

   >>> class IGeared(metaclass=abstracts.Interface):
   ...
   ...     @property
   ...     @abstracts.interfacemethod
   ...     def number_of_gears(self):
   ...         # Raising an error is ~superfluous as the decorator will raise
   ...         # anyway if the method is invoked.
   ...         raise NotImplementedError


Implementing an ``Interface``
-----------------------------

Just like with an ``Abstraction``, an ``Interface`` can be implemented using
the ``@implementer`` decorator.

An implementer, can implement a combination of ``Abstractions`` and
``Interfaces``.

.. code-block:: pythonx

   >>> @abstracts.implementer((AMover, IGeared))
   ... class Bicycle:
   ...
   ...     @property
   ...     def direction(self):
   ...         return super().direction
   ...
   ...     @property
   ...     def speed(self):
   ...         return super().speed
   ...
   ...     @property
   ...     def number_of_gears(self):
   ...         return 7

   >>> Bicycle().number_of_gears
   7


An implementer does **not** inherit from its ``Interfaces``
-----------------------------------------------------------

An ``implementer`` class is a subclass of its ``Interfaces``.

.. code-block:: python

   >>> issubclass(Bicycle, AMover)
   True
   >>> issubclass(Bicycle, IGeared)
   True

Likewise an instance of an implementer is an instance of its ``Interfaces``

.. code-block:: python

   >>> isinstance(Bicycle(), AMover)
   True
   >>> isinstance(Bicycle(), IGeared)
   True

Unlike with ``Abstractions`` it does **not** however, inherit from its ``Interfaces``.

.. code-block:: python

   >>> AMover in inspect.getmro(Bicycle)
   True

   >>> IGeared in inspect.getmro(Bicycle)
   False

``@interfacemethods`` can never be invoked
------------------------------------------

The key thing to remember is that you cannot call ``super()`` on any
``@interfacemethod``, or directly invoke it.

If it was defined as part of an ``Interface`` you will receive an
``AttributeError``, as the implementation does not inherit directly from the
interface.

.. code-block:: python

   >>> @abstracts.implementer((AMover, IGeared))
   ... class BrokenBicycle:
   ...
   ...     @property
   ...     def direction(self):
   ...         return super().direction
   ...
   ...     @property
   ...     def speed(self):
   ...         return super().speed
   ...
   ...     @property
   ...     def number_of_gears(self):
   ...         return super().number_of_gears

   >>> BrokenBicycle().number_of_gears
   Traceback (most recent call last):
   ...
   AttributeError: 'super' object has no attribute 'number_of_gears'

.. warning::

   Misuse of this class can have `unintended consequences <https://www.dailymotion.com/video/x2howud>`_

If you invoke ``super()`` on an ``@interfacemethod`` defined as part of an
``Abstraction`` it will raise ``NotImplementedError``.

As an ``Interface`` can only hold this type of method, you can never invoke
any of its methods. Doing so directly will raising a ``NotImplementedError``.

.. code-block:: python

   >>> IGeared.number_of_gears.__get__(Bicycle())
   Traceback (most recent call last):
   ...
   NotImplementedError

Combining ``@abstractmethod`` and ``@interfacemethod`` in an ``Abstraction``
----------------------------------------------------------------------------

As ``Interfaces`` are "pure", they cannot use ``@abstractmethod`` or contain any implementation.

An ``Abstraction`` on the other hand can combine both.

Lets create a pure ``Interface`` that represents a "shed".

.. code-block:: python

   >>> class IShed(metaclass=abstracts.Interface):
   ...
   ...     @property
   ...     @abstracts.interfacemethod
   ...     def size(self):
   ...         raise NotImplementedError

We can use this interface to create an ``ABikeShed`` ``Abstraction``

.. code-block:: python

   >>> class ABikeShed(IShed, metaclass=abstracts.Abstraction):
   ...
   ...     @property
   ...     @abstracts.interfacemethod
   ...     def max_bike_size(self):
   ...         raise NotImplementedError
   ...
   ...     @abc.abstractmethod
   ...     def get_capacity(self):
   ...         return int(self.size / self.max_bike_size)

We can now create an implementation.

It will need to define both the ``size`` and the ``max_bike_size``,
as these are ``interfacemethods``.

It can, however, make use of the abstract implementation of ``get_capacity``,
even if it must be defined.

.. code-block:: python

   >>> @abstracts.implementer(ABikeShed)
   ... class BikeShed:
   ...
   ...     @property
   ...     def max_bike_size(self):
   ...         return 7
   ...
   ...     @property
   ...     def size(self):
   ...         return 161
   ...
   ...     def get_capacity(self):
   ...         return super().get_capacity()

   >>> bikeshed = BikeShed()
   >>> bikeshed.get_capacity()
   23
