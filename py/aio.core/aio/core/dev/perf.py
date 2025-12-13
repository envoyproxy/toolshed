
import functools
import time


def timing(fun):

    @functools.wraps(fun)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        value = fun(*args, **kwargs)
        end_time = time.perf_counter()
        run_time = end_time - start_time
        print("Finished {} in {} secs".format(
            repr(fun.__name__), round(run_time, 3)))
        return value

    return wrapper
