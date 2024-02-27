#!/bin/bash

BIN_PATH=$1
REF=$2
QRY=$3
PFX=$4 # prefix
ERR_LOG=$5
NCPUS=$6

export PATH=${BIN_PATH}:${PATH}

minimap2 -ax map-ont -t $NCPUS --secondary=no $REF $QRY -o $PFX.sam 2>>$ERR_LOG
if [ $? != 0 ]; then
    exit 1
fi

samtools sort -@$NCPUS -O BAM -o $PFX.bam $PFX.sam 2>>$ERR_LOG
if [ $? != 0 ]; then
    exit 1
fi

samtools index $PFX.bam 2>>$ERR_LOG
if [ $? != 0 ]; then
    exit 1
fi

exit 0