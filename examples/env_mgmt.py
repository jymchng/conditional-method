from src.conditional_method.lib import conditional_method

import os

ENVIRONMENT_KEY = "ENVIRONMENT_KEY"

os.environ[ENVIRONMENT_KEY] = "production"

ENVIRONMENT = os.environ[ENVIRONMENT_KEY]


class Worker:
    __slots__ = ()

    @conditional_method(condition=lambda: ENVIRONMENT == "production")
    def work(self, *args, **kwargs):
        print("Working in production")
        print(f"Args: {args}")
        print(f"Kwargs: {kwargs}")
        return "production"

    @conditional_method(condition=lambda: ENVIRONMENT == "development")
    def work(self, *args, **kwargs):
        print("Working in development")
        print(f"Args: {args}")
        print(f"Kwargs: {kwargs}")
        return "development"

    @conditional_method(condition=lambda: ENVIRONMENT == "staging")
    def work(self, *args, **kwargs):
        print("Working in staging")
        print(f"Args: {args}")
        print(f"Kwargs: {kwargs}")
        return "staging"


worker = Worker()

print(f"ENVIRONMENT: {ENVIRONMENT}")
print(f"Worker.__dict__: {Worker.__dict__}")
# only one of the `work` methods will be bound to the Worker class

print(worker.work(1, 2, 3, a=4, b=5))
