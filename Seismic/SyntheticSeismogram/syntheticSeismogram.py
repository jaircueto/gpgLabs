import numpy as np
import matplotlib.pyplot as plt
import scipy.io
try:
    from IPython.html.widgets import  interact, interactive, IntSlider, widget, FloatText, FloatSlider
    pass
except Exception, e:
    from ipywidgets import interact, interactive, IntSlider, widget, FloatText, FloatSlider

def getPlotLog(d,log,dmax=200):
    d = np.array(d, dtype=float)
    log = np.array(log, dtype=float)

    dplot   = np.kron(d,np.ones(2))
    logplot = np.kron(log,np.ones(2))

    # dplot   = dplot[1:]
    dplot   = np.append(dplot[1:],dmax)

    return dplot, logplot


def getImpedance(rholog,vlog):
    """
    Acoustic Impedance is the product of density and velocity
    $$
    Z = \\rho v
    $$
    """
    rholog, vlog = np.array(rholog, dtype=float), np.array(vlog, dtype=float),
    return rholog*vlog


def getReflectivity(d,rho,v,usingT=True):
    """
    The reflection coefficient of an interface is
    $$
    R_i = \\frac{Z_{i+1} - Z_{i}}{Z_{i+1}+Z_{i}}
    $$
    The reflectivity can also include the effect of transmission through above layers, in which case the reflectivity is given by
    $$
    \\text{reflectivity} = R_i \\pi_{j = 1}^{i-1}(1-R_j^2)
    $$
    """
    Z   = getImpedance(rho,v)         # acoustic impedance
    dZ  = (Z[1:] - Z[:-1])
    sZ  = (Z[:-1] + Z[1:])
    R   = dZ/sZ # reflection coefficients

    nlayer = len(v) # number of layers

    rseries = R

    if usingT:
        for i in range(nlayer-1):
            rseries[i+1:] = rseries[i+1:]*(1.-R[i]**2)

    rseries = np.array(rseries, dtype=float)
    R       = np.array(R, dtype = float)

    return rseries, R


def getTimeDepth(d,v,dmax=200):
    """
    The time depth conversion is computed by determining the two-way travel time for a reflection from a given depth.
    """

    d = np.sort(d)
    d = np.append(d,dmax)

    twttop  = 2.*np.diff(d)/v    # 2-way travel time within each layer
    twttop  = np.append(0.,twttop)
    twttop  = np.cumsum(twttop)       # 2-way travel time from surface to top of each layer

    return d, twttop


def getLogs(d, rho, v, usingT=True):
    """
    Function to make plotting convenient
    """
    dpth, rholog  = getPlotLog(d,rho)
    _   , vlog    = getPlotLog(d,v)
    zlog          = getImpedance(rholog,vlog)
    rseries, _    = getReflectivity(d,rho,v,usingT)
    return dpth, rholog, vlog, zlog, rseries


def syntheticSeismogram(d, rho, v, wavf, wavA=1., usingT=True, wavtyp = 'RICKER', dt=0.0001, dmax=200):
    """
    function syntheticSeismogram(d, rho, v, wavtyp, wavf, usingT)

    syntheicSeismogram generates a synthetic seismogram for
    a simple 1-D layered model.

    Inputs:
        d      : depth to the top of each layer (m)
        rho    : density of each layer (kg/m^3)
        v      : velocity of each layer (m/s)
                    The last layer is assumed to be a half-space
        wavf   : wavelet frequency
        wavA   : wavelet amplitude
        usintT : using Transmission coefficients?
        wavtyp : type of Wavelet
                    The wavelet options are:
                        Ricker: takes one frequency
                        Gaussian: still in progress
                        Ormsby: takes 4 frequencies
                        Klauder: takes 2 frequencies
        usingT : use transmission coefficients?

    Lindsey Heagy
    lheagy@eos.ubc.ca
    Created:  November 30, 2013
    Modified: October 3, 2014
    """

    v, rho, d = np.array(v, dtype=float),   np.array(rho, dtype=float), np.array(d, dtype=float)
    usingT    = np.array(usingT, dtype=bool)

    _, t = getTimeDepth(d,v,dmax)
    rseries,R = getReflectivity(d,rho,v)

    # time for reflectivity series
    tref   = t[1:-1]

    # create time vector
    t = np.arange(t.min(),t.max(),dt)

    # make wavelet
    twav   = np.arange(-2.0/np.min(wavf), 2.0/np.min(wavf), dt)

    # Get source wavelet
    wav = {'RICKER':getRicker, 'ORMSBY':getOrmsby, 'KLAUDER':getKlauder}[wavtyp](wavf,twav)
    wav = wavA*wav

    rseriesconv = np.zeros(len(t))
    for i in range(len(tref)):
         index = np.abs(t - tref[i]).argmin()
         rseriesconv[index] = rseries[i]

    # Do the convolution
    seis  = np.convolve(wav,rseriesconv)
    tseis = np.min(twav)+dt*np.arange(len(seis))
    index = np.logical_and(tseis >= 0, tseis <= np.max(t))
    tseis = tseis[index]
    seis  = seis[index]

    return tseis, seis, twav, wav, tref, rseries



