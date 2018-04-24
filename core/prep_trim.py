import sys
import subprocess
import os
import os.path

#-------------------------------------------------------------------------------------
def runShellCommand(cmd):
   # run shell command, capture stdout and stderror (assumes log is not large and not redirected to disk)
   try:
      log = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
      error = False
   except subprocess.CalledProcessError, ex:
      log = ex.output
      error = True
      
   # print command log output
   for line in log.split("\n"):
      print("prep_trim: " + line.strip())
   
   # re-raise exception now that error detail has been printed
   if error:
      raise(ex)

#-------------------------------------------------------------------------------------
def run(cutadaptDir,umiTagName,filePrefix):

   # split read set name from input file directory (NOTE: ".R1.fastq" and ".R2.fastq" are required file suffixes here!)
#    dirIn, filePrefix = os.path.split(filePrefix)
#    if len(dirIn) > 0:
#       dirIn = dirIn + "/"
   
   # trim R1 reads 3' end (gets R2 12 bp barcode, 11-mer common, and ILMN adapter not cut by ILMN software) (primer side)
   cmd  = cutadaptDir + "cutadapt -e 0.18 -O 3 " \
        + "-a AGGACTCCAAT -n 1 " \
        + "-o " + filePrefix + ".temp0.R1.fastq " \
        + filePrefix +       ".R1.fastq "
   runShellCommand(cmd)
   
   # trim R2 reads 3' end (gets R1 custom sequencing adapter region not cut by ILMN software - customer sequencing primer settings usually wrong) (barcode side)
   cmd  = cutadaptDir + "cutadapt -e 0.18 -O 3 " \
        + "-a CAAAACGCAATACTGTACATT -n 1 " \
        + "-o " + filePrefix + ".temp0.R2.fastq " \
        + filePrefix +       ".R2.fastq "
   runShellCommand(cmd)
      
   # open output
   fileOut1 = open(filePrefix + ".temp1.R1.fastq", "w")
   fileOut2 = open(filePrefix + ".temp1.R2.fastq", "w")
   fileIn1  = open(filePrefix + ".temp0.R1.fastq", "r")
   fileIn2  = open(filePrefix + ".temp0.R2.fastq", "r")

   # extract barcode at beginning of R1 - just take first 12 bp
   numReadPairsTotal = 0
   numReadPairsDropped = 0
   linesR1 = []
   linesR2 = []
   lineIdx = 0
   for line in fileIn1:
      linesR1.append(line.strip())
      line = fileIn2.readline()
      linesR2.append(line.strip())
      lineIdx += 1

      # read all four lines of R1 and R2 into memory
      if lineIdx == 4:
         lineIdx = 0
         numReadPairsTotal += 1
      
         # skip reads too short
         if len(linesR1[1]) < 40 or len(linesR2[1]) < 40:
            numReadPairsDropped += 1
            del(linesR1[:])
            del(linesR2[:])
            continue
         
         # get barcode, trim R2 - 12 bp barcode, 11 bp univeral
         line = linesR2[1]
         if not line.startswith("N"):
            umiSeq = line[0:12]
            linesR2[1] = linesR2[1][23:]
            linesR2[3] = linesR2[3][23:]
         else:
            umiSeq = line[1:13]
            linesR2[1] = linesR2[1][24:]
            linesR2[3] = linesR2[3][24:]

         # make a UMI tag
         umiTag = umiTagName + ":Z:" + umiSeq
            
         # add barcode to R1 id line
         line = linesR1[0]
         idx = line.find(" ")
         readId = line[1:idx]
         linesR1[0] = "@" + readId + " " + umiTag
         
         # debug check on R2 being in sync with R1
         line = linesR2[0]
         idx = line.find(" ")
         readId_ = line[1:idx]
         if readId_ != readId:
            raise Exception("R1/R2 no synchronized")
         
         # add barcode to R2 id line
         linesR2[0] = linesR1[0]
         
         # write output
         for i in range(4):
            fileOut1.write(linesR1[i] + "\n")
            fileOut2.write(linesR2[i] + "\n")

         # clear for next read           
         del(linesR1[:])
         del(linesR2[:])
   
   # write summary file 
   fileOut = open(filePrefix + ".prep_trim.summary.txt", "w")
   fileOut.write("{}\tread fragments total\n".format(numReadPairsTotal))
   fileOut.write("{}\tread fragments dropped, less than 40 bp\n".format(numReadPairsDropped))
   fileOut.close()   
      
   # delete unneeded temp files
   os.remove(filePrefix + ".temp0.R1.fastq")
   os.remove(filePrefix + ".temp0.R2.fastq")
   
   # rename the output files - overwrite the input files!
   os.rename(filePrefix + ".temp1.R1.fastq", filePrefix + ".R1.fastq")
   os.rename(filePrefix + ".temp1.R2.fastq", filePrefix + ".R2.fastq")
   
#-------------------------------------------------------------------------------------
if __name__ == "__main__":
   cutadaptDir = sys.argv[1]
   umiTagName = sys.argv[2]
   readFilePrefix = sys.argv[3]
   run(cutadaptDir,umiTagName,readFilePrefix)
