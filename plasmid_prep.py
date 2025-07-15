from argparse import ArgumentParser as AP
from pathlib import Path
import os
from datetime import datetime
from shutil import copy2, rmtree
import gzip


def generate_complete_run_script(top_dir_path, client_script_paths):
    """
    Make a top-level script that launches all client scripts sequentially
    top_dir_path = client_dir_path.parent
    """
    run_path = Path(top_dir_path) / 'run_plasmids.sh'
    with open(run_path,'wt') as fout:
        print('#!/bin/bash', file=fout)
        print('', file=fout)
        print('# this loads the conda environment', file=fout)
        print('source ~/.bashrc', file=fout)
        for csp in client_script_paths:
            print(f'./{csp.name}', file=fout)
    os.chmod(run_path, 0o755)
    print(f'Generated top-level script {run_path}')


def logstr_from_fastq_path(fp):
    """
    Return the str to a log file renames from the fastq path
    """
    suffix = ['.fq','.fq.gz','.fastq','.fastq.gz']
    fq_str = str(fp)
    for s in suffix:
        if fq_str.endswith(s):
            log_str = fq_str.replace(s,'.log')
            return log_str
    return ''


def generate_nanofilt_run_scripts(client_path, client_info, client_sheet, filter_path, maxfilt_path, prefilter_prefix='unfilt_', min_quality=15):
    """
    client_path - Path to client directory
    client_info - client_info dictionary
    client_sheet - user provided client/sample info (client,alias,barcode,size,reference)
    filter_path - path to filter program (Nanofilt or Chopper)
    prefilter_prefix - rename all fastq files with this prior to filtering
    For each sample, create a script which:
    - renames the original fastq XXX to unfilt_XXX
    - filters the unfilt_XXX file to the parameters given and outputs as XXX (matching the expected file names)
    The script should be in available in the client directory to avoid sample name clashes
    """
    filter_script_paths = []
    for sample_name in client_info[client_path.name]:
        size = client_sheet[client_path.name][sample_name].get('size','')
        if not size:
            print(f'No size provided for sample {sample_name} in client {client_path.name}. Exiting.')
            exit(1)
        min_size = int(size) - 2000
        max_size = int(size) + 2000
        filter_script_path = client_path / (str(sample_name) + '_filt.sh')
        with open(filter_script_path, 'wt') as fout:
            print('#!/bin/bash', file=fout)
            fq_files = client_info[client_path.name][sample_name]['fastq_files']
            # if client_info[client_path.name][sample_name]['collapse_fq']:
            #     fq_files = client_path/sample_name/client_info[client_path.name][sample_name]['collapse_fq']
            # else:
                
            for fp in fq_files:
                # print(f'{fp=} {fp.parent=}')
                prefilt_path = Path(client_path.name) / fp.parent.name / (str(prefilter_prefix) + fp.name)
                filt_path = Path(client_path.name)/str(sample_name)/fp.name
                log_path = logstr_from_fastq_path(filt_path)
                if not log_path:
                    log_path = '/dev/null'
                print(f'if [[ ! -e {prefilt_path} ]]', file=fout)
                print(f'then', file=fout)
                print(f'    mv {filt_path} {prefilt_path}', file=fout)
                print(f'fi', file=fout)
                ungzipped_filt_path = str(filt_path)[:-3]
                # trim off the .gz from the filt_path
                print(f'gunzip -c {prefilt_path} | {filter_path} -l {min_size} '+\
                        f'-q {min_quality} | python {maxfilt_path} {max_size} > '+\
                        f'{ungzipped_filt_path} 2> {log_path}', file=fout)
                print(f'')
                print(f'gzip {ungzipped_filt_path}', file=fout)
        os.chmod(filter_script_path, 0o755)
        filter_script_paths.append(filter_script_path)
    return filter_script_paths


