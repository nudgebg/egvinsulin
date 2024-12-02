from line_profiler import LineProfiler
import run_functions
import src.postprocessing as pp


# Profiling setup
lp = LineProfiler()
lp.add_function(run_functions.process_folder)
lp.add_function(pp.bolus_transform)
lp.add_function(pp.basal_transform)
lp.add_function(pp.cgm_transform)
lp_wrapper = lp(run_functions.main)
lp_wrapper(test=True)
lp.print_stats()