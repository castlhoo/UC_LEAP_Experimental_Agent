# Dataset for Figure 2

## Description:

This data set contains the processed data and the simulated time-dependent stable and unstable solutions used to generate Figure 2 of the manuscript "*Slow and fast topological dynamical phase transitions in a Duffing resonator driven by two detuned tones*". 
Additionally, the python code used to numerically solved the full equation of motion required to extract a syncronization time is included. 
The data set is organized into 18 txt files and one python code. 9 files contains the simulated time-dependent stable and unstable solutitions of a Duffing resonator driven with an effective force (varying in time) corresponding to a certain driving frequency, 5 containing measured data, 4 contains the simulated data needed to plot the vector field and one python code used to extract a synchronization factor.

## Creator: 

Letizia Catalini (L.Catalini@amolf.nl), AMOLF

1. simulated_high_fast.txt

	- Description: Simulated Amplitude of the upper stable solution at the pump frequency Omega1 as a function of time. Each amplitude has been simulated with a different instantaneus value of an amplitude modulated force with a fixed parameters Delta21 and h. Details on the generation of the effective force in the methodology.
	- Driving force generation parameters: 
	  Omega1 = 6968928.7893655365
	  F1 = K*140 mV
	  K = 1.1e7 (conversion factor extracted from fit of the linear respose of the resonator)
	  h = 0.21
	  phi = from linear fit
	  time sync parameter = -0.0012
	  Delta21/2pi = 90 Hz 
	- Columns: Time, Simulated upper stable solution at the pump frquency
	- Units: seconds, mVolt

2. simulated_high_slow.txt

	- Description: Simulated Amplitude of the upper stable solution at the pump frequency Omegap as a function of time. Each amplitude has been simulated with a different instantaneus value of an amplitude modulated force with a fixed parameters Delta21 and h. Details on the generation of the effective force in the methodology.
	- Driving force generation parameters: 
	  Omega1 = 6968928.7893655365
	  F1 = K*140 mV
	  K = 1.1e7 (conversion factor extracted from fit of the linear respose of the resonator)
	  h = 0.21
	  phi = from linear fit
	  time sync parameter = -0.024
	  Delta21/2pi = 10 Hz 
	- Columns: Time, Simulated upper stable solution at the pump frquency
	- Units: seconds, mVolt

3. simulated_high_weak.txt

	- Description: Simulated Amplitude of the upper stable solution at the pump frequency Omegap as a function of time. Each amplitude has been simulated with a different instantaneus value of an amplitude modulated force with a fixed parameters Delta21 and h. Details on the generation of the effective force in the methodology.
	- Driving force generation parameters: 
	  Omega1 = 6968928.7893655365
	  F1 = K*140 mV
	  K = 1.1e7 (conversion factor extracted from fit of the linear respose of the resonator)
	  h = 0.14
	  phi = from linear fit
	  time sync parameter = -0.118
	  Delta21/2pi = 10 Hz 
	- Columns: Time, Simulated upper stable solution at the pump frquency
	- Units: seconds, mVolt
4. simulated_low_fast.txt

	- Description: Simulated Amplitude of the lower stable solution at the pump frequency Omegap as a function of time. Each amplitude has been simulated with a different instantaneus value of an amplitude modulated force with a fixed parameters Delta21 and h. Details on the generation of the effective force in the methodology.
	- Driving force generation parameters: 
	  Omega1 = 6968928.7893655365	  
	  F1 = K*140 mV
	  K = 1.1e7 (conversion factor extracted from fit of the linear respose of the resonator)
	  h = 0.21
	  phi = from linear fit
	  time sync parameter = -0.0012
	  Delta21/2pi = 90 Hz 
	- Columns: Time, Simulated upper stable solution at the pump frquency
	- Units: seconds, mVolt

