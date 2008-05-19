#!/usr/bin/env python
#
#   charts.py
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

"""
Programmatic access to `Google Chart API`_.

.. _Google Chart API: http://code.google.com/apis/chart/
"""

from string import ascii_lowercase, ascii_uppercase, digits
from urllib import urlencode

__author__ = 'Ross Light'
__date__ = 'May 2, 2008'
__docformat__ = 'reStructuredText'
__all__ = ['Chart',
           'PieChart',
           'GoogleOMeter',]

class Chart(object):
    """
    Abstract base class for charts.
    
    Each chart can have several data sets, the meaning of which depends on the
    chart type.  Most charts only have one data set.
    
    :CVariables:
        chart_type : str
            The Google Chart API chart type
    :IVariables:
        data : list of list of numbers
            The data set(s) for the chart
        colors : list of hex strings
            The colors of the chart components
    """
    chart_type = None
    
    def __init__(self, data, colors=None):
        if type(self) is Chart:
            raise TypeError("Chart is an abstract base class")
        if isinstance(data[0], (list, tuple)):
            self.data = data
        else:
            self.data = [data]
        self.colors = colors
    
    def build_link(self, size, transparent=True):
        """
        Builds the link to the chart.
        
        :Parameters:
            size : tuple of int
                The size of the chart image (in pixels)
        :Keywords:
            transparent : bool
                Whether the background should be transparent
        :Returns: The link to the chart
        :ReturnType: str
        """
        params = self._get_params()
        params['chs'] = '%ix%i' % (size[0], size[1])
        params['cht'] = self._get_type()
        params['chd'], params['chds'] = self.__build_data()
        if self.colors is not None:
            params['chco'] = ','.join(self.colors)
        if transparent:
            params['chf'] = 'bg,s,00000000'
        params = dict((key, value) for key, value in params.iteritems()
                      if value is not None)
        return "http://chart.apis.google.com/chart?" + urlencode(params)
    
    def _get_params(self):
        """
        Returns type-specific parameters.
        
        This method exists solely for subclasses to override.
        
        :Returns: Additional parameters to give to the link
        :ReturnType: dict
        """
        return dict()
    
    def _get_type(self):
        """
        Returns chart type.
        
        This method exists solely for subclasses to override.  Default
        implementation returns `chart_type`.
        
        :Returns: Chart type
        :ReturnType: str
        """
        return self.chart_type
    
    def __build_data(self):
        absmin = min(min(dataset) for dataset in self.data)
        absmax = max(max(dataset) for dataset in self.data)
        max_range = max((max(dataset) - min(dataset) + 1)
                        for dataset in self.data)
        allints = all(all(isinstance(datum, (int, long)) for datum in dataset)
                      for dataset in self.data)
        if absmin >= 0.0 and absmax <= 100.0:
            return self.__build_text_data()
        elif allints and max_range <= 62:
            return self.__build_simple_data()
        elif allints and max_range <= 4096:
            return self.__build_extended_data()
        else:
            return self.__build_scaled_data()
    
    def __build_text_data(self):
        encoded_sets = []
        for dataset in self.data:
            new_set = []
            for datum in dataset:
                if datum is None:
                    new_set.append(-1)
                else:
                    new_set.append(float(datum))
            encoded_sets.append(','.join('%.1f' % datum for datum in new_set))
        return ('t:' + '|'.join(encoded_sets), None)
    
    def __build_scaled_data(self):
        encoded_sets = []
        set_limits = []
        for dataset in self.data:
            new_set = []
            datamin = min(dataset)
            datamax = max(dataset)
            set_limits += [datamin, datamax]
            for datum in dataset:
                if datum is None:
                    new_set.append(datamin - 50)
                else:
                    new_set.append(float(datum))
            encoded_sets.append(','.join('%.1f' % datum for datum in new_set))
        return ('t:' + '|'.join(encoded_sets),
                ','.join('%.1f' % limit for limit in set_limits))
    
    def __build_simple_data(self):
        simple_chars = ascii_uppercase + ascii_lowercase + digits
        encoded_sets = []
        for dataset in self.data:
            new_set = ''
            datamin = min(dataset)
            for datum in dataset:
                if datum is None:
                    new_set += '_'
                else:
                    new_set += simple_chars[int(datum) - datamin]
            encoded_sets.append(new_set)
        return ('s:' + ','.join(encoded_sets), None)
    
    def __build_extended_data(self):
        extended_chars = ascii_uppercase + ascii_lowercase + digits + '-.'
        encoded_sets = []
        for dataset in self.data:
            new_set = ''
            datamin = min(dataset)
            for datum in dataset:
                if datum is None:
                    new_set += '__'
                else:
                    upper, lower = divmod(datum - datamin, len(extended_chars))
                    new_set += extended_chars[int(upper)]
                    new_set += extended_chars[int(lower)]
            encoded_sets.append(new_set)
        return ('e:' + ','.join(encoded_sets), None)

class PieChart(Chart):
    """
    A circular chart representing portions of a general whole.
    
    :IVariables:
        title : str
            The title to show above the chart
        labels : list of str
            Labels for the different regions
        pie3D : bool
            Whether the chart should appear three-dimensional
    """
    chart_type = 'p'
    def __init__(self, *args, **kw):
        self.title = kw.pop('title', None)
        self.labels = kw.pop('labels', None)
        self.pie3D = kw.pop('pie3D', False)
        super(PieChart, self).__init__(*args, **kw)
    
    def _get_params(self):
        if self.labels is None:
            labels = None
        else:
            labels = '|'.join(self.labels)
        return dict(chtt=self.title,
                    chl=labels,)
    
    def _get_type(self):
        if self.pie3D:
            return 'p3'
        else:
            return self.chart_type

class GoogleOMeter(Chart):
    """
    A gauge that goes from left to right as the value increases from 0 to 100.
    """
    chart_type = 'gom'
