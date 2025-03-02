import os
from functools import wraps
from conditional_method.lib import cfg, cfg_attr


# Example decorators to use with cfg_attr
def log_calls(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print("In `log_calls` decorator")
        print(f"Calling function: `{func.__name__}` with {args}, {kwargs}")
        result = func(*args, **kwargs)
        print(f"Function `{func.__name__}` returned: `{result}` ")
        print("Exiting `log_calls` decorator")
        return result

    return wrapper


def cache_result(func):
    cache = {}

    @wraps(func)
    def wrapper(*args, **kwargs):
        print("In `cache_result` decorator")
        key = str(args) + str(kwargs)
        print(f"Key: `{key}`")
        if key not in cache:
            print("Key not in cache, calling function")
            cache[key] = func(*args, **kwargs)
        else:
            print("Key in cache, returning cached result")
        print("Exiting `cache_result` decorator")
        return cache[key]

    return wrapper


# Set environment variables for our example
os.environ["ENV"] = "development"
os.environ["FEATURE_FLAG"] = "enabled"


# Example 1: Simple conditional function
@cfg_attr(condition=os.environ.get("ENV") == "production")
def connect_to_database():
    print("Connecting to PRODUCTION database")
    return "production_connection"


@cfg_attr(condition=os.environ.get("ENV") == "development")
def connect_to_database():
    print("Connecting to DEVELOPMENT database")
    return "development_connection"


# Example 2: Using decorators conditionally
@cfg_attr(
    condition=os.environ.get("ENV") == "development",
    decorators=[log_calls],  # Apply logging only in development
)
def process_data(data):
    print(f"Processing {len(data)} items")
    return [item.upper() for item in data]


# Example 3: Feature flag with multiple decorators
@cfg_attr(
    condition=os.environ.get("FEATURE_FLAG") == "enabled",
    decorators=[
        log_calls,
        cache_result,
    ],  # Apply both logging and caching if the feature flag is enabled
)
def experimental_feature(input_value):
    print("Running experimental feature")
    return f"Processed: {input_value}"


# Example 4: Class method conditional implementation
class ApiClient:
    @cfg(condition=os.environ.get("ENV") == "production")
    def fetch_data(self, endpoint):
        print(f"Production API call to {endpoint}")
        return {"status": "production_data"}

    @cfg(condition=os.environ.get("ENV") == "development")
    def fetch_data(self, endpoint):
        print(f"Development API call to {endpoint} with extra logging")
        return {"status": "development_data", "debug_info": "extra details"}


# Run the examples
if __name__ == "__main__":
    print("--- Example 1: Simple conditional function ---")
    result = connect_to_database()
    print(f"Result: {result}\n")

    print("--- Example 2: Using decorators conditionally ---")
    result = process_data(["a", "b", "c"])
    print(f"Result: {result}\n")

    print("--- Example 3: Feature flag with multiple decorators ---")
    try:
        result = experimental_feature("test_input")
        print(f"Result: {result}")
        print("--- Running again to test cache ---")
        result = experimental_feature("test_input")
        print(f"Result: {result}")
    except RuntimeError as e:
        print(f"Feature not available: {e}\n")

    print("--- Example 4: Class method conditional implementation ---")
    client = ApiClient()
    result = client.fetch_data("/users")
    print(f"Result: {result}")

# --- Example 1: Simple conditional function ---
# Connecting to DEVELOPMENT database
# Result: development_connection

# --- Example 2: Using decorators conditionally ---
# In `log_calls` decorator
# Calling function: `process_data` with (['a', 'b', 'c'],), {}
# Processing 3 items
# Function `process_data` returned: `['A', 'B', 'C']`
# Exiting `log_calls` decorator
# Result: ['A', 'B', 'C']

# --- Example 3: Feature flag with multiple decorators ---
# In `cache_result` decorator
# Key: `('test_input',){}`
# Key not in cache, calling function
# In `log_calls` decorator
# Calling function: `experimental_feature` with ('test_input',), {}
# Running experimental feature
# Function `experimental_feature` returned: `Processed: test_input`
# Exiting `log_calls` decorator
# Exiting `cache_result` decorator
# Result: Processed: test_input
# --- Running again to test cache ---
# In `cache_result` decorator
# Key: `('test_input',){}`
# Key in cache, returning cached result
# Exiting `cache_result` decorator
# Result: Processed: test_input
# --- Example 4: Class method conditional implementation ---
# Development API call to /users with extra logging
# Result: {'status': 'development_data', 'debug_info': 'extra details'}
