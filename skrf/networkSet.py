#       networkSet.py
#
#
#       Copyright 2011 alex arsenovic <arsenovic@virginia.edu>
#
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later versionpy.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.

'''
.. module:: skrf.networkSet
========================================
networkSet (:mod:`skrf.networkSet`)
========================================


Provides a class representing an un-ordered set of n-port
microwave networks.


Frequently one needs to make calculations, such as mean or standard
deviation, on an entire set of n-port networks. To facilitate these
calculations the :class:`NetworkSet` class provides convenient
ways to make such calculations.

The results are returned in :class:`~skrf.network.Network` objects, so they can be plotted and saved in the same way one would do with a
:class:`~skrf.network.Network`.

The functionality in this module is provided as methods and
properties of the :class:`NetworkSet` Class.


NetworkSet Class
================

.. autosummary::
   :toctree: generated/

   NetworkSet



'''


from network import average as network_average
from network import Network
import mathFunctions as mf
import zipfile
from copy import deepcopy
import warnings
import numpy as npy
import pylab as plb

class NetworkSet(object):
    '''
    A set of Networks.

    This class allows functions on sets of Networks, such as mean or
    standard deviation, to be calculated conveniently. The results are
    returned in :class:`~skrf.network.Network` objects, so that they may be
    plotted and saved in like :class:`~skrf.network.Network` objects.

    This class also provides methods which can be used to plot uncertainty
    bounds for a set of :class:`~skrf.network.Network`.

    The names of the :class:`NetworkSet` properties are generated
    dynamically upon ititialization, and thus documentation for
    individual properties and methods is not available. However, the
    properties do follow the convention::

            >>> my_network_set.function_name_network_property_name

    For example, the complex average (mean)
    :class:`~skrf.network.Network` for a
    :class:`NetworkSet` is::

            >>> my_network_set.mean_s

    This accesses the  property 's', for each element in the
    set, and **then** calculates the 'mean' of the resultant set. The
    order of operations is important.

    Results are returned as :class:`~skrf.network.Network` objects,
    so they may be plotted or saved in the same way as for
    :class:`~skrf.network.Network` objects::

            >>> my_network_set.mean_s.plot_s_mag()
            >>> my_network_set.mean_s.write_touchstone('mean_response')

    If you are calculating functions that return scalar variables, then
    the result is accessable through the Network property .s_re. For
    example::

            >>> std_s_deg = my_network_set.std_s_deg

    This result would be plotted by::

            >>> std_s_deg.plot_s_re()


    The operators, properties, and methods of NetworkSet object are
    dynamically generated by private methods

     * :func:`~NetworkSet.__add_a_operator`
     * :func:`~NetworkSet.__add_a_func_on_property`
     * :func:`~NetworkSet.__add_a_element_wise_method`
     * :func:`~NetworkSet.__add_a_plot_uncertainty`

    thus, documentation on the individual methods and properties are
    not available.


    '''

    def __init__(self, ntwk_set, name = None):
        '''
        Initializer for NetworkSet

        Parameters
        -----------
        ntwk_set : list of :class:`~skrf.network.Network` objects
                the set of :class:`~skrf.network.Network` objects
        name : string
                the name of the NetworkSet, given to the Networks returned
                from properties of this class.
        '''
        ## type checking
        # did they pass a list of Networks?
        if not isinstance(ntwk_set[0], Network):
            raise(TypeError('input must be list of Network types'))

        # do all Networks have the same # ports?
        if len (set([ntwk.number_of_ports for ntwk in ntwk_set])) >1:
            raise(ValueError('All elements in list of Networks must have same number of ports'))

        # is all frequency information the same?
        if npy.all([(ntwk_set[0].frequency == ntwk.frequency) \
                for ntwk in ntwk_set]) == False:
            raise(ValueError('All elements in list of Networks must have same frequency information'))

        ## initialization
        # we are good to go
        self.ntwk_set = ntwk_set
        self.name = name

        # dynamically generate properties. this is slick.
        for network_property_name in \
                ['s','s_re','s_im','s_mag','s_deg','s_deg_unwrap','s_rad',\
                's_rad_unwrap','s_arcl','s_arcl_unwrap','passivity']:
            for func in [npy.mean, npy.std]:
                self.__add_a_func_on_property(func, network_property_name)


            self.__add_a_plot_uncertainty(network_property_name)
            self.__add_a_element_wise_method('plot_'+network_property_name)
            self.__add_a_element_wise_method('plot_s_db')
        for network_method_name in \
                ['write_touchstone','interpolate','plot_s_smith']:
            self.__add_a_element_wise_method(network_method_name)

        for operator_name in \
                ['__pow__','__floordiv__','__mul__','__div__','__add__','__sub__']:
            self.__add_a_operator(operator_name)

    @classmethod
    def from_zip(cls, zip_file_name, *args, **kwargs):
        '''
        creates a NetworkSet from a zipfile of touchstones. 
        
        Parameters
        -----------
        zip_file_name : string
            name of zipfile
        \\*args,\\*\\*kwargs : arguments
            passed to NetworkSet constructor
        
        Examples
        ----------
        >>>import skrf as rf
        >>>my_set = rf.NetworkSet.from_zip('myzip.zip')
            
        '''
        z = zipfile.ZipFile(zip_file_name)
        filename_list = z.namelist()
        return cls([Network(z.open(filename))
            for filename in filename_list])
    
    def __add_a_operator(self,operator_name):
        '''
        adds a operator method to the NetworkSet.

        this is made to
        take either a Network or a NetworkSet. if a Network is passed
        to the operator, each element of the set will operate on the
        Network. If a NetworkSet is passed to the operator, and is the
        same length as self. then it will operate element-to-element
        like a dot-product.
        '''
        def operator_func(self, other):
            if isinstance(other, NetworkSet):
                if len(other) != len(self):
                    raise(ValueError('Network sets must be of same length to be casacaded'))
                return NetworkSet([self.ntwk_set[k].__getattribute__(operator_name)(other.ntwk_set[k]) for k in range(len(self))])

            elif isinstance(other, Network):
                return NetworkSet([ntwk.__getattribute__(operator_name)(other) for ntwk in self.ntwk_set])

            else:
                raise(TypeError('NetworkSet operators operate on either Network, or NetworkSet types'))
        setattr(self.__class__,operator_name,operator_func)


    def __str__(self):
        '''
        '''
        output =  \
                'A NetworkSet of length %i'%len(self.ntwk_set)

        return output

    def __repr__(self):
        return self.__str__()

    def __getitem__(self,key):
        '''
        returns an element of the network set
        '''
        return self.ntwk_set[key]

    def __len__(self):
        '''
        returns an element of the network set
        '''
        return len(self.ntwk_set)


    def __add_a_element_wise_method(self,network_method_name):
        def func(self,  *args, **kwargs):
            return self.element_wise_method(network_method_name, *args, **kwargs)
        setattr(self.__class__,network_method_name,func)


    def __add_a_func_on_property(self,func,network_property_name):
        '''
        dynamically adds a property to this class (NetworkSet).
        this is mostly used internally to genrate all of the classes
        properties.

        takes:
                network_property_name: a property of the Network class,
                        a string. this must have a matrix output of shape fxnxn
                func: a function to be applied to the network_property
                        accross the first axis of the property's output



        example:
                my_ntwk_set.add_a_func_on_property('s',mean)


        '''
        fget = lambda self: fon(self.ntwk_set,func,network_property_name,\
                name = self.name)
        setattr(self.__class__,func.__name__+'_'+network_property_name,\
                property(fget))

    def __add_a_plot_uncertainty(self,network_property_name):
        '''

        takes:
                network_property_name: a property of the Network class,
                        a string. this must have a matrix output of shape fxnxn



        example:
                my_ntwk_set.add_a_func_on_property('s',mean)


        '''
        def plot_func(self,*args, **kwargs):
            kwargs.update({'attribute':network_property_name})
            self.plot_uncertainty_bounds_component(*args,**kwargs)

        setattr(self.__class__,'plot_uncertainty_bounds_'+\
                network_property_name,plot_func)
    
    def element_wise_method(self,network_method_name, *args, **kwargs):
        '''
        calls a given method of each element and returns the result as
        a new NetworkSet if the output is a Network.
        '''
        output = [ntwk.__getattribute__(network_method_name)(*args, **kwargs) for ntwk in self.ntwk_set]
        if isinstance(output[0],Network):
            return NetworkSet(output)
        else:
            return output


    @property
    def mean_s_db(self):
        '''
        the mean magnitude in dB.

        note:
                the mean is taken on the magnitude before convertedto db, so
                        magnitude_2_db( mean(s_mag))
                which is NOT the same as
                        mean(s_db)
        '''
        ntwk= self.mean_s_mag
        ntwk.s = ntwk.s_db
        return ntwk

    @property
    def std_s_db(self):
        '''
        the mean magnitude in dB.

        note:
                the mean is taken on the magnitude before convertedto db, so
                        magnitude_2_db( mean(s_mag))
                which is NOT the same as
                        mean(s_db)
        '''
        ntwk= self.std_s_mag
        ntwk.s = ntwk.s_db
        return ntwk

    @property
    def inv(self):
        return NetworkSet( [ntwk.inv for ntwk in self.ntwk_set])

    def set_wise_function(self, func, a_property, *args, **kwargs):
        '''
        calls a function on a specific property of the networks in
        this NetworkSet.

        example:
                my_ntwk_set.set_wise_func(mean,'s')
        '''
        return fon(self.ntwk_set, func, a_property, *args, **kwargs)

    # plotting functions
    #def plot_uncertainty_bounds(self,attribute='s_mag',m=0,n=0,\
        #n_deviations=3, alpha=.3,fill_color ='b',std_attribute=None,*args,**kwargs):
        #'''
        #plots mean value with +- uncertainty bounds in an Network attribute,
        #for a list of Networks.

        #takes:
            #attribute: attribute of Network type to analyze [string]
            #m: first index of attribute matrix [int]
            #n: second index of attribute matrix [int]
            #n_deviations: number of std deviations to plot as bounds [number]
            #alpha: passed to matplotlib.fill_between() command. [number, 0-1]
            #*args,**kwargs: passed to Network.plot_'attribute' command

        #returns:
            #None


        #Caution:
            #if your list_of_networks is for a calibrated short, then the
            #std dev of deg_unwrap might blow up, because even though each
            #network is unwrapped, they may fall on either side fo the pi
            #relative to one another.
        #'''

        ## calculate mean response, and std dev of given attribute
        #ntwk_mean = average(self.ntwk_set)
        #if std_attribute is None:
            ## they want to calculate teh std deviation on a different attribute
            #std_attribute = attribute
        #ntwk_std = func_on_networks(self.ntwk_set,npy.std, attribute=std_attribute)

        ## pull out port of interest
        #ntwk_mean.s = ntwk_mean.s[:,m,n]
        #ntwk_std.s = ntwk_std.s[:,m,n]

        ## create bounds (the s_mag here is confusing but is realy in units
        ## of whatever 'attribute' is. read the func_on_networks call to understand
        #upper_bound =  ntwk_mean.__getattribute__(attribute) +\
            #ntwk_std.s_mag*n_deviations
        #lower_bound =   ntwk_mean.__getattribute__(attribute) -\
            #ntwk_std.s_mag*n_deviations

        ## find the correct ploting method
        #plot_func = ntwk_mean.__getattribute__('plot_'+attribute)

        ##plot mean response
        #plot_func(*args,**kwargs)

        ##plot bounds
        #plb.fill_between(ntwk_mean.frequency.f_scaled, \
            #lower_bound.squeeze(),upper_bound.squeeze(), alpha=alpha, color=fill_color)
        #plb.axis('tight')
        #plb.draw()

    def uncertainty_ntwk_triplet(self, attribute,n_deviations=3):
        '''
        returns a 3-tuple of Network objects which contain the
        mean, upper_bound, and lower_bound for the given Network
        attribute.

        Used to save and plot uncertainty information data
        '''
        ntwk_mean = self.__getattribute__('mean_'+attribute)
        ntwk_std = self.__getattribute__('std_'+attribute)
        ntwk_std.s = n_deviations * ntwk_std.s

        upper_bound = (ntwk_mean +ntwk_std)
        lower_bound = (ntwk_mean -ntwk_std)

        return (ntwk_mean, lower_bound, upper_bound)

    def plot_uncertainty_bounds_component(self,attribute,m=0,n=0,\
            type='shade',n_deviations=3, alpha=.3, color_error =None,markevery_error=20,
            ax=None,ppf=None,kwargs_error={},*args,**kwargs):
        '''
        plots mean value of the NetworkSet with +- uncertainty bounds
        in an Network's attribute. This is designed to represent
        uncertainty in a scalar component of the s-parameter. for example
        ploting the uncertainty in the magnitude would be expressed by,

                mean(abs(s)) +- std(abs(s))

        the order of mean and abs is important.


        takes:
                attribute: attribute of Network type to analyze [string]
                m: first index of attribute matrix [int]
                n: second index of attribute matrix [int]
                type: ['shade' | 'bar'], type of plot to draw
                n_deviations: number of std deviations to plot as bounds [number]
                alpha: passed to matplotlib.fill_between() command. [number, 0-1]
                color_error: color of the +- std dev fill shading
                markevery_error: if type=='bar', this controls frequency
                        of error bars
                ax: Axes to plot on
                ppf: post processing function. a function applied to the
                        upper and low
                *args,**kwargs: passed to Network.plot_s_re command used
                        to plot mean response
                kwargs_error: dictionary of kwargs to pass to the fill_between
                        or errorbar plot command depending on value of type.

        returns:
                None


        Note:
                for phase uncertainty you probably want s_deg_unwrap, or
                similar.  uncerainty for wrapped phase blows up at +-pi.

        '''
        ylabel_dict = {'s_mag':'Magnitude','s_deg':'Phase (deg)',
                's_deg_unwrap':'Phase (deg)','s_deg_unwrapped':'Phase (deg)',
                's_db':'Magnitude (dB)'}

        ax = plb.gca()

        ntwk_mean = self.__getattribute__('mean_'+attribute)
        ntwk_std = self.__getattribute__('std_'+attribute)
        ntwk_std.s = n_deviations * ntwk_std.s

        upper_bound = (ntwk_mean.s[:,m,n] +ntwk_std.s[:,m,n]).squeeze()
        lower_bound = (ntwk_mean.s[:,m,n] -ntwk_std.s[:,m,n]).squeeze()

        if ppf is not None:
            if type =='bar':
                warnings.warn('the \'ppf\' options doesnt work correctly with the bar-type error plots')
            ntwk_mean.s = ppf(ntwk_mean.s)
            upper_bound = ppf(upper_bound)
            lower_bound = ppf(lower_bound)
            lower_bound[npy.isnan(lower_bound)]=min(lower_bound)

        if type == 'shade':
            ntwk_mean.plot_s_re(ax=ax,m=m,n=n,*args, **kwargs)
            if color_error is None:
                color_error = ax.get_lines()[-1].get_color()
            ax.fill_between(ntwk_mean.frequency.f_scaled, \
                    lower_bound,upper_bound, alpha=alpha, color=color_error,
                    **kwargs_error)
            #ax.plot(ntwk_mean.frequency.f_scaled,ntwk_mean.s[:,m,n],*args,**kwargs)
        elif type =='bar':
            ntwk_mean.plot_s_re(ax=ax,m=m,n=n,*args, **kwargs)
            if color_error is None:
                color_error = ax.get_lines()[-1].get_color()
            ax.errorbar(ntwk_mean.frequency.f_scaled[::markevery_error],\
                    ntwk_mean.s_re[:,m,n].squeeze()[::markevery_error], \
                    yerr=ntwk_std.s_mag[:,m,n].squeeze()[::markevery_error],\
                    color=color_error,**kwargs_error)

        else:
            raise(ValueError('incorrect plot type'))

        ax.set_ylabel(ylabel_dict.get(attribute,''))
        ax.axis('tight')

    def plot_uncertainty_bounds_s_db(self,*args, **kwargs):
        '''
        this just calls
                plot_uncertainty_bounds(attribute= 's_mag',*args,**kwargs)
        see plot_uncertainty_bounds for help

        '''
        kwargs.update({'attribute':'s_mag','ppf':mf.magnitude_2_db})
        self.plot_uncertainty_bounds_component(*args,**kwargs)

    
    def plot_uncertainty_decomposition(self, m=0,n=0):
        '''
        plots the total and  component-wise uncertainty
        
        Parameters
        --------------
        m : int
            first s-parameters index
        n :
            second s-parameter index
            
        '''
        if self.name is not None:
            plb.title(r'Uncertainty Decomposition: %s $S_{%i%i}$'%(self.name,m,n))
        self.std_s.plot_s_mag(label='Distance', m=m,n=n)
        self.std_s_re.plot_s_mag(label='Real',  m=m,n=n)
        self.std_s_im.plot_s_mag(label='Imaginary',  m=m,n=n)
        self.std_s_mag.plot_s_mag(label='Magnitude',  m=m,n=n)
        self.std_s_arcl.plot_s_mag(label='Arc-length',  m=m,n=n)


    def signature(self,m=0,n=0, vmax = None, *args, **kwargs):
        '''
        visualization of relative changes in a NetworkSet.

        Creates a colored image representing the devation of each
        Network from the from mean Network of the NetworkSet, vs
        frequency.


        Parameters
        ------------
        m : int
            first s-parameters index
        n : int
            second s-parameter index
        vmax : number
            sets upper limit of colorbar, if None, will be set to
            3*mean of the magnitude of the complex difference
        \*args,\*\*kwargs : arguments, keyword arguments
            passed to :func:`~pylab.imshow`

        
        '''
        diff_set = (self - self.mean_s)
        sig = npy.array([diff_set[k].s_mag[:,m,n] \
            for k in range(len(ntwk_set))])
        if vmax is None:
            vmax == 3*sig.mean()
        imshow(sig, vmax = vmax, *args, **kwargs)
        axis('tight')
        ylabel('Network \#')
        c_bar = colorbar()
        c_bar.set_label('Distance From Mean')
        show();draw()


