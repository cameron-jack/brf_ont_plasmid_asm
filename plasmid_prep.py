from argparse import ArgumentParser as AP
from pathlib import Path
import os


def generate_complete_run_script(top_dir_path, client_script_paths):
    """
    Make a top-level script that launches all client scripts sequentially
    top_dir_path = client_dir_path.parent
    """
    run_path = Path(top_dir_path) / 'run_plasmids.sh'
    with open(run_path,'wt') as fout:
        print('#!/bin/bash', file=fout)
        for csp in client_script_paths:
            print(f'{top_dir_path}/{csp.name}', file=fout)
    os.chmod(run_path, 0o755)
    print(f'Generated top-level script {run_path}')


def logstr_from_fastq_path(fp):
    """
    Return the str to a log file renames from the fastq path
    """
    suffix = ['.fq','.fq.gz','.fastq','.fastq.gz']
    fq_str = str(fp).lower()
    for s in suffix:
        if fq_str.endswith(s):
            log_str = fq_str.replace(s,'.log')
            return log_str
    return ''


def generate_nanofilt_run_scripts(client_path, client_info, filter_path, prefilter_prefix='unfilt_', min_length=150, min_quality=10):
    """
    client_path - Path to client directory
    client_info - client_info dictionary
    filter_path - path to filter program (Nanofilt or Chopper)
    prefilter_prefix - rename all fastq files with this prior to filtering
    For each sample, create a script which:
    - renames the original fastq XXX to unfilt_XXX
    - filters the unfilt_XXX file to the parameters given and outputs as XXX (matching the expected file names)
    The script should be in available in the client directory to avoid sample name clashes
    """
    filter_script_paths = []
    for sample_name in client_info[client_path.name]:
        filter_script_path = client_path / (str(sample_name) + '_filt.sh')
        with open(filter_script_path, 'wt') as fout:
            print('#!/bin/bash', file=fout)
            for fp in client_info[client_path.name][sample_name]['fastq_files']:
                log_path = logstr_from_fastq_path(fp) 
                if not log_path:
                    log_path = '/dev/null'
                prefilt_path = fp.parent / (str(prefilter_prefix) + fp.name)
                print(f'if [[ ! -e {prefilt_path}]]', file=fout)
                print(f'then', file=fout)
                print(f'    mv {fp} {prefilt_path}', file=fout)
                print(f'fi', file=fout)
                print(f'{filter_path} -l {min_length} -q {min_quality} {prefilt_path} > {fp} 2> {log_path}', file=fout)
        os.chmod(filter_script_path, 0o755)
        filter_script_paths.append(filter_script_path)
    return filter_script_paths