## WAVELET DEFINITIONS
pi = np.pi
def getRicker(f,t):
    """
    Retrieves a Ricker wavelet with center frequency f.
    See: http://www.subsurfwiki.org/wiki/Ricker_wavelet
    """
    # assert len(f) == 1, 'Ricker wavelet needs 1 frequency as input'
    # f = f[0]
    pift = pi*f*t
    wav = (1 - 2*pift**2)*np.exp(-pift**2)
    return wav

# def getGauss(f,t):
#     assert len(f) == 1, 'Gauss wavelet needs 1 frequency as input'
#     f = f[0]

def getOrmsby(f,t):
    """
    Retrieves an Ormsby wavelet with low-cut frequency f[0], low-pass frequency f[1], high-pass frequency f[2] and high-cut frequency f[3]
    See: http://www.subsurfwiki.org/wiki/Ormsby_filter
    """
    assert len(f) == 4, 'Ormsby wavelet needs 4 frequencies as input'
    f = np.sort(f) #Ormsby wavelet frequencies must be in increasing order
    pif   = pi*f
    den1  = pif[3] - pif[2]
    den2  = pif[1] - pif[0]
    term1 = (pif[3]*np.sinc(pif[3]*t))**2 - (pif[2]*np.sinc(pif[2]))**2
    term2 = (pif[1]*np.sinc(pif[1]*t))**2 - (pif[0]*np.sinc(pif[0]))**2

    wav   = term1/den1 - term2/den2;
    return wav

def getKlauder(f,t,T=5.0):
    """
    Retrieves a Klauder Wavelet with upper frequency f[0] and lower frequency f[1].
    See: http://www.subsurfwiki.org/wiki/Ormsby_filter
    """
    assert len(f) == 2, 'Klauder wavelet needs 2 frequencies as input'

    k  = np.diff(f)/T
    f0 = np.sum(f)/2.0
    wav = np.real(np.sin(pi*k*t*(T-t))/(pi*k*t)*np.exp(2*pi*1j*f0*t))
    return wav



## Plotting Functions

def plotLogFormat(log, dpth,xlim, col='blue'):
    """
    Nice formatting for plotting logs as a function of depth
    """
    ax = plt.plot(log,dpth,linewidth=2,color=col)
    plt.xlim(xlim)
    plt.ylim((dpth.min(),dpth.max()))
    plt.grid()
    plt.gca().invert_yaxis()
    plt.setp(plt.xticks()[1],rotation='90',fontsize=9)
    plt.setp(plt.yticks()[1],fontsize=9)

    return ax