def generate_client_run_script(client_sample_sheet_ref_path, client_sample_sheet_noref_path, client_info, client_sheet,
        client_path, 
        nextflow_path, pipeline_path, pipeline_version, filter_path, maxfilt_path, prefilter_prefix,
        minimap2_path, samtools_path):
    """
    Inputs:
        client_sample_sheet_path - path to client sample sheet
        client_info - client_info dictionary
        client_path - full path to client directory
        nextflow_path - path to nextflow installation
        pipeline_path - singularity container path
        pipeline_version - e.g. v1.6.0
        filter_path - path to Nanofilt or Chopper
        maxfilt_path - path to max_length.py script
        prefilter_prefix - a prefix applied to FASTQ files before filtering
        minimap2_path - path to minimap2
        samtools pth - path to samtools

    /mnt/c0d8cf05-4ff7-4ee0-b973-db5773baaa03/Simple_Plasmid_Fork/bin/nextflow \
    run epi2me-labs/wf-clone-validation -r v1.6.0 \
    --fastq /mnt/c0d8cf05-4ff7-4ee0-b973-db5773baaa03/plasmid_test2/calledFastq/barcode15/ \
    --out_dir /mnt/c0d8cf05-4ff7-4ee0-b973-db5773baaa03/plasmid_test2/asmOutput/20241108-Mla7-45-1--BC15_barcode15_raw_flye \
    --full_reference /mnt/c0d8cf05-4ff7-4ee0-b973-db5773baaa03/plasmid_test2/ReferenceMaps/20241108-Mla7-45-1--BC15.fasta \
    -profile singularity

    Runs: 
    1) Nanofilt
    2) ONT Plasmid Pipeline wf-clone-validation
    3) minimap2 of reads back to final assembly
    4) samtools index on the mapped BAM file

    """
    filter_script_paths = generate_nanofilt_run_scripts(client_path, client_info, client_sheet, filter_path, maxfilt_path, prefilter_prefix)
    client_script_path = client_path.parent/f'run_{client_path.name}.sh'
    client_name = client_path.name
    out_dn = client_name +"/output"
    #print(f'{client_info=}')
    with open(client_script_path, 'wt') as fout:
        print('#!/bin/bash', file=fout)
        print(f'', file=fout)
        print(f'# Comment any of the filtering script paths below to disable filtering prior to plasmid assembly', file=fout)
        for fsp in filter_script_paths:
            print(f'{client_name}/{fsp.name}', file=fout)
        print('', file=fout)
        if client_sample_sheet_ref_path:
            print('# ONT wf-clone-validation pipeline with reference', file=fout)
            print(f'{nextflow_path} \\', file=fout)
            print(f'run {pipeline_path} -r {pipeline_version} \\', file=fout)
            print(f'  --fastq {client_name} \\', file=fout)
            print(f'  --out_dir {out_dn} \\', file=fout)
            print(f'  --sample_sheet ./{client_sample_sheet_ref_path.name} \\', file=fout)
            print(f'  -profile singularity', file=fout)
            print(f'', file=fout)
        if client_sample_sheet_noref_path:
            print('# ONT wf-clone-validation pipeline without reference', file=fout)
            print(f'{nextflow_path} \\', file=fout)
            print(f'run {pipeline_path} -r {pipeline_version} \\', file=fout)
            print(f'  --fastq {client_name} \\', file=fout)
            print(f'  --out_dir {out_dn} \\', file=fout)
            print(f'  --sample_sheet ./{client_sample_sheet_noref_path.name} \\', file=fout)
            print(f'  -profile singularity', file=fout)
            print(f'', file=fout)
        print(f'# map each original FASTQ back to assembly', file=fout)
        for sample_name in client_info[client_path.name]:
            for fp in client_info[client_path.name][sample_name]['fastq_files']:
                alias = client_sheet[client_path.name][sample_name]['alias']
                assembly_fp = f'{client_path.name}/output/{alias}.final.fasta'  # path to assembled plasmid
                #print(f'Found fastq {fp=}')
                fi = Path(client_path.name)/sample_name/fp.name
                fo = rename_fastq_to_bam(fi)
                print(f'{minimap2_path} -x map-ont -a {assembly_fp} {fi} | {samtools_path} sort -o {fo} - ', file=fout)
                print(f'{samtools_path} index {fo}', file=fout)
                print(f'', file=fout)
    os.chmod(client_script_path, 0o755)
    return client_script_path