def plot_uncertainty_bounds_s_db(ntwk_list, *args, **kwargs):
    NetworkSet(ntwk_list).plot_uncertainty_bounds_s_db(*args, **kwargs)

def func_on_networks(ntwk_list, func, attribute='s',name=None, *args,\
        **kwargs):
    '''
    Applies a function to some attribute of a list of networks.


    Returns the result in the form of a Network. This means information
    that may not be s-parameters is stored in the s-matrix of the
    returned Network.

    Parameters
    -------------
    ntwk_list : list of :class:`~skrf.network.Network` objects
            list of Networks on which to apply `func` to
    func : function
            function to operate on `ntwk_list` s-matrices
    attribute : string
            attribute of Network's  in ntwk_list for func to act on
    \*args,\*\*kwargs : arguments and keyword arguments
            passed to func

    Returns
    ---------
    ntwk : :class:`~skrf.network.Network`
            Network with s-matrix the result of func, operating on
            ntwk_list's s-matrices


    Examples
    ----------
    averaging can be implemented with func_on_networks by

    >>> func_on_networks(ntwk_list,mean)

    '''
    data_matrix = \
            npy.array([ntwk.__getattribute__(attribute) for ntwk in ntwk_list])

    new_ntwk = ntwk_list[0].copy()
    new_ntwk.s = func(data_matrix,axis=0,*args,**kwargs)

    if name is not None:
        new_ntwk.name = name

    return new_ntwk

