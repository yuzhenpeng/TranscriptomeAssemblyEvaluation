# formerly CigarBedToOneBpResBed.py
import os
import argparse
from subprocess import Popen,PIPE
from Bio import SeqIO

def ExtractContigLengthFromFasta(fasta_handle):
    length_dict = {}
    for record in SeqIO.parse(fasta_handle,'fasta'):
        length_dict[record.id] = len(record.seq)
    return length_dict

def ParseBedWithCigar(bedline,keys=None):
    if keys == None:
        keys = ['target','start','end','query','mapqual','strand','cigar']
        bedline_dict = dict(zip(keys,bedline.strip().split('\t')))
    return bedline_dict

def ParseCigarToSingleBaseQueryCoordinates(bedline_dict,lengthdict):
    integers = '0123456789'
    query_consume_flags = ['M','I','S','=','X']
    writeables = ['M','=','X']
    strand_dict = {'+': 0,'-': 1}
    interval_length = ''
    cigar = bedline_dict['cigar']    
    target_position = int(bedline_dict['start'])
    query_position = (1,lengthdict[bedline_dict['query']])[strand_dict[bedline_dict['strand']]]    
    bed_intervals = []
    for character in cigar:
        if character in integers:
            interval_length+=character
        else:
            if character in query_consume_flags:
                for i in range(int(interval_length)):
                    bed_intervals.append('%s\t%s\t%s\t%s\t%s\t%s\n' % (bedline_dict['target'],target_position,target_position+1,bedline_dict['strand'],bedline_dict['query'],query_position))
                    if bedline_dict['strand'] == '+':
                        query_position+=1
                    else:
                        query_position-=1
                    target_position+=1
            else:
                target_position+=int(interval_length)
            interval_length = '' 
    
    return bed_intervals

def IntersectWithExons(targetbed,exonbed):
    cmd = 'intersectBed -wa -a %s -b %s > exons_%s' % (targetbed,exonbed,targetbed)
    proc = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    stdout, stderr = proc.communicate()
    return stdout,stderr

def ReformatSuperTsDepthBed(depthbed):
    """
    takes bedtools depth bed, which is not proper
    bed format, and converts it back to a 
    proper bed format
    """
    fin = open(depthbed,'r')
    fout = open('reformat_%s' % depthbed,'w')
    try:
        for line in fin:
            linelist = line.strip().split('\t')
            fout.write('%s\t%s\t%s\t%s\n' % (linelist[0],int(linelist[3])-1,linelist[3],linelist[4]))
        fout.close() 
        return ''
    except:
       return Exception('Could not convert %s to properly formatted depth bed\n' % depthbed)

def SortAndMergeBed(bed):
    sortcmd = 'sortBed -i %s > sorted_%s' % bed
    sortproc = Popen(sortcmd, shell=True, stdout=PIPE, stderr=PIPE)
    sortstdout, sortstderr = sortproc.communicate()
    mergecmd = 'mergeBed -i sorted_%s > merged_sorted_%s' % bed
    mergeproc = Popen(mergecmd, shell=True, stdout=PIPE, stderr=PIPE)
    mergestdout, mergestderr = mergeproc.communicate()
    return sortstderr,mergestderr   
    
def ConvertGenomicToSuperTscriptCoords(intersectbed):
    fin = open(intersectbed,'r')
    fout = open('supertscoords_%s' % intersectbed,'w')
    for line in fin:
        linelist = line.strip().split('\t')
        fout.write('%s\t%s\t%s\t%s\t%s\t%s\t%s\n' % (linelist[4],int(linelist[5])-1,linelist[5],linelist[0],linelist[1],linelist[2],linelist[3]))
    fout.close() 
        
def IntersectGmapSuperTsCoordWithDepth(supertsbed,depthbed):
    intersect_cmd = 'intersectBed -loj -a %s -b %s |awk \'{print $1"\t"$2"\t"$3"\t"$4"\t"$5"\t"$6"\t"$7"\t"$11}\'> wdepth_%s' % (supertsbed,depthbed,supertsbed)
    intersect_proc = Popen(intersect_cmd, shell=True, stdout=PIPE, stderr=PIPE)
    inter_stdout, inter_stderr = intersect_proc.communicate()
    return inter_stdout,inter_countstderr

def FilterVcfBySuperTsExonicSites(vcf,superexonbed):
    cmd = 'vcftools --vcf %s --recode --bed %s --out exonsonly' % (vcf,superexonbed)
    print cmd
    proc = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE) 
    stdout, stderr = proc.communicate()
    return stdout,stderr

