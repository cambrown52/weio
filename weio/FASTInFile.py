from __future__ import division
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from io import open
from builtins import map
from builtins import range
from builtins import chr
from builtins import str
from future import standard_library
standard_library.install_aliases()

from .File import File, WrongFormatError
import numpy as np
import re
import pandas as pd

# from .dtuwetb import fast_io
# TODO members for  BeamDyn with mutliple key point
NUMTAB_FROM_VAL_DETECT  = ['HtFract' ,'TwrElev'  ,'BlFract' ,'Genspd_TLU','BlSpn'       ,'WndSpeed','HvCoefID','AxCoefID','JointID','PropSetID'        ,'Dpth'     ,'FillNumM'   ,'MGDpth'   ,'SimplCd' ,'RNodes'      ,'kp_xr']
NUMTAB_FROM_VAL_DIM_VAR = ['NTwInpSt','NumTwrNds','NBlInpSt','DLL_NumTrq','NumBlNds'    ,'NumCases','NHvCoef' ,'NAxCoef' ,'NJoints','NPropSets'        ,'NCoefDpth','NFillGroups','NMGDepths',1         ,'BldNodes'    ,'kp_total']
NUMTAB_FROM_VAL_VARNAME = ['TowProp' ,'TowProp'  ,'BldProp' ,'DLLProp'   ,'BldAeroNodes','Cases'   ,'HvCoefs' ,'AxCoefs' ,'Joints' ,'MemberSectionProp','DpthProp' ,'FillGroups' ,'MGProp'   ,'SmplProp','BldAeroNodes','MemberGeom']
NUMTAB_FROM_VAL_NHEADER = [2         ,2          ,2         ,2           ,2             ,2         ,2         ,2         ,2        ,2                  ,2          ,2            ,2          ,2         ,1             ,2]
NUMTAB_FROM_VAL_DETECT_L = [s.lower() for s in NUMTAB_FROM_VAL_DETECT]

NUMTAB_FROM_LAB_DETECT   = ['NumAlf' ,'F_X'      ,'MemberCd1'    ,'MJointID1','NOutLoc']
NUMTAB_FROM_LAB_DIM_VAR  = ['NumAlf' ,'NKInpSt'  ,'NCoefMembers','NMembers' ,'NMOutputs']
NUMTAB_FROM_LAB_VARNAME  = ['AFCoeff','TMDspProp','MemberProp'   ,'Members'  ,'MemberOuts']
NUMTAB_FROM_LAB_DETECT_L = [s.lower() for s in NUMTAB_FROM_LAB_DETECT]

FILTAB_FROM_LAB_DETECT   = ['FoilNm' ,'AFNames']
FILTAB_FROM_LAB_DIM_VAR  = ['NumFoil','NumAFfiles']
FILTAB_FROM_LAB_VARNAME  = ['FoilNm' ,'FoilNm']
FILTAB_FROM_LAB_DETECT_L = [s.lower() for s in FILTAB_FROM_LAB_DETECT]

TABTYPE_NOT_A_TAB          = 0
TABTYPE_NUM_WITH_HEADER    = 1
TABTYPE_NUM_WITH_HEADERCOM = 2
TABTYPE_NUM_NO_HEADER      = 4
TABTYPE_FIL                = 3
TABTYPE_FMT                = 9999 # TODO