def plotLogs(d, rho, v, usingT=True):
    """
    Plotting wrapper to plot density, velocity, acoustic impedance and reflectivity as a function of depth.
    """
    d = np.sort(d)
    dpth, rholog, vlog, zlog, rseries  = getLogs(d, rho, v, usingT)
    nd   = len(dpth)


    xlimrho = (1.95,5.05)
    xlimv   = (0.25,4.05)
    xlimz   = (xlimrho[0]*xlimv[0], xlimrho[1]*xlimv[1])

    # Plot Density
    plt.figure(1)

    plt.subplot(141)
    plotLogFormat(rholog*10**-3,dpth,xlimrho,'blue')
    plt.title('$\\rho$')
    plt.xlabel('Density \n $\\times 10^3$ (kg /m$^3$)',fontsize=9)
    plt.ylabel('Depth (m)',fontsize=9)

    plt.subplot(142)
    plotLogFormat(vlog*10**-3,dpth,xlimv,'red')
    plt.title('$v$')
    plt.xlabel('Velocity \n $\\times 10^3$ (m/s)',fontsize=9)
    plt.setp(plt.yticks()[1],visible=False)

    plt.subplot(143)
    plotLogFormat(zlog*10.**-6.,dpth,xlimz,'green')
    plt.gca().set_title('$Z = \\rho v$')
    plt.gca().set_xlabel('Impedance \n $\\times 10^{6}$ (kg m$^{-2}$ s$^{-1}$)',fontsize=9)
    plt.setp(plt.yticks()[1],visible=False)

    plt.subplot(144)
    plt.hlines(d[1:],np.zeros(len(d)-1),rseries,linewidth=2)
    plt.plot(np.zeros(nd),dpth,linewidth=2,color='black')
    plt.xlim((-1., 1.))
    if usingT == True:
        plt.title('Reflectivity', fontsize = 8.);
        plt.gca().set_xlabel('Reflectivity', fontsize = 8.)
    else:
        plt.title('Reflection Coeff.', fontsize = 8.);
        plt.gca().set_xlabel('Reflection Coeff.', fontsize = 8.)
    plt.grid()
    plt.gca().invert_yaxis()
    plt.setp(plt.xticks()[1],rotation='90',fontsize=9)
    plt.setp(plt.yticks()[1],visible=False)

    plt.tight_layout()
    plt.show()


def plotTimeDepth(d,rho,v):
    """
    Wrapper to plot time-depth conversion based on the provided velocity model
    """
    rseries, _    = getReflectivity(d,rho,v,usingT=True)
    dpth,t = getTimeDepth(d,v)
    nd   = len(dpth)

    plt.figure(num=0, figsize = (10, 4))
    ax1 = plt.subplot(131)
    ax2 = plt.subplot(132)
    ax3 = plt.subplot(133)

    ax1.hlines(d[1:],np.zeros(len(d)-1),rseries,linewidth=2)
    ax1.plot(np.zeros(nd),dpth,linewidth=2,color='black')
    ax1.invert_yaxis()
    ax1.set_xlim(-1, 1)
    ax1.grid(True)
    ax1.set_xlabel("Reflectivity")
    ax1.set_ylabel("Depth (m)")

    ax3.hlines(t[1:-1],np.zeros(len(d)-1),rseries,linewidth=2)
    ax3.plot(np.zeros(nd),t,linewidth=2,color='black')
    # ax3.set_ylim(0., 0.28)
    ax3.invert_yaxis()
    ax3.set_xlim(-1, 1)
    ax3.grid(True)
    ax3.set_xlabel("Reflectivity")
    ax3.set_ylabel("Two Way Time (s)")


    ax2.plot(t,dpth,linewidth=2)
    ax2.ticklabel_format(style='sci', axis='x', scilimits=(0,0))
    ax1.set_title('Depth')
    ax2.set_title('Depth to Time')
    ax3.set_title('Time')
    ax2.grid()

    ax2.set_ylabel('Depth (m)',fontsize=9)
    ax2.set_xlabel('Two Way Time (s)',fontsize=9)
    ax1.set_ylabel('Depth (m)',fontsize=9)
    ax3.set_ylabel('Two Way Time (s)',fontsize=9)

    plt.tight_layout()
    plt.show()


