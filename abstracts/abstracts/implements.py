from typing import Dict, List, Set, Tuple, Type, Union

import abstracts


class Implementer(type):
    """Metaclass for implementers of an Abstract interface

    Any `Abstraction` classes that are listed in `__implements__` for the
    class are added as bases (ie added to the class's inheritance).

    Any docs for methods are copied from the interface method to the
    implementation if the implementation method has no docs of its own.

    For example:

    ```

    from tools.base.abstract import Abstraction, Implementer


    class AFoo(metaclass=Abstraction):

        @abstractmethod
        def do_something(self):
            ""\"Do something""\"
            raise NotImplementedError

    class Foo(metaclass=Implementer)
        __implements__ = (AFoo, )

        def do_something(self):
            return "DONE"
    ```
    Given the above, you should see that instantiating `Foo`:

    ```
    >>> isinstance(Foo(), AFoo)
    True
    >>> Foo().do_something.__doc__
    'Do something'
    ```
    """

    @classmethod
    def abstract_info(
            cls,
            abstract: "abstracts.Abstraction") -> Tuple[
                str, Union[str, None], List[str]]:
        """Information for a specific abstract implementation class

        For given abstract class, returns:

        - qualified class name
        - class docstring
        - abstract methods
        """
        if not isinstance(abstract, abstracts.Interface):
            raise TypeError(
                "Implementers can only implement subclasses of "
                f"`abstracts.Abstraction`, unrecognized: '{abstract}'")
        methods: List[str] = []
        for method in getattr(abstract, "__abstractmethods__", []):
            methods.append(method)
        return (
            f"{abstract.__module__}.{abstract.__name__}",
            abstract.__doc__,
            methods)

    @classmethod
    def add_docs(cls, clsdict: Dict, klass: "Implementer") -> None:
        """Add docs to the implementation class

        If the implementation class has no docstring, then a docstring is
        generated with the format:

        ```
        Implements: foo.bar.ABaz
        An implementer of the ABaz protocol...

        Implements: foo.bar.AOtherBaz
        An implementer of the AOtherBaz protocol...
        ```

        For each of the methods that are marked abstract in any of the abstract
        classes, if the method in the implementation class has no docstring the
        docstring is resolved from the abstract methods, using standard mro.
        """
        abstract_docs, abstract_methods = cls.implementation_info(clsdict)
        if not klass.__doc__:
            klass.__doc__ = "\n".join(
                f"Implements: {k}\n{v}\n" for k, v in abstract_docs.items())
        for abstract_method, abstract_klass in abstract_methods.items():
            method = getattr(klass, abstract_method, None)
            if not method:
                # this will not instantiate, so bail now
                return
            # Only set the doc for the method if its not already set.
            # `@classmethod` `__doc__`s are immutable, so skip them.
            if not method.__doc__ and not hasattr(method, "__self__"):
                method.__doc__ = getattr(
                    abstract_klass, abstract_method).__doc__

    @classmethod
    def add_interfaces(
            cls,
            ifaces: Tuple,
            klass: "Implementer") -> None:
        for iface in ifaces:
            if issubclass(klass, iface):
                continue
            missing = iface.__abstractmethods__ - set(dir(klass))
            if missing:
                raise TypeError(
                    "Not all methods for interface "
                    f"{iface} provided: missing {sorted(missing)}")
            iface.register(klass)

    @classmethod
    def check_interface(
            cls,
            clsdict: dict) -> None:
        extra = (
            cls.get_class_attrs(clsdict)
            - cls.get_interface_methods(clsdict))
        if extra:
            raise TypeError(
                "Interfaces can only contain methods decorated with "
                f"`@interfacemethod`: got {extra}")

    @classmethod
    def get_bases(
            cls,
            bases: Tuple[Type, ...],
            clsdict: Dict) -> Tuple[Type["abstracts.Abstraction"], ...]:
        """Returns a tuple of base classes, with `__implements__` classes
        included
        """
        return (
            bases
            + tuple(
                x for x in clsdict["__implements__"]
                if x not in bases
                and isinstance(x, abstracts.Abstraction)))

    @classmethod
    def get_class_attrs(
            cls,
            clsdict: dict) -> Set[str]:
        return set(
            x for x in clsdict
            if not x.startswith("__"))

    @classmethod
    def get_interface_methods(
            cls,
            clsdict: Dict) -> Set[str]:
        return set(
            k for k, v in clsdict.items()
            if (isinstance(v, property)
                and getattr(v.fget, "__isinterfacemethod__", False))
            or getattr(v, "__isinterfacemethod__", False))

    @classmethod
    def get_interfaces(
            cls,
            bases: Tuple[Type, ...],
            clsdict: Dict) -> Tuple[Type["abstracts.Interface"], ...]:
        return tuple(
            x for x in clsdict["__implements__"]
            if (x not in bases and cls.is_interface(x)))

    @classmethod
    def implementation_info(
            cls,
            clsdict: Dict) -> Tuple[Dict[str, str], Dict[str, Type]]:
        """Returns 2 dictionaries

        - abstract_docs: abstract docs for all abstract classes
        - abstract_methods: resolved abstract methods -> abstract class
        """
        abstract_docs: Dict[str, str] = {}
        abstract_methods: Dict[str, Type] = {}
        for abstract in reversed(clsdict["__implements__"]):
            name, docs, methods = cls.abstract_info(abstract)
            for method in methods:
                abstract_methods[method] = abstract
            if docs:
                abstract_docs[name] = docs
        return abstract_docs, abstract_methods

    @classmethod
    def is_interface(
            cls,
            klass: Union["abstracts.Interface", "Implementer"]) -> bool:
        return (
            isinstance(klass, abstracts.Interface)
            and not isinstance(klass, abstracts.Abstraction))

    def __new__(
            cls,
            clsname: str,
            bases: Tuple[Type, ...],
            clsdict: Dict) -> "Implementer":
        """Create a new Implementer class"""
        if "__implements__" not in clsdict:
            klass = super().__new__(cls, clsname, bases, clsdict)
            if cls.is_interface(klass):
                cls.check_interface(clsdict)
            return klass
        ifaces = cls.get_interfaces(bases, clsdict)
        klass = super().__new__(
            cls, clsname, cls.get_bases(bases, clsdict), clsdict)
        cls.add_docs(clsdict, klass)
        cls.add_interfaces(ifaces, klass)
        return klass