def generate_sample_sheets(client_info: dict, client_path: Path, client_sheet: dict):
    """
    Generate two sample sheets, one with reference and one without.
    If we ever want to use insert references then we'll need to add these separately too
    comma separate sample sheet file covering all client samples

    Inputs:
        client_info - dictionary of clients and samples
        client_path - full path to client directory
        client_sheet - user provided client/sample info (client,alias,barcode,size,reference)
    Returns:
        client_sample_sheet_noref_path, client_sample_sheet_ref_path

    note that 'barcode' is the name of the sample directory which contains fastq files for that sample
    cut_site is an optional cut site to check linearisation efficiency
    approx_size is taken from the sample sheet, but can be empty (which will crash the pipeline, on purpose)
    type defaults to 'test_sample' but could also be 'postive_control','negative_control','no_template_control'
    headers: alias, barcode, type, approx_size, cut_site, full_reference, insert_reference
    """
    client_sample_sheet_noref_path = None
    client_sample_sheet_ref_path = None
    samples_with_references = []
    samples_without_references = []
    for sample_name in client_info[client_path.name]:
        reference = str(client_info[client_path.name][sample_name].get('reference',''))
        if reference:
            samples_with_references.append(sample_name)
        else:
            samples_without_references.append(sample_name)
    
    if samples_with_references:
        client_sample_sheet_ref_path = client_path.parent / (str(client_path.name) + '_sample_sheet_ref.csv')
        with open(client_sample_sheet_ref_path, 'wt') as fout:
            print(','.join(['alias','barcode','type','approx_size','full_reference']), file=fout)
            for sample_name in samples_with_references:
                alias = client_sheet[client_path.name][sample_name]['alias']
                barcode = sample_name
                reference = str(client_info[client_path.name][sample_name].get('reference',''))
                #insert = str(client_info[client_path.name][sample_name].get('insert',''))
                print(','.join([alias,barcode,'test_sample','7000',reference]), file=fout)

    if samples_without_references:
        client_sample_sheet_noref_path = client_path.parent / (str(client_path.name) + '_sample_sheet_noref.csv')
        with open(client_sample_sheet_noref_path, 'wt') as fout:
            print(','.join(['alias','barcode','type','approx_size']), file=fout)
            for sample_name in samples_without_references:
                alias = client_sheet[client_path.name][sample_name]['alias']
                size = client_sheet[client_path.name][sample_name].get('size','')
                barcode = sample_name
                print(','.join([alias,barcode,'test_sample',size]), file=fout)
    
    return client_sample_sheet_noref_path, client_sample_sheet_ref_path


def check_fastq_name(fn):
    """
    Check that the FASTQ file name ends with the expected suffix. Ignore case.
    Returns True if name is good, otherwise False
    """
    suffix = ['.fq','.fq.gz','.fastq','.fastq.gz']
    for s in suffix:
        if str(fn).lower().endswith(s):
            return True
    return False


def check_fasta_name(fn:str) -> bool:
    """
    Check that the FASTA file name ends with the expected suffix. Ignore case
    Returns True if name is good, otherwise False
    """
    suffix = ['.fa','.fa.gz','.fasta','.fasta.gz']
    for s in suffix:
        if str(fn).lower().endswith(s):
            return True
    return False


def rename_fastq_to_bam(fp: str) -> Path|None:
    """
    Replace extension with .bam
    """
    suffix = ['.fq','.fq.gz','.fastq','.fastq.gz']
    for s in suffix:
        if str(fp).lower().endswith(s):
            return Path(str(fp).replace(s,'.bam'))

