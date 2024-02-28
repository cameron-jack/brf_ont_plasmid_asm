import os
import sys
import re
from utils.utils import System, Create, get_fasta_todict


# columns
# sample name
# barcode
# supplied map?
# path to map
# quality cutoff
# length cutoff
# size (bp)
def simp_preparation(root_dir: str, no_sample: str, ref_map: str, csv_file: str):
    print("===============Start Data Preparation===============")
    print(f">>>Parsing SUMMARY csv file {csv_file}..")
    samples = []
    with open(csv_file, "r", encoding='utf-8-sig') as fd:
        header = [s.lower() for s in fd.readline().strip().split(",")]
        hidx = {}
        for i, name in enumerate(header):
            hidx[name] = i

        for j, line in enumerate(fd.readlines()):
            row = line.strip().split(",")
            sample = row[hidx["sample name"]]
            barcode = row[hidx["barcode"]]
            has_map = 1 if row[hidx["supplied map?"]] == "Y" else 0
            if has_map:
                path_to_map = row[hidx["path to map"]]
                if path_to_map == "" or not os.path.exists(ref_map + "/" + path_to_map):
                    print(
                        f"Error! refmap file does not exist but claimed for existence."
                    )
                    print(f"Please investigate {j+2}th line in the {csv_file}")
                    print("Exit..")
                    fd.close()
                    sys.exit(1)
            else:
                path_to_map = None

            if row[hidx["quality cutoff"]] == "":
                score = 11  # default quality score cutoff
            else:
                if not str.isdecimal(row[hidx["quality cutoff"]]):
                    print(
                        f"Error! quality cutoff {row[hidx['quality cutoff']]} is not decimal"
                    )
                    print(f"Please investigate {j+2}th line in the {csv_file}")
                    print("Exit..")
                    fd.close()
                    sys.exit(1)
                score = row[hidx["quality cutoff"]]

            if row[hidx["length cutoff"]] == "":
                length = 0  # default length cutoff
            else:
                if not str.isdecimal(row[hidx["length cutoff"]]):
                    print(
                        f"Error! length cutoff {row[hidx['length cutoff']]} is not decimal"
                    )
                    print(f"Please investigate {j+2}th line in the {csv_file}")
                    print("Exit..")
                    fd.close()
                    sys.exit(1)
                length = row[hidx["length cutoff"]]

            tmp_size = row[hidx["size (bp)"]]
            if tmp_size == "":
                size = 0
            else:
                if not str.isdecimal(tmp_size):
                    print(f"Error! approx size {tmp_size} is not decimal")
                    print(f"Please investigate {j+2}th line in the {csv_file}")
                    print("Exit..")
                    fd.close()
                    sys.exit(1)
                size = tmp_size

            samples.append((sample, barcode, size, has_map, path_to_map, score, length))
        fd.close()

    if len(samples) == 0:
        print(f"No legal sample information be found in the file {csv_file}")
        print("Please double check the csv file")
        print("Exit..")
        sys.exit(1)
    print("Done")

    cfg_file = root_dir + "/plas_config.csv"
    Create(cfg_file)

    # correct naming, get a formatted CSV record for execution
    print(f">>>Preparing config file {cfg_file}..")
    barcodes_sanity = {}
    with open(cfg_file, "w") as fd:
        for sample, barcode, size, has_map, path_to_map, score, length in samples:

            # 0. check collide barcode(s)
            if barcode in barcodes_sanity:
                print(f"Error! First barcode collision found: {barcode}")
                print(
                    f"Please investigate sample {sample} and {barcodes_sanity[barcode]} in the {csv_file}"
                )
                print("Exit..")
                fd.close()
                sys.exit(1)
            else:
                barcodes_sanity[barcode] = sample

            # 1. format sample name and barcode
            # - any non (digits, alphabets, dashes) characters will be replaced by dash
            new_sample = re.sub("[^0-9a-zA-Z-]+", "-", sample.strip())
            barcode = "barcode" + barcode

            # 2. format refmap file
            dst_file = "NULL"
            if has_map:
                res, _ = get_fasta_todict(ref_map + f"/{path_to_map}")
                if len(res) != 1:
                    print(
                        f"Error! #reference in the refmap file {ref_map}/{path_to_map} for sample {sample} is more than 1"
                    )
                    print(
                        f"Please investigate sample {sample} with barcode {barcode} in the {csv_file}"
                    )
                    print("Exit..")
                    fd.close()
                    sys.exit(1)

                dst_file = ref_map + f"/{new_sample}.fasta"
                Create(dst_file)
                with open(dst_file, "w") as fa:
                    for _, rseq in res.items():
                        fa.write(f">{new_sample}\n{rseq}\n")
                    fa.close()
                System(f"rm {ref_map}/{path_to_map}")

            # 3. write to formatted csv
            fd.write(f"{barcode},{new_sample},{size},{has_map},{score},{length}\n")
        fd.close()
    print("Done")

    # move all fast5 files to <root_dir>/calledFast5/
    fast5sdir = root_dir + "/calledFast5"
    os.makedirs(fast5sdir, exist_ok=True)
    System(f'find {no_sample} -type f -name "*.fast5" | xargs -I X mv X {fast5sdir}/.')
    print(f">>>All fast5 files under {no_sample} have been moved to {fast5sdir}/")
    cfast5 = 0
    for fname in os.listdir(fast5sdir):
        if fname.endswith(".fast5"):
            print(f"\t{fname}")
            cfast5 += 1
        else:
            print(f"\tWarning, non-fast5 file found: {fname}")
    print(f"Number of fast5 file in {fast5sdir}: {cfast5}")
    print("==============Complete Data Preparation=============")

    return 0
