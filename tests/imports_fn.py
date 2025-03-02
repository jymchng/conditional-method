from conditional_method import if_, cm
import os

os.environ["ENV"] = "LOCAL"

ENV = os.environ["ENV"]
assert ENV == "LOCAL"


@if_(condition=ENV == "PRODUCTION")
def env():
    return "PRODUCTION"


@if_(condition=ENV == "DEVELOPMENT")
def env():
    return "DEVELOPMENT"


@if_(condition=ENV == "PREPRODUCTION")
def env():
    return "PREPRODUCTION"


@if_(condition=ENV == "LOCAL")
def env():
    return "LOCAL"


@cm(condition=True)
class Person:
    def hello(self):
        return "Person::hello One"


@cm(condition=False)
class Person:
    def hello(self):
        return "Person::hello Two"