# --------------------------------------------------------------------------------}
# --- INPUT FILE 
# --------------------------------------------------------------------------------{
class FASTInFile(File):

    @staticmethod
    def defaultExtensions():
        return ['.dat','.fst','.txt']

    @staticmethod
    def formatName():
        return 'FAST input file'

    def getID(self,label):
        # brute force search
        for i in range(len(self.data)):
            d = self.data[i]
            if d['label']==label:
                return i
        raise KeyError('Variable '+ label+' not found')

    # Making object an iterator
    def __iter__(self):
        self.iCurrent=-1
        self.iMax=len(self.data)-1
        return self

    def __next__(self): # Python 2: def next(self)
        if self.iCurrent > self.iMax:
            raise StopIteration
        else:
            self.iCurrent += 1
            return self.data[self.iCurrent]

    # Making it behave like a dictionary
    def __setitem__(self,key,item):
        i = self.getID(key)
        self.data[i]['value'] = item

    def __getitem__(self,key):
        i = self.getID(key)
        return self.data[i]['value']

    def __repr__(self):
        s ='Fast input file: {}\n'.format(self.filename)
        return s+'\n'.join(['{:15s}: {}'.format(d['label'],d['value']) for i,d in enumerate(self.data)])


    def _read(self):
        try: 
            self.data =[]
            with open(self.filename, 'r', errors="surrogateescape") as f:
                lines = f.read().splitlines()
            # Fast files start with ! or -
            #if lines[0][0]!='!' and lines[0][0]!='-':
            #    raise Exception('Fast file do not start with ! or -, is it the right format?')
            
            # Special case Old AirfoilData
            if self.detectAndReadAirfoil(lines):
                        return

            # Parsing line by line, storing each line into a disctionary
            i=0    
            nComments  = 0
            nWrongLabels = 0
            while i<len(lines):
                line = lines[i]
                # OUTLIST Exceptions
                if line.upper().find('ADDITIONAL OUTPUTS')>0 \
                or line.upper().find('MESH-BASED OUTPUTS')>0 \
                or line.upper().find('OUTPUT CHANNELS'   )>0:
                    # TODO, lazy implementation so far, MAKE SUB FUNCTION
                    OutList,i = parseFASTOutList(lines,i+1)
                    d = getDict()
                    d['label']   = 'OutList'   # TODO
                    d['tabType'] = TABTYPE_FIL # TODO
                    d['value']   = OutList
                    self.data.append(d)
                    if i>=len(lines):
                        break
                elif line.upper().find('ADDITIONAL STIFFNESS')>0:
                    # TODO, lazy implementation so far, MAKE SUB FUNCTION
                    i +=1
                    KDAdd = []
                    for _ in range(19):
                        KDAdd.append(lines[i])
                        i +=1
                    d = getDict()
                    d['label']   = 'KDAdd'   # TODO
                    d['tabType'] = TABTYPE_FIL # TODO
                    d['value']   = KDAdd
                    self.data.append(d)
                    if i>=len(lines):
                        break

                # --- Parsing of standard lines: value(s) key comment
                line = lines[i]
                d = parseFASTInputLine(line,i)


                # --- Handling of special files
                if d['label'].lower()=='numcoords':
                    # TODO, lazy implementation so far, MAKE SUB FUNCTION
                    self.data.append(d); i+=1;
                    if isStr(d['value']):
                        if d['value'][0]=='@':
                            # it's a ref to the airfoil coord file
                            pass
                    else:
                        if not strIsInt(d['value']): 
                            raise WrongFormatError('Wrong value of NumCoords')
                        if int(d['value'])<=0:
                            pass
                        else:
                            # 3 comment lines
                            self.data.append(parseFASTInputLine(lines[i],i)); i+=1;
                            self.data.append(parseFASTInputLine(lines[i],i)); i+=1;
                            self.data.append(parseFASTInputLine(lines[i],i)); i+=1;
                            splits=cleanAfterChar(cleanLine(lines[i]),'!').split()
                            # Airfoil ref point
                            try:
                                pos=[float(splits[0]), float(splits[1])]
                            except:
                                raise WrongFormatError('Wrong format while reading coordinates of airfoil reference')
                            i+=1
                            d = getDict()
                            d['label'] = 'AirfoilRefPoint'
                            d['value'] = pos
                            self.data.append(d)
                            # 2 comment lines
                            self.data.append(parseFASTInputLine(lines[i],i)); i+=1;
                            self.data.append(parseFASTInputLine(lines[i],i)); i+=1;
                            # Table of coordinats itself
                            d = getDict()
                            d['label']     = 'AirfoilCoord'
                            d['tabDimVar'] = 'NumCoords'
                            d['tabType']   = TABTYPE_NUM_WITH_HEADERCOM
                            nTabLines = self[d['tabDimVar']]-1  # SOMEHOW ONE DATA POINT LESS
                            d['value'], d['tabColumnNames'],_  = parseFASTNumTable(lines[i:i+nTabLines+1],nTabLines,i,1)
                            d['tabUnits'] = ['(-)','(-)']
                            self.data.append(d)
                            break


                #print('label>',d['label'],'<',type(d['label']));
                #print('value>',d['value'],'<',type(d['value']));
                #print(isStr(d['value']))
                #if isStr(d['value']):
                #    print(d['value'].lower() in NUMTAB_FROM_VAL_DETECT_L)

                    
                # --- Handling of tables
                if isStr(d['value']) and d['value'].lower() in NUMTAB_FROM_VAL_DETECT_L:
                    # Table with numerical values, 
                    ii             = NUMTAB_FROM_VAL_DETECT_L.index(d['value'].lower())
                    d['label']     = NUMTAB_FROM_VAL_VARNAME[ii]
                    d['tabDimVar'] = NUMTAB_FROM_VAL_DIM_VAR[ii]
                    d['tabType']   = TABTYPE_NUM_WITH_HEADER
                    nHeaders       = NUMTAB_FROM_VAL_NHEADER[ii]
                    nTabLines=0
                    #print('Reading table {} Dimension {} (based on {})'.format(d['label'],nTabLines,d['tabDimVar']));
                    if isinstance(d['tabDimVar'],int):
                        nTabLines = d['tabDimVar']
                    else:
                        nTabLines = self[d['tabDimVar']]
                    d['value'], d['tabColumnNames'], d['tabUnits'] = parseFASTNumTable(lines[i:i+nTabLines+nHeaders],nTabLines,i,nHeaders)
                    i += nTabLines+nHeaders-1

                elif isStr(d['label']) and d['label'].lower() in NUMTAB_FROM_LAB_DETECT_L:
                    ii      = NUMTAB_FROM_LAB_DETECT_L.index(d['label'].lower())
                    # Special case for airfoil data, the table follows NumAlf, so we add d first
                    if d['label'].lower()=='numalf':
                        d['tabType']=TABTYPE_NOT_A_TAB
                        self.data.append(d)
                        # Creating a new dictionary for the table
                        d = {'value':None, 'label':'NumAlf', 'isComment':False, 'descr':'', 'tabType':None}
                        i += 1
                    d['label']     = NUMTAB_FROM_LAB_VARNAME[ii]
                    d['tabDimVar'] = NUMTAB_FROM_LAB_DIM_VAR[ii]
                    if d['label'].lower()=='afcoeff' :
                        d['tabType']        = TABTYPE_NUM_WITH_HEADERCOM
                    else:
                        d['tabType']   = TABTYPE_NUM_WITH_HEADER
                    nTabLines = self[d['tabDimVar']]
                    #print('Reading table {} Dimension {} (based on {})'.format(d['label'],nTabLines,d['tabDimVar']));
                    d['value'], d['tabColumnNames'], d['tabUnits'] = parseFASTNumTable(lines[i:i+nTabLines+2],nTabLines,i,2)
                    i += nTabLines+1

                elif isStr(d['label']) and d['label'].lower() in FILTAB_FROM_LAB_DETECT_L:
                    ii             = FILTAB_FROM_LAB_DETECT_L.index(d['label'].lower())
                    d['label']     = FILTAB_FROM_LAB_VARNAME[ii]
                    d['tabDimVar'] = FILTAB_FROM_LAB_DIM_VAR[ii]
                    d['tabType']   = TABTYPE_FIL
                    nTabLines = self[d['tabDimVar']]
                    #print('Reading table {} Dimension {} (based on {})'.format(d['label'],nTabLines,d['tabDimVar']));
                    d['value'] = parseFASTFilTable(lines[i:i+nTabLines],nTabLines,i)
                    i += nTabLines-1



                self.data.append(d)
                i += 1
                # --- Safety checks
                if d['isComment']:
                    #print(line)
                    nComments +=1
                else:
                    if hasSpecialChars(d['label']):
                        nWrongLabels +=1
                        #print('label>',d['label'],'<',type(d['label']),line);
                        if i>3: # first few lines may be comments, we allow it
                            raise WrongFormatError('Special Character found in Label.')
                    if len(d['label'])==0:
                        nWrongLabels +=1
                if nComments>len(lines)*0.35:
                    #print('Comment fail',nComments,len(lines),self.filename)
                    raise WrongFormatError('Most lines were read as comments, probably not a FAST Input File')
                if nWrongLabels>len(lines)*0.10:
                    #print('Label fail',nWrongLabels,len(lines),self.filename)
                    raise WrongFormatError('Too many lines with wrong labels, probably not a FAST Input File')
                 
        except WrongFormatError as e:    
            raise WrongFormatError('Fast File {}: '.format(self.filename)+'\n'+e.args[0])
        except Exception as e:    
            raise Exception('Fast File {}: '.format(self.filename)+'\n'+e.args[0])

            

    def _write(self):
        with open(self.filename,'w') as f:
            for i in range(len(self.data)):
                d=self.data[i]
                if d['isComment']:
                    f.write('{}'.format(d['value']))
                elif d['tabType']==TABTYPE_NOT_A_TAB:
                    if isinstance(d['value'], list):
                        sList=', '.join([str(x) for x in d['value']])
                        f.write('{} {} {}'.format(sList,d['label'],d['descr']))
                    else:
                        f.write('{} {} {}'.format(d['value'],d['label'],d['descr']))
                elif d['tabType']==TABTYPE_NUM_WITH_HEADER:
                    f.write('{}'.format(' '.join(d['tabColumnNames'])))
                    if d['tabUnits'] is not None:
                        f.write('\n')
                        f.write('{}'.format(' '.join(d['tabUnits'])))
                    if np.size(d['value'],0) > 0 :
                        f.write('\n')
                        f.write('\n'.join('\t'.join('%15.8e' %x for x in y) for y in d['value']))
                elif d['tabType']==TABTYPE_NUM_WITH_HEADERCOM:
                    f.write('! {}\n'.format(' '.join(d['tabColumnNames'])))
                    f.write('! {}\n'.format(' '.join(d['tabUnits'])))
                    f.write('\n'.join('\t'.join('%15.8e' %x for x in y) for y in d['value']))
                elif d['tabType']==TABTYPE_FIL:
                    f.write('{} {} {}\n'.format(d['value'][0],d['tabDetect'],d['descr']))
                    f.write('\n'.join(fil for fil in d['value'][1:]))
                else:
                    raise Exception('Unknown table type for variable {}',d)
                if i<len(self.data)-1:
                    f.write('\n')

    def _toDataFrame(self):
        dfs={}
        for i in range(len(self.data)): 
            d=self.data[i]
            if d['tabType'] in [TABTYPE_NUM_WITH_HEADER, TABTYPE_NUM_WITH_HEADERCOM, TABTYPE_NUM_NO_HEADER]:
                Val= d['value']
                if d['tabUnits'] is None:
                    Cols=d['tabColumnNames']
                else:
                    Cols=['{}_{}'.format(c,u.replace('(','[').replace(')',']')) for c,u in zip(d['tabColumnNames'],d['tabUnits'])]
                #print(Val)
                #print(Cols)
                name=d['label']
                dfs[name]=pd.DataFrame(data=Val,columns=Cols)
        return dfs