def plotSeismogram(d, rho, v, wavf, wavA=1., noise = 0., usingT=True, wavtyp='RICKER'):
    """
    Plotting function to plot the wavelet, reflectivity series and seismogram as functions of time provided the geologic model (depths, densities, and velocities)
    """

    tseis, seis, twav, wav, tref, rseriesconv = syntheticSeismogram(d, rho, v, wavf, wavA, usingT,wavtyp)

    noise  = noise*np.max(np.abs(seis))*np.random.randn(seis.size)
    filt   = np.arange(1., 15.)
    filtr  = filt[::-1]
    filt   = np.append(filt,filtr[1:])*1./15.
    noise  = np.convolve(noise,filt)
    noise  = noise[0:seis.size]

    seis = seis + noise

    plt.figure(num=0, figsize = (8, 5))

    plt.subplot(131)
    plt.plot(wav, twav,linewidth=1,color='black')
    posind = wav > 0.
    plt.fill_between(wav[posind], twav[posind], np.zeros_like(wav[posind]), color='k')
    plt.title('Wavelet')
    plt.xlim((-2.,2.))
    plt.grid()
    plt.ylim((tseis.min()-tseis.mean(),tseis.max()-tseis.mean()))
    plt.gca().invert_yaxis()
    plt.setp(plt.xticks()[1],rotation='90',fontsize=9)
    plt.setp(plt.yticks()[1],fontsize=9)
    plt.gca().set_xlabel('Amplitude',fontsize=9)
    plt.gca().set_ylabel('Time (s)',fontsize=9)

    plt.subplot(132)
    plt.plot(np.zeros(tref.size),(tseis.max(),tseis.min()),linewidth=2,color='black')
    plt.hlines(tref,np.zeros(len(rseriesconv)),rseriesconv,linewidth=2) #,'marker','none'
    if usingT == True:
        plt.title('Reflectivity')
    else:
        plt.title('Reflection Coeff.')
    plt.grid()
    plt.ylim((0,tseis.max()))
    plt.gca().invert_yaxis()
    plt.xlim((-2.,2.))
    plt.setp(plt.xticks()[1],rotation='90',fontsize=9)
    plt.setp(plt.yticks()[1],fontsize=9)
    plt.gca().set_xlabel('Amplitude',fontsize=9)
    plt.gca().set_ylabel('Time (s)',fontsize=9)

    plt.subplot(133)
    posind = seis > 0.
    plt.plot(seis,tseis,color='black',linewidth=1)
    plt.fill_between(seis[posind], tseis[posind], np.zeros_like(seis[posind]), color='k', edgecolor='white')
    plt.title('Seismogram')
    plt.grid()
    plt.ylim((tseis.min(),tseis.max()))
    plt.gca().invert_yaxis()
    plt.xlim((-0.95,0.95))
    plt.setp(plt.xticks()[1],rotation='90',fontsize=9)
    plt.setp(plt.yticks()[1],fontsize=9)
    plt.gca().set_xlabel('Amplitude',fontsize=9)
    plt.gca().set_ylabel('Time (s)',fontsize=9)

    plt.tight_layout()
    plt.show()

def plotSeismogramV2(d, rho, v, wavf, wavA=1., noise = 0., usingT=True, wavtyp='RICKER'):
    """
    Plotting function to show physical property logs (in depth) and seismogram (in time).
    """

    dpth, rholog, vlog, zlog, rseries  = getLogs(d, rho, v, usingT)
    tseis, seis, twav, wav, tref, rseriesconv = syntheticSeismogram(d, rho, v, wavf, wavA, usingT,wavtyp)

    noise  = noise*np.max(np.abs(seis))*np.random.randn(seis.size)
    filt   = np.arange(1.,21.)
    filtr  = filt[::-1]
    filt   = np.append(filt,filtr[1:])*1./21.
    noise  = np.convolve(noise,filt)
    noise  = noise[0:seis.size]

    xlimrho = (1.95,5.05)
    xlimv   = (0.25,4.05)
    xlimz   = (xlimrho[0]*xlimv[0], xlimrho[1]*xlimv[1])

    seis = seis + noise

    plt.figure(num=0, figsize = (8, 5))

    plt.subplot(141)
    plt.plot(wav,twav,linewidth=1,color='black')
    posind = wav > 0.
    plt.fill_between(wav[posind], twav[posind], np.zeros_like(wav[posind]), color='k')
    plt.title('Wavelet')
    plt.xlim((-1., 1.))
    plt.ylim((tseis.min()-tseis.mean(),tseis.max()-tseis.mean()))
    plt.grid()
    plt.gca().invert_yaxis()
    plt.setp(plt.xticks()[1],rotation='90',fontsize=9)
    plt.setp(plt.yticks()[1],fontsize=9)
    plt.gca().set_xlabel('Amplitude',fontsize=9)
    plt.gca().set_ylabel('Time (s)',fontsize=9)

    plt.subplot(142)
    plotLogFormat(rholog*10**-3,dpth,xlimrho,'blue')
    plt.title('$\\rho$')
    plt.xlabel('Density \n $\\times 10^3$ (kg /m$^3$)',fontsize=9)
    plt.ylabel('Depth (m)',fontsize=9)

    plt.subplot(143)
    plotLogFormat(vlog*10**-3,dpth,xlimv,'red')
    plt.title('$v$')
    plt.xlabel('Velocity \n $\\times 10^3$ (m/s)',fontsize=9)
    plt.ylabel('Depth (m)',fontsize=9)

    plt.subplot(144)
    posind = seis > 0.
    plt.plot(seis,tseis,color='black',linewidth=1)
    plt.fill_between(seis[posind], tseis[posind], np.zeros_like(seis[posind]), color='k', edgecolor='white')
    plt.title('Seismogram')
    plt.grid()
    plt.ylim((tseis.min(),tseis.max()))
    plt.gca().invert_yaxis()
    plt.xlim((-1., 1.))
    plt.setp(plt.xticks()[1],rotation='90',fontsize=9)
    plt.setp(plt.yticks()[1],fontsize=9)
    plt.gca().set_xlabel('Amplitude',fontsize=9)
    plt.gca().set_ylabel('Depth (m)',fontsize=9)

    plt.tight_layout()
    plt.show()



