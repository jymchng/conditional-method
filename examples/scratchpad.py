from conditional_method import cm


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


A().hello()
A().bye()

print(B.__dict__)

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
