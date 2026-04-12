%Importing magnetic hysteresis transport data.  This script extracts the
%magnetic coercive fields using a simple threshold detection on the
%magnetic hysteresis of the Hall resistance.  

data1 = FastHystOneFile(12147,500); 
data2 = FastHystOneFile(12148,500);

von_klitzing = 25812.80745; 

%data1 and data2 are structures containing hall resistances measurements,
%split into traceR and retraceR (rising and falling), as a function of
%magnetic field B and gate voltage V.  The gate voltage goes into a x3
%voltage amplifier before being applied to the device's gate.  The magnetic
%field is in tesla.  The resistance is in Ohms.  

%This dataset was taken in two passes because in the first run we didn't go
%to high enough magnetic fields to fully polarize the magnet.  Thus for
%gate voltages in the domain of data2 we want to use data2 transport data;
%all other data comes from data1.  

[m,n] = size(data1.B); 
 
data=struct(); data.B = []; data.V = []; data.traceR = []; data.retraceR = []; data.diff = []; 
index = 1; 
 
for i = 1:m
    if data1.V(i,1) < min(data2.V(:,1)) -0.002
        data.B = [data.B; data1.B(i,:)] ; 
        data.V = [data.V; data1.V(i,:)] ; 
        data.retraceR = [data.retraceR; data1.retraceR(i,:)] ; 
        data.traceR = [data.traceR; data1.traceR(i,:)] ; 
        data.diff = [data.diff; data1.retraceR(i,:)-data1.traceR(i,:)] ;         
    elseif data1.V(i,1) > max(data2.V(:,1))
        data.B = [data.B; data1.B(i,:)] ; 
        data.V = [data.V; data1.V(i,:)] ; 
        data.retraceR = [data.retraceR; data1.retraceR(i,:)] ; 
        data.traceR = [data.traceR; data1.traceR(i,:)] ; 
        data.diff = [data.diff; data1.retraceR(i,:)-data1.traceR(i,:)] ;         
    elseif data1.V(i,1) > min(data2.V(:,1))
        data.B = [data.B; data2.B(index,:)] ; 
        data.V = [data.V; data2.V(index,:)] ; 
        data.retraceR = [data.retraceR; data2.retraceR(index,:)] ; 
        data.traceR = [data.traceR; data2.traceR(index,:)] ; 
        data.diff = [data.diff; data2.retraceR(index,:)-data2.traceR(index,:)] ;         
        index = index + 1; 
    end
end

%data.diff now contains the Rxy trace - retrace difference data that we've
%plotted in a few different places.  


coercives1 = []; 
coercives2 = []; 

for i = 1:194
    
    %Smoothing the transport data so the coercive field threshold detection
    %doesn't produce too many false positives
    
     smooth_diff = movmean(data.diff(i,:),15); 
     smooth_diff(isnan(smooth_diff)) = 0; 
     
     %Finding regions with detectable hysteresis above the noise
     
     if max(abs(smooth_diff)) < 1000 & abs(std(smooth_diff(1:10)))<300
         cutoff = 300;
     elseif max(abs(smooth_diff)) < 1000 & abs(std(smooth_diff(1:10)))>300
         cutoff = abs(std(smooth_diff(1:10))); 
     else 
         cutoff = max(abs(smooth_diff))/3;
     end
     
     hyst_cut = abs(movmean(data.diff(i,:),15)) > cutoff; 
     
     [coercive_1, coercive_i_1] = max(data.B(i,:).*hyst_cut); 
     [coercive_2, coercive_i_2] = min(data.B(i,:).*hyst_cut); 

     if isempty(coercive_i_1)
         coercives1 = [coercives1 0]; 
         %No magnetic hysteresis detected, coercive field recorded as 0
     else
         coercives1 = [coercives1 coercive_1];
     end
     
     if isempty(coercive_i_2)         
         coercives2 = [coercives2 0];
     else
         coercives2 = [coercives2 coercive_2];
     end
end

%%
%Turning gate voltage into an electron density
density=(data.V(1:145,1) + 0.08*ones(size([data.V(1:145,1)]))).*3 ./3.9;

%%
%Plotting coercive fields
figure();
coercives_cut = coercives1(1:145); 
plot(density,coercives_cut,'b-') 
hold on
plot(density,coercives_cut,'b.')
hold on
xlabel('nu')
ylabel('B_{TF}')
axis([1.4462,3.1385,-0.1,0.625])
pbaspect([1.388 0.75 1])

figure()
plot((data.V(:,251) + 0.08*ones(size([data.V(:,251)]))).*3 ./3.9,-data.diff(:,251)/(2*von_klitzing),'r.')
axis([1.4462,3.1385,-0.1,1.25])



