%Plot function loads /formats the raw data from the HDF5 file and plots it
%First input specifies the dataset number. 
%Second input specified the SQUID transfer function in units of T/V
%Third input is the total gain on the measurement. 
%Last input sets the spatial filtering applied by default. 0 corresponds to
%no filtering. 
%Data is stored as a structure of 2D arrays. A.X is the x position in
%microns associated with each pixel, A.Y is the y position in microns, 
%and A.z is the measured gradient magnetometry magnetic field. A.x and 
%A.y store the total displacement in microns along the line (this account
%for a tilted data set)
A = Plot_nSOT_Mag(11963, 36.3, 200000, 0); % With domains (point D)
B = Plot_nSOT_Mag(11977, 33.7, 50000, 0); % Positive Field Training (point E)

%Dataset 11963 was taken with a 126nm TF amplitude instead of 189 nm.
%Assuming the TF signal is linear, we scale it by a factor of 1.5 to
%compensate
A.z = 1.5*A.z;

%Make a difference data set to find magnetic field features associated with
%domain flips
%Divide by two since otherwise we are doubling the signal.
Diff = A;
Diff.z = (B.z - A.z)./2;
close all

%Zero offsets associated with temperature temperature offset drifting
%between measurements. Data used to zero offsets is in the bottom left
%corner (or bottom lines for the difference data, which should be zero
%everywhere on the bottom lines)
%Also, multiply by sqrt(2) to get the true amplitude instead of the RMS 
%amplitude. 
A.z = sqrt(2).*(A.z-mean(mean(A.z(1:100, 1:5))));
B.z = sqrt(2).*(B.z-mean(mean(B.z(1:100, 1:5))));
Diff.z = sqrt(2).*(Diff.z-mean(mean(Diff.z(1:100,1:10))));

%Low pass filter the data to get average signal 
%Length scale of the low pass filter should be similar to the true spatial
%resolution of the gradient measurements. SQUID diameter is 215 nm, height
%is 153nm, and the TF amplitude is 189nm. The precise imaging Kernal is a
%complicated function of these three values. We find empirically that a
%Hanning window low pass filter with 150nm length scale (a value that is
%reasonable given the above lengthscales) seems to average the data
%sufficiently without unphysically compromising the spatial resolution
ASmooth = LowPassFilter(A, 150e-9, 1);
BSmooth = LowPassFilter(B, 150e-9, 1);
DiffSmooth = LowPassFilter(Diff, 150e-9, 1);

minmax = 180e-9;

%Plot the datasets
figure, Plot_nSOT_Mag(ASmooth); %This is Fig. 3 D
%Define the colormap
x = linspace(0,1,11);
J = customcolormap(x, {'#68011D','#B5172F','#D75F4E','#F7A580','#FEDBC9','#F5F9F3','#D5E2F0','#93C5DC','#4295C1','#2265AD','#062E61'});
colorbar; colormap(J);
caxis([-minmax,minmax])

figure, Plot_nSOT_Mag(BSmooth); %This is Fig. 3 E
%Define the colormap
x = linspace(0,1,11);
J = customcolormap(x, {'#68011D','#B5172F','#D75F4E','#F7A580','#FEDBC9','#F5F9F3','#D5E2F0','#93C5DC','#4295C1','#2265AD','#062E61'});
colorbar; colormap(J);
caxis([-minmax,minmax])

figure, Plot_nSOT_Mag(DiffSmooth); %This is Fig. 3 F
%Define the colormap
x = linspace(0,1,11);
J = customcolormap(x, {'#68011D','#B5172F','#D75F4E','#F7A580','#FEDBC9','#F5F9F3','#D5E2F0','#93C5DC','#4295C1','#2265AD','#062E61'});
colorbar; colormap(J);
caxis([-minmax,minmax])

%Integrate the difference data to get the magnetic field data from the
%gradient data. Uses 189e-9m as the TF oscillation amplitude and 70 degrees
%from the horiontal as the angle along which to integrate. 
DiffInt = InterpIntegrate(Diff,70,189e-9);

%Get the magnetization from the integrated different data prior to
%smoothing. This applies a deconvolution from the SQUID diameter.
MagSmooth = ConvertBtoMoment(DiffInt, 153e-9, 215e-9, 1);
%Low pass filter with the same length scale
MagSmooth = LowPassFilter(MagSmooth, 150e-9, 1); 
%remove offsets from the bottom
off  = mean(mean(MagSmooth.z(:,1:10)));
%convert to units of Bohr magnetons per moire unit cell
MagSmooth.z = (MagSmooth.z - off)./(7.13e-8); 

figure, Plot_nSOT_Mag(MagSmooth); %This is Fig. 3 H
%Define the colormap
x= [linspace(0,0.3,5),0.5,linspace(0.7,1,5)]; 
J = customcolormap(x, {'#7f3c0a','#b35807','#e28212','#f9b967','#ffe0b2','#f7f7f5','#d7d9ee','#b3abd2','#8073a9','#562689','#2f004d'});
colorbar; colormap(J);
caxis([-4,4])