5. simulated_low_slow.txt

	- Description: Simulated Amplitude of the lower stable solution at the pump frequency Omegap as a function of time. Each amplitude has been simulated with a different instantaneus value of an amplitude modulated force with a fixed parameters Delta21 and h. Details on the generation of the effective force in the methodology.
	- Driving force generation parameters: 
	  Omega1 = 6968928.7893655365
	  F1 = K*140 mV
	  K = 1.1e7 (conversion factor extracted from fit of the linear respose of the resonator)
	  h = 0.21
	  phi = from linear fit
	  time sync parameter = -0.024
	  Delta21/2pi = 10 Hz 
	- Columns: Time, Simulated upper stable solution at the pump frquency
	- Units: seconds, mVolt

6. simulated_low_weak.txt

	- Description: Simulated Amplitude of the lower stable solution at the pump frequency Omegap as a function of time. Each amplitude has been simulated with a different instantaneus value of an amplitude modulated force with a fixed parameters Delta21 and h. Details on the generation of the effective force in the methodology.
	- Driving force generation parameters: 
	  Omega1 = 6968928.7893655365
	  F1 = K*140 mV
	  K = 1.1e7 (conversion factor extracted from fit of the linear respose of the resonator)
	  h = 0.14
	  phi = from linear fit
	  time sync parameter = -0.118
	  Delta21/2pi = 10 Hz 
	- Columns: Time, Simulated upper stable solution at the pump frquency
	- Units: seconds, mVolt
7. simulated_unst_fast.txt

	- Description: Simulated Amplitude of the unstable solution at the pump frequency Omegap as a function of time. Each amplitude has been simulated with a different instantaneus value of an amplitude modulated force with a fixed parameters Delta21 and h. Details on the generation of the effective force in the methodology.
	- Driving force generation parameters: 
	  Omega1 = 6968928.7893655365
	  F1 = K*140 mV
	  K = 1.1e7 (conversion factor extracted from fit of the linear respose of the resonator)
	  h = 0.21
	  phi = from linear fit
	  time sync parameter = -0.0012
	  Delta21/2pi = 90 Hz 
	- Columns: Time, Simulated upper stable solution at the pump frquency
	- Units: seconds, mVolt

8. simulated_unst_slow.txt

	- Description: Simulated Amplitude of the unstable solution at the pump frequency Omegap as a function of time. Each amplitude has been simulated with a different instantaneus value of an amplitude modulated force with a fixed parameters Delta21 and h. Details on the generation of the effective force in the methodology.
	- Driving force generation parameters: 
	  Omega1 = 6968928.7893655365
	  F1 = K*140 mV
	  K = 1.1e7 (conversion factor extracted from fit of the linear respose of the resonator)
	  h = 0.21
	  phi = from linear fit
	  time sync parameter = -0.024
	  Delta21/2pi = 10 Hz 
	- Columns: Time, Simulated upper stable solution at the pump frquency
	- Units: seconds, mVolt

9. simulated_unst_weak.txt

	- Description: Simulated Amplitude of the unstable solution at the pump frequency Omegap as a function of time. Each amplitude has been simulated with a different instantaneus value of an amplitude modulated force with a fixed parameters Delta21 and h. Details on the generation of the effective force in the methodology.
	- Driving force generation parameters: 
	  Omega1 = 6968928.7893655365
	  F1 = K*140 mV
	  K = 1.1e7 (conversion factor extracted from fit of the linear respose of the resonator)
	  h = 0.14
	  phi = from linear fit
	  time sync parameter = -0.118
	  Delta21/2pi = 10 Hz 
	- Columns: Time, Simulated upper stable solution at the pump frquency
	- Units: seconds, mVolt

10. detuning_figure_fast_do.txt

	- Description: Measured amplitude and corresponding mechanical quadratures X, Y as a function of time of a duffing resonator driven with two tones (F1 and F2= hF1). The resonator is initialized in the lower stable solution before turning on the second tone, and it is driven with fixed frequency detuning Delta21 between the two tones. 
	- Driving settings:
	  Omega1 = 6968928.7893655365
	  F1 = K*140 mV
	  K = 1.1e7 (conversion factor extracted from fit of the linear respose of the resonator)
	  h = 0.21 
	  Delta21/2pi = 90 Hz
	- Columnes: Time, Measured Amplitude, Measured quadrature X, Measured quadrature Y
	- Units: seconds, Volts, Volts, Volts
		
