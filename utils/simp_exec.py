import sys
import os
import datetime
import time

from utils.configs import *
from utils.utils import *


def base_calling(prefix: str, idir: str, odir: str, barcodes: list, run_through=True):
    print(f">>>Guppy Base calling..")
    ts = time.time()

    skip_basecalling = False
    if all(os.path.isdir(f"{odir}/{barcode}") for barcode in barcodes):
        if run_through:
            print(
                "Found all intermediate directories required from configuration, skip base calling.."
            )
            skip_basecalling = True
        else:
            print(
                f"Remove all intermediate basecalled directories {odir}/*, rerun base calling.."
            )
            System(f"rm -rf {odir}/*")
    else:
        # remove corrupted intermediate directories if any
        for barcode in barcodes:
            if os.path.isdir(f"{odir}/{barcode}"):
                print(f"Remove intermediate corrupted basecalled dir: {odir}/{barcode}")
                System(f"rm -rf {odir}/{barcode}")
            if os.path.isdir(f"{odir}/{barcode}_filt"):
                print(
                    f"Remove intermediate corrupted basecalled dir: {odir}/{barcode}_filt"
                )
                System(f"rm -rf {odir}/{barcode}_filt")
    if not skip_basecalling:
        ologfile = f"{prefix}.out.log"
        elogfile = f"{prefix}.err.log"
        with open(ologfile, "w") as out, open(elogfile, "w") as err:
            command = [
                guppy_basecaller,
                "-i",
                idir,
                "-s",
                odir,
                "-c",
                "dna_r10.4.1_e8.2_400bps_sup.cfg",
                "-r",
                "-x",
                "auto",
                "--disable_qscore_filtering",
                "--barcode_kits",
                "SQK-RBK114-96",
            ]
            return_code = Run_Program(command, out, err)
            out.close(), err.close()
        if not is_success(return_code, ologfile, elogfile, "guppy base calling"):
            print("Command: " + " ".join(command))
            print("Exit..")
            sys.exit(1)

    # merge all fastq per barcode
    for barcode in barcodes:
        os.makedirs(f"{odir}/{barcode}_filt", exist_ok=True)
        System(f"cat {odir}/{barcode}/*.fastq > {odir}/{barcode}_filt/merged.fastq")

    print("Done")
    print(f"time_elapsed {round(time.time() - ts, 2)} seconds")
    return


def asm_sample(
    prefix: str,
    fqdir: str,
    odir: str,
    barcode: str,
    sample: str,
    nattempts: int,
    add_prefix="",
    opts=[],
):
    print(f">>>running plasmid assembly")
    ts = time.time()
    passed = False
    cattempt = 0
    asm_odir = f"{odir}/NULL"
    while cattempt < nattempts and not passed:
        cattempt += 1
        print(f"\ttrial {cattempt}")
        ologfile = f"{prefix}_{sample}_{barcode}_{add_prefix}trial{cattempt}.out.log"
        elogfile = f"{prefix}_{sample}_{barcode}_{add_prefix}trial{cattempt}.err.log"
        asm_odir = f"{odir}/{sample}_{barcode}_{add_prefix}trial{cattempt}"
        with open(ologfile, "w") as out, open(elogfile, "w") as err:
            command = [
                nextflow,
                "run",
                wf_clone_validation,
                "-r",
                "8b9748bc00",
                "--fastq",
                fqdir,
                "--out_dir",
                asm_odir,
            ] + opts

            return_code = Run_Program(command, out, err)
            out.close(), err.close()

        if not is_success(return_code, ologfile, elogfile, "wf clone validation"):
            print("Failed command: " + " ".join(command))
            passed = False
        else:
            _, is_succ, _ = read_sample_status(f"{asm_odir}/sample_status.txt")
            if is_succ:
                passed = True

    if not passed:
        print(f"FAILURE")
        print(
            f"Please check error log {prefix}_{sample}_{barcode}_{add_prefix}trial[*].err.log"
        )
        print(
            f"and output log {prefix}_{sample}_{barcode}_{add_prefix}trial[*].err.log"
        )
        return None

    print(f"SUCCESS")
    final_asm_odir = f"{odir}/{sample}_{barcode}_{add_prefix}final"
    System(f"mv {asm_odir}/ {final_asm_odir}/")

    # post assembly, format files
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
    return final_asm_odir


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
    nattempts: int,
    apx_ratio: float,
    filt_first: bool,
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
    for dir in [logs, bscall, asms, alns]:
        os.makedirs(dir, exist_ok=True)

    fast5sdir = root_dir + "/calledFast5"
    barcodes = [data[0] for data in samples]
    base_calling(f"{logs}/{cdata}_guppy", fast5sdir, bscall, barcodes)

    for barcode, sample, size, has_map, score, length in samples:
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
        asm_dir = asm_sample(
            asm_prefix,
            asm_fqdir,
            asms,
            barcode,
            sample,
            nattempts,
            add_prefix=asm_add_prefix,
        )
        if asm_dir == None:
            print("Skip..")
            continue

        _, _, alen = read_sample_status(f"{asm_dir}/sample_status.txt")
        if size != "unknown":
            isize = int(size)
            if size != 0 and alen != 0:
                if max(alen, isize) / min(alen, isize) > apx_ratio:
                    print("plasmid is smaller/bigger than expected")
                    print(f"assembly size: {alen}, approximate size: {isize}")
                    print(f"rerun assembly with --approx_size {isize}")

                    asm_dir = asm_sample(
                        asm_prefix,
                        asm_fqdir,
                        asms,
                        barcode,
                        sample,
                        nattempts,
                        add_prefix=asm_add_prefix + f"s{size}_",
                        opts=["--approx_size", size],
                    )

        System(f"gzip {filt_fq}")  # filt_fq is auto-removed by gzip later

        if has_map:
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
