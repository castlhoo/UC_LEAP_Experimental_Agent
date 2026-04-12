function [output_struct] = FastHystOneFile(filenumber,fieldpoints)
%FastHystOneFile imports transport data and organizes it into a single
%structure- it's just a reformatting script.  

data = OpenDataVaultFile( filenumber ); 

voltages = data(:,4); 
B = data(:,5);
R = data(:,6);
unique_voltages = unique(voltages); 
B_interp = linspace(min(data(:,5)),max(data(:,5)),fieldpoints); 

B_matrix = []; 
Gate_matrix = []; 
trace_R_matrix = []; 
retrace_R_matrix = []; 


for i = 1:length(unique_voltages)

    %This the trace
    
    trace_cut = data(:,1) == 0 & voltages == unique_voltages(i);
    
    trace_these_Vs = voltages(trace_cut);
    trace_these_Bs = B(trace_cut);
    trace_these_Rs = R(trace_cut);
    
    trace_R_interp = interp1(trace_these_Bs,trace_these_Rs,B_interp); 
       
    %This the retrace
    
    retrace_cut = data(:,1) == 1 & voltages == unique_voltages(i);
    
    retrace_these_Vs = voltages(retrace_cut);
    retrace_these_Bs = B(retrace_cut);
    retrace_these_Rs = R(retrace_cut);
    
    retrace_R_interp = interp1(retrace_these_Bs,retrace_these_Rs,B_interp);     
    
    B_matrix = [B_matrix; B_interp]; 
    Gate_matrix = [Gate_matrix; unique_voltages(i) * ones(size(B_interp))]; 
    trace_R_matrix = [trace_R_matrix; trace_R_interp]; 
    retrace_R_matrix = [retrace_R_matrix; retrace_R_interp]; 
    
end

output_struct = struct(); 
output_struct.B = B_matrix;
output_struct.V = Gate_matrix;
output_struct.traceR = trace_R_matrix;
output_struct.retraceR = retrace_R_matrix;

end