# short hand name for convenience
fon = func_on_networks


def getset(ntwk_dict, s, *args, **kwargs):
    '''
    Creates a :class:`NetworkSet`, of all :class:`~skrf.network.Network`s
    objects in a dictionary that contain `s` in its key. This is useful 
    for dealing with the output of 
    :func:`~skrf.convenience.load_all_touchstones`, which contains
    Networks grouped by some kind of naming convention.
    
    Parameters
    ------------
    ntwk_dict : dictionary of Network objects
        network dictionary that contains a set of keys `s`
    s : string
        string contained in the keys of ntwk_dict that are to be in the 
        NetworkSet that is returned
    \*args,\*\*kwargs : passed to NetworkSet()
    
    Returns
    --------
    ntwk_set :  NetworkSet object
        A NetworkSet that made from values of ntwk_dict with `s` in 
        their key
        
    Examples
    ---------
    >>>ntwk_dict = rf.load_all_touchstone('my_dir')
    >>>set5v = getset(ntwk_dict,'5v')
    >>>set10v = getset(ntwk_dict,'10v')
    '''
    ntwk_list = [ntwk_dict[k] for k in ntwk_dict if s in k]
    if len(ntwk_list) > 0:
        return NetworkSet( ntwk_list,*args, **kwargs)
    else:
        print 'Warning: No keys in ntwk_dict contain \'%s\''%s
        return None 