def generate_client_run_script(client_sample_sheet_path, client_info, client_path, 
        nextflow_path, pipeline_path, pipeline_version, filter_path, prefilter_prefix,
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
    1) Nanofilt (if required)
    2) ONT Plasmid Pipeline wf-clone-validation
    3) minimap2 of reads back to final assembly
    4) samtools index on the mapped BAM file

    """
    filter_script_paths = generate_nanofilt_run_scripts(client_path, client_info, filter_path, prefilter_prefix)
    client_script_path = client_path.parent/f'run_{client_path.name}.sh'
    out_dn = client_path/"output"
    #print(f'{client_info=}')
    with open(client_script_path, 'wt') as fout:
        print('#!/bin/bash', file=fout)
        print(f'', file=fout)
        print(f'# Uncomment any of the filtering script paths below to run filtering prior to plasmid assembly', file=fout)
        for fsp in filter_script_paths:
            print(f'#{client_path.name}/{fsp.name}', file=fout)
        print('', file=fout)
        print('# ONT wf-clone-validation pipeline', file=fout)
        print(f'{nextflow_path} \\', file=fout)
        print(f'run {pipeline_path} -r {pipeline_version} \\', file=fout)
        print(f'  --fastq {client_path} \\', file=fout)
        print(f'  --output {out_dn} \\', file=fout)
        print(f'  --sample_sheet {client_sample_sheet_path} \\', file=fout)
        print(f'  -profile singularity', file=fout)
        print(f'', file=fout)
        print(f'# map each original FASTQ back to assembly', file=fout)
        for sample_name in client_info[client_path.name]:
            for fp in client_info[client_path.name][sample_name]['fastq_files']:
                assembly_fp = f'{out_dn}/{sample_name}.final.fasta'  # path to assembled plasmid
                #print(f'Found fastq {fp=}')
                fo = rename_fastq_to_bam(fp)
                print(f'{minimap2_path} -X map-ont -a {assembly_fp} {fp} | {samtools_path} sort -o {fo} - ', file=fout)
                print(f'{samtools_path} index {fo}', file=fout)
    os.chmod(client_script_path, 0o755)
    return client_script_path


def generate_sample_sheets(client_info, client_path):
    """
    Generate two sample sheets, one with reference and one without.
    If we ever want to use insert references then we'll need to add these separately too
    comma separate sample sheet file covering all client samples

    Inputs:
        client_info - dictionary of clients and samples
        client_path - full path to client directory
    Returns:
        client_sample_sheet_noref_path, client_sample_sheet_ref_path

    note that 'barcode' is the name of the sample directory which contains fastq files for that sample
    cut_site is an optional cut site to check linearisation efficiency
    approx_size defaults to 7000
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
                alias = sample_name
                barcode = sample_name
                reference = str(client_info[client_path.name][sample_name].get('reference',''))
                #insert = str(client_info[client_path.name][sample_name].get('insert',''))
                print(','.join([alias,barcode,'test_sample','7000',reference]), file=fout)

    if samples_without_references:
        client_sample_sheet_noref_path = client_path.parent / (str(client_path.name) + '_sample_sheet_noref.csv')
        with open(client_sample_sheet_noref_path, 'wt') as fout:
            print(','.join(['alias','barcode','type','approx_size']), file=fout)
            for sample_name in samples_without_references:
                alias = sample_name
                barcode = sample_name
                print(','.join([alias,barcode,'test_sample','7000']), file=fout)
    
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


def check_fasta_name(fn):
    """
    Check that the FASTA file name ends with the expected suffix. Ignore case
    Returns True if name is good, otherwise False
    """
    suffix = ['.fa','.fa.gz','.fasta','.fasta.gz']
    for s in suffix:
        if str(fn).lower().endswith(s):
            return True
    return False


def rename_fastq_to_bam(fp):
    """
    Replace extension with .bam
    """
    suffix = ['.fq','.fq.gz','.fastq','.fastq.gz']
    for s in suffix:
        if str(fp).lower().endswith(s):
            return Path(str(fp).replace(s,'.bam'))


