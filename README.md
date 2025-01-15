## BRF ONT Plasmid Assembly
Version 2.0
Replaces the original Simple Plasmid Pipeline by John Luo here: https://github.com/RunpengLuo/Simple_Plasmid

Requires one top-level directory for all the client plasmids you want to run in one go. 
Inside, you'd have one directory for each client. In each client directory you'd have 
an experiment directory for each separate plasmid (the barcode name, or sample name). 
Within that are all the FASTQ sequences files for that plasmid, an optional 
directory called "reference" - if you have a reference - and another optional directory 
called "insert" - for if you have a short fragment that you're trying to find in the plasmid.
 
You then a Python script called "plasmid_prep.py" which would take the path to that 
top-level directory. It would then make per-client tables that inform the pipeline how 
to run the samples, and would print the paths to each of these on the screen, so that 
you can then customise them if needed (unlikely).
 
It would also make a shell script for that top-level directory, which would run each of 
the stages of the pipeline for each of the clients and their samples. It'd just run each 
in turn. I think you'd be looking at perhaps being able to get through 10 plasmids per 
hour. It will run Nanofilt, the wf-clone-validation pipeline, 
and minimap2 (just the same as the existing pipeline).
 
There should be one report per client.

Run plasmid sequencing, assembly, and alignment as simple as it is.

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
plasmid_dir/
    | - clientA/
        | - fastq1...fastqN (.gz possible)
        | - reference/ref_filename.fa (optional)
        | - insert/insert_filename.fa (optional)
    | - clientB/
        | ...
    ...

### Running the plasmid assembly
To perform the actual pipeline, ensure that the whole output directory tree is available 
to the machine that will run the pipeline. Then you can simply execute the bash script
"run_plasmids.sh" in the top-level directory. This will execute each client pipeline sequentially.

### Notes
The old simp_plas.py script is deprecated and will be removed in the next release.
