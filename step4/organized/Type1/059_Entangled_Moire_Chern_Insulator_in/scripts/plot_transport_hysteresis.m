function [output_struct, offset] = plot_transport_hysteresis(trace_num,retrace_num,Rxy_yx_bool,plotinfo)
%plot_transport_hysteresis 

von_klitzing = 25813; 

%Open the trace and retrace datasets
trace = OpenDataVaultFile(trace_num); 
retrace = OpenDataVaultFile(retrace_num); 

%Raw data format
%Column 1: measurement index
%Column 2: B (Tesla)
%Column 3: Voltage (Volts)
%Column 4: Current (Amps)
%Column 5: Resistance (ohms) 
%Column 6: Conductance (S)

%Get the magnetic field axis datapoints. The script correctly assumes that
%the magnetic field axis of the retrace is the opposite (i.e. if trace is
%-1 to 1 Tesla, retrace is 1 to -1 tesla with the same number of points)
traceB = trace(:,2); %In mT

%Get the resistance values
traceRxy = trace(:,5); %In Ohms
retraceRxy = flipud(retrace(:,5)); %In Ohms

%Get the current values
traceI = trace(:,4); %In amps
retraceI = flipud(retrace(:,4)); %In amps

%Get the voltage values
traceVxy = trace(:,3); %In volts
retraceVxy = flipud(retrace(:,3)); %In volts

%If the contacts were hooked up to measure Vyx instead of Vxy, multiply by
%negative 1 to correct it
if Rxy_yx_bool == 1
    traceRxy = -traceRxy; 
    retraceRxy = -retraceRxy; 
else 
end

%Consolidate data into a single output structure
output_struct= struct();
output_struct.B = traceB; 
output_struct.Rxy.trace = traceRxy; 
output_struct.I.trace = traceI; 
output_struct.Vxy.trace = traceVxy;  
output_struct.Rxy.retrace = retraceRxy; 
output_struct.I.retrace = retraceI; 
output_struct.Vxy.retrace = retraceVxy; 

%Plot both the trace and retrace data
plot(10^3*output_struct.B,(1/von_klitzing)*(output_struct.Rxy.trace),plotinfo,'LineWidth',0.5);
hold on 
plot(10^3*output_struct.B,(1/von_klitzing)*(output_struct.Rxy.retrace),plotinfo,'LineWidth',0.5);

xlabel('B (mT)')
ylabel('R_{xy} (h/e^2)')
end