# --------------------------------------------------------------------------------}
# --- SubReaders /detectors
# --------------------------------------------------------------------------------{
    def detectAndReadAirfoil(self,lines):
        if len(lines)<14:
            return False
        # Reading number of tables
        L3 = lines[2].strip().split()
        if len(L3)<=0:
            return False
        if not strIsInt(L3[0]):
            return False
        nTables=int(L3[0])
        # Reading table ID
        L4 = lines[3].strip().split()
        if len(L4)<=nTables:
            return False
        TableID=L4[:nTables]
        if nTables==1:
            TableID=['']
        # Keywords for file format
        KW1=lines[12].strip().split()
        KW2=lines[13].strip().split()
        if len(KW1)>nTables and len(KW2)>nTables:
            if KW1[nTables].lower()=='angle' and KW2[nTables].lower()=='minimum':
                d = getDict(); d['isComment'] = True; d['value'] = lines[0]; self.data.append(d);
                d = getDict(); d['isComment'] = True; d['value'] = lines[1]; self.data.append(d);
                for i in range(2,14):
                    splits = lines[i].split()
                    #print(splits)
                    d = getDict()
                    d['label'] = ' '.join(splits[1:]) # TODO
                    d['descr'] = ' '.join(splits[1:]) # TODO
                    d['value'] = float(splits[0])
                    self.data.append(d)
                #pass
                #for i in range(2,14):
                nTabLines=0
                while 14+nTabLines<len(lines) and  len(lines[14+nTabLines].strip())>0 :
                    nTabLines +=1
                #data = np.array([lines[i].strip().split() for i in range(14,len(lines)) if len(lines[i])>0]).astype(np.float)
                #data = np.array([lines[i].strip().split() for i in takewhile(lambda x: len(lines[i].strip())>0, range(14,len(lines)-1))]).astype(np.float)
                data = np.array([lines[i].strip().split() for i in range(14,nTabLines+14)]).astype(np.float)
                #print(data)
                d = getDict()
                d['label']     = 'Polar'
                d['tabDimVar'] = nTabLines
                d['tabType']   = TABTYPE_NUM_NO_HEADER
                d['value']     = data
                if np.size(data,1)==1+nTables*3:
                    d['tabColumnNames'] = ['Alpha']+[n+l for l in TableID for n in ['Cl','Cd','Cm']]
                    d['tabUnits']       = ['(deg)']+['(-)' , '(-)' , '(-)']*nTables
                elif np.size(data,1)==1+nTables*2:
                    d['tabColumnNames'] = ['Alpha']+[n+l for l in TableID for n in ['Cl','Cd']]
                    d['tabUnits']       = ['(deg)']+['(-)' , '(-)']*nTables
                else:
                    d['tabColumnNames'] = ['col{}'.format(j) for j in range(np.size(data,1))]
                self.data.append(d)
                return True

