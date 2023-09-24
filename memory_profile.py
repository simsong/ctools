
################################################################
##
# memory profiling tools
##

import resource
import time

import total_size


def maxrss():
    """Return maxrss in bytes, not KB"""
    return resource.getrusage(resource.RUSAGE_SELF)[2]*1024


def print_maxrss():
    for who in ['RUSAGE_SELF', 'RUSAGE_CHILDREN']:
        rusage = resource.getrusage(getattr(resource, who))
        print(who, 'utime:', rusage[0], 'stime:',
              rusage[1], 'maxrss:', rusage[2])


def mem_info(what, df, dump=True):
    import pandas as pd
    start_time = time.time()
    print(f'mem_info {what} ({type(df)}):')
    if type(df) != pd.core.frame.DataFrame:
        print("Total {} memory usage: {:}".format(what, total_size(df)))
    else:
        if dump:
            pd.options.display.max_columns = 240
            pd.options.display.max_rows = 5
            pd.options.display.max_colwidth = 240
            print(df)
        for dtype in ['float', 'int', 'object']:
            selected_dtype = df.select_dtypes(include=[dtype])
            mean_usage_b = selected_dtype.memory_usage(deep=True).mean()
            mean_usage_mb = mean_usage_b / 1024 ** 2
            print("Average {} memory usage for {} columns: {:03.2f} MB".format(
                what, dtype, mean_usage_mb))
        for dt in ['object', 'int64']:
            for c in df.columns:
                try:
                    if df[c].dtype == dt:
                        print(f"{dt} column: {c}")
                except AttributeError:
                    pass
        df.info(verbose=False, max_cols=160,
                memory_usage='deep', null_counts=True)
    print("elapsed time at {}: {:.2f}".format(what, time.time() - start_time))
    print("==============================")
