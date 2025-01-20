## BRF ONT Plasmid Assembly
Version 3.00.001
Prepares a PromethION plasmid sequencing run for processing by the ONT 
Epi2me-labs wf-clone-validation pipeline.

Replaces the original Simple Plasmid Pipeline by John Luo here: https://github.com/RunpengLuo/Simple_Plasmid

Requires a PromethION sequencing directory, a plasmid sample sheet
from user, and a path to build a new directory tree.

It then creates the directory tree expected by the wf-clone-validation
pipeline, and populates it with the appropriate files from the PromethION.
It also creates all the scripts to run each given client, collapses
multiple fastqs to a single file for each sample, filters
by sequence length and quality, runs the pipeline, and maps back
the reads against the assembled plasmid sequence.

You may provide custom reference sequences for each barcode in the
plasmid sample sheet (details below).
 
There is one report generated per client.

### Download and Setup
This pipeline requires a 64-bit Linux system and python (supported versions are python3.8 and higher).

Download the pipeline via Git:
```bash
git clone brf_ont_plasmid_asm
```

External dependencies:
* minimap2
* samtools
* Nanofilt (deprecated and to be replaced with Chopper - requires Ubuntu 20 or later)
* Nextflow
* Singularity - make sure you have temporary directories assigned as environment variables
  for temp files and working space

Each of these by default will be expected to be found in $path, but full paths for each 
can be provided as command line arguments to plasmid_prep.py

### Running the prep
Call plasmid_prep.py with command line arguments for the existing ONT data source, 
the output directory, and any other parameters as required. This will produce a new
directory tree that is populated with the files and structure expected by the ONT
wf-clone-validation pipeline. It is possible to enable pre-assembly filtering of reads
by adjusting the run scripts that are produced for each client.

### Output:
- plasmid_dir/
  - clientA/
    - fastq1...fastqN (.gz possible)
    - reference/ref_filename.fa (optional)
    - insert/insert_filename.fa (optional)
  - clientB/
    - ...
  - ...

### Running the plasmid assembly
To perform the actual pipeline, ensure that the whole output directory tree is available 
to the machine that will run the pipeline. Then you can simply execute the bash script
"run_plasmids.sh" in the top-level directory. This will execute each client pipeline sequentially.

### Notes
Possibly zip up each client's set of output files and alignments.
