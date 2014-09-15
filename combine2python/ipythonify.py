# -*- coding: utf-8 -*-

"""
Ipythonify module v0.1 May 20 2014
Author: Kiri Choi
University of Washington
kirichoi@uw.edu

This module will convert hex string back to its original zip file and uncompress them within the same folder.
"""

import sys, os, errno, time, json, shutil
import subprocess as sp
import binascii as bi
import zipfile as zi
import tellurium as te
import xml.etree.ElementTree as xe
import SedmlToRr as se
import fileinput as fi
import base64 as b64
from string import Template

print "Ipythonify v0.1"


#Given a string, directory path, and output filename, it creates a python script and a folder with raw model
def str2py(inputstr, dirpth, fname, encode):
    zoutfname = fname + '.zip'
    zoutputloc = os.path.join(dircheck(os.path.join(dirpth,fname)), zoutfname)
    zipdirname = fname + '_raw_model'
    zipextloc = os.path.join(dircheck(os.path.join(dirpth,fname)), zipdirname)

    pymodelloc = os.path.join(dircheck(os.path.join(dirpth,fname)), fname + '.py')
    
    decodestr(inputstr, zoutputloc, zipextloc, encode)
    codestitch(pymodelloc, zipextloc, fname)
    codeanalysis(pymodelloc, zipextloc)
    

#Given the path of the combine archive, converts the combine archive into python script
def combine2py(combloc):
    fname = os.path.basename(combloc)
    zipdirname = fname.replace('.zip','') + '_raw'
    pardir = os.path.dirname(combloc)
    if 'win32' in sys.platform:
        pardir = pardir.replace('/','\\')
    elif 'linux' or 'darwin' in sys.platform:
        pardir = pardir.replace('\\','/')
    zipextloc = os.path.join(dircheck(pardir), zipdirname)

    pymodelloc = os.path.join(dircheck(pardir), fname.replace('.zip','') + '.py')
    
    zipext(combloc,zipextloc)
    codestitch(pymodelloc, zipextloc, fname)
    codeanalysis(pymodelloc, zipextloc)
    
    print "Python script created at (", pymodelloc, ")"
    delseq(zipextloc)
    
    usrinput = inq()

    if usrinput == 'Y' or usrinput == 'y' or usrinput == 'yes' or usrinput == 'Yes':
        if 'win32' in sys.platform:
            sp.Popen("spyder " + '"' + pymodelloc + '"', shell=True)
        elif 'linux' or 'darwin' in sys.platform:
            sp.Popen(["spyder", pymodelloc], shell=True)
    elif usrinput == 'N' or usrinput == 'n' or usrinput == 'no' or usrinput == 'No':
        pass
    else:
        print "Wrong input"
        usrinput = inq()


def dircheck(loc):
    if not os.path.exists(loc):
        os.makedirs(loc)
    return loc
    

#Takes a string in either hex or base64, creates zip file and extracts it
def decodestr(inputstr, outputloc, extloc, etype):
    str_nnl = inputstr.replace('\n','').replace('\r','')
    
    if etype == 'base64':
        decstr = b64.urlsafe_b64decode(str_nnl)
    elif etype == 'hex':
        decstr = bi.unhexlify(str_nnl)
    else:
        raise TypeError('String error: Cannot obtain format information from given link')
        
    f = open(outputloc, "wb")    
    f.write(decstr)
    f.close()
    print "Zip file recovered"
    
    zipext(outputloc, extloc)
    delseq(outputloc)

    print "Zip file removed \n"

    
def zipext(outputloc, extloc):
    tarzip = zi.ZipFile(outputloc)
    tarzip.extractall(extloc)
    tarzip.close()
    
    print "Zip file decompressed at (", extloc, ")"


#Search manifest for appropriate SBML and SEDML locations
def manifestsearch(zipextloc):
    manifestloc = os.path.join(zipextloc, 'manifest.xml')
    manifest = xe.parse(manifestloc)
    root = manifest.getroot()
    for child in root:
        attribute = child.attrib
        formtype = attribute.get('format')
        loc = attribute.get('location')
        if 'sbml' in formtype:
            sbmlloc = loc
            sbmlloc = sbmlloc[1:]
        elif 'sedml' or 'sed-ml' in formtype:
            sedmlloc = loc
            sedmlloc = sedmlloc[1:]
    #sbmlloc = sbmlloc.replace('/','\\')
    #sedmlloc = sedmlloc.replace('/','\\')
    return (sbmlloc, sedmlloc)


#SBML conversion into antimony string
def sbmlconv(zipextloc):
    sbmlloc, sedmlloc = manifestsearch(zipextloc)
    sbml = te.readFromFile(zipextloc + sbmlloc)
    sbmlantimony = te.sbmlToAntimony(sbml)
    return sbmlantimony
    
    
#SEDML conversion
def sedmlconv(zipextloc):
    sbmlloc, sedmlloc = manifestsearch(zipextloc)
    sedmlantimony = se.sedml_to_python(zipextloc + sedmlloc)
    return sedmlantimony
    
    
#Creates a python script with both SBML and SEDML included
def codestitch(pymodelloc, extloc, filename):
    sbmlstr = sbmlconv(extloc)
    sedmlstr = sedmlconv(extloc)
    with open(pymodelloc, "w+") as filef:
        filef.seek(0)
        readf = filef.read()
        filef.write("# -*- coding: utf-8 -*-\n\n" + '"Generated by Ipythonify ' + time.strftime("%m/%d/%Y") + '"\n"Extracted from ' + filename + '"\n\n')
        if not "import tellurium" in readf:
            filef.write("import tellurium as te\n\n")
        filef.write("AntimonyTranslation = '''\n" + sbmlstr + "'''\n" + sedmlstr)
        filef.close()

       
#Included in case of SEDML codes not compatible with single model file approach
def codeanalysis(pymodelloc, extloc):
    sbmlloc, sedmlloc = manifestsearch(extloc)
    for line in fi.input(pymodelloc,inplace = 1):
        line = line.strip()
        if not '.xml' in line:
            if "roadrunner.RoadRunner()" in line:
                line = line.replace("roadrunner.RoadRunner()", "te.loada(AntimonyTranslation)")
            print line


#Given the location of python script, outputs JSON string
def jsonify(pydirloc, fname):
    srcfile = open(os.path.join(os.path.join(pydirloc,fname), fname + '.py'), "r+")
    srcfile.seek(0)
    srcread = srcfile.readlines(0)
    modelcon = json.dumps(srcread)
    temp = Template("""{
 "metadata": {
  "name": "$filetitle",
  "signature": ""
 },
 "nbformat": 3,
 "nbformat_minor": 0,
 "worksheets": [
  {
   "cells": [
    {
     "cell_type": "code",
     "collapsed": false,
     "input": $modeldes,
     "language": "python",
     "metadata": {},
     "outputs": []
    }
   ],
   "metadata": {}
  }
 ]
}
""")
    outputstr = temp.substitute(filetitle = str(fname), modeldes = str(modelcon))
    srcfile.close()
    return outputstr


def inq():
    usrinput = raw_input("Open with Spyder? (Y/N) = ")
    return usrinput
    

def delseq(floc):
    try:
        os.remove(floc)
    except OSError as E1:
        try:
            shutil.rmtree(floc)
        except OSError as E2:
            if E1.errno != errno.ENOENT or E2.errno != errno.ENOENT:
                raise
    print "Raw files removed."


def exitseq():
    raw_input('Press enter to exit.')
    exit(0)
