"""This function transforms Matlab7.3 HDF5 '.mat' files into a Python
dictionary of arrays and strings (and some leftover).

Copyright 2012, Emanuele Olivetti

BSD License, 3 clauses.
"""

import numpy as np
import h5py

dtypes = {}


def string(seq):
    """Convert a sequence of integers into a single string.
    """
    return ''.join([chr(a) for a in seq])


def add_dtype_name(f, name):
    """Keep track of all dtypes and names in the HDF5 file using it.
    """
    global dtypes
    dtype = f.dtype            
    if dtypes.has_key(dtype.name):
        dtypes[dtype.name].add(name)
    else:
        dtypes[dtype.name] = set([name])
    return


def recursive_dict(f, root=None, name='root'):
    """This function recursively navigates the HDF5 structure from
    node 'f' and tries to unpack the data structure by guessing their
    content from dtype, shape etc.. It returns a dictionary of
    strings, arrays and some leftovers. 'root' is the root node of the
    HDF5 structure, i.e. what h5py.File() returns.

    Note that this function works well on the Matlab7.3 datasets on
    which it was tested, but in general it might be wrong and it might
    crash. The motivation is that it has to guess the content of
    substructures so it might fail. One source of headache seems to be
    Matlab7.3 format that represents strings as array of 'uint16' so
    not using the string datatype. For this reason it is not possible
    to discriminate strings from arrays of integers without using
    heuristics.
    """
    if root is None: root = f
    if hasattr(f, 'keys'):
        a = dict(f)
        if u'#refs#' in a.keys(): # we don't want to keep this
            del(a[u'#refs#'])
        for k in a.keys():
            # print k
            a[k] = recursive_dict(f[k], root, name=name+'->'+k)
        return a
    elif hasattr(f, 'shape'):
        if f.dtype.name not in ['object', 'uint16']: # this is a numpy array
            # Check shape to assess whether it can fit in memory
            # or not. If not recast to a smaller dtype!
            add_dtype_name(f, name)
            dtype = f.dtype
            if (np.prod(f.shape)*f.dtype.itemsize) > 2e9:
                print "WARNING: The array", name, "requires > 2Gb"
                if f.dtype.char=='d':
                    print "\t Recasting", dtype, "to float32"
                    dtype = np.float32
                else:
                    raise MemoryError
            return np.array(f, dtype=dtype).squeeze()
        elif f.dtype.name in ['uint16']: # this may be a string for Matlab
            add_dtype_name(f, name)
            try:
                return string(f)
            except ValueError: # it wasn't...
                print "WARNING:", name, ":"
                print "\t", f
                print "\t CONVERSION TO STRING FAILED, USING ARRAY!"
                tmp = np.array(f).squeeze()
                print "\t", tmp
                return tmp
            pass
        elif f.dtype.name=='object': # this is a 2D array of HDF5 object references or just objects
            add_dtype_name(f, name)
            container = []
            for i in range(f.shape[0]):
                for j in range(f.shape[1]):
                    if str(f[i][j])=='<HDF5 object reference>': # reference follow it:
                        container.append(recursive_dict(root[f[i][j]], root, name=name))
                    else:
                        container.append(np.array(f[i][j]).squeeze())
            try:
                return np.array(container).squeeze()
            except ValueError:
                print "WARNING:", name, ":"
                print "\t", container
                print "\t CANNOT CONVERT INTO NON-OBJECT ARRAY"
                return np.array(container, dtype=np.object).squeeze()
        else:
            raise NotImplemented
    return

    
if __name__ == '__main__':

    import sys
    import cPickle as pickle

    filename = sys.argv[-1]

    print "Loading", filename

    f = h5py.File(filename)

    data = recursive_dict(f)

    filename = filename[:-4]+".pickle"
    print "Saving", filename
    pickle.dump(data, open(filename,'w'),
                protocol=pickle.HIGHEST_PROTOCOL)


