import sys
from argparse import ArgumentParser as AP
from argparse import FileType as FT

if __name__ == "__main__":
    
    parser = AP(description="max sequence length checker")
    parser.add_argument('max_length', type=int, help="Maximum allowed sequence length")
    parser.add_argument('input', nargs='?', type=FT('r'), default=sys.stdin,
        help="Input file (default: stdin)")
    args = parser.parse_args()

    # Read and process the input
    record = []
    bad_record = False
    for i, line in enumerate(sys.stdin):
        if i % 4 == 0:
            if record:
                if not bad_record:
                    for l in record:
                        print(l)
                else:
                    bad_record = False
            record = [line.strip()]
        elif i % 4 == 1:  # sequence line in FASTQ format
            sequence = line.strip()
            if len(sequence) > args.max_length:
                bad_record = True
            else:
                record.append(sequence)
        else:
            record.append(line.strip())
    if record:
        if not bad_record:
            for l in record:
                print(l)