# --------------------------------------------------------------------------------}
# --- Helper functions 
# --------------------------------------------------------------------------------{
def isStr(s):
    # Python 2 and 3 compatible
    # Two options below
    # NOTE: all this avoided since we import str from builtins
    # --- Version 2
    #     isString = False;
    #     if(isinstance(s, str)):
    #         isString = True;
    #     try:
    #         if(isinstance(s, basestring)): # todo unicode as well
    #             isString = True;
    #     except NameError:
    #         pass; 
    #     return isString
    # --- Version 1
    #     try: 
    #        basestring # python 2
    #        return isinstance(s, basestring) or isinstance(s,unicode)
    #     except NameError:
    #          basestring=str #python 3
    #     return isinstance(s, str)
   return isinstance(s, str)

def strIsFloat(s):
    #return s.replace('.',',1').isdigit()
    try:
        float(s)
        return True
    except:
        return False

def strIsBool(s):
    return (s.lower() is 'true') or (s.lower() is 'false')

def strIsInt(s):
    s = str(s)
    if s[0] in ('-', '+'):
        return s[1:].isdigit()
    return s.isdigit()    

def hasSpecialChars(s):
    # fast allows for parenthesis
    # For now we allow for - but that's because of BeamDyn geometry members 
    return not re.match("^[a-zA-Z0-9_()-]*$", s)

