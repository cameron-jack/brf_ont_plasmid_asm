import os
import sys
from subprocess import Popen


def System(command: str):
    return os.system(command)


def Create(file: str):
    return System('echo "" > ' + file)


def Run_Program(command, out, err):
    p = Popen(
        command,
        stdout=out,
        stderr=err,
    )
    return_code = p.wait()
    return return_code


def Run_Program_Conda(env, command, out, err):
    command = ["conda", "run", "-p", env] + command
    return Run_Program(command, out, err)


def Rename(olddir, oldname, newdir, newname):
    # assume directories exist in advance
    System(f"mv {olddir}/{oldname} {newdir}/{newname}")


def Rename_multi(olddir, oldnames, newdir, newnames):
    for oldname, newname in zip(oldnames, newnames):
        Rename(olddir, oldname, newdir, newname)


def is_success(exit_code: int, out_log: str, err_log: str, prog: str):
    if exit_code != 0:
        print(f"Error while running {prog} with exit code {exit_code}!!!")
        print(f"Please check error log {err_log} and output log {out_log}")
        return False
    else:
        print(f"out log can be found at {out_log}")
        print(f"err log can be found at {err_log}")
        return True


def get_fasta_todict(fasta_file: str):
    res = {}
    lend = {}
    with open(fasta_file, "r") as fa_fd:
        sid = ""
        seq = ""
        for line in fa_fd:
            if line.startswith(">"):
                # process previous entry
                if sid != "":
                    res[sid] = seq
                    lend[sid] = len(seq)
                sid = line.strip()[1:]
                seq = ""
            else:
                seq += line.strip()
        fa_fd.close()
        if sid != "":
            res[sid] = seq
            lend[sid] = len(seq)
    return res, lend


def read_sample_status(ss_file: str):
    barcode = None
    status = None
    length = None
    with open(ss_file, "r") as fd:
        barcode, status, length = fd.readlines()[1].strip().split(",")
        fd.close()
    if status == "Completed successfully":
        return barcode, True, int(length)
    else:
        return barcode, False, None
