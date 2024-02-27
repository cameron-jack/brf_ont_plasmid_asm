import argparse
import os
import sys


def argument_parsing():
    argp = argparse.ArgumentParser(
        prog="Simple Plasmid Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # create sub-parser
    sub_parsers = argp.add_subparsers(
        title="Mode",
        description="Select the operating mode",
        dest="mode",
        required=True,
    )

    parser_prep = sub_parsers.add_parser("prep", help="Preparation")
    parser_prep.add_argument(
        "-c",
        "--csv_file",
        dest="csv_file",
        type=str,
        required=True,
        help="SUMMARY CSV-format file",
    )

    parser_prep.add_argument(
        "-r",
        "--root_dir",
        dest="root_dir",
        type=str,
        required=True,
        help="path to the root directory, consists of subdirectories 1) no_sample and 2) ReferenceMaps.",
    )

    parser_exec = sub_parsers.add_parser("exec", help="Execution")

    parser_exec.add_argument(
        "-f",
        "--filt_first",
        dest="filt_first",
        action="store_true",
        default=False,
        help="if `-f` be set, filterred reads will be used for assembly, (default: False)",
    )

    parser_exec.add_argument(
        "-a",
        "--apx_ratio",
        dest="apx_ratio",
        type=float,
        default=1.5,
        help="rerun assembly (if size is given) with `-approx_size` option when ratio between alen and size > apx_ratio. (default: 1.5)",
    )

    parser_exec.add_argument(
        "-r",
        "--root_dir",
        dest="root_dir",
        type=str,
        required=True,
        help="path to the root directory after `prep` step.",
    )

    parser_exec.add_argument(
        "-n",
        "--num_attempts",
        dest="nattempts",
        type=int,
        required=False,
        default=1,
        help="number of attempts allowed per sample (default: 1)",
    )

    args = argp.parse_args()

    if not os.path.isdir(args.root_dir):
        print(
            f"Error! -r/--root_dir does not exist / not a directory, given {args.root_dir}"
        )
        print("Exit..")
        sys.exit(1)

    root_dir = os.path.abspath(args.root_dir)
    no_sample = root_dir + "/no_sample"
    ref_map = root_dir + "/ReferenceMaps"

    if not os.path.isdir(no_sample):
        print(f"Error! subdirectory {no_sample}/ does not exist.")
        print("Exit..")
        sys.exit(1)

    if not os.path.isdir(ref_map):
        print(f"Error! subdirectory {ref_map}/ does not exist.")
        print("Exit..")
        sys.exit(1)

    if args.mode == "prep":
        if not os.path.exists(args.csv_file):
            print(f"Error! -c/--csv_file does not exist, given {args.csv_file}")
            print("Exit..")
            sys.exit(1)
        return args.mode, (root_dir, no_sample, ref_map, args.csv_file)

    elif args.mode == "exec":
        cfg_file = root_dir + "/plas_config.csv"
        if not os.path.exists(cfg_file):
            print(f"Error! {cfg_file} does not exist.")
            print("Have you run `prep` mode?")
            print("Exit..")
            sys.exit(1)
        nattempts = args.nattempts
        if nattempts <= 0:
            print(
                f"Error, -n/--num_attempts should be integer larger than 0, given {nattempts}"
            )
            print("Exit..")
            sys.exit(1)

        apx_ratio = args.apx_ratio
        if apx_ratio <= 1.0:
            print(f"Error, -a/--apx_ratio must be greater than 1.0, given {apx_ratio}")
            print("Exit..")
            sys.exit(1)

        filt_first = args.filt_first

        return args.mode, (
            root_dir,
            ref_map,
            cfg_file,
            nattempts,
            apx_ratio,
            filt_first,
        )
    else:
        pass

    return None
