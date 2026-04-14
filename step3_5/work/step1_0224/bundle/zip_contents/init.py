import numpy as np
import proplot as pplt
from scipy.signal import savgol_filter


def find_center(da, xthreshold=0.5, ythreshold=0.5, xname='dmma_V_axis', yname='RMG_Vdc', debug=False):
    """
    Takes an xarray DataArray and find the center of the CAR/ECT feature.
    Curves are normalized between 0 and 1 and values above the thresholds are used to find the center.
    """
    def normalize(v):
        return (v - v.min()) / (v.max()-v.min())
    
    xmean = normalize(savgol_filter(np.abs(da).mean(dim=xname), 11, 1)) 
    # noise is higher along this direction
    ymean = normalize(savgol_filter(np.abs(da).mean(dim=yname), 5, 1))
    
    xfinite = da[xname][ymean > xthreshold]
    yfinite = da[yname][xmean > ythreshold]
    
    xcen, ycen = np.median(xfinite.values), np.median(yfinite.values)
    
    if debug:
        fig = pplt.figure()
        ax = fig.subplots()
        px = ax.panel('b')
        py = ax.panel('r')
        da.plot(ax=ax)
        px.plot(da[xname], ymean)
        px.axhline(xthreshold, color='r')
        py.plot(xmean, da[yname])
        py.axvline(ythreshold, color='r')
        ax.scatter(xfinite, [da[yname].values[2]]*len(xfinite))
        ax.scatter([da[xname].values[-3]]*len(yfinite), yfinite)
        ax.scatter([xcen], [ycen])
    
    return xcen, ycen
    
    
def split_in_four(da, xborder=None, yborder=None, xname='dmma_V_axis', yname='RMG_Vdc'):
    if xborder is None:
        xborder = da[xname].values.mean()
    if yborder is None:
        yborder = da[yname].values.mean()
    
    tl = da.sel(**{xname: slice(-np.inf,xborder), yname: slice(yborder, np.inf)})
    tr = da.sel(**{xname: slice(xborder,np.inf), yname: slice(yborder, np.inf)})
    bl = da.sel(**{xname: slice(-np.inf,xborder), yname: slice(-np.inf,yborder)})
    br = da.sel(**{xname: slice(xborder,np.inf), yname: slice(-np.inf,yborder)})
        
    return tl, tr, bl, br


def format_twobytwo(axs):
    """
    turn off spines, labels, ticks for shared axes
    """
    axs[0].spines['right'].set_visible(False)
    axs[0].spines['bottom'].set_visible(False)
    axs[1].spines['left'].set_visible(False)
    axs[1].spines['bottom'].set_visible(False)
    axs[2].spines['right'].set_visible(False)
    axs[2].spines['top'].set_visible(False)
    axs[3].spines['left'].set_visible(False)
    axs[3].spines['top'].set_visible(False)
    
    axs[0].format(xticks=[], xlabel='', ylabel='$V_\mathrm{RD}$ (mV)')
    axs[1].format(xticks=[], yticks=[], xlabel='', ylabel='')
    axs[2].format(xlabel='$V_\mathrm{LD}$ (mV)', ylabel='$V_\mathrm{RD}$ (mV)')
    axs[3].format(yticks=[], xlabel='$V_\mathrm{LD}$ (mV)', ylabel='')
    
    
def frame_sel(dx, name, selector, isel=True):
    if isel:
        dxsel = dx[name].isel(**selector)
    else:
        dxsel = dx[name].sel(**selector)
        
    return dxsel.to_dataframe().dropna().to_xarray()[name]


def plot_QD_fit(ax, Ec=3.6, Ez=0, C=0.2, delta=0.24, LA=0.43, gates=np.linspace(-10,10,501), offset=158.8):
    """
    Plots a pair of diamond charge degeneracy tips
    """
    Xs, Ys, conds = [gates+offset]*4, [], []
    
    Ys.append((gates*LA-Ez) / (1-C))
    conds.append(Ys[-1] < -delta)
    
    Ys.append((gates*LA-Ez) / (1-C))
    conds.append(Ys[-1] > delta)
    
    Ys.append((gates*LA-Ez+delta) / (-C))
    conds.append(Ys[-1] < -delta)
    
    Ys.append((gates*LA-Ez-delta) / (-C))
    conds.append(Ys[-1] > delta)
    
    for X, Y, cond in zip(Xs, Ys, conds):
        ax.plot(X[cond], Y[cond], color='k', ls='--')
        ax.plot((X+Ec/LA)[cond], Y[cond], color='k', ls='--')
        
        