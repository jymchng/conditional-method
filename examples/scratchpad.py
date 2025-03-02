from conditional_method import cm
from conditional_method.lib import _raise_exec


class A:
    @cm(condition=False)
    def hello(self):
        print("A::hello; False")

    @cm(condition=False)
    def hello(self):
        print("A::hello; True")

    @cm(condition=False)
    def hello(self):
        print("A::hello; False 2")

    @cm(condition=True)
    def bye(self):
        print("A::bye; True")

    @cm(condition=False)
    def bye(self):
        print("A::bye; True 2")

    @cm(condition=True)
    def hello(self):
        print("A::hello True 2")


print("cm._cache: ", cm._cache)


class B:
    @cm(condition=True)
    @property
    def hello(self):
        print("B::hello; False")

    @cm(condition=False)
    def hello(self):
        print("B::hello; True")

    @cm(condition=False)
    def hello(self):
        print("B::hello; False 2")

    @cm(condition=False)
    def bye(self):
        print("B::bye; True")

    @cm(condition=True)
    def bye(self):
        print("B::bye; True 2")

    @cm(condition=True)
    @hello.setter
    def hello(self, value):
        print(f"B::hello.setter One; value = {value}")

    @cm(condition=False)
    @hello.setter
    def hello(self, value):
        print(f"B::hello.setter Two; value = {value}")


print("cm._cache: ", cm._cache)
A().hello()
A().bye()

print(B.__dict__)
print("cm._cache: ", cm._cache)

b = B()
b.hello = 69
b.hello
b.bye()


@cm(condition=False)
class Person:
    def hello(self):
        print("Person::hello One")


@cm(condition=True)
class Person:
    def hello(self):
        print("Person::hello Two")


Person().hello()


def cfg_attr(f=None, /, condition=None, decorators=()):
    if f is None:
        if condition is None:
            raise ValueError(
                "condition is required and must be a bool or a callable that takes the decorated function and returns a bool"
            )
        return lambda f: cfg_attr(f, condition=condition, decorators=decorators)
    if f is not None and condition:
        from functools import reduce

        return reduce(lambda f, arg: arg(f), decorators, f)
    return _raise_exec()


@cfg_attr(condition=False, decorators=[lambda f: f, lambda f: f])
def hey():
    print("::hey One")


hey()
print("cm._cache: ", cm._cache)