def cleanLine(l):
    # makes a string single space separated
    l = l.replace('\t',' ')
    l = ' '.join(l.split())
    l = l.strip()
    return l

def cleanAfterChar(l,c):
    # remove whats after a character
    n = l.find(c);
    if n>0:
        return l[:n]
    else:
        return l

def getDict():
    return {'value':None, 'label':'', 'isComment':False, 'descr':'', 'tabType':TABTYPE_NOT_A_TAB}


def parseFASTInputLine(line_raw,i):
    d = getDict()
    try:
        # preliminary cleaning (Note: loss of formatting)
        line = cleanLine(line_raw)
        # Comment
        if any(line.startswith(c) for c in ['#','!','--','==']) or len(line)==0:
            d['isComment']=True
            d['value']=line_raw
            return d

        # Detecting lists
        List=[];
        iComma=line.find(',')
        if iComma>0 and iComma<30:
            fakeline=line.replace(' ',',')
            fakeline=re.sub(',+',',',fakeline)
            csplits=fakeline.split(',')
            # Splitting based on comma and looping while it's numbers of booleans
            ii=0
            s=csplits[ii]
            while strIsFloat(s) or strIsBool(s) and ii<len(csplits):
                if strIsInt(s):
                    List.append(int(s))
                elif strIsFloat(s):
                    List.append(float(s))
                elif strIsBool(s):
                    List.append(bool(s))
                else:
                    raise WrongFormatError('Lists of strings not supported.')
                ii =ii+2
                if ii>=len(csplits):
                    raise WrongFormatError('Wrong number of list values')
                s = csplits[ii]
            #print('[INFO] Line {}: Found list: '.format(i),List)
        # Defining value and remaining splits
        if len(List)>=2:
            d['value']=List
            sLast=csplits[ii-1]
            ipos=line.find(sLast)
            line_remaining = line[ipos+len(sLast):]
            splits=line_remaining.split()
            iNext=0
        else:
            # It's not a list, we just use space as separators
            splits=line.split(' ')
            s=splits[0]

            if strIsInt(s):
                d['value']=int(s)
            elif strIsFloat(s):
                d['value']=float(s)
            elif strIsBool(s):
                d['value']=bool(s)
            else:
                d['value']=s
            iNext=1
            #import pdb  ; pdb.set_trace();

        # Extracting label (TODO, for now only second split)
        bOK=False
        while (not bOK) and iNext<len(splits):
            # Nasty handling of !XXX: comments
            if splits[iNext][0]=='!' and splits[iNext][-1]==':': 
                iNext=iNext+2
                continue
            # Nasty handling of the fact that sometimes old values are repeated before the label
            if strIsFloat(splits[iNext]):
                iNext=iNext+1
                continue
            else:
                bOK=True
        if bOK:
            d['label']= splits[iNext].strip()
            iNext = iNext+1
        else:
            #print('[WARN] Line {}: No label found -> comment assumed'.format(i+1))
            d['isComment']=True
            d['value']=line_raw
            iNext = len(splits)+1
        
        # Recombining description
        if len(splits)>=iNext+1:
            d['descr']=' '.join(splits[iNext:])
    except WrongFormatError as e:
        raise WrongFormatError('Line {}: '.format(i+1)+e.args[0])
    except Exception as e:
        raise Exception('Line {}: '.format(i+1)+e.args[0])

    return d

