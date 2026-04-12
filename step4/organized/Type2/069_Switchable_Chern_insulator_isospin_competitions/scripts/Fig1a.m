%Raw data format
%Column 1: measurement index
%Column 2: B (Tesla)
%Column 3: Voltage (Volts)
%Column 4: Current (Amps)
%Column 5: Resistance (ohms) 
%Column 6: Conductance (S)

trace = OpenDataVaultFile(11892);
retrace = OpenDataVaultFile(11893);

%Plot -trace and - retrace since measurements were made with a contact
%figuration giving a negative sign on the voltage
plot(trace(:,2),-trace(:,5)./25813,'Color', [0.6350, 0.0780, 0.1840])
hold on
plot(retrace(:,2),-retrace(:,5)./25813,'Color', [0.6350, 0.0780, 0.1840])