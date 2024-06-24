import sys
import os
import datetime
import time

from utils.configs import *
from utils.utils import *

from utils.base_calling import *
from utils.assembly import asm_sample


def nano_filt_fastq(
    prefix: str, idir: str, barcode: str, sample: str, score: int, length: int
):
    print(f">>>running NanoFilt")
    ts = time.time()
    filt_fq_file = f"{idir}/{barcode}_filt/filt_l{length}_q{score}.fastq"
    elog_file = f"{prefix}_{sample}_{barcode}.err.log"
    with open(filt_fq_file, "w") as out, open(elog_file, "w") as err:
        command = [
            nanoFilt,
            "-l",
            str(length),
            "-q",
            str(score),
            f"{idir}/{barcode}_filt/merged.fastq",
        ]
        return_code = Run_Program_Conda(nanofilt_env, command, out, err)
        out.close(), err.close()

    if not is_success(return_code, None, elog_file, "NanoFilt filtering"):
        print("Command: " + " ".join(command))
        print(f"FAILURE")
        print(f"Please check {idir}/{barcode}_filt/merged.fastq")
        return None

    print(f"SUCCESS")
    System(f"rm {idir}/{barcode}_filt/merged.fastq")
    print("Done")
    print(f"time_elapsed {round(time.time() - ts, 2)} seconds")
    return filt_fq_file


def perf_alignment(
    prefix: str, op_prefix: str, ref_file: str, qry_file: str, barcode: str, sample: str
):
    print(f">>>running alignment")
    ts = time.time()
    elog_file = f"{prefix}_{sample}_{barcode}.err.log"
    # run alignments & indexing
    command = [
        "bash",
        alignment_sh_script,
        path2bin,
        ref_file,
        qry_file,
        op_prefix,
        elog_file,
        nthreads,
    ]

    ret = System(" ".join(command))
    if not is_success(ret, None, elog_file, "Minimap2 Alignment"):
        print("Command: " + " ".join(command))
        print(f"FAILURE - sample {sample} with barcode {barcode}")
        print(f"Please check reference file {ref_file} and query file {qry_file}")
        return None

    print("SUCCESS")
    print("Done")
    print(f"time_elapsed {round(time.time() - ts, 2)} seconds")
    return


def simp_execution(
    root_dir: str,
    ref_map: str,
    cfg_file: str,
    apx_ratio: float,
    filt_first: bool,
    caller: str
):
    print("===============Start Data Execution===============")
    samples = []
    with open(cfg_file, "r") as fd:
        for line in fd:
            samples.append(line.strip().split(","))
        fd.close()

    ts = time.time()
    cdata = datetime.date.today().__str__()
    logs = f"{root_dir}/logs"
    bscall = f"{root_dir}/calledFastq"
    asms = f"{root_dir}/asmOutput"
    alns = f"{root_dir}/alnOutput"
    tmps = f"{root_dir}/tmp"
    for dir in [logs, bscall, asms, alns, tmps]:
        os.makedirs(dir, exist_ok=True)

    if caller == "guppy":
        fast5sdir = root_dir + "/calledFast5"
        barcodes = [data[0] for data in samples]
        base_calling_guppy(f"{logs}/{cdata}_guppy", fast5sdir, bscall, tmps, barcodes)
    elif caller == "dorado":
        pod5sdir = root_dir + "/calledPod5"
        barcodes = [data[0] for data in samples]
        # sample_sheet = root_dir + "/sample_sheet.csv"
        base_calling_dorado(f"{logs}/{cdata}_dorado", pod5sdir, bscall, tmps, barcodes)
    else:
        print(f"Unknown caller option: {caller}")
        sys.exit(1)

    for barcode, sample, exp_size, has_map, score, length in samples:
        print(f"******Processing - {barcode} - {sample}******")
        ts1 = time.time()
        # {root_dir}/calledFastq/{barcode}_filt/filt_l{length}_q{score}.fastq
        filt_fq = nano_filt_fastq(
            f"{logs}/{cdata}_nanofilt", bscall, barcode, sample, score, length
        )
        if filt_fq == None:
            print("Skip..")
            continue

        # {root_dir}/asmOutput/{sample}_{barcode}_{asm_add_prefix}final
        asm_dir = None
        if filt_first:
            asm_prefix = f"{logs}/{cdata}_wf_cval_filt"
            asm_fqdir = f"{bscall}/{barcode}_filt/"
            asm_add_prefix = "filt_"
        else:
            asm_prefix = f"{logs}/{cdata}_wf_cval"
            asm_fqdir = f"{bscall}/{barcode}/"
            asm_add_prefix = "raw_"

        asm_type, asm_dir = asm_sample(
            asm_prefix,
            asm_fqdir,
            asms,
            barcode,
            sample,
            exp_size,
            apx_ratio,
            add_prefix=asm_add_prefix,
        )
        if asm_dir == None:
            print("Skip..")
            continue

        System(f"gzip {filt_fq}")  # filt_fq is auto-removed by gzip later

        if has_map == "1":
            rmap_file = f"{ref_map}/{sample}.fasta"
            perf_alignment(
                f"{logs}/{cdata}_aln",
                f"{alns}/aln_{sample}_{barcode}_l{length}_q{score}",
                rmap_file,
                f"{filt_fq}.gz",
                barcode,
                sample,
            )
        else:
            print("No reference map file provided, skip alignment.")

        print("Done")
        print(f"time_elapsed {round(time.time() - ts1, 2)} seconds")
        print()

    # clean up
    print("clean up..")
    for barcode in barcodes:
        System(f"rm -rf {bscall}/{barcode}_filt/")

    print(f"All the logs can be found under directory: {logs}")
    print(f"All the base-called fastq can be found under directory: {bscall}")
    print(f"All the assemblies can be found under directory: {asms}")
    print(f"All the alignments can be found under directory: {alns}")
    print("Done")
    print(f"time_elapsed {round(time.time() - ts, 2)} seconds")

    print("==============Complete Data Execution=============")

    return 0