from __future__ import absolute_import
from .File import File
import numpy as np
import pandas as pd
import struct
import os
import re


# --------------------------------------------------------------------------------}
# --- OUT FILE 
# --------------------------------------------------------------------------------{
class FASTOutFile(File):

    @staticmethod
    def defaultExtensions():
        return ['.out','.outb']

    @staticmethod
    def formatName():
        return 'FAST output file (.out,.outb)'

    def _read(self):
        ext = os.path.splitext(self.filename.lower())[1]
        if ext=='.out':
            self.data, self.info = load_ascii_output(self.filename)
        elif ext=='.outb':
            self.data, self.info = load_binary_output(self.filename)
        else:
            self.data, self.info = load_output(self.filename)

        self.info['attribute_units'] = [re.sub('[()\[\]]','',u) for u in self.info['attribute_units']]


    #def _write(self): # TODO
    #    pass

    def _toDataFrame(self):
        cols=[n+'_['+u+']' for n,u in zip(self.info['attribute_names'],self.info['attribute_units'])]
        return pd.DataFrame(data=self.data,columns=cols)

# --------------------------------------------------------------------------------}
# --- Helper functions
# --------------------------------------------------------------------------------{
# Adapted from:
#   File:    wetb/fast/fast_io.py 
#   Site:    https://gitlab.windenergy.dtu.dk/toolbox/WindEnergyToolbox
#   Author:  Mads M Pedersen, DTU Wind
#   License: GNU

def load_output(filename):
    """Load a FAST binary or ascii output file

    Parameters
    ----------
    filename : str
        filename

    Returns
    -------
    data : ndarray
        data values
    info : dict
        info containing:
            - description: description of dataset
            - attribute_names: list of attribute names
            - attribute_units: list of attribute units
    """
    with open(filename, 'r') as f:
        try:
            f.readline()
        except UnicodeDecodeError:
            return load_binary_output(filename)
    return load_ascii_output(filename)

def load_ascii_output(filename):
    # Read with panda
    #self.data=pd.read_csv(self.filename, sep='\t', skiprows=[0,1,2,3,4,5,7])
    #self.data.rename(columns=lambda x: x.strip(),inplace=True)
    with open(filename) as f:
        info = {}
        try:
            header = [f.readline() for _ in range(8)]
            info['description'] = header[4].strip()
            info['attribute_names'] = header[6].split()
            info['attribute_units'] = [unit[1:-1] for unit in header[7].split()]  #removing "()"
            data = np.array([line.split() for line in f.readlines()]).astype(np.float)

            return data, info
        except (ValueError, AssertionError):
            raise


def load_binary_output(filename):
    """Ported from ReadFASTbinary.m by Mads M Pedersen, DTU Wind
    Info about ReadFASTbinary.m:
    % Author: Bonnie Jonkman, National Renewable Energy Laboratory
    % (c) 2012, National Renewable Energy Laboratory
    %
    %  Edited for FAST v7.02.00b-bjj  22-Oct-2012
    """
    def fread(fid, n, type):
        fmt, nbytes = {'uint8': ('B', 1), 'int16':('h', 2), 'int32':('i', 4), 'float32':('f', 4), 'float64':('d', 8)}[type]
        return struct.unpack(fmt * n, fid.read(nbytes * n))

    FileFmtID_WithTime = 1  #% File identifiers used in FAST
    FileFmtID_WithoutTime = 2
    LenName = 10  #;  % number of characters per channel name
    LenUnit = 10  #;  % number of characters per unit name

    with open(filename, 'rb') as fid:
        FileID = fread(fid, 1, 'int16')[0]  #;             % FAST output file format, INT(2)
        if FileID not in [FileFmtID_WithTime, FileFmtID_WithoutTime] :
            raise Exception('Fast binary ID `{}` unsupported. Not a binary file? '.format(FileID))

        NumOutChans = fread(fid, 1, 'int32')[0]  #;             % The number of output channels, INT(4)
        NT = fread(fid, 1, 'int32')[0]  #;             % The number of time steps, INT(4)

        if FileID == FileFmtID_WithTime:
            TimeScl = fread(fid, 1, 'float64')  #;           % The time slopes for scaling, REAL(8)
            TimeOff = fread(fid, 1, 'float64')  #;           % The time offsets for scaling, REAL(8)
        else:
            TimeOut1 = fread(fid, 1, 'float64')  #;           % The first time in the time series, REAL(8)
            TimeIncr = fread(fid, 1, 'float64')  #;           % The time increment, REAL(8)




        ColScl = fread(fid, NumOutChans, 'float32')  #; % The channel slopes for scaling, REAL(4)
        ColOff = fread(fid, NumOutChans, 'float32')  #; % The channel offsets for scaling, REAL(4)

        LenDesc = fread(fid, 1, 'int32')[0]  #;  % The number of characters in the description string, INT(4)
        DescStrASCII = fread(fid, LenDesc, 'uint8')  #;  % DescStr converted to ASCII
        DescStr = "".join(map(chr, DescStrASCII)).strip()



        ChanName = []  # initialize the ChanName cell array
        for iChan in range(NumOutChans + 1):
            ChanNameASCII = fread(fid, LenName, 'uint8')  #; % ChanName converted to numeric ASCII
            ChanName.append("".join(map(chr, ChanNameASCII)).strip())


        ChanUnit = []  # initialize the ChanUnit cell array
        for iChan in range(NumOutChans + 1):
            ChanUnitASCII = fread(fid, LenUnit, 'uint8')  #; % ChanUnit converted to numeric ASCII
            ChanUnit.append("".join(map(chr, ChanUnitASCII)).strip()[1:-1])


        #    %-------------------------
        #    % get the channel time series
        #    %-------------------------

        nPts = NT * NumOutChans  #;           % number of data points in the file


        if FileID == FileFmtID_WithTime:
            PackedTime = fread(fid, NT, 'int32')  #; % read the time data
            cnt = len(PackedTime)
            if cnt < NT:
                raise Exception('Could not read entire %s file: read %d of %d time values' % (filename, cnt, NT))
        PackedData = fread(fid, nPts, 'int16')  #; % read the channel data
        cnt = len(PackedData)
        if cnt < nPts:
            raise Exception('Could not read entire %s file: read %d of %d values' % (filename, cnt, nPts))

    #    %-------------------------
    #    % Scale the packed binary to real data
    #    %-------------------------
    #


    data = np.array(PackedData).reshape(NT, NumOutChans)
    data = (data - ColOff) / ColScl

    if FileID == FileFmtID_WithTime:
        time = (np.array(PackedTime) - TimeOff) / TimeScl;
    else:
        time = TimeOut1 + TimeIncr * np.arange(NT)

    data = np.concatenate([time.reshape(NT, 1), data], 1)

    info = {'description': DescStr,
            'attribute_names': ChanName,
            'attribute_units': ChanUnit}
    return data, info

if __name__ == "__main__":
    B=FASTOutFile('Turbine.outb')
    print(B.data)