11. detuning_figure_slow_do.txt

	- Description: Measured amplitude and corresponding mechanical quadratures X, Y as a function of time of a duffing resonator driven with two tones (F1 and F2= hF1). The resonator is initialized in the lower stable solution before turning on the second tone, and it is driven with fixed frequency detuning Delta21 between the two tones. 
	- Driving settings:
	  Omega1 = 6968928.7893655365
	  F1 = K*140 mV
	  K = 1.1e7 (conversion factor extracted from fit of the linear respose of the resonator)
	  h = 0.21 
	  Delta21/2pi = 10 Hz
	- Columnes: Time, Measured Amplitude, Measured quadrature X, Measured quadrature Y
	- Units: seconds, Volts, Volts, Volts

12. detuning_figure_weak_do.txt

	- Description: Measured amplitude and corresponding mechanical quadratures X, Y as a function of time of a duffing resonator driven with two tones (F1 and F2= hF1). The resonator is initialized in the lower stable solution before turning on the second tone, and it is driven with fixed frequency detuning Delta21 between the two tones. 
	- Driving settings:
	  Omega1 = 6968928.7893655365
	  F1 = K*140 mV
	  K = 1.1e7 (conversion factor extracted from fit of the linear respose of the resonator)
	  h = 0.14 
	  Delta21/2pi = 10 Hz
	- Columnes: Time, Measured Amplitude, Measured quadrature X, Measured quadrature Y
	- Units: seconds, Volts, Volts, Volts

13. detuning_figure_zerod_do.txt

	- Description: Measured amplitude and corresponding mechanical quadratures X, Y as a function of time of a duffing resonator driven with only one tone (F1 and F2= 0). The resonator is initialized in the lower stable solution. 
	- Driving settings:
	  Omega1 = 6968928.7893655365
	  F1 = K*140 mV
	  K = 1.1e7 (conversion factor extracted from fit of the linear respose of the resonator)
	  h = 0
	- Columnes: Time, Measured Amplitude, Measured quadrature X, Measured quadrature Y
	- Units: seconds, Volts, Volts, Volts

14. detuning_figure_zerod_up.txt

	- Description: Measured amplitude and corresponding mechanical quadratures X, Y as a function of time of a duffing resonator driven with only one tone (F1 and F2= 0). The resonator is initialized in the higher stable solution. 
	- Driving settings:
	  Omega1 = 6968928.7893655365
	  F1 = K*140 mV
	  K = 1.1e7 (conversion factor extracted from fit of the linear respose of the resonator)
	  h = 0
	- Columnes: Time, Measured Amplitude, Measured quadrature X, Measured quadrature Y
	- Units: seconds, Volts, Volts, Volts

15. numerical.ipynb
	- Description: python code used to fully reporduced the amplitude as a function of time in the three cases (fast, slow and weak). Example only for the slow case. This code was only used to find the time sync parameter for the analytical solution obtained with the Harmonic Balance julia package. 
	  The solution of this numerical simulation obtained with this code are not shown in the manuscript, since we only used them to get the sync factor. This code has been included for completeness and to give the reader who would like to reproduce the results a method to find the sync parameter.

16. simulated_flow_X.txt
    - Description: The X grid coordinates for the vector flow shown as grey lines.
    - Units: mVolts
    
17. simulated_dlow_Y.txt
    - Description: The Y grid coordinates for the vector flow shown as grey lines.
    - Units: mVolts
    
