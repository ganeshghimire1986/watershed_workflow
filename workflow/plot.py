import logging
import numpy as np
from matplotlib import pyplot as plt
from matplotlib import collections as pltc
import shapely
import rasterio
import descartes
import cartopy.crs

import workflow.utils
import workflow.conf

def get_ax(crs=None, fig=None, nrow=1, ncol=1, index=1):
    """Returns an axis with a projection."""
    # make a figure
    if fig is None:
        fig = plt.figure()

    # no crs, just get an ax -- you deal with it.
    if crs is None:
        return fig.add_subplot(nrow, ncol, index)
            
    try:
        # maybe the crs is itself a projected crs!
        ax = fig.add_subplot(nrow, ncol, index, projection=cartopy.crs.epsg(crs['init'][5:]))
        return ax

    except ValueError:
        if crs == workflow.conf.latlon_crs():
            # use PlateCaree projection for Lat-Long 
            projection = cartopy.crs.PlateCarree()
            ax = fig.add_subplot(nrow, ncol, index, projection=projection)
            return ax
        else:
            # not a projected crs, and don't have an easy guess for a valid projection, give up
            raise ValueError('Cannot plot CRS, it is not a projection: {}'.format(crs['init']))


def huc(huc, crs, color='k', ax=None, **kwargs):
    """Plot HUC object, a wrapper for plot.shply()"""
    return shply([huc,], crs, color, ax, **kwargs)

def hucs(hucs, crs, color='k', ax=None, **kwargs):
    """Plot SplitHUCs object, a wrapper for plot.shply()"""
    ps = [p for p in hucs.polygons()]
    return shply(ps, crs, color, ax, **kwargs)

def shapes(shps, crs, color='k', ax=None, **kwargs):
    shplys = [workflow.utils.shply(shp['geometry']) for shp in shps]
    shply(shplys, crs, color, ax, **kwargs)

def river(river, crs, color='b', ax=None, **kwargs):
    shply(river, crs, color, ax, **kwargs)

def rivers(rivers, crs, color='b', ax=None,  **kwargs):
    if type(rivers) is shapely.geometry.MultiLineString:
        return river(rivers, crs, color, ax, **kwargs)
    
    if type(color) is not str and len(color) == len(rivers):
        for r, c in zip(rivers, color):
            river(r, crs, c, ax, **kwargs)
    else:
        for r in rivers:
            river(r, crs, color, ax, **kwargs)
            
    
def shply(shps, crs, color=None, ax=None, style='-', **kwargs):
    """Plot shapely objects.

    Currently this assumes shps is an iterable collection of Points,
    Lines, or Polygons.  So while a single MultiPolygon is allowed,
    lists of MultiPolygons are not currently supported.  And
    heterogeneous collections are not supported.
    """
    if len(shps) is 0:
        return
    if 'facecolor' not in kwargs:
        kwargs['facecolor'] = 'none'

    if ax is None:
        ax = get_ax(crs)

    if not hasattr(ax, 'projection') or crs is None:
        transform = None
    else:
        transform = workflow.conf.get_transform(crs)
        
    if type(next(iter(shps))) is shapely.geometry.Point:
        # plot points
        if 'marker' not in kwargs:
            kwargs['marker'] = 'o'
        
        points = np.array([p.coords for p in shps])[:,0,:]
        if transform is None:
            ax.scatter(points[:,0], points[:,1], c=color, **kwargs)
        else:
            ax.scatter(points[:,0], points[:,1], c=color, transform=transform, **kwargs)
            
            
    elif type(next(iter(shps))) is shapely.geometry.LineString:
        # plot lines
        if 'linestyle' not in kwargs:
            kwargs['linestyle'] = style
        if 'colors' not in kwargs:
            kwargs['colors'] = color
        
        lines = [np.array(l.coords) for l in shps]
        lc = pltc.LineCollection(lines, **kwargs)
        if transform is not None:
            lc.set_transform(transform)
        ax.add_collection(lc)
        ax.autoscale()
        
    elif type(next(iter(shps))) is shapely.geometry.Polygon:
        if 'linestyle' not in kwargs:
            kwargs['linestyle'] = style

        try:
            color_len = len(color)
        except (AttributeError,TypeError):
            color_len = -1

        if type(color) is str or color_len != len(shps):
            # assume this is ONE color, and therefore can add as a multipolygon/polygon collection
            if 'edgecolor' not in kwargs:
                kwargs['edgecolor'] = color
            
            multi_poly = shapely.geometry.MultiPolygon(shps)
            patch = descartes.PolygonPatch(multi_poly, **kwargs)
            if transform is not None:
                patch.set_transform(transform)
            ax.add_patch(patch)

        else:
            # add polygons independently
            if color is None:
                for shp in shps:
                    patch = descartes.PolygonPatch(shp, **kwargs)
                    # if transform is not None:
                    #     patch.set_transform(transform)
                    ax.add_patch(patch)
            else:
                for c, shp in zip(color, shps):
                    patch = descartes.PolygonPatch(shp, edgecolor=c, **kwargs)
                    # if transform is not None:
                    #     patch.set_transform(transform)
                    ax.add_patch(patch)
        ax.autoscale()

def triangulation(points, tris, crs, color='gray', ax=None, **kwargs):
    if ax is None:
        ax = get_ax(crs)
    
    if type(color) is str and color == 'elevation' and points.shape[1] != 3:
        color = 'gray'

    if type(color) is str and color == 'elevation':
        col =  ax.tripcolor(points[:,0], points[:,1], tris, points[:,2], **kwargs)
    elif type(color) != str:
        col =  ax.tripcolor(points[:,0], points[:,1], tris, color, **kwargs)
    else:        
        col =  ax.triplot(points[:,0], points[:,1], tris, color=color, **kwargs)
    return col

def dem(profile, data, ax=None, vmin=None, vmax=None, **kwargs):
    if ax is None:
        ax = get_ax(profile['crs'])

    if vmin is None:
        vmin = np.nanmin(data)
    if vmax is None:
        vmax = np.nanmax(data)

    bounds = rasterio.transform.array_bounds(profile['height'], profile['width'], profile['transform'])
    extent = [bounds[0], bounds[2], bounds[1], bounds[3]]
    logging.info('BOUNDS: {}'.format(bounds))
    return ax.imshow(data, origin='upper', extent=extent, vmin=vmin, vmax=vmax)
