#!/usr/bin/env python
#
#   model/images.py
#   TurboHvZ
#
#   Copyright (C) 2008 Ross Light
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""User-uploaded image database"""

import os
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
from uuid import UUID, uuid4

from PIL import Image as PILImage
from turbogears import config

import hvz
from hvz.model.errors import InvalidImageTypeError, ImageNotFoundError

__author__ = 'Ross Light'
__date__ = 'April 23, 2008'
__docformat__ = 'reStructuredText'
__all__ = ['pil_mime_types',
           'Image',]

pil_mime_types = {'BMP':  'image/x-ms-bmp',
                  'CUR':  'image/vnd.microsoft.icon',
                  'EPS':  'image/eps',
                  'FPX':  'image/fpx',
                  'GIF':  'image/gif',
                  'ICO':  'image/vnd.microsoft.icon',
                  'JPEG': 'image/jpeg',
                  'PCX':  'image/pcx',
                  'PDF':  'application/pdf',
                  'PNG':  'image/png',
                  'PPM':  'image/x-ppm',
                  'PSD':  'image/photoshop',
                  'SGI':  'image/sgi',
                  'TGA':  'image/x-targa',
                  'TIFF': 'image/tiff',
                  'WMF':  'image/x-wmf',
                  'XBM':  'image/x-xbm',
                  'XPM':  'image/x-xpm',}

class Image(object):
    """
    A user-submitted image.
    
    :IVariables:
        uuid : uuid.UUID
            The image's identifier
    """
    @staticmethod
    def _get_image_dir():
        dirname = config.get('hvz.image_dir',
                             os.path.join(os.getcwd(), 'images'))
        if os.path.isdir(dirname):
            pass
        elif os.path.exists(dirname):
            raise IOError("Image directory path is not a directory")
        else:
            os.mkdir(dirname)
        return dirname
    
    @staticmethod
    def get_max_file_size():
        """
        Finds the maximum image file size.
        
        :Returns: The maximum file size (in bytes)
        :ReturnType: int
        """
        # Defaults to 1MiB
        return config.get('hvz.image_max_file_size', 1024 * 1024)
    
    @staticmethod
    def get_max_image_size():
        """
        Finds the maximum image size.
        
        :Returns: The maximum image size (in pixels)
        :ReturnType: tuple of int
        """
        return config.get('hvz.image_max_image_size', (512, 512))
    
    @staticmethod
    def get_allowed_formats():
        """
        Finds the allowed file formats.
        
        :Returns: The allowed formats
        :ReturnType: frozenset of str
        """
        return frozenset(config.get('hvz.allowed_image_formats',
                                    ['JPEG', 'GIF', 'PNG']))
    
    @classmethod
    def _get_image_path(cls, uuid, make_dirs=False):
        uuid = hvz.util.to_uuid(uuid)
        dir1, dir2 = uuid.hex[:4], uuid.hex[4:8]
        if make_dirs:
            abs_dir1 = os.path.join(cls._get_image_dir(), dir1)
            abs_dir2 = os.path.join(abs_dir1, dir2)
            if not os.path.exists(abs_dir1):
                os.mkdir(abs_dir1)
            if not os.path.exists(abs_dir2):
                os.mkdir(abs_dir2)
        return os.path.join(cls._get_image_dir(), dir1, dir2, uuid.hex)
    
    @classmethod
    def by_uuid(cls, uuid):
        """
        Retrieves an image by its identifier.
        
        :Parameters:
            uuid : uuid.UUID
                The identifier to query
        :Returns: The image requested, or ``None`` if not found
        :ReturnType: Image
        """
        path = cls._get_image_path(uuid)
        if os.path.exists(path):
            return Image(uuid)
        else:
            return None
    
    def __init__(self, uuid=None):
        if uuid is None:
            uuid = uuid4()
        self.uuid = hvz.util.to_uuid(uuid)
    
    def get_mime_type(self):
        """
        Determines the MIME type of the file.
        
        This is a relatively expensive operation because it requires that
        PIL must open up the file and try to read it.
        
        :Raises IOError: If the image does not exist
        :Raises errors.InvalidImageTypeError:
            If the image is in an unrecognized format
        :Returns: The MIME type of the file
        :ReturnType: str
        """
        path = self.path
        if not os.path.exists(path):
            raise IOError("Image does not exist")
        try:
            img = PILImage.open(path)
        except IOError:
            raise InvalidImageTypeError("Unrecognized data")
        else:
            return pil_mime_types.get(img.format, 'application/octet-stream')
    
    def write(self, data):
        """
        Writes data to the image file.
        
        :Parameters:
            data : str or file-like object
                The data to write (strings are converted to StringIO files)
        :Raises errors.ImageTooLargeError: If the image is too large
        :Raises errors.InvalidImageTypeError: If the data is not a valid format
        """
        from shutil import copyfileobj
        # Convert to StringIO if data is string
        if isinstance(data, basestring):
            data = StringIO(data)
        # Check for file length
        max_size = self.get_max_file_size()
        img_buffer = data.read(max_size + 1)
        if len(img_buffer) > max_size:
            raise ImageTooLargeError("Image is greater than %i bytes" %
                                     max_size)
        data.seek(0)
        # Check for acceptable types
        try:
            img = PILImage.open(data)
        except IOError:
            raise InvalidImageTypeError("Unrecognized data")
        else:
            if img.format not in self.get_allowed_formats():
                raise InvalidImageTypeError("Image is %r, not allowed" %
                                            img.format)
        # Check for size
        max_width, max_height = self.get_max_image_size()
        img_width, img_height = img.size
        if img_width > max_width or img_height > max_height:
            raise ImageTooLargeError("Image is larger than %ix%i" %
                                     (max_width, max_height))
        # Clean up PIL image
        del img
        data.seek(0)
        # Write to path
        path = self._get_image_path(self.uuid, make_dirs=True)
        f = open(path, 'wb')
        copyfileobj(data, f)
        f.close()
    
    def delete(self):
        """
        Deletes the image from disk.
        
        :Raises errors.ImageNotFoundError: If the image is not found
        """
        path = self._get_image_path(self.uuid)
        if os.path.exists(path):
            os.remove(path)
        else:
            raise ImageNotFoundError("Image does not exist")
    
    @property
    def path(self):
        return self._get_image_path(self.uuid)