def plotSeismogramV3(d, rho, v, wavf, wavA=1., noise = 0., usingT=True, wavtyp='RICKER'):
    """
    Plotting function to show physical property logs (in depth) and seismogram (in time).
    """

    dpth, rholog, vlog, zlog, rseries  = getLogs(d, rho, v, usingT)
    tseis, seis, twav, wav, tref, rseriesconv = syntheticSeismogram(d, rho, v, wavf, wavA, usingT,wavtyp)

    noise  = noise*np.max(np.abs(seis))*np.random.randn(seis.size)
    filt   = np.arange(1.,21.)
    filtr  = filt[::-1]
    filt   = np.append(filt,filtr[1:])*1./21.
    noise  = np.convolve(noise,filt)
    noise  = noise[0:seis.size]

    xlimrho = (1.95,5.05)
    xlimv   = (0.25,4.05)
    xlimz   = (xlimrho[0]*xlimv[0], xlimrho[1]*xlimv[1])

    seis = seis + noise

    plt.figure(num=0, figsize = (8, 5))

    plt.subplot(141)
    plt.plot(wav,twav,linewidth=1,color='black')
    posind = wav > 0.
    plt.fill_between(wav[posind], twav[posind], np.zeros_like(wav[posind]), color='k')
    plt.title('Wavelet')
    plt.xlim((-1., 1.))
    # plt.ylim((tseis.min()-tseis.mean(),tseis.max()-tseis.mean()))
    plt.ylim((-0.1, 0.1))
    plt.grid()
    plt.gca().invert_yaxis()
    plt.setp(plt.xticks()[1],rotation='90',fontsize=9)
    plt.setp(plt.yticks()[1],fontsize=9)
    plt.gca().set_xlabel('Amplitude',fontsize=9)
    plt.gca().set_ylabel('Time (s)',fontsize=9)

    plt.subplot(142)
    plotLogFormat(rholog*10**-3,dpth,xlimrho,'blue')
    plt.title('$\\rho$')
    plt.xlabel('Density \n $\\times 10^3$ (kg /m$^3$)',fontsize=9)
    plt.ylabel('Depth (m)',fontsize=9)
    plt.xlim((0., 4.6))

    plt.subplot(143)
    plotLogFormat(vlog*10**-3,dpth,xlimv,'red')
    plt.ylim((15., 0.))
    plt.xlim((0., 1500*1e-3))
    plt.title('$v$')
    plt.xlabel('Velocity \n $\\times 10^3$ (m/s)',fontsize=9)
    plt.ylabel('Depth (m)',fontsize=9)

    plt.subplot(144)
    posind = seis > 0.
    plt.plot(seis,tseis,color='black',linewidth=1)
    plt.fill_between(seis[posind], tseis[posind], np.zeros_like(seis[posind]), color='k', edgecolor='white')
    plt.title('Seismogram')
    plt.grid()
    plt.ylim(( 0., 0.2))
    plt.gca().invert_yaxis()
    plt.xlim((-1., 1.))

    plt.setp(plt.xticks()[1],rotation='90',fontsize=9)
    plt.setp(plt.yticks()[1],fontsize=9)
    plt.gca().set_xlabel('Amplitude',fontsize=9)
    plt.gca().set_ylabel('Time (s)',fontsize=9)

    plt.tight_layout()
    plt.show()

