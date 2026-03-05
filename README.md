## BRF ONT Plasmid Assembly
Version 3.04.001
Prepares a PromethION plasmid sequencing run for processing by the ONT 
Epi2me-labs wf-clone-validation pipeline using v1.8.4

Replaces the original Simple Plasmid Pipeline by John Luo here: https://github.com/RunpengLuo/Simple_Plasmid

There are two ways of running this pipeline.
1) Gadi cluster launch scripts using setup_plasmids.qsub
2) Local run scripts using plasmid_prep.py

Both require a PromethION sequencing directory, a plasmid sample sheet
from user, and an output path to build a new directory tree for downstream processing.

It then creates the directory tree structure expected by the wf-clone-validation
pipeline, and populates it with the appropriate files from the PromethION.
It also creates all the scripts to run each given client, collapses
multiple fastqs to a single file for each sample (you can disable this), filters
by sequence length and quality, runs the pipeline, and maps back
the reads against the assembled plasmid sequence.

You may provide custom reference sequences for each barcode in the
plasmid sample sheet (details below).
 
There is one report generated per client.

### Download and Setup
This pipeline requires a 64-bit Linux system and python (supported versions are python3.12 and higher).

Download the pipeline via Git:
```bash
git clone brf_ont_plasmid_asm
```

External dependencies:
* minimap2
* samtools
* Nanofilt (deprecated and to be replaced with Chopper - requires Ubuntu 20 or later)
* Chopper (https://github.com/wdecoster/chopper)
* Nextflow
* Singularity - temporary directories for cache and tmp are required to be linked from the scripts

Each tool can have custom paths provided via command line arguments.

### Running the prep
You must create a CSV (Comma Separated Value) file describing the client,sample_name, barcode, size, and the path to a reference file (if available). 

E.g. note that the names given are ficticious and you should use your actual client names. Also, if you leave spaces in client names, the pipeline will automatically change these to underscores _

$ cat sample_spreadsheet.csv 

client,alias,barcode,size,reference
A_Person,pEG11,barcode01,12302,
B_Researcher,11_2,barcode02,11456,
B_Researcher,11_4,barcode03,11456,
C_Labhead,P19-3,barcode04,13135,
C_Labhead,P19-4,barcode05,13135,
D_Student,D1,barcode09,9985,/g/data/vz35/PromethION_data/sequencer_uploads/ONT_PlasmidSeq_20260225/D1.fasta
D_Student,D2,barcode10,10217,/g/data/vz35/PromethION_data/sequencer_uploads/ONT_PlasmidSeq_20260225/D2.fasta
D_Student,D3,barcode11,10270,/g/data/vz35/PromethION_data/sequencer_uploads/ONT_PlasmidSeq_20260225/D3.fasta

### Output of prep
The prep stage will create a new directory structure that looks like this:

- plasmid_dir/
  - clientA/
    - fastq1...fastqN (.gz possible)
    - reference/ref_filename.fa (optional)
    - insert/insert_filename.fa (optional)
  - clientB/
    - ...
  - ...

This is required for the ONT pipelines to run.

# On Gadi

Edit the file setup_plasmids.qsub. It contains a section that looks like this:

### Set these variables and launch with qsub ###

# EMAIL is your email address to get Gadi job messages
EMAIL="brf.staff.name@anu.edu.au"

# PROMDATA is the path to the PromethION run containing the plasmids
PROMDATA="../PromethION_data/sequencer_uploads/ONT_PlasmidSeq_20260225/Plasmid_pool_relocated/20260225_1600_2B_PBK21844_1a3b8bcb"

# PLASDIR is the name of the directory you want to put the plasmid assemblies in
PLASDIR="plastest2"

# SAMPLESHEET is the path to the sample sheet that describes the plasmid samples, users, plasmid length, and any reference. You make this file!
SAMPLESHEET="../PromethION_data/sequencer_uploads/ONT_PlasmidSeq_20260225/plasmid_samplesheet_20260225.csv"

You should replace the quoted sections with names and paths that are appropriate for your run. PLASDIR is where your prepared pipeline files will end up.

Save your changes and the launch it to Gadi. This will run the plasmid_prep_gadi.py script for you. Launch it with: qsub ./setup_plasmids.qsub

# Local prep

Run plasmid_prep.py with command line arguments for the existing ONT data source, 
the output directory, and any other parameters as required. This will produce a new
directory tree that is populated with the files and structure expected by the ONT
wf-clone-validation pipeline. Pre-assembly filtering of reads is done by default with Nanofilt and passes on quality 15 and the expected size band +/- 2KB
by adjusting the run scripts that are produced for each client.


### Running the plasmid assembly

After the new directory structure has been created, you need to run the actual pipeline which will:
1) trim the reads to +/- 2KB of the expected plasmid size
2) Assemble the plasmid using Canu (we get better results with this than with Flye)
3) Map the reads back to the assembled plasmid

# On Gadi
Change directory (cd) into the directory defined in your setup_plasmids.qsub script by $PLASDIR. Launch all of your client processing jobs by running:
./run_plasmids.sh

This will launch each client's samples to the cluster as a separate job. Alternatively, you can launch individual client jobs e.g.
qsub ./run_A_user.qsub

# Running locally

To perform the actual pipeline, ensure that the whole output directory tree is available 
to the machine that will run the pipeline. Then you can simply execute the bash script
"run_plasmids.sh" in the top-level directory. This will execute each client pipeline sequentially.

### Outputs

The final outputs of the main ONT Plasmid Assembly pipeline will be in the client directory under /outputs/. There are many files here related to various stages of the pipeline.
In each barcode directory there will also be a BAM file, mapping the filtered reads back to the final assembly. This can be helpful for anyone wishing to check on the validity of the final assembly.


### Notes
Clean up and Zip of each client's set of output files and alignments is performed separately after the pipeline has completed.
