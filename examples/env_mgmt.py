from conditional_method import conditional_method

import os

ENVIRONMENT_KEY = "ENVIRONMENT_KEY"
os.environ[ENVIRONMENT_KEY] = "production"

ENVIRONMENT = os.environ[ENVIRONMENT_KEY]


class Worker:
    __slots__ = ()

    @conditional_method(condition=ENVIRONMENT == "production")
    def work(self, *args, **kwargs):
        print("Working in production")
        print(f"Args: {args}")
        print(f"Kwargs: {kwargs}")
        return "production"

    @conditional_method(condition=ENVIRONMENT == "development")
    def work(self, *args, **kwargs):
        print("Working in development")
        print(f"Args: {args}")
        print(f"Kwargs: {kwargs}")
        return "development"

    @conditional_method(condition=ENVIRONMENT == "staging")
    def work(self, *args, **kwargs):
        print("Working in staging")
        print(f"Args: {args}")
        print(f"Kwargs: {kwargs}")
        return "staging"


class WorkerTwo:
    __slots__ = ()

    @conditional_method(condition=ENVIRONMENT == "production")
    def work(self, *args, **kwargs):
        print("WorkerTwo: Working in production")
        print(f"Args: {args}")
        print(f"Kwargs: {kwargs}")
        return "production"

    @conditional_method(condition=ENVIRONMENT == "development")
    def work(self, *args, **kwargs):
        print("WorkerTwo: Working in development")
        print(f"Args: {args}")
        print(f"Kwargs: {kwargs}")
        return "development"

    @conditional_method(condition=ENVIRONMENT == "staging")
    def work(self, *args, **kwargs):
        print("WorkerTwo: Working in staging")
        print(f"Args: {args}")
        print(f"Kwargs: {kwargs}")
        return "staging"


worker = Worker()

print(f"ENVIRONMENT: {ENVIRONMENT}")  # ENVIRONMENT: production
print(f"Worker.__dict__: {Worker.__dict__}")
# only one of the `work` methods will be bound to the Worker class
# Worker.__dict__: {
#     '__module__': '__main__',
#     '__slots__': (),
#     'work': <function Worker.work at 0x7f6151683670>,
#     '__doc__': None
# }

print(worker.work(1, 2, 3, a=4, b=5))

# Working in production
# Args: (1, 2, 3)
# Kwargs: {'a': 4, 'b': 5}
# production (return value of the selected method)


worker_two = WorkerTwo()

print(worker_two.work(1, 2, 3, a=4, b=5))

# WorkerTwo: Working in production
# Args: (1, 2, 3)
# Kwargs: {'a': 4, 'b': 5}
# production (return value of the selected method)