def parse_samplesheet(samplesheet: str):
    """
    Reads an ONT wf-clone-validation plasmid sample sheet: e.g. 
    client,alias,barcode,size,reference
    A,plasmid1,barcode21,7000,/path/to/reference.fa
    A,plasmid2,barcode22,3000,ref.fasta
    B,plasmid3,barcode23,21000,
    C,plasmid4,barcode24,14000,

    Returns a dict [client]={barcode:{'alias':'','ref':'','size':7000,'fastqs':[]}}
    """
    if not Path(samplesheet).exists():
        print(f'Samplesheet {samplesheet} does not exist')
        exit(1)
    if not Path(samplesheet).is_file():
        print(f'Samplesheet {samplesheet} is not a file. Did you swap the parameters by mistake?')
        exit(1)

    client_info = {}
    client_barcode_aliases = {}  # per client set of (barcode,alias) to ensure uniqueness
    with open(samplesheet, 'rt') as f:
        for i,line in enumerate(f):
            cols = line.split(',')
            if i==0 and cols[0].lower().startswith('client'):
                continue  # header
            if len(cols) < 4:
                continue  # we must have at least 4 columns: client,alias,barcode,size
            client = cols[0].strip().replace(' ','_')
            alias = cols[1].strip().replace(' ','_')
            barcode = cols[2].strip()
            size = cols[3].strip()  # no default size
            ref = ''
            if len(cols) > 4:  # optional reference in 4th column, ignore later columns 
                ref = cols[4].strip()
            if client not in client_info:
                client_info[client] = {}
                client_barcode_aliases[client] = set()
            if (barcode,alias) not in client_barcode_aliases[client]:
                client_barcode_aliases[client].add((barcode,alias))
            else:
                print(f'barcode {barcode} and alias {alias} are not a unique combination in client {client}')
                exit(1)
            if barcode not in client_info[client]:
                client_info[client][barcode] = {'alias':alias,'ref':ref,'size':size,'fastqs':[]}
            else:
                print(f'barcode {barcode} must be unique for client {client}')
                exit(1)
    return client_info


# now iterate through the PromethION directory tree looking for barcodes
def get_barcode_dirs(p, all_barcodes, chosen_dirs):
    """
    iterate through directories finding all the barcode dirs we want
    """
    dirs = [x for x in p.iterdir() if x.is_dir()]
    for d in dirs:
        if d.name == 'fastq_pass':
            bc_dirs = [x for x in d.iterdir() if x.is_dir() if x.name in all_barcodes]
            if bc_dirs:
                chosen_dirs.extend(bc_dirs)
        else:
            get_barcode_dirs(d, all_barcodes, chosen_dirs)
    return chosen_dirs


def parse_input_dirs(prom_dir, client_sheet):
    """
    Scans a PromethION directory structure:
        Mla7_45_pool/
            -> 20241121_1136_3C_PAW74316_2656d858/
                -> fastq_pass/
                    -> barcode21/ (fastqs)
    Should be able to find everything listed in client_sheet
    returns a dict source_dirs[client] = {barcode:path_to_barcode_dir}}
    """
    pdp = Path(prom_dir)
    if not pdp.exists():
        print(f"PromethION directory {pdp} does not exist")
        exit(1)
    if not pdp.is_dir():
        print(f"PromethION directory {pdp} is not a directory")
        exit(1)

    source_dirs = {}
    all_barcodes = set()
    for client in client_sheet:
        source_dirs[client] = {}
        for barcode in client_sheet[client]:
            source_dirs[client][barcode] = ''  # src dirname
            all_barcodes.add(barcode)

    barcode_dirs = get_barcode_dirs(pdp, all_barcodes, [])
    bcds = {bcd.name:bcd for bcd in barcode_dirs}
    bcd_names = set(bcds.keys())
    if all_barcodes.difference(bcd_names):
        print(f"Barcodes not found {all_barcodes.difference(bcd_names)}")
        exit(2)
    if bcd_names.difference(all_barcodes):
        print(f"Extra barcodes found {bcd_names.difference(all_barcodes)}")
        exit(2)
    
    for client in source_dirs:
        for barcode in source_dirs[client]:
            source_dirs[client][barcode] = bcds[barcode]

    return source_dirs