18. simulated_flow_dX.txt
    - Description: The X component of the vector field arising from a duffing resonator driven with only one tone.
    - Driving settings:
	  Omega1 = 6968928.7893655365
	  F1 = K*140 mV
	  K = 1.1e7 (conversion factor extracted from fit of the linear respose of the resonator)
	  h = 0
    - Units: mVolts
    - Usage: In plotting software (e.g., Python's Matplotlib), this data can be used as `streamplot(X, Y, dX, dY)`
    
19. simulated_flow_dY.txt
    - Description: The Y component of the vector field arising from a duffing resonator driven with only one tone.
    - Driving settings:
	  Omega1 = 6968928.7893655365
	  F1 = K*140 mV
	  K = 1.1e7 (conversion factor extracted from fit of the linear respose of the resonator)
	  h = 0
    - Units: mVolts
    - Usage: In plotting software (e.g., Python's Matplotlib), this data can be used as `streamplot(X, Y, dX, dY)`

## Methodology simulated stable and unstable solution:

The data where simulate using the Harmonic Balance julia package (https://juliapackages.com/p/harmonicbalance). 
First we generated a force with the amplitude modulated using the following expression in the frame rotating at Omega1:
F(t) = F1 cos(theta1)+ F2 cos(delta21*t+theta1), with F1 = K*140mV and F2 = hF1 and theta1 extracted from the fit of the linear response of the resonator.
To generate the time axis, we generate an array with 10000 points starting at 0s end ending after 4 full modulations.
In this way, we generate an array of effective forces, which has a different value for every point in time. We numerically extract a full Duffing curve the Julia package for each effective force and we extract the two stable and the unstable solution corresponding the frequency Omega1 and we save them in separated txt files. If the solution does not exist, the time instant and the solution are not saved.
Note that the time exis of the simulated values and the measured values are not syncronized. To find the syncronization time, we perform a numerical simulation of the full equation of motion of the resontator driven with two tones where we find the vibration amplitde as a function of time (numerical.ipynb code). We then superimposed the simulated data to the measured data and adjust the time axis to find the syncronization factor needed for the analytical case. 

The two generated files corresponding to the two sweep direction has been divided in two (high and low branches) and reduced (only frequency and Amplitude). We converted the frequency in angular frequency. 
The simulated solutions has been evaluated using the Harmonic Balance julia package (https://juliapackages.com/p/harmonicbalance) using the mechanical parameters

Omega0  = 6.97e6 Hz
Gamma = 695 Hz
beta = -1.89e17 V^-2s^-2

Omega0 and Gamma are extracted from the fit of the linear response of the resonator, beta from the fit of the Duffing response.

## Methodology vector field:

The vector field  was generated by numerically solving the harmonic equations of motion for a driven, damped Duffing oscillator using the **HarmonicBalance.jl** package in Julia (https://quantumengineeredsystems.github.io/HarmonicBalance.jl/stable/) using the normalized values of the following experimental parameters within the HarmonicBalance framework:
 
-   Natural Frequency (Omega0): 6.96986322513185e+06/(2*pi) Hz
-   Nonlinearity (beta): -1.89e17 V^-2s^-2
-   Primary Drive Amplitude (F₁): 140mV
-   Damping (Gamma): ~110 Hz
-   Drive Detuning (Delta10): -148 Hz
 
The background vector fields was determined by solving the steady-state harmonic equations for h=0.


## Methodology data acquisition:

The data are acquired with an MFLI lock-in amplifier from Zurich instrument. We generate a driving tone with strength F1 and frequency Omega1 and we initialize it in the lower stable solution by approaching the driving frequency from lower frequency value.
Then, a second tone with strength F2=hF1 and frequency detuned from the first one by a factor Delta 21 is turned on. We then start saving data demodulated at the frequency Omega1. The lock-in file return time, amplitude and quadrature of the measured signal.
The time saved by the zurich instrument is not initialized at zero, but it is initialized at an earlier reference time. The data processing consisted in setting the time axis to zero by substracting the first time value to the time data, and removing the unnecessary data (phase and time stamp) returned by the instrument.




