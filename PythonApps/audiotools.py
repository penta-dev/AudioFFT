from __future__ import division
import sys
import csv
import sys
from scipy.signal import blackmanharris
from scipy.fft import rfft, irfft, fft
from scipy.ndimage import interpolation
from scipy.interpolate import interp1d
from numpy import argmax, sqrt, mean, absolute, arange, log10, mod, logspace
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
#from .PyOctaveBand import octavefilter
printed = 0

try:
    import soundfile as sf
except ImportError:
    from scikits.audiolab import Sndfile


def octavefilter(x, fs, fraction=1, order=6, limits=None, show=0, sigbands =0):
    """
    Filter a signal with octave or fractional octave filter bank. This
    method uses a Butterworth filter with Second-Order Sections
    coefficients. To obtain the correct coefficients, a subsampling is
    applied to the signal in each filtered band.

    :param x: Signal
    :param fs: Sample rate
    :param fraction: Bandwidth 'b'. Examples: 1/3-octave b=3, 1-octave b=1,
    2/3-octave b = 3/2. [Optional] Default: 1.
    :param order: Order of Butterworth filter. [Optional] Default: 6.
    :param limits: Minimum and maximum limit frequencies. [Optional] Default
    [12,20000]
    :param show: Boolean for plot o not the filter response.
    :param sigbands: Boolean to also return the signal in the time domain
    divided into bands. A list with as many arrays as there are frequency bands.
    :returns: Sound Pressure Level and Frequency array
    """

    if limits is None:
        limits = [12, 20000]

    # List type for signal var
    x = _typesignal(x)

    # Generate frequency array
    freq, freq_d, freq_u = _genfreqs(limits, fraction, fs)

    # Calculate the downsampling factor (array of integers with size [freq])
    factor = _downsamplingfactor(freq_u, fs)

    # Get SOS filter coefficients (3D - matrix with size: [freq,order,6])
    sos = _buttersosfilter(freq, freq_d, freq_u, fs, order, factor, show)

    if sigbands:
        # Create array with SPL for each frequency band
        spl = np.zeros([len(freq)])
        xb = []
        for idx in range(len(freq)):
            sd = signal.decimate(x, factor[idx])
            y = signal.sosfilt(sos[idx], sd)
            spl[idx] = 20 * np.log10(np.std(y) / 2e-5)
            xb.append(signal.resample_poly(y,factor[idx],1))
        return spl.tolist(), freq, xb
    else:
        # Create array with SPL for each frequency band
        spl = np.zeros([len(freq)])
        for idx in range(len(freq)):
            sd = signal.decimate(x, factor[idx])
            y = signal.sosfilt(sos[idx], sd)
            spl[idx] = 20 * np.log10(np.std(y) / 2e-5)
        return spl.tolist(), freq


def _typesignal(x):
    if type(x) is list:
        return x
    elif type(x) is np.ndarray:
        return x.tolist()
    elif type(x) is tuple:
        return list(x)


def _buttersosfilter(freq, freq_d, freq_u, fs, order, factor, show=0):
    # Initialize coefficients matrix
    sos = [[[]] for i in range(len(freq))]
    # Generate coefficients for each frequency band
    for idx, (lower, upper) in enumerate(zip(freq_d, freq_u)):
        # Downsampling to improve filter coefficients
        fsd = fs / factor[idx]  # New sampling rate
        # Butterworth Filter with SOS coefficients
        sos[idx] = signal.butter(
            N=order,
            Wn=np.array([lower, upper]) / (fsd / 2),
            btype='bandpass',
            analog=False,
            output='sos')

    if show:
        _showfilter(sos, freq, freq_u, freq_d, fs, factor)

    return sos


def _showfilter(sos, freq, freq_u, freq_d, fs, factor):
    wn = 8192
    w = np.zeros([wn, len(freq)])
    h = np.zeros([wn, len(freq)], dtype=np.complex_)

    for idx in range(len(freq)):
        fsd = fs / factor[idx]  # New sampling rate
        w[:, idx], h[:, idx] = signal.sosfreqz(
            sos[idx],
            worN=wn,
            whole=False,
            fs=fsd)

    fig, ax = plt.subplots()
    ax.semilogx(w, 20 * np.log10(abs(h) + np.finfo(float).eps), 'b')
    ax.grid(which='major')
    ax.grid(which='minor', linestyle=':')
    ax.set_xlabel(r'Frequency [Hz]')
    ax.set_ylabel('Amplitude [dB]')
    ax.set_title('Second-Order Sections - Butterworth Filter')
    plt.xlim(freq_d[0] * 0.8, freq_u[-1] * 1.2)
    plt.ylim(-4, 1)
    ax.set_xticks([16, 31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000])
    ax.set_xticklabels(['16', '31.5', '63', '125', '250', '500',
                        '1k', '2k', '4k', '8k', '16k'])
    plt.show()


