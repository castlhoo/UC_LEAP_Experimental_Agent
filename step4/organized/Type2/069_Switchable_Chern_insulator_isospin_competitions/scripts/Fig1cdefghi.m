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
A = Plot_nSOT_Mag(11977, 33.7, 50000, 0); % Positive Field Training dataset
B = Plot_nSOT_Mag(11978, 35.5, 50000, 0); % Negative Field Training dataset

%Make a difference data set to find true magnetic field features
%Divide by two since otherwise we are doubling the signal by 
Diff = A;
Diff.z = (A.z - B.z)./2; 

%Close plots opened by default from the Plot function since the data hasn't
%been processed yet. 
close all

%Zero offsets associated with temperature temperature offset drifting
%between measurements. Data used to zero offsets is in the bottom left
%corner (or bottom lines for the difference data, which should be zero
%everywhere on the bottom lines)
%Also, multiply by sqrt(2) to get the true amplitude instead of the RMS 
%amplitude. 
A.z = sqrt(2).*(A.z-mean(mean(A.z(1:100, 1:5))));
B.z = sqrt(2).*(B.z-mean(mean(B.z(1:100, 1:5))));
Diff.z = sqrt(2).*(Diff.z- mean(mean(Diff.z(:,1:12))));

%Integrate the difference data to get the magnetic field data from the
%gradient data. Uses 189e-9m as the TF oscillation amplitude and 70 degrees
%from the horiontal as the angle along which to integrate. 
DiffInt = InterpIntegrate(Diff,70,189e-9);

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
DiffIntSmooth = LowPassFilter(DiffInt, 150e-9, 1);

%Plot the datasets
figure, Plot_nSOT_Mag(ASmooth); %This if Fig. 1 C
%Define the colormap
%x= [linspace(0,0.35,5),0.5,linspace(0.65,1,5)]; 
x = linspace(0,1,11);
J = customcolormap(x, {'#68011D','#B5172F','#D75F4E','#F7A580','#FEDBC9','#F5F9F3','#D5E2F0','#93C5DC','#4295C1','#2265AD','#062E61'});
colorbar; colormap(J);
caxis([-180e-9,180e-9])

figure, Plot_nSOT_Mag(BSmooth); %This if Fig. 1 D
%Define the colormap
x = linspace(0,1,11);
J = customcolormap(x, {'#68011D','#B5172F','#D75F4E','#F7A580','#FEDBC9','#F5F9F3','#D5E2F0','#93C5DC','#4295C1','#2265AD','#062E61'});
colorbar; colormap(J);
caxis([-180e-9,180e-9])

figure, Plot_nSOT_Mag(DiffSmooth); %This if Fig. 1 E
%Define the colormap
x = linspace(0,1,11);
J = customcolormap(x, {'#68011D','#B5172F','#D75F4E','#F7A580','#FEDBC9','#F5F9F3','#D5E2F0','#93C5DC','#4295C1','#2265AD','#062E61'});
colorbar; colormap(J);
caxis([-180e-9,180e-9])

figure, Plot_nSOT_Mag(DiffIntSmooth); %This if Fig. 1 F
%Define the colormap
x= [linspace(0,0.4,5),0.5,linspace(0.6,1,5)]; 
J = customcolormap(x, {'#860454','#C51B7C','#DC75AB','#F0B7DA','#FFDEEF','#F8F7F7','#E5F4D9','#B9E084','#7FBC42','#4D921E','#276418'});
colorbar; colormap(J);
caxis([-280e-9,280e-9])

%Get the magnetization from the integrated different data prior to
%smoothing. This applies a deconvolution from the SQUID diameter.
MagSmooth = ConvertBtoMoment(DiffInt, 153e-9, 215e-9, 1);
%Low pass filter with the same length scale
MagSmooth = LowPassFilter(MagSmooth, 150e-9, 1); 
%remove offsets from the bottom
off  = mean(mean(MagSmooth.z(:,1:10)));
%convert to units of Bohr magnetons per moire unit cell
MagSmooth.z = (MagSmooth.z - off)./(7.13e-8); 

figure, Plot_nSOT_Mag(MagSmooth); %This is Fig. 1 G
%Define the colormap
x= [linspace(0,0.3,5),0.5,linspace(0.7,1,5)]; 
J = customcolormap(x, {'#7f3c0a','#b35807','#e28212','#f9b967','#ffe0b2','#f7f7f5','#d7d9ee','#b3abd2','#8073a9','#562689','#2f004d'});
colorbar; colormap(J);
caxis([-4,4])

%Plot linecuts through these datasets. 
line_interp_field = InterpDataLine(DiffSmooth, [8.353*10^-7,4.632*10^-6], [2.866*10^-6,5.449*10^-8], 1000);
figure, plot(line_interp_field.x,line_interp_field.z,'Color', [181, 43, 256]./256)
xlim([0 5e-6])
ylim([-200e-9 200e-9])

%Below plots the linecut through the magnetization data with a range
%determined by the absolute uncertainty in the magnetization arising from
%the TF amplitude
line_interp_long = InterpDataLine(MagSmooth, [8.353*10^-7,4.632*10^-6], [2.866*10^-6,5.449*10^-8], 1000);
figure, plot(line_interp_long.x,line_interp_long.z,'Color', [94, 256, 0]./256)
hold on
plot(line_interp_long.x, line_interp_long.z./1.42,'Color', [94, 256, 0]./256)

x2 = [line_interp_long.x, fliplr(line_interp_long.x)];
inBetween = [line_interp_long.z, fliplr(line_interp_long.z./1.42)];
h = fill(x2, inBetween, [94, 256, 0]./256);
set(h,'facealpha',0.5);
set(h,'EdgeColor','none')
xlim([0 5e-6])
ylim([0 5])