import utils.parsing_args as parsing_args
import utils.simp_prep as simp_prep
import utils.simp_exec as simp_exec


def run_prep(args):
    (root_dir, no_sample, ref_map, csv_file, caller) = args
    return simp_prep.simp_preparation(root_dir, no_sample, ref_map, csv_file, caller)


def run_exec(args):
    (root_dir, ref_map, cfg_file, apx_ratio, filt_first, caller) = args
    return simp_exec.simp_execution(
        root_dir, ref_map, cfg_file, apx_ratio, filt_first, caller
    )


if __name__ == "__main__":
    mode, args = parsing_args.argument_parsing()
    {"prep": run_prep, "exec": run_exec}[mode](args)