def parseFASTOutList(lines,iStart):
    OutList=[]
    i = iStart
    MAX=200
    while i<len(lines) and lines[i].upper().find('END')!=0:
        OutList.append(lines[i]) #TODO better parsing
        #print('OutList',lines[i])
        i += 1
        if i-iStart>MAX :
            raise Exception('More that 200 lines found in outlist')
        if i>=len(lines):
            print('[WARN] End of file reached while reading Outlist')
    i=min(i+1,len(lines))
    return OutList,i


def extractWithinParenthesis(s):
    mo = re.search(r'\((.*)\)', s)
    if mo:
        return mo.group(1)
    return ''

def extractWithinBrackets(s):
    mo = re.search(r'\((.*)\)', s)
    if mo:
        return mo.group(1)
    return ''

def detectUnits(s,nRef):
    nPOpen=s.count('(')
    nPClos=s.count(')')
    nBOpen=s.count('[')
    nBClos=s.count(']')

    sep='!#@#!'
    if (nPOpen == nPClos) and (nPOpen>=nRef):
        #that's pretty good
        Units=s.replace('(','').replace(')',sep).split(sep)[:-1]
    elif (nBOpen == nBClos) and (nBOpen>=nRef):
        Units=s.replace('[','').replace(']',sep).split(sep)[:-1]
    else:
        Units=s.split()
    return Units


def parseFASTNumTable(lines,n,iStart,nHeaders=2):
    Tab = None
    ColNames = None
    Units = None

    if len(lines)!=n+nHeaders:
        raise WrongFormatError('Not enough lines in table: {} lines instead of {}'.format(len(lines)-nHeaders,n))

    if nHeaders<1:
        raise NotImplementedError('Reading FAST tables with no headers not implemented yet')

    try:
        if nHeaders>=1:
            # Extract column names
            i = 0
            sTmp = cleanLine(lines[i])
            sTmp = cleanAfterChar(sTmp,'[')
            if sTmp.startswith('!'):
                sTmp=sTmp[1:].strip()
            ColNames=sTmp.split()
        if nHeaders>=2:
            # Extract units
            i = 1
            sTmp = cleanLine(lines[i])
            if sTmp.startswith('!'):
                sTmp=sTmp[1:].strip()

            Units = detectUnits(sTmp,len(ColNames))
            Units = ['({})'.format(u.strip()) for u in Units]
            # Forcing user to match number of units and column names
            if len(ColNames) != len(Units):
                print(ColNames)
                print(Units)
                raise Exception('Number of column names different from number of units in table')

        nCols=len(ColNames)

        Tab = np.zeros((n, len(ColNames))) 
        for i in range(nHeaders,n+nHeaders):
            l = lines[i].lower()
            v = l.split()
            if len(v) > nCols:
                print('[WARN] Line {}: number of data different from number of column names'.format(iStart+i+1))
            if len(v) < nCols:
                raise Exception('Number of data is lower than number of column names')
            # Accounting for TRUE FALSE and converting to float
            v = [s.replace('true','1').replace('false','0').replace('noprint','0').replace('print','1') for s in v]
            v = [float(s) for s in v[0:nCols]]
            if len(v) < nCols:
                raise Exception('Number of data is lower than number of column names')
            Tab[i-nHeaders,:] = v
            
    except Exception as e:    
        raise Exception('Line {}: '.format(iStart+i+1)+e.args[0])
    return Tab, ColNames, Units


def parseFASTFilTable(lines,n,iStart):
    Tab = []
    try:
        i=0
        if len(lines)!=n:
            raise WrongFormatError('Not enough lines in table: {} lines instead of {}'.format(len(lines),n))
        for i in range(n):
            l = lines[i].split()
            #print(l[0].strip())
            Tab.append(l[0].strip())
            
    except Exception as e:    
        raise Exception('Line {}: '.format(iStart+i+1)+e.args[0])
    return Tab


if __name__ == "__main__":
    pass
    #B=FASTIn('Turbine.outb')


