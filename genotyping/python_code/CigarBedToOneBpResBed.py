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
    #if sortproc.returncode != 0:
    mergecmd = 'mergeBed -i sorted_%s > merged_sorted_%s' % bed
    mergeproc = Popen(mergecmd, shell=True, stdout=PIPE, stderr=PIPE)
    mergestdout, mergestderr = mergeproc.communicate()
    return sortstderr,mergestderr   
    
def ConvertGenomicToSuperTscriptCoords(intersectbed):
    fin = open(intersectbed,'r')
    fout = open('supertscoords_%s' % intersectbed,'w')
    for line in fin:
        linelist = line.strip().split('\t')
        fout.write('%s\t%s\t%s\n' % (linelist[4],int(linelist[5])-1,linelist[5]))
    fout.close() 
        
def IntersectGmapSuperTsCoordWithDepth(supertsbed,depthbed):
    intersect_cmd = 'intersectBed -a %s -b %s > mindepth5_%s' % (supertsbed,depthbed,supertsbed)
    intersect_proc = Popen(intersect_cmd, shell=True, stdout=PIPE, stderr=PIPE)
    inter_stdout, inter_stderr = intersect_proc.communicate()
    count_cmd = 'wc -l mindepth5_%s' % supertsbed
    count_proc = Popen(count_cmd, shell=True, stdout=PIPE, stderr=PIPE)
    countstdout, countstderr = count_proc.communicate()
    return countstdout,countstderr

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
        
def BedToVcf(bed,header):
    vcf=open('%s.vcf' % bed[:-4],'w')
    headin=open(header,'r')
    for line in headin:
        vcf.write(line)
    bedin = open(bed,'r')
    for line in bedin:
        linelist = line.strip().split('\t')
        contig,position = linelist[0],linelist[2]
        fieldsdata = '\t'.join(linelist[3:])
        vcf.write('%s\t%s\t%s\n' % (contig,position,fieldsdata))
    vcf.close()



if __name__=="__main__": 
    parser = argparse.ArgumentParser(description="Converts bed file with cigar string, of sequence alignment")
    parser.add_argument('-i','--cigarbed_infile',dest='bedin',type=str,help='bed file with cigar string field')
    parser.add_argument('-f','-assembly_fasta',dest='afasta',type=str,help='fasta file of de novo transcriptome assembly')
    parser.add_argument('-o','--bed_out',dest='outbed',type=str,help='output bed file')
    parser.add_argument('-ex','--exons_bed',dest='exons',type=str,help='merged genomic exons bed file')
    parser.add_argument('-sd','--superts_depth_bed',dest='stdepthbed',type=str,help='name of bedtools output single base resolution depth file')
    parser.add_argument('-v','--vcf',dest='vcf',type=str,help='GATK filtered vcf file')
    parser.add_argument('-p','--polyploid',dest='polyploid',action='store_true')
    opts = parser.parse_args()
    
    assembly_fasta = open(opts.afasta,'r')
    length_dict = ExtractContigLengthFromFasta(assembly_fasta)
    
    #### transform supertranscript depth bed into proper format  ### 
    depth_fix = ReformatSuperTsDepthBed(opts.stdepthbed)
    
    #### create single base resolution bed file of superts mappings to genome, with superts coords as values ###
    bedin = open(opts.bedin,'r')
    bedout = open(opts.outbed,'w')
    for line in bedin:
        bed_dict = ParseBedWithCigar(line,keys=None)  
        basecoord_intervals = ParseCigarToSingleBaseQueryCoordinates(bed_dict,length_dict)
        for coordinate in basecoord_intervals:
            bedout.write(coordinate)
    bedout.close()

    #### intersect single bp bed with genomic exons ### OK
    intersectout,intersecterr = IntersectWithExons(opts.outbed,opts.exons)
    if intersecterr != '':
        print intersecterr
   
    #### convert the exon-intersect bed back to supertranscript coordinates ## OK
    ConvertGenomicToSuperTscriptCoords('exons_%s' % opts.outbed)

    ### get callable sites ###
    callable_out,callable_err = IntersectGmapSuperTsCoordWithDepth('supertscoords_exons_%s' % opts.outbed, 'reformat_%s' % opts.stdepthbed)
    print 'callable sites: ', callable_out
    callwrite = open('callable_sites','w')
    callwrite.write('%s\n' % callable_out)
    callwrite.close()

    ### filter GATK-filtered vcf file to only contain exonic sites
    ### ... done with all superts-exon intersect sites rather than just
    ### min depth 5 (callable sites), since a small fraction of sites
    ### have genotypes called by GATK with depth < 5
    if opts.polyploid == False:
        vcffilt_out,vcffilt_err = FilterVcfBySuperTsExonicSites(opts.vcf,'supertscoords_exons_%s' % opts.outbed)
    else:
        VcfToBed(opts.vcf)
        IntersectWithExons('%s.bed' % opts.vcf[:-4],'supertscoords_exons_%s' % opts.outbed)
        BedToVcf('exons_%s.bed' % opts.vcf[:-4],'%s.header' % opts.vcf)
                
 

