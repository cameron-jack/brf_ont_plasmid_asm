import sys
import os
import datetime
import time

from utils.configs import *
from utils.utils import *


def assembly(
    prefix: str,
    fqdir: str,
    odir: str,
    barcode: str,
    sample: str,
    revision: str,
    asm_prefix="",
    add_prefix="",
    opts=[],
):
    ologfile = f"{prefix}_{sample}_{barcode}_{add_prefix}_{asm_prefix}.out.log"
    elogfile = f"{prefix}_{sample}_{barcode}_{add_prefix}_{asm_prefix}.err.log"
    asm_odir = f"{odir}/{sample}_{barcode}_{add_prefix}_{asm_prefix}"
    with open(ologfile, "w") as out, open(elogfile, "w") as err:
        command = [
            nextflow,
            "run",
            wf_clone_validation,
            "-r",
            revision,
            "--fastq",
            fqdir,
            "--out_dir",
            asm_odir,
        ] + opts

        return_code = Run_Program(command, out, err)
        out.close(), err.close()
    if not is_success(return_code, ologfile, elogfile, "wf clone validation"):
        print("Failed command: " + " ".join(command))
    return return_code, asm_odir


def asm_sample(
    prefix: str,
    fqdir: str,
    odir: str,
    barcode: str,
    sample: str,
    exp_size: str,
    apx_ratio: float,
    add_prefix="",
    opts=[],
):
    print(f">>>running plasmid assembly")
    ts = time.time()

    run_canu = False
    succ_asm_odir = None
    asm_type = None
    # run flye with normal case
    is_succ, asm_odir = assembly(
        prefix, fqdir, odir, barcode, sample, "8b9748bc00", "flye", add_prefix, opts
    )
    if is_succ:
        # check approx size
        _, status, err_str, alen = read_sample_status(f"{asm_odir}/sample_status.txt")
        if status == 1:  # check asm size
            if exp_size != "unknown":
                isize = int(exp_size)
                if isize != 0 and alen != 0:
                    # run flye with apx-size case
                    if max(alen, isize) / min(alen, isize) > apx_ratio:
                        print("plasmid is smaller/bigger than expected")
                        print(f"assembly size: {alen}, approximate size: {isize}")
                        print(f"rerun assembly with --approx_size {isize}")

                        is_succ, asm_odir = assembly(
                            prefix,
                            fqdir,
                            odir,
                            barcode,
                            sample,
                            "8b9748bc00",
                            f"flye_{isize}",
                            add_prefix,
                            opts + ["--approx_size", exp_size],
                        )
            else:
                succ_asm_odir = asm_odir
                asm_type = "flye"
        elif status > 1:  # run canu
            print(f"Flye assembly failed: {err_str}")
            run_canu = True
        else:
            print(f"Flye assembly failed with unknown error: {err_str}")

    if run_canu:
        if exp_size != "unknown":
            canu_revision = "v0.2.13"
            # pull image
            System(f"{nextflow} pull {wf_clone_validation} -revision {canu_revision}")
            is_succ, asm_odir = assembly(
                prefix,
                fqdir,
                odir,
                barcode,
                sample,
                canu_revision,
                f"canu_{alen}",
                add_prefix,
                opts + ["-approx_size", exp_size],
            )
            if is_succ:
                succ_asm_odir = asm_odir
                asm_type = "canu"
        else:
            print("Expect to run canu, but expected size is unknown")

    if succ_asm_odir == None:
        print(f"FAILURE")
        print(
            f"Please check error log {prefix}_{sample}_{barcode}_{add_prefix}*.err.log"
        )
        print(f"and output log {prefix}_{sample}_{barcode}_{add_prefix}*.err.log")
        return "", None

    print(f"SUCCESS with {asm_type} assembly, renamed as final version")
    final_asm_odir = f"{odir}/{sample}_{barcode}_{add_prefix}final"
    System(f"mv {succ_asm_odir}/ {final_asm_odir}/")

    # post assembly, format files
    # for now only be done for flye assembly
    if asm_type == "flye":
        Rename_multi(
            final_asm_odir,
            [
                f"{barcode}.final.fasta",
                f"{barcode}.annotations.bed",
                "wf-clone-validation-report.html",
            ],
            final_asm_odir,
            [
                f"{sample}.{barcode}.assembly.fasta",
                f"{sample}.{barcode}.annotations.bed",
                f"{sample}_{barcode}_assembly_report.html",
            ],
        )
        System(
            f'sed -i "s/{barcode}/{sample}_{barcode}/g" {final_asm_odir}/{sample}.{barcode}.assembly.fasta'
        )

    print("Done")
    print(f"time_elapsed {round(time.time() - ts, 2)} seconds")
    return asm_type, final_asm_odir