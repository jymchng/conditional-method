from cfg import cm


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

A().hello()
A().bye()
print("cm._cache: ", cm._cache)

print(A.__dict__)


@cm(condition=False)
class Person:
    def hello(self):
        print("Person::hello One")


print("cm._cache: ", cm._cache)


@cm(condition=True)
class Person:
    def hello(self):
        print("Person::hello Two")


print("cm._cache: ", cm._cache)


Person().hello()
print("cm._cache: ", cm._cache)
