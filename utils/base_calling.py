import sys
import os
import datetime
import time

from utils.configs import *
from utils.utils import *

def base_calling_guppy(prefix: str, idir: str, odir: str, barcodes: list, run_through=True):
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
        print(
                f"Remove all intermediate basecalled directories {odir}/*, rerun base calling.."
            )
        System(f"rm -rf {odir}/*")
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
                guppy_model,
                "-r",
                "-x",
                "auto",
                "--disable_qscore_filtering",
                "--barcode_kits",
                guppy_kit,
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
        if not os.path.exists(f"{odir}/{barcode}_filt/merged.fastq"):
            System(f"cat {odir}/{barcode}/*.fastq > {odir}/{barcode}_filt/merged.fastq")

    print("Done")
    print(f"time_elapsed {round(time.time() - ts, 2)} seconds")
    return

def base_calling_dorado(prefix: str, idir: str, odir: str, barcodes: list, sample_sheet: str, run_through=True):
    print(f">>>Dorado Base calling..")
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
        print(
                f"Remove all intermediate basecalled directories {odir}/*, rerun base calling.."
            )
        System(f"rm -rf {odir}/*")

    if skip_basecalling:
        print("Skip base calling..")
        print(f"time_elapsed {round(time.time() - ts, 2)} seconds")
        return

    # base calling
    cbamfile = f"{odir}/calls.bam"
    elogfile = f"{prefix}.basecaller.err.log"
    ibamfile = ""
    if os.path.exists(cbamfile):
        ibamfile = f"{odir}/incomplete.bam"
        System(f"mv {cbamfile} {ibamfile}")
    
    with open(cbamfile, "w") as out, open(elogfile, "w") as err:
        command = [
            dorado_basecaller,
            "basecaller",
            dorado_model,
            idir,
            "--kit-name",
            dorado_kit
        ]
        if ibamfile != "":
            command += ["--resume-from", ibamfile]

        return_code = Run_Program(command, out, err)
        out.close(), err.close()
    
    if ibamfile != "":
        System(f"rm {ibamfile}")
    
    if not is_success(return_code, None, elogfile, "dorado base calling"):
        print("Command: " + " ".join(command))
        print("Exit..")
        sys.exit(1)

    # run demux
    ologfile = f"{prefix}.demux.out.log"
    elogfile = f"{prefix}.demux.err.log"
    with open(ologfile, "w") as out, open(elogfile, "w") as err:
        command = [
            dorado_basecaller,
            "demux",
            "--emit-fastq",
            "--kit-name",
            guppy_kit,
            "--sample-sheet",
            sample_sheet,
            "--output-dir",
            odir,
            cbamfile
        ]
        return_code = Run_Program(command, out, err)
        out.close(), err.close()
    
    if not is_success(return_code, None, elogfile, "dorado demux"):
        print("Command: " + " ".join(command))
        print("Exit..")
        sys.exit(1)

    # move fastq to directories
    for barcode in barcodes:
        os.makedirs(f"{odir}/{barcode}")
        os.makedirs(f"{odir}/{barcode}_filt")
        if not os.path.exists(f"{odir}/{barcode}.fastq"):
            print(f"Error! basecalling error, {odir}/{barcode}.fastq does not exists")
            print(f"Please check log files {prefix}.*.out(.err)")
            print("Exit..")
            sys.exit(1)

        System(f"mv {odir}/{barcode}.fastq {odir}/{barcode}/")
        System(f"ln -s {odir}/{barcode}/{barcode}.fastq {odir}/{barcode}_filt/merged.fastq")
    
    os.makedirs(f"{odir}/unclassified")
    for path in os.listdir(odir):
        if path.endswith(".fastq"):
            System(f"mv {odir}/{path} {odir}/unclassified/")

    
    print("Done")
    print(f"time_elapsed {round(time.time() - ts, 2)} seconds")
    return