def VcfToBed(vcf):
    vcfhead = open('%s.header' % vcf, 'w')
    vcfopen = open(vcf,'r')
    bedout = open('%s.bed' % vcf[:-4],'w')
    for line in vcfopen:
        if line[0] == '#':
            vcfhead.write(line)
        else:
            contig,position = line.strip().split('\t')[0],line.strip().split('\t')[1]
            bedvalstring = '\t'.join(line.strip().split('\t')[2:])
            bedout.write('%s\t%s\t%s\t%s\n' % (contig,int(position)-1, position,bedvalstring))
    bedout.close()

def IntersectGenotypesGenomicPosDepth(genotype_bed,depthbed):
    intersect_cmd = 'intersectBed -a %s -b %s > wGenomePosDepth_%s' % (depth_bed,genotype_bed,genotype_bed)
    proc = Popen(intersect_cmd, shell=True, stdout=PIPE, stderr=PIPE)
    stdout, stderr = proc.communicate()
    return stdout,stderr


if __name__=="__main__": 
    parser = argparse.ArgumentParser(description='Performs sundry format and coordinate conversions for comparing map-to-reference and map-to-SuperTranscripts genotypes from RNA-seq data')
    parser.add_argument('-i','--cigarbed_infile',dest='bedin',type=str,help='bed file with cigar string field')
    parser.add_argument('-f','-assembly_fasta',dest='afasta',type=str,help='fasta file of de novo transcriptome SuperTranscripts')
    parser.add_argument('-o','--bed_out',dest='outbed',type=str,help='output bed file')
    parser.add_argument('-ex','--exons_bed',dest='exons',type=str,help='merged genomic exons bed file')
    parser.add_argument('-sd','--superts_depth',dest='stdepthbed',type=str,help='name of bedtools output single base resolution depth file')
    parser.add_argument('-v','--vcf',dest='vcf',type=str,help='GATK filtered vcf file')
    parser.add_argument('-p','--polyploid',dest='polyploid',action='store_true')
    opts = parser.parse_args()
    
    logging = open('analysis.log','w')
    
    if opts.polyploid == False:
        if 'vcftools' not in ''.join(os.environ.values()):
            raise Exception('vcftools not in PATH but is required for diploid samples')  
            logging.write('WARNING: vcftools not in PATH but is required for diploid samples\n')
    if 'bedtools' not in ''.join(os.environ.values()):
        raise Exception('bedtools required but not in PATH')
        logging.write('WARNING:bedtools required but not in PATH\n')
    assembly_fasta = open(opts.afasta,'r')
    logging.write('building length dictionary from supertranscript assembly fasta\n')
    length_dict = ExtractContigLengthFromFasta(assembly_fasta)
    
    logging.write('transforming supertranscript coverage depth  into proper bed format\n')
    depth_fix = ReformatSuperTsDepthBed(opts.stdepthbed)
    
    logging.write('creating single base resolution bed file of superts mappings to genome, with superts coords as values\n')
    bedin = open(opts.bedin,'r')
    bedout = open(opts.outbed,'w')
    for line in bedin:
        bed_dict = ParseBedWithCigar(line,keys=None)  
        basecoord_intervals = ParseCigarToSingleBaseQueryCoordinates(bed_dict,length_dict)
        for coordinate in basecoord_intervals:
            bedout.write(coordinate)
    bedout.close()

    logging.write('intersecting single bp bed of superts mappings with genomic exons\n')
    intersectout,intersecterr = IntersectWithExons(opts.outbed,opts.exons)
    if intersecterr != '':
        print intersecterr
   
    logging.write('converting the exon-intersect bed of superts genomic mappings back to supertranscript coordinates\n')
    ConvertGenomicToSuperTscriptCoords('exons_%s' % opts.outbed)

    logging.write('left joining superts coverage to supertranscript exons intervals,in superts coords\n')
    callable_out,callable_err = IntersectGmapSuperTsCoordWithDepth('supertscoords_exons_%s' % opts.outbed, 'reformat_%s' % opts.stdepthbed)

    logging.write('filteing GATK-filtered vcf file to only contain exonic sites (in superts coords)\n')
    if opts.polyploid == False:
        vcffilt_out,vcffilt_err = FilterVcfBySuperTsExonicSites(opts.vcf,'supertscoords_exons_%s' % opts.outbed)
    else:
        VcfToBed(opts.vcf)
        IntersectWithExons('%s.bed' % opts.vcf[:-4],'supertscoords_exons_%s' % opts.outbed)
                
    logging.write('intersecting genotypes with genomic position and coverage data\n') 
    gtype_dp_intersect_out,gtype_dp_intersect_err=IntersectGenotypesGenomicPosDepth('supertscoords_exons_%s' % opts.vcf, 'superts_coords_exons_%s' % opts.outbed)