def main():
    """
    Replacement of original 'simple plasmid' project.
    Requires one top-level directory for all the client plasmids you want to run in one go. 
    Inside, you'd have one directory for each client. In each client directory you'd have 
    an experiment directory for each separate plasmid (the barcode name, or sample name). 
    Within that are all the FASTQ sequences files for that plasmid, an optional 
    directory called "reference" - if you have a reference - and another optional directory 
    called "insert" - for if you have a short fragment that you're trying to find in the plasmid.
 
    You'd then a Python script called "plasmid_prep.py" which would take the path to that 
    top-level directory. It would then make per-client tables that inform the pipeline how 
    to run the samples, and would print the paths to each of these on the screen, so that 
    you can then customise them if needed (unlikely).
 
    It would also make a shell script for that top-level directory, which would run each of 
    the stages of the pipeline for each of the clients and their samples. It'd just run each 
    in turn. I think you'd be looking at perhaps being able to get through 10 plasmids per 
    hour. It will run Nanofilt, the wf-clone-validation pipeline, 
    and minimap2 (just the same as the existing pipeline).
 
    There should be one report per client.
    """

    parser = AP()
    parser.add_argument('plasmid_dir', help='Path to folder containing all client plasmid data')
    parser.add_argument('-v', '--verbose', help='Display more information about the prep process')
    parser.add_argument('--minimap2', default='bin/minimap2', help='Path to minimap2')
    parser.add_argument('--samtools', default='bin/samtools', help='Path to samtools')
    parser.add_argument('--filter_path', default='/home/brf/lib/miniconda3/bin/NanoFilt', help='Path to nanofilt or chopper')
    parser.add_argument('--nextflow', default='bin/nextflow', help='Path to nextflow')
    parser.add_argument('--pipeline_path', default='epi2me-labs/wf-clone-validation', help='Path to ONT wf-clone-validation pipeline')
    parser.add_argument('--pipeline_version', default='v1.6.0', help='wf-clone-validation pipeline version')
    parser.add_argument('--prefilter_prefix', default='unfilt_', help='Prefix for unfilterd FASTQs')
    parser.add_argument('--purge', action='store_true', help='Remove all old scripts and sample sheets from the top level plasmid directory before continuing')
    args = parser.parse_args()

    local_path = Path(os.path.realpath(__file__)).parent
    minimap2_fp = local_path/args.minimap2
    samtools_fp = local_path/args.samtools
    nextflow_fp = local_path/args.nextflow
    p = Path(args.plasmid_dir).absolute()
    if not p.exists():
        print(f'Error: no such directory {args.plasmid_dir}')
        exit(1)
    elif not p.is_dir():
        print(f'Error: {args.plasmid_dir} is not a directory')
        exit(1)
    
    client_dirs = [d for d in p.glob('*') if d.is_dir()]
    if not client_dirs:
        print(f'Error: no client directories found in {args.plasmid_dir}')
        exit(1)
    if args.verbose:
        print(f'Client directories found: {client_dirs}')

    if args.purge:
        old_files = [f for f in p.glob('*') if f.is_file() and \
                (str(f).endswith('.csv') or str(f).endswith('.sh'))]
        for d in client_dirs:
            for fp in d.glob('*'):
                if fp.is_file() and str(fp).endswith(f'_filt.sh'):
                    old_files.append(fp)
        for old_fp in old_files:
            print(f'Purging existing file {old_fp}')
            old_fp.unlink()

    # each sample/alias has it's own set of records, alias is the barcode name and is the directory that holds the FASTQ files
    client_info = {}
    client_script_paths = []
    for cdir in client_dirs:
        client_info[cdir.name] = {}
        sample_dirs = [d for d in cdir.glob('*') if d.is_dir()]
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
                client_info[cdir.name][sd.name]['reference'] = ref_fp[0]
                
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
                client_info[cdir.name][sd.name]['insert'] = insert_fp[0]

        # generate client sample sheets without, and with, references
        client_sample_sheet_noref_path, client_sample_sheet_ref_path = generate_sample_sheets(client_info, cdir)
        if client_sample_sheet_noref_path:
            print(f'Created sample sheet with no reference sequences {client_sample_sheet_noref_path} for client {cdir.name}')
            client_run_script_noref_path = generate_client_run_script(client_sample_sheet_noref_path, client_info, cdir, 
                    nextflow_fp, args.pipeline_path, args.pipeline_version, args.filter_path, 
                    args.prefilter_prefix, minimap2_fp, samtools_fp)
            print(f'Created no reference script {client_run_script_noref_path} for client {cdir.name}')
            client_script_paths.append(client_run_script_noref_path)
        if client_sample_sheet_ref_path:
            print(f'Created sample sheet with reference sequences {client_sample_sheet_ref_path} for client {cdir.name}')
            client_run_script_ref_path = generate_client_run_script(client_sample_sheet_ref_path, client_info, cdir, 
                    nextflow_fp, args.pipeline_path, args.pipeline_version, args.filter_path, 
                    args.prefilter_prefix, minimap2_fp, samtools_fp)
            print(f'Created with reference script {client_run_script_ref_path} for client {cdir.name}')
            client_script_paths.append(client_run_script_ref_path)
        
    # generate an overall run script that launches everything else
    generate_complete_run_script(args.plasmid_dir, client_script_paths)


if __name__ == '__main__':
    main()