def create_new_structure(plasmid_dir, client_sheet, source_dirs, collapse=True, verbose=False):
    """
    Create new plasmid directory tree

    args:
    plasmid_dir - Path to new plasmid directory
    client_sheet - dict of client and barcode info provided by the user
    source_dirs - dict of provided client and barcode directories
    collapse - bool, whether to collapse FASTQs into a single file
    verbose - bool, whether to display more information about the process

    returns: 
    True if successful, otherwise False

    plasmid_run_20241217/ 
        -> clientA/
            -> barcode01/ (fastqs)
                -> reference/ (fasta)  optional
            -> barcode02/ (fastqs)
        -> clientB/
            -> barcode03/ (fastqs)
    By default the new barcode directories contain only the collapsed FASTQ file
    """
    #try:
        # make directories and copy files
    if True:
        if not plasmid_dir.exists():
            plasmid_dir.mkdir()
        for client in client_sheet:
            p = plasmid_dir / client
            if not p.exists():
                p.mkdir()
            for barcode in client_sheet[client]:
                bp = p/barcode
                if not bp.exists():
                    bp.mkdir()
                fps = [source_dirs[client][barcode]/f for f in os.listdir(source_dirs[client][barcode])]
                if collapse:
                    collapse_fp = plasmid_dir/client/barcode/f'{barcode}.fq.gz'
                    with gzip.open(collapse_fp,'wt') as fout:
                            for fp in fps:
                                if fp.name.lower().endswith('.gz'):
                                    if verbose:
                                        print(f'Collapsing {fp} to {collapse_fp}')
                                    with gzip.open(fp, 'rt') as f:
                                        for line in f:
                                            if line.strip():
                                                fout.write(line)
                                else:
                                    if verbose:
                                        print(f'Collapsing {fp} to {collapse_fp}')
                                    with open(fp, 'rt') as f:
                                        for line in f:
                                            if line.strip():
                                                fout.write(line)
                else:
                    for fp in fps:
                        if verbose:
                            print(f'Copying {fp} to {plasmid_dir/client/barcode}')
                        copy2(fp, plasmid_dir/client/barcode/fp.name)
                                    
                ref = client_sheet[client][barcode]['ref']
                if ref:
                    ref_dp = bp/'reference'
                    if not ref_dp.exists():
                        ref_dp.mkdir()
                    copy2(ref, ref_dp/Path(ref).name)
    # except Exception as exc:
    #     print(f'Failed to create new plasmid experiment directories {exc}')
    #     exit(3)
    return True
            