## INTERACTIVE PLOT WRAPPERS
def plotLogsInteract(d2, d3, rho1, rho2, rho3, v1, v2, v3, usingT=False):
    """
    interactive wrapper of plotLogs
    """
    d   = np.array((0.,d2,d3), dtype=float)
    rho = np.array((rho1,rho2,rho3), dtype=float)
    v   = np.array((v1,v2,v3), dtype=float)
    plotLogs(d, rho, v, usingT)


def plotTimeDepthInteract(d2, d3, v1, v2, v3, rho):
    """
    interactive wrapper for plotTimeDepth
    """
    d   = np.array((0., d2, d3), dtype=float)
    v   = np.array((v1, v2, v3), dtype=float)
    plotTimeDepth(d, rho, v)

def plotSeismogramInteractFixMod(d, v, rho, wavf, wavA):
    """
    interactive wrapper for plot seismogram
    """

    # d      = [0., 50., 100.]      # Position of top of each layer (m)
    # v      = [500., 1000., 1500.]  # Velocity of each layer (m/s)
    # rho    = [2000., 2300., 2500.] # Density of each layer (kg/m^3)
    wavf   = np.array(wavf, dtype=float)
    usingT = True
    plotSeismogram(d, rho, v, wavf, wavA, 0., usingT)

def plotSeismogramInteract(d2,d3,rho1,rho2,rho3,v1,v2,v3,wavf,wavA,AddNoise=False,usingT=True):
    """
    interactive wrapper for plot SeismogramV2 for a fixed geologic model
    """
    d      = np.array((0.,d2,d3), dtype=float)
    v      = np.array((v1,v2,v3), dtype=float)
    rho    = np.array((rho1,rho2,rho3), dtype=float)

    if AddNoise:
        noise = 0.02
    else:
        noise = 0.

    plotSeismogramV2(d, rho, v, wavf, wavA, noise,usingT)

def plotSeismogramInteractTBL(d2,d3,rho1,rho2,rho3,v1,v2,v3,wavf,wavA,AddNoise=False,usingT=True):
    """
    interactive wrapper for plot SeismogramV2 for a fixed geologic model
    """
    d      = np.array((0.,d2,d3), dtype=float)
    v      = np.array((v1,v2,v3), dtype=float)
    rho    = np.array((rho1,rho2,rho3), dtype=float)

    if AddNoise:
        noise = 0.02
    else:
        noise = 0.

    plotSeismogramV3(d, rho, v, wavf, wavA, noise,usingT)


def plotSeismogramInteractRes(h2,wavf,AddNoise=False):
    """
    Interactive wrapper for plotSeismogramV2 for a fixed geologic model
    """
    d      = [0., 50., 50.+h2]      # Position of top of each layer (m)
    v      = [500., 1000., 1500.]  # Velocity of each layer (m/s)
    rho    = [2000., 2300., 2500.] # Density of each layer (kg/m^3)
    wavf   = np.array(wavf, dtype=float)
    usingT = True

    if AddNoise:
        noise = 0.02
    else:
        noise = 0.

    plotSeismogramV2(d, rho, v, wavf, 1., noise)

def InteractLogs(d2=50, d3=100, rho1=2300, rho2=2300, rho3=2300, v1=500, v2=1000, v3=1500):
    logs = interactive(plotLogsInteract,
        d2  =FloatSlider(min = 0.   ,max = 100. ,step = 5  , value = d2  ),
        d3  =FloatSlider(min = 100. ,max = 200. ,step = 5  , value = d3  ),
        rho1=FloatSlider(min = 2000.,max = 5000.,step = 50., value = rho1),
        rho2=FloatSlider(min = 2000.,max = 5000.,step = 50., value = rho2),
        rho3=FloatSlider(min = 2000.,max = 5000.,step = 50., value = rho3),
        v1  =FloatSlider(min = 300. ,max = 4000.,step = 50., value = v1  ),
        v2  =FloatSlider(min = 300. ,max = 4000.,step = 50., value = v2  ),
        v3  =FloatSlider(min = 300. ,max = 4000.,step = 50., value = v3  ))
    return logs

