dataset_1_number_start = 12223; 
dataset_1_number_end = 12243; 
dataset_1_voltage_start = 2.6; 
dataset_1_voltage_end = 3.8; 

dataset_2_number_start = 12244; 
dataset_2_number_end = 12250; 
dataset_2_voltage_start = 2.2; 
dataset_2_voltage_end = 2.6; 

dataset_3_number_start = 12251; 
dataset_3_number_end = 12256; 
dataset_3_voltage_start = 1.8; 
dataset_3_voltage_end = 2.2; 

dataset_4_number_start = 12257; 
dataset_4_number_end = 12261; 
dataset_4_voltage_start = 3.8; 
dataset_4_voltage_end = 4; 

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

ZurichGain = 10000/(sqrt(2)); %Gain on the Zurich is 10000, also multiplying signal by sqrt(2) here to go from RMS to amplitude
squidSlope = (-127 - 120) / (2*5) ; %Sensitivity of SQUID in volts / tesla
%SR560 has x5 gain, transfer function measured before and after measurement

unit = 1e9; %Desired unit in tesla. 1e6 is uT, 1e9 is nT

%Concatenating these dataset voltage ranges into one big one.  
volts1 = linspace(dataset_1_voltage_start,dataset_1_voltage_end,dataset_1_number_end - dataset_1_number_start + 1);
volts2 = linspace(dataset_2_voltage_start,dataset_2_voltage_end,dataset_2_number_end - dataset_2_number_start + 1);
volts3 = linspace(dataset_3_voltage_start,dataset_3_voltage_end,dataset_3_number_end - dataset_3_number_start + 1);
volts4 = linspace(dataset_4_voltage_start,dataset_4_voltage_end,dataset_4_number_end - dataset_4_number_start + 1);

dataset_nums = [dataset_3_number_start:dataset_3_number_end,dataset_2_number_start:dataset_2_number_end,dataset_1_number_start:dataset_1_number_end,dataset_4_number_start:dataset_4_number_end,]; 
volts = [volts3, volts2, volts1, volts4]; 

density = (volts + 0.08)*3/3.9;

%Concantenating the magnetic field linecut data into one big matrix

x_matrx = []; 
y_matrx = []; 
scandata = [];
gates_matrx = []; 

for i = 1:length(dataset_nums)
    
    dataset = OpenDataVaultFile(dataset_nums(i));
    trace = dataset(dataset(:,1) ==0,:);
    retrace = dataset(dataset(:,1) ==1,:);
    
    l  =  max(dataset(:,2))+1;
 
    Axis1 = reshape(trace(:,4),l,[]);
    Axis2 = reshape(trace(:,5),l,[]);

    TFy = reshape((trace(:,9)+retrace(:,9))./2,l,[]);

    x = Axis1.*5.333;
    y = Axis2.*5.333;
    z = TFy.*unit./(ZurichGain*squidSlope);

    linecut_x = mean(x,2); 
    
    %Instead of using a large time constant to average while measuring, we 
    %sample at the maximum rate our DAC/ADC supports, and we use a small 
    %time constant (10 ms) so that these measurements are independent and
    %meaningful.  We then use a moving mean to average data, which produces
    %a more symmetrical averaging window than a large lock-in time constant
    %(which is a lagging window).  This is implemented here.  
    
    linecut_TFy = movmean(mean(z,2)-mean(mean(z))*ones(size(mean(z,2))),100); 
    
    x_matrx = [x_matrx x(:,1)]; 
    y_matrx = [y_matrx y(:,1)]; 
    gates_matrx = [gates_matrx volts(i)*ones(size(y(:,1)))]; 
    scandata = [scandata linecut_TFy];
    
end

old_scandata = scandata; 
%This is the data from the linecut at a gate voltage that doesn't support
%any magnetism.  
zero_vect = mean(scandata(:,4:7),2); 

for i = 1:length(dataset_nums)
    
    %Subtracting the no-magnetism vector
    scandata(:,i) = scandata(:,i) - zero_vect; 

end    


%The linecut was not aligned with a scan axis, so this calculates the
%displacement in position for the x-axis of figure 2.  
displacement = (x_matrx.^2 + y_matrx.^2).^0.5; 
scanlength = sqrt((trace(end,4)-trace(1,4))^2 + (trace(end,5)-trace(1,5))^2)*5.33;
plot_volts = [min(volts),max(volts)]; 
plot_x = [0,scanlength]; 

[m,n] = size(displacement); 

displacement = displacement - min(displacement).*ones(size(displacement)); 

fitting_line = 25; 
this_gate_voltage = volts(fitting_line); 
x_vals = displacement(:,fitting_line)- min(displacement(:,fitting_line)).*ones(size(displacement(:,fitting_line))); 
[fit,error_struct] = polyfit(x_vals, scandata(:,fitting_line), 7); 

fits = []; 
errors = []; 
intercepts = []; 

for i = 1:length(volts)
    
    the_lin_fit = polyfit(polyval(fit,x_vals),scandata(:,i),1); 
    this_gate_voltage = volts(i); 
    fits(i) = the_lin_fit(1); 
    intercepts(i) = the_lin_fit(2); 
    errors(i) = (std(scandata(:,i) - (the_lin_fit(1)*polyval(fit,x_vals)+intercepts(i)*ones(size(x_vals)))))/(sqrt(length(scandata(:,i)))*mean(abs(scandata(:,10)))); 

end


plot(x_vals,polyval(fit,x_vals),'k-','LineWidth',2)
hold on
plot(x_vals, scandata(:,25),'r.','LineWidth',2)
axis([0,1.5,-180,180])

figure()

imagesc([min(density),max(density)],[min(x_vals),max(x_vals)],flipud(scandata))
x= [linspace(0,0.35,5), 0.5, linspace(0.65,1,5)]; 
J = customcolormap(x, {'#68011D','#B5172F','#D75F4E','#F7A580','#FEDBC9','#F5F9F3','#D5E2F0','#93C5DC','#4295C1','#2265AD','#062E61'});
colormap(J)
h = colorbar(); 
caxis([-180,180])

figure()
errorbar(density,fits,errors,'k.')