def main():
    """
    Replacement of original 'simple plasmid' project.

    Reads a (user provided) plasmid sample sheet of 3 or 4 columns: e.g. 
        client,alias,barcode,reference
        A,plasmid1,barcode21,/path/to/reference.fa
        A,plasmid2,barcode22,ref.fasta
        B,plasmid3,barcode23,
        C,plasmid4,barcode24,

    Scans a PromethION directory structure:
        Mla7_45_pool/
            -> 20241121_1136_3C_PAW74316_2656d858/
                -> fastq_pass/
                    -> barcode21/ (fastqs)

    And creates the required directory structure and all scripts, etc, for the ONT
    wf-clone-validation pipeline:
    plasmid_run_20241217/ 
        -> clientA/
            -> barcode01/ (fastqs)
                -> reference/ (fasta)  optional
            -> barcode02/ (fastqs)
        -> clientB/
            -> barcode03/ (fastqs)

    Requires one top-level directory for all the client plasmids you want to run in one go. 
    Inside, you'd have one directory for each client. In each client directory you'd have 
    an experiment directory for each separate plasmid (the barcode name, or sample name). 
    Within that are all the FASTQ sequences files for that plasmid, an optional 
    directory called "reference" - if you have a reference - and another optional directory 
    called "insert" - for if you have a short fragment that you're trying to find in the plasmid.

    """
    dt = datetime.today().strftime('%Y%m%d')
    plasmid_dn = f'plasmid_run_{dt}'
    
    parser = AP()
    parser.add_argument('prom_dir', help='Path to input PromethION sequencing')
    parser.add_argument('-s','--samplesheet', required=True, help='Path to 3 or 4 column samplesheet to set up experiment')
    parser.add_argument('-p', '--plasmid_dir', default=plasmid_dn, help='Path to output folder containing all client plasmid data')
    parser.add_argument('-v', '--verbose', action='store_true', help='Display more information about the prep process')
    parser.add_argument('-o','--overwrite', action='store_true', help='Overwrite existing plasmid directory')
    parser.add_argument('--minimap2', default='/mnt/c0d8cf05-4ff7-4ee0-b973-db5773baaa03/Simple_Plasmid_Fork/bin/minimap2', help='Path to minimap2')
    parser.add_argument('--samtools', default='/mnt/c0d8cf05-4ff7-4ee0-b973-db5773baaa03/Simple_Plasmid_Fork/bin/samtools', help='Path to samtools')
    parser.add_argument('--filter_path', default='/home/brf/lib/miniconda3/bin/NanoFilt', help='Path to nanofilt or chopper')
    parser.add_argument('--maxfilt_path', default='/mnt/c0d8cf05-4ff7-4ee0-b973-db5773baaa03/Simple_Plasmid_Fork/max_length.py', help='Path to maxfilt.py script')
    parser.add_argument('--nextflow', default='/mnt/c0d8cf05-4ff7-4ee0-b973-db5773baaa03/Simple_Plasmid_Fork/bin/nextflow', help='Path to nextflow')
    parser.add_argument('--pipeline_path', default='epi2me-labs/wf-clone-validation', help='Path to ONT wf-clone-validation pipeline')
    parser.add_argument('--pipeline_version', default='v1.6.0', help='wf-clone-validation pipeline version')
    parser.add_argument('--prefilter_prefix', default='unfilt_', help='Prefix for unfilterd FASTQs')
    parser.add_argument('--no_collapse', action='store_true', help='Disable collapsing FASTQs to a single file for each barcode')
    
    args = parser.parse_args()

    prom_dir = Path(args.prom_dir)
    if not prom_dir.exists():
        print(f'PromethION sequencing directory {prom_dir} does not exist')
        exit(1)
    
    plasmid_dir = Path(args.plasmid_dir)
    if plasmid_dir.exists():
        if not args.overwrite:
            print(f'Plasmid run directory {plasmid_dir} already exists. '+\
                    f'Please delete it, choose to overwrite it, or name a different output directory')
            exit(1)
        else:
            rmtree(plasmid_dir)
    plasmid_dir.mkdir()

    # client sheet is the user input about each client and sample
    client_sheet = parse_samplesheet(args.samplesheet)
    #print(f'{client_sheet=}')

    # create a dictionary of provided barcode directories for each client
    source_dirs = parse_input_dirs(args.prom_dir, client_sheet)

    #print(f'{copy_dirs=}')
    collapse_fastqs = True
    if args.no_collapse:
        collapse_fastqs = False
    success = create_new_structure(plasmid_dir, client_sheet, source_dirs, collapse=collapse_fastqs, verbose=args.verbose)

    if success:
        print(f'Successfully create plasmid directory {plasmid_dir}')

    #local_path = Path(os.path.realpath(__file__)).parent
    minimap2_fp = args.minimap2
    samtools_fp = args.samtools
    nextflow_fp = args.nextflow
    
    # each sample/alias has it's own set of records, alias is the barcode name and is the directory that holds the FASTQ files
    client_info = {}
    client_script_paths = []
    for client in client_sheet:
        cdir = plasmid_dir/client
        client_info[cdir.name] = {}
        sample_dirs = [d for d in cdir.glob('*') if d.is_dir() and str(d.name).startswith('barcode')]
        if not sample_dirs:
            print(f'Skipping client {cdir}, no sample directories found')
            continue
        if args.verbose:
            print(f'{cdir} contains samples: {sample_dirs}')

        # now create a sample_sheet.csv for each client so we run all their jobs together
        for sd in sample_dirs:
            client_info[cdir.name][sd.name] = {}
            
            seq_fns = [fp for fp in sd.glob('*') if fp.is_file() and check_fastq_name(fp.name)]
            if not seq_fns:
                print(f'No FASTQ (.fq/.fastq/.fq.gz/.fastq.gz files found for client {cdir.name} sample {sd.name}')
                exit(1)
            # 
            client_info[cdir.name][sd.name]['fastq_files'] = seq_fns
            
            ref_dir = sd.joinpath('reference')  # optional
            insert_dir = sd.joinpath('insert')  # optional

            if not ref_dir.exists():
                if args.verbose:
                    print(f'Reference directory {ref_dir} not found. Client {cdir.name} sample {sd.name}')
            else:
                if not ref_dir.is_dir():
                    print(f'Reference directory {ref_dir} is not a directory! Client {cdir.name} sample {sd.name}')
                    exit(1)
                ref_fp = [f for f in ref_dir.glob('*') if f.is_file() and check_fasta_name(f.name)]
                if len(ref_fp) != 1:
                    print(f'Reference files {ref_fp} found. There should be exactly one reference file')
                    exit(1)
                client_info[cdir.name][sd.name]['reference'] = Path(cdir.name)/sd.name/'reference'/ref_fp[0].name
                
            if not insert_dir.exists():
                if args.verbose:
                    print(f'Insert directory {insert_dir} not found. Client {cdir.name} sample {sd.name}')
            else:
                if not insert_dir.is_dir():
                    print(f'Insert directory {insert_dir} is not a directory! Client {cdir.name} sample {sd.name}')
                    exit(1)
                insert_fp = [f for f in insert_dir.glob('*') if f.is_file() and check_fasta_name(f.name)]
                if len(insert_fp) != 1:
                    print(f'Insert files {ref_fp} found. There should be exactly one insert file')
                    exit(1)
                client_info[cdir.name][sd.name]['insert'] = Path(cdir.name)/sd.name/'insert'/insert_fp[0].name

        # generate client sample sheets without, and with, references
        client_sample_sheet_noref_path, client_sample_sheet_ref_path = generate_sample_sheets(client_info, cdir, client_sheet)
        if client_sample_sheet_noref_path:
            print(f'Created sample sheet without reference sequences {client_sample_sheet_noref_path} for client {cdir.name}')
        if client_sample_sheet_ref_path:
            print(f'Created sample sheet with reference sequences {client_sample_sheet_ref_path} for client {cdir.name}')

        client_run_script_path = generate_client_run_script(client_sample_sheet_ref_path, 
                client_sample_sheet_noref_path, client_info, client_sheet, cdir, 
                nextflow_fp, args.pipeline_path, args.pipeline_version, args.filter_path, 
                args.maxfilt_path, args.prefilter_prefix, minimap2_fp, samtools_fp)
        print(f'Created script {client_run_script_path} for client {cdir.name}')
        client_script_paths.append(client_run_script_path)
        
    # generate an overall run script that launches everything else
    generate_complete_run_script(args.plasmid_dir, client_script_paths)


if __name__ == '__main__':
    main()