def InteractDtoT(Model):
    d20 = Model.kwargs["d2"]
    d30 = Model.kwargs["d3"]
    v10 = Model.kwargs["v1"]
    v20 = Model.kwargs["v2"]
    v30 = Model.kwargs["v3"]
    rho10 = Model.kwargs["rho1"]
    rho20 = Model.kwargs["rho2"]
    rho30 = Model.kwargs["rho3"]
    rho = np.r_[rho10, rho20, rho30]
    func = lambda d2, d3, v1, v2, v3: plotTimeDepthInteract(d2, d3, v1, v2, v3, rho)
    DtoT = interactive(
        func,
        d2=FloatSlider(min=0. , max=100. , step=5  , value=d20),
        d3=FloatSlider(min=100., max=200. , step=5  , value=d30),
        v1=FloatSlider(min=500., max=3000., step=50., value=v10),
        v2=FloatSlider(min=500., max=3000., step=50., value=v20),
        v3=FloatSlider(min=500., max=3000., step=50., value=v30)
        )

    return Model, DtoT

def InteractWconvR(Model, DtoT):
    d20 = DtoT.kwargs["d2"]
    d30 = DtoT.kwargs["d3"]
    v10 = DtoT.kwargs["v1"]
    v20 = DtoT.kwargs["v2"]
    v30 = DtoT.kwargs["v3"]
    rho10 = Model.kwargs["rho1"]
    rho20 = Model.kwargs["rho2"]
    rho30 = Model.kwargs["rho3"]
    func = lambda wavf, wavA: plotSeismogramInteractFixMod(
        d=np.r_[0., d20, d30], v=np.r_[v10, v20, v30],
        rho=np.r_[rho10, rho20, rho30], wavf=wavf, wavA=wavA)
    return interact(func,
                    wavf=(5., 100., 5.),
                    wavA=FloatSlider(min=-2., max=2., step=0.25, value=1.))

def InteractSeismogram():
    return interact(plotSeismogramInteract,d2=(0., 150., 1),
                                           d3=(0.,200., 1),
                                           rho1=(2000.,5000.,50.),
                                           rho2=(2000.,5000.,50.),
                                           rho3=(2000.,5000.,50.),
                                           v1=(100.,4000.,5.),
                                           v2=(100.,4000.,5.),
                                           v3=(300.,4000.,50.),
                                           wavf=(5., 100.,2.5),
                                           wavA=FloatSlider(min = -0.5, max = 1., step = 0.25, value = 1.),
                                           addNoise=False,
                                           usingT=True)

def InteractSeismogramTBL(v1=125, v2=125, v3=125):
    return interact(plotSeismogramInteractTBL,d2=FloatSlider(min = 1. ,max = 100.,step = 0.1, value = 9.),
                                           d3=FloatSlider(min=2. ,max = 100.,step = 0.1, value = 9.5),
                                           rho1=FloatSlider(min = 2000.,max = 5000.,step = 50.,value = 2300.),
                                           rho2=FloatSlider(min = 2000.,max = 5000.,step = 50.,value = 2300.),
                                           rho3=FloatSlider(min = 2000.,max = 5000.,step = 50.,value = 2300.),
                                           v1=FloatSlider(min = 100.,max = 1200.,step = 5., value = v1),
                                           v2=FloatSlider(min = 100.,max = 1200.,step = 5., value = v2),
                                           v3=FloatSlider(min = 100.,max = 1200.,step = 5., value = v3),
                                           wavf=FloatSlider(min = 5.,max = 100.,step = 1, value = 67),
                                           wavA=FloatSlider(min = -0.5, max = 1., step = 0.25, value = 1.),
                                           addNoise=False,
                                           usingT=True)
if __name__ == '__main__':

    d      = [0., 50., 100.]       # Position of top of each layer (m)
    v      = [500.,  1000., 1500.] # Velocity of each layer (m/s)
    rho    = [2000., 2300., 2500.] # Density of each layer (kg/m^3)
    wavtyp = 'RICKER'              # Wavelet type
    wavf   = 50.                   # Wavelet Frequency
    usingT = False                 # Use Transmission Coefficients?

    plotLogs(d,rho,v)
    #plotTimeDepth(d,v)
    #plotSeismogram(d, rho, v, wavtyp, wavf, usingT)
    #plotSeismogramV2(d, rho, v, 50., wavA=1., noise = 0., usingT=True, wavtyp='RICKER')