def _genfreqs(limits, fraction, fs):
    # Generate frequencies
    freq, freq_d, freq_u = getansifrequencies(fraction, limits)

    # Remove outer frequency to prevent filter error (fs/2 < freq)
    freq, freq_d, freq_u = _deleteouters(freq, freq_d, freq_u, fs)

    return freq, freq_d, freq_u


def normalizedfreq(fraction):
    """
    Normalized frequencies for one-octave and third-octave band. [IEC
    61260-1-2014]

    :param fraction: Octave type, for one octave fraction=1,
    for third-octave fraction=3
    :type fraction: int
    :returns: frequencies array
    :rtype: list
    """
    predefined = {1: _oneoctave(),
                  3: _thirdoctave(),
                  }
    return predefined[fraction]


def _thirdoctave():
    # IEC 61260 - 1 - 2014 (added 12.5, 16, 20 Hz)
    return [12.5, 16, 20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250,
            315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000,
            5000, 6300, 8000, 10000, 12500, 16000, 20000]


def _oneoctave():
    # IEC 61260 - 1 - 2014 (added 16 Hz)
    return [16, 31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]


def _deleteouters(freq, freq_d, freq_u, fs):
    idx = np.asarray(np.where(np.array(freq_u) > fs / 2))
    if any(idx[0]):
        _printwarn('Low sampling rate, frequencies above fs/2 will be removed')
        freq = np.delete(freq, idx).tolist()
        freq_d = np.delete(freq_d, idx).tolist()
        freq_u = np.delete(freq_u, idx).tolist()
    return freq, freq_d, freq_u


def getansifrequencies(fraction, limits=None):
    """ ANSI s1.11-2004 && IEC 61260-1-2014
    Array of frequencies and its edges according to the ANSI and IEC standard.

    :param fraction: Bandwidth 'b'. Examples: 1/3-octave b=3, 1-octave b=1,
    2/3-octave b = 3/2
    :param limits: It is a list with the minimum and maximum frequency that
    the array should have. Example: [12,20000]
    :returns: Frequency array, lower edge array and upper edge array
    :rtype: list, list, list
    """

    if limits is None:
        limits = [12, 20000]

    # Octave ratio g (ANSI s1.11, 3.2, pg. 2)
    g = 10 ** (3 / 10)  # Or g = 2
    # Reference frequency (ANSI s1.11, 3.4, pg. 2)
    fr = 1000

    # Get starting index 'x' and first center frequency
    x = _initindex(limits[0], fr, g, fraction)
    freq = _ratio(g, x, fraction) * fr

    # Get each frequency until reach maximum frequency
    freq_x = 0
    while freq_x * _bandedge(g, fraction) < limits[1]:
        # Increase index
        x = x + 1
        # New frequency
        freq_x = _ratio(g, x, fraction) * fr
        # Store new frequency
        freq = np.append(freq, freq_x)

    # Get band-edges
    freq_d = freq / _bandedge(g, fraction)
    freq_u = freq * _bandedge(g, fraction)

    return freq.tolist(), freq_d.tolist(), freq_u.tolist()


def _initindex(f, fr, g, b):
    if b % 2:  # ODD ('x' solve from ANSI s1.11, eq. 3)
        return np.round(
                (b * np.log(f / fr) + 30 * np.log(g)) / np.log(g)
                )
    else:  # EVEN ('x' solve from ANSI s1.11, eq. 4)
        return np.round(
                (2 * b * np.log(f / fr) + 59 * np.log(g)) / (2 * np.log(g))
                )


def _ratio(g, x, b):
    if b % 2:  # ODD (ANSI s1.11, eq. 3)
        return g ** ((x - 30) / b)
    else:  # EVEN (ANSI s1.11, eq. 4)
        return g ** ((2 * x - 59) / (2 * b))


def _bandedge(g, b):
    # Band-edge ratio (ANSI s1.11, 3.7, pg. 3)
    return g ** (1 / (2 * b))


def _printwarn(msg):
    print('*********\n' + msg + '\n*********')


def _downsamplingfactor(freq, fs):
    guard = 0.10
    factor = (np.floor((fs / (2+guard)) / np.array(freq))).astype('int')
    for idx in range(len(factor)):
        # Factor between 1<factor<50
        factor[idx] = max(min(factor[idx], 50), 1)
    return factor


