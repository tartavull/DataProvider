#!/usr/bin/env python
__doc__ = """

Read-only/writable TensorData classes.

Kisuk Lee <kisuklee@mit.edu>, 2015-2016
"""

import math
import numpy as np

from box import *
from vector import *

class TensorData(object):
    """Read-only tensor data.

    The 1st dimension is regarded as parallel channels, and arbitrary access
    along this dimension is not allowed. Threfore, every data access should be
    made through 3D vector, not 4D.

    Attributes:
        _data:   numpy 4D array (channel,z,y,x)
        _dim:    Dimension of each channel
        _offset: Coordinate offset from the origin
        _bb:     Bounding box
        _fov:    Patch size
        _rg:     Range (update dep.: dim, offset, fov)
    """

    def __init__(self, data, fov=(0,0,0), offset=(0,0,0)):
        """
        Initialize a TensorData object.
        """
        # Set immutable attributes
        self._data   = self._check_data(data)
        self._dim    = Vec3d(self._data.shape[1:])
        self._offset = Vec3d(offset)

        # Set bounding box
        self._bb = Box((0,0,0), self._dim)
        self._bb.translate(self._offset)

        # Set fov (patch size)
        self.set_fov(fov)

    def set_fov(self, fov):
        """
        Set a nonnegative field of view (FoV), i.e., patch size.
        """
        # Zero FoV indicates covering the whole volume.
        fov = Vec3d(fov)
        if fov == (0,0,0):
            fov = Vec3d(self._dim)

        # FoV should be nonnegative, and smaller than data dimension
        assert fov==minimum(maximum(fov,(0,0,0)), self._dim)

        # Set FoV
        self._fov = fov

        # Update range
        self._set_range()

    def get_patch(self, pos):
        """
        Extract a patch of size _fov centered on pos.
        """
        assert self._rg.contains(pos)  # check validity
        pos -= self._offset  # local coordinate system
        box  = centered_box(pos, self._fov)
        vmin = box.min()
        vmax = box.max()
        return np.copy(self._data[:,vmin[0]:vmax[0],
                                    vmin[1]:vmax[1],
                                    vmin[2]:vmax[2]])

    ####################################################################
    ## Public methods for accessing attributes
    ####################################################################

    def get_data(self):
        return self._data

    def shape(self):
        """Return data shape (c,z,y,x)."""
        return self._data.shape

    def dimension(self):
        """Return channel shape (z,y,x)."""
        return Vec3d(self._dim)

    def fov(self):
        return Vec3d(self._fov)

    def offset(self):
        return Vec3d(self._offset)

    def bounding_box(self):
        return Box(self._bb)

    def range(self):
        return Box(self._rg)

    ####################################################################
    ## Private helper methods
    ####################################################################

    def _check_data(self, data):
        # data should be either numpy 3D or 4D array
        assert isinstance(data, np.ndarray)
        assert data.ndim==3 or data.ndim==4

        # Add channel dimension if data is 3D array
        if data.ndim == 3:
            data = data[np.newaxis,...]

        return data

    def _set_range(self):
        """Set a valid range for extracting patches."""
        top  = self._fov/2                # top margin
        btm  = self._fov - top - (1,1,1)  # bottom margin
        vmin = self._offset + top
        vmax = self._offset + self._dim - btm

        self._rg = Box(vmin, vmax)

    # String representaion (for printing and debugging).
    def __str__( self ):
        return "<TensorData>\nshape: %s\ndim: %s\nFoV: %s\noffset: %s\n" % \
               (self.shape(), self._dim, self._fov, self._offset)


class WritableTensorData(TensorData):
    """
    Writable tensor data.
    """

    def __init__(self, data_or_dim, fov=(0,0,0), offset=(0,0,0)):
        """
        Initialize a writable tensor data, or create a new tensor of zeros.
        """
        if isinstance(data_or_dim, np.ndarray):
            TensorData.__init__(self,data_or_dim, fov, offset)
        else:
            dim  = Vec3d(data_or_dim)
            data = np.zeros(dim)
            TensorData.__init__(self,data, fov, offset)

    def set_patch(self, pos, patch):
        """
        Write a patch of size _fov centered on pos.
        """
        assert self._rg.contains(pos)
        patch = self._check_data(patch)
        dim = patch.shape[1:]
        assert dim == self._fov
        box = centered_box(pos, dim)

        # local coordinate
        box.translate(-self._offset)
        vmin = box.min()
        vmax = box.max()
        self._data[:,vmin[0]:vmax[0],vmin[1]:vmax[1],vmin[2]:vmax[2]] = patch


########################################################################
## Unit Testing
########################################################################
if __name__ == "__main__":

    import unittest

    ####################################################################
    class UnitTestTensorData(unittest.TestCase):

        def setup(self):
            pass

        def testCreation(self):
            data = np.zeros((4,4,4,4))
            T = TensorData(data, (3,3,3), (1,1,1))
            self.assertTrue(T.shape()==(4,4,4,4))
            self.assertTrue(T.offset()==(1,1,1))
            self.assertTrue(T.fov()==(3,3,3))
            bb = T.bounding_box()
            rg = T.range()
            self.assertTrue(bb==Box((1,1,1),(5,5,5)))
            self.assertTrue(rg==Box((2,2,2),(4,4,4)))

        def testGetPatch(self):
            # (4,4,4) random 3D araray
            data = np.random.rand(4,4,4)
            T = TensorData(data, (3,3,3))
            p = T.get_patch((2,2,2))
            self.assertTrue(np.array_equal(data[1:,1:,1:], p[0, ...]))
            T.set_fov((2,2,2))
            p = T.get_patch((2,2,2))
            self.assertTrue(np.array_equal(data[1:3,1:3,1:3], p[0, ...]))


    ####################################################################
    class UnitTestWritableTensorData(unittest.TestCase):

        def setup(self):
            pass

        def testCreation(self):
            data = np.zeros((1,4,4,4))
            T = WritableTensorData(data, (3,3,3), (1,1,1))
            self.assertTrue(T.shape()==(1,4,4,4))
            self.assertTrue(T.offset()==(1,1,1))
            self.assertTrue(T.fov()==(3,3,3))
            bb = T.bounding_box()
            rg = T.range()
            self.assertTrue(bb==Box((1,1,1),(5,5,5)))
            self.assertTrue(rg==Box((2,2,2),(4,4,4)))

        def testSetPatch(self):
            T = WritableTensorData(np.zeros((1,5,5,5)), (3,3,3), (1,1,1))
            p = np.random.rand(1,3,3,3)
            self.assertFalse(np.array_equal(p, T.get_patch((4,4,4))))
            T.set_patch((4,4,4), p)
            self.assertTrue(np.array_equal(p, T.get_patch((4,4,4))))

    ####################################################################
    unittest.main()

    ####################################################################