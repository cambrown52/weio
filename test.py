from __future__ import print_function, absolute_import
import weio
import glob

def tests():
    # for now only weio tests
    nError=0
    #f=weio.FASTInFile('_tests/FASTAirfoil.dat')
    f=weio.FASTOutFile('_tests/FASTOutBin.outb')

    for f in glob.glob('_tests/*.*'):
        try:
            fileformat = weio.detectFormat(f)
            weio.read(f,fileformat)
            print('[ OK ] '+f + ' read as {}'.format(fileformat))
        except:
            nError += 1
            print('[FAIL] '+f + ' read as {}'.format(fileformat))
            raise 

    if nError>0:
        raise Exception('Some tests failed')


if __name__ == '__main__':
    tests()