def rms_flat(a):
    """
    Return the root mean square of all the elements of *a*, flattened out.
    """
    return sqrt(mean(absolute(a)**2))


def find_range(f, x):
    """
    Find range between nearest local minima from peak at index x
    """
    for i in arange(x+1, len(f)):
        if f[i+1] >= f[i]:
            uppermin = i
            break
    for i in arange(x-1, 0, -1):
        if f[i] <= f[i-1]:
            lowermin = i + 1
            break
    return (lowermin, uppermin)

def peakSPL(signal,fs):
    N = len(signal)

    # Apply window to the signal
    win = np.hamming(N)
    signal = signal * win

    # Get the spectrum and shift it so that DC is in the middle
    spectrum = np.fft.fftshift( np.fft.fft(signal) )
    freq = np.fft.fftshift( np.fft.fftfreq(N, 1 / fs) )

    # Take only the positive frequencies
    spectrum = spectrum[N//2:]
    freq = freq[N//2:]

    # Since we just removed the energy in negative frequencies, account for that
    spectrum *= 2
    # If there is even number of samples, do not normalize the Nyquist bin
    if N % 2 == 0:
        spectrum[-1] /= 2

    # Scale the magnitude of FFT by window energy
    spectrum_mag = np.abs(spectrum) / np.sum(win)

    # To obtain RMS values, divide by sqrt(2)
    spectrum_rms = spectrum_mag / np.sqrt(2)
    # Do not scale the DC component
    spectrum_rms[0] *= np.sqrt(2)

    # Convert to decibel scale
    spectrum_db = 20 * np.log10(spectrum_rms)

    #0 dB signal is always -3dB
    fudge_factor = 3.010324185888650916
    return spectrum_db.max() + fudge_factor

def THDN(signal, sample_rate):
    """
    Measure the THD+N for a signal and print the results

    Prints the estimated fundamental frequency and the measured THD+N.  This is
    calculated from the ratio of the entire signal before and after
    notch-filtering.

    Currently this tries to find the "skirt" around the fundamental and notch
    out the entire thing.  A fixed-width filter would probably be just as good,
    if not better.
    """
    spl = format(peakSPL(signal, sample_rate))

    #spl = format(peakSPL(signal, sample_rate))
    # Get rid of DC and window the signal

    # TODO: Do this in the frequency domain, and take any skirts with it?
    signal -= mean(signal)
    windowed = signal * blackmanharris(len(signal))  # TODO Kaiser?

    # Measure the total signal before filtering but after windowing
    total_rms = rms_flat(windowed)

    # Find the peak of the frequency spectrum (fundamental frequency), and
    # filter the signal by throwing away values between the nearest local
    # minima
    f = rfft(windowed)
    i = argmax(abs(f))

    # Not exact
    #lowermin, uppermin = find_range(abs(f), i)
    #f[lowermin: uppermin] = 0

    #Use fixed
    width = 50
    f[i-width: i+width+1] = 0

    # Transform noise back into the signal domain and measure it
    # TODO: Could probably calculate the RMS directly in the frequency domain
    # instead
    noise = irfft(f)
    THDN = rms_flat(noise) / total_rms

    return ("Sample Rate: %d Frequency: %.2f SPL: %s THDpercent: %.2f THDdB: %.2f" % ( sample_rate, (sample_rate * (i / len(windowed))), spl, THDN * 100, 20 * log10(THDN)))

def FFT(signal,sample_rate):
    # Without window
    b1_o = fft(signal)

    # keep only meaningful frequencies
    NFFT = len(b1_o)
    
    if mod(NFFT,2)==0:
        Nout = (NFFT/2)+1
    else:
        Nout = (NFFT+1)/2
    
    #keep the useful half of the fft
    b1_o = b1_o[ 1 : int(Nout)]

    # Convert to dB
    b1_o = 20 * log10(abs(b1_o) / NFFT)
    
    # Scale data from 0 - Nyquist using interpolation
    freq_range = (int) (sample_rate/2)
    scale = freq_range / len(b1_o)
    b1_o_intp = interpolation.zoom(b1_o,scale,mode='nearest')

    logarr = logspace(2.4771, 3.9, num=1000)
    freq = []
    for i in logarr:
        freq.append(round(i))

    y = []
    wr.writerow(freq)
    for i in freq:
        index = 0
        y.append( b1_o_intp[i] + 50 )

    print("Sample Rate: %d Frequency Range: %dHz-%dHz" % ( sample_rate, 0, freq_range))
    
    wr.writerow(y)
    return

def load(filename):
    """
    Load a wave file and return the signal, sample rate and number of channels.

    Can be any format that libsndfile supports, like .wav, .flac, etc.
    """
    try:
        wave_file = sf.SoundFile(filename)
        signal = wave_file.read()
    except ImportError:
        wave_file = Sndfile(filename, 'r')
        signal = wave_file.read_frames(wave_file.nframes)

    channels = wave_file.channels
    sample_rate = wave_file.samplerate

    return signal, sample_rate, channels

def analyze_channels(operation,boardtype,filename, function, printresults):
    """
    Given a filename, run the given analyzer function on each channel of the
    file
    """
    signal, sample_rate, channels = load(filename)
    print('Analyzing ' + filename + ' Sample Rate:%d Channels:%d' % (sample_rate, channels))
    
    #if( operation == 'FFT'):
    #    printresults(list(range((int)(sample_rate/2))))
    print('Boardtype: ' + boardtype + ' Operation: ' + operation)
    if channels == 1:
        # Monaural
        print('-- Channel=Mono SampleRate=%d--' % (sample_rate))
        printresults(function(signal, sample_rate))
    elif channels == 2:
        # Stereo
        if np.array_equal(signal[:, 0], signal[:, 1]):
            print('-- Channel=DuplicateStereo (left/right identical) --')
            printresults(function(signal[:, 0], sample_rate))
        else:
            print('-- Channel=Left --')
            printresults(function(signal[:, 0], sample_rate))
            print('-- Channel=Right --')
            printresults(function(signal[:, 1], sample_rate))
    elif channels ==8:
        # 8-channel TDM
        if( boardtype == 'DVT'):
            print('-- Channel=Top --')
            printresults(function(signal[:, 1], sample_rate))
            print('-- Channel=SideRight --')
            printresults(function(signal[:, 3], sample_rate))
            print('-- Channel=SideLeft --')
            printresults(function(signal[:, 2], sample_rate))
            print('-- Channel=BottomRight --')
            printresults(function(signal[:, 4], sample_rate))
            print('-- Channel=BottomLeft --')
            printresults(function(signal[:, 5], sample_rate))
            print('-- Channel=BottomCentre --')
            printresults(function(signal[:, 0], sample_rate))
        elif( boardtype == 'EVT'):
            print('-- Channel=Top --')
            printresults(function(signal[:, 0], sample_rate))
            print('-- Channel=SideRight --')
            printresults(function(signal[:, 3], sample_rate))
            print('-- Channel=SideLeft --')
            printresults(function(signal[:, 2], sample_rate))
            print('-- Channel=BottomRight --')
            printresults(function(signal[:, 4], sample_rate))
            print('-- Channel=BottomLeft --')
            printresults(function(signal[:, 5], sample_rate))
            print('-- Channel=BottomCentre --')
            printresults(function(signal[:, 6], sample_rate))
    else:
        sys.exit("Unsupported channel count")
    print("Success")

def logthd(freq):
    print()
    #wr.writerow(freq)
    #wr.writerow(spl)

operation = sys.argv[1]
boardtype = sys.argv[2]
inputfile = sys.argv[3]
if inputfile:
    try:
        if( operation == 'FFT'):
            outputfile = sys.argv[4]
            with open(outputfile, 'w', newline='', encoding='utf-8') as myfile:
                wr = csv.writer(myfile)
                analyze_channels(operation,boardtype,inputfile,FFT,logthd)
        elif( operation == 'THD'):
            analyze_channels(operation,boardtype,inputfile,THDN,print)
        elif( operation == "Criteria"):
            points = sys.argv[4]
            amp = sys.argv[5]
            erle = sys.argv[6]
            # py .\audiotools.py Criteria DVT test.csv 40 10 30
            print('Creating criteria file: ' + inputfile + ' Amplitude: ' + amp + ' Data points: ' + points)
            with open(inputfile, 'w', newline='', encoding='utf-8') as myfile:
                wr = csv.writer(myfile)
                logarr = logspace(2.477, 3.875, int(points))
                x = []
                y = []
                z = []
                for i in logarr:
                     x.append(int(i))
                     y.append(amp)
                     z.append(erle)
                wr.writerow(x)
                wr.writerow(y)
                wr.writerow(z)
                print('Writing results to ' + inputfile )
    except Exception as e:
        print('Couldn\'t analyze "' + inputfile + '"')
        print(e)
    print()
else:
    sys.exit("You must provide at least one file to analyze")

