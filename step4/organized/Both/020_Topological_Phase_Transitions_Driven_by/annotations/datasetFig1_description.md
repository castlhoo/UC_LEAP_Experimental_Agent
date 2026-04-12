# Dataset for Figure 1

## Description:
This data set contains the raw and simulated data used to generate Figure 1 of the manuscript "*Slow and fast topological dynamical phase transitions in a Duffing resonator driven by two detuned tones*". 

The data set is organized into 5 .txt files, corresponding to measured and simulated Duffing respons. 


## Creator:  

Letizia Catalini (L.Catalini@amolf.nl), AMOLF

1. Duffing_lowerstable.txt

	- Description: simulated Amplitude of the lower stable solution as a function of frequency (from lowest measured frequency up to high frequency bifurcation point).
	- Columns: Frequency, Simulated Amplitude
	- Units: Hz, Volt

2. Duffing_unstable.txt

	- Description: simulated Amplitude of the unstable stable solution as a function of frequency (only between bifurcation points).
	- Columns: Frequency, Simulated Amplitude
	- Units: Hz, Volt

3. Duffing_upperstable.txt

	- Description: simulated Amplitude of the upper stable solution as a function of frequency (from low frequency bifurcation point up to higher measured frequency).
	- Columns: Frequency, Simulated Amplitude
	- Units: Hz, Volt

4. nl_sweep_A_do.txt
	
	- Description: Measured amplitude as a function of Frequency. We sweep around the natural resonance frequency Omega0 from low to high frequencies.
	- Columns: Frequency, Measured Amplitude
	- Units: Hz, Volt

5. nl_sweep_A_up.txt
	
	- Description: Measured amplitude as a function of Frequency. We sweep around the natural resonance frequency Omega0 from high to low frequencies.
	- Columns: Frequency, Measured Amplitude
	- Units: Hz, Volt


##Methodology:

The data where acquired using an MFLI lock-in amplifier from Zurich Instrument with the built in Sweep function. The Sweep function return amplitude and phase of the resonator in the frame rotating at a frequency Omega1 as it is sweep in a certain frequency range. 
The demodulator frequency is locked with the frequency of the a drive tone which we generate with a voltage amplitude U1=140 mV.
The two generated files, corresponding to the two sweep direction, contains the driving frequency and the corresponding measured amplitude.
The simulated Duffing has been evaluated using the Harmonic Balance julia package (https://juliapackages.com/p/harmonicbalance) using the parameters. We separated the files in three, corresponding to the lowest stable, the higher stable and the unstable branch.

Omega0  = 6.97e6 Hz
Gamma = 695 Hz
beta = -1.89e17 V^-2s^-2
K = 1.1e7 s^-2
F = K 140 mV

The value for Omega0, Gamma and K are extracted from the fit of the linear response of the resonator. The force is obtained multiblying the driving voltage (140mV) by the conversion factor K. 
beta is extracted from the fit of the Duffing response. 

