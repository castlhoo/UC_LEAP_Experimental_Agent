% Column 1: Trace (0)/ Retrace (1)
% Column 2: bottom gate index
% Column 3: n0 voltage (V)
% Column 4: p0 voltage (V)
% Column 5: Bottom gate voltage (V)
% Column 6: Sample gate voltage (V)
% Column 7: x index
% Column 8: y index
% Column 9: x coordinate
% Column 10: y coordinate
% Column 11: SQUID signal 1wx (V)
% Column 12: SQUID signal DC (V)

filenumbers=[12270];

data = OpenDataVaultFile2(filenumbers(1));
l= max(data(:,2))+1;

squidSlope = 500; 
ZurichGain = 200000; 
SR560Gain = 10;
SR560GainDC = 50;
SR860Sensitivity = 0.0005;
filter = 1; 
unit = 1e9; %Desired unit in tesla. 1e6 is uT, 1e9 is nT
ac_excitation_FCI = 0.015; %in V

max_bottom_gate_index = max(data(:,2)) + 1; %Matlab 1 indexes, Python 0 indexes

max_x_position_index = max(data(:,7)) + 1; %Matlab 1 indexes, Python 0 indexes

trace_data = data(data(:,1)==0,:); 
retrace_data = data(data(:,1)==1,:); 

length_data = length(trace_data);
number_of_lines = floor(length_data/max_x_position_index/l);
max_y_position_index = number_of_lines;
trace_data = trace_data(1:number_of_lines*max_x_position_index*l,:);
retrace_data = retrace_data(1:number_of_lines*max_x_position_index*l,:);
n0_vals = reshape(trace_data(:,3),l,max_x_position_index,[]); 
p0_vals = reshape(trace_data(:,4),l,max_x_position_index,[]); 
x_vals = reshape(trace_data(:,9),l,max_x_position_index,[]); 
y_vals = reshape(trace_data(:,10),l,max_x_position_index,[]); 
SG_vals_FCI = reshape(trace_data(:,6),l,max_x_position_index,[]);
BG_vals = reshape(trace_data(:,5),l,max_x_position_index,[]);
squid_vals_trace = reshape(trace_data(:,11),l,max_x_position_index,[])*unit./(squidSlope*SR560Gain)*SR860Sensitivity/10; 
squid_vals_retrace = reshape(retrace_data(:,11),l,max_x_position_index,[])*unit./(squidSlope*SR560Gain)*SR860Sensitivity/10; 
squid_DC_trace = reshape(trace_data(:,12),l,max_x_position_index,[])*unit./(squidSlope*SR560GainDC); 
squid_DC_retrace = reshape(retrace_data(:,12),l,max_x_position_index,[])*unit./(squidSlope*SR560GainDC);
squid_vals = (squid_vals_trace+squid_vals_retrace)/2;
squid_DC = (squid_DC_trace+squid_DC_retrace)/2;
n0_FCI = n0_vals(:,1,1);

y_vals = linspace(0, 2e-6, max_x_position_index);
y_vals = repmat(y_vals, l, 1, max_y_position_index);

x_vals = linspace(0, 2e-6, max_y_position_index).';
x_vals = repmat(x_vals, 1, max_x_position_index, l);
x_vals = permute(x_vals, [3 2 1]);

%%
smooth = 100;
smooth_squid_vals = smoothdata(squid_vals,1,'sgolay',smooth); 
smooth_squid_vals_DC = smoothdata(squid_DC,1,'sgolay',4*smooth); 
smooth_squid_vals_DC = -(smooth_squid_vals_DC-mean(smooth_squid_vals_DC(1:100,:,:),1));

spatial_filter_squid_vals_FCI_DC = zeros(size(squid_vals)); 
spatial_filter_squid_vals_FCI = zeros(size(squid_vals)); 
for i = 1:l
    
    this_squid_dataset = reshape(smooth_squid_vals(i,:,:),max_x_position_index,[]); 
    this_squid_dataset_DC = reshape(smooth_squid_vals_DC(i,:,:),max_x_position_index,[]); 

    
    winsize = 5;
    H = [gausswin(winsize) , gausswin(winsize) , gausswin(winsize)];
    H = H./sum(sum(H));
    this_squid_dataset = filter2(H,this_squid_dataset);
    this_squid_dataset_DC = filter2(H,this_squid_dataset_DC);
    
    spatial_filter_squid_vals_FCI(i,:,:) = this_squid_dataset; 
    spatial_filter_squid_vals_FCI_DC(i,:,:) = this_squid_dataset_DC;
    
end


%%
dx = abs(max(SG_vals_FCI,[],'all')-min(SG_vals_FCI,[],'all'))/(l);
integrated_B_vals_FCI = cumsum(spatial_filter_squid_vals_FCI).* dx ./ (ac_excitation_FCI);  

a_M = 0.353 / (2*sin(3.7/180*pi/2)) * 10^-9; % m
%a_M ~ 5nm
Area_of_triangle = sqrt(3)/2*a_M^2;

h = 6.63*10^-34; %  J Hz^(-1)
e = 1.6*10^-19;  % C
m_e = 9.1 * 10^(-31); % kg
spin_M =  e * (h/2/pi) / (2 * m_e) / Area_of_triangle; % mu_B/u.c.

Magnetization_FCI = zeros(l, max_x_position_index,max_y_position_index);
for i = 1:l
        this_dataset = integrated_B_vals_FCI(i,:, :); 
        Magnetization_FCI(i, :, :) = NewMomentCalculatorWithPadding_v3(x_vals, y_vals, this_dataset*1e-9, 140e-9,15);
        Magnetization_FCI(i, :, :) = Magnetization_FCI(i, :, :)./spin_M;
end

Magnetization_gradient_FCI = zeros(l, max_x_position_index,max_y_position_index);
for i = 1:l
        this_dataset = spatial_filter_squid_vals_FCI(i,:, :); 
        
        Magnetization_gradient_FCI(i, :, :) = NewMomentCalculatorWithPadding_v3(x_vals, y_vals, this_dataset*1e-9, 140e-9,15);
        Magnetization_gradient_FCI(i, :, :) = Magnetization_gradient_FCI(i, :, :)./spin_M;
        
end


%% FCI gap measurement
frames_FCI = [100 700 920];
centerx = 16;
centery = 16;
f = figure(5);
clf

for i = 1:length(frames_FCI)
    nexttile
    this_dataset = reshape(Magnetization_FCI(frames_FCI(i),:,:),max_x_position_index,[]);
    pcolor(-this_dataset)
    shading flat; 
    set(gca,'YDir','normal') 
    pbaspect([max_y_position_index max_x_position_index 1])

    a= [linspace(0,0.3,5),0.5,linspace(0.7,1,5)]; 
    J = customcolormap(a, {'#7f3c0a','#b35807','#e28212','#f9b967','#ffe0b2','#f7f7f5','#d7d9ee','#b3abd2','#8073a9','#562689','#2f004d'});
    colormap(customcolormap_preset('red-white-blue'));
    clim([-0.1 0.7])
    colormap((bone))

    hold on
    scatter(centerx,centery, 500, 'ro')
    set(gca, 'XColor','black')
    set(gca, 'YColor','black')
    set(gca, 'LineWidth',1)
end
colorbar;

%% FCI gap measurement (16,16)
frames_FCI = [200 680 920];

window = 2;

flux_quantum = h/e;

n0_offset = (-2/3*8.37 + 5.89)*3;
n0_density_FCI = 3*(n0_FCI+n0_offset)*8.85e-12/1.6e-19/33.1e-9*10^-4*1e-12;
v_FCI = (n0_FCI+0.93)/(8.35-0.93);

f = figure(4);
clf
t = tiledlayout(1,1);
ax1 = axes(t);

hold on
for i = centerx-window:centerx+window
    for j = centery-window:centery+window
        plot(ax1, n0_density_FCI, -(Magnetization_FCI(:,j ,i)-Magnetization_FCI(frames_FCI(2),j ,i)),'Color', [0 0 0 0.4],'LineWidth',0.3)
    end
end

mean_m_FCI = -mean(Magnetization_FCI(:,centery-window:centery+window ,centerx-window:centerx+window),[2 3],'omitnan');
plot(ax1, n0_density_FCI, (mean_m_FCI-mean(mean_m_FCI(frames_FCI(2)))),'Color', [0 0 0 1],'LineWidth',2)
ylim([-0.5 0.5])
xlim(ax1, [min(n0_density_FCI), max(n0_density_FCI)])

ax2 = axes(t);
ax2.XAxisLocation = 'top';
ax2.YAxisLocation = 'right';
ax2.Color = 'none';
ax1.Box = 'off';
ax2.Box = 'off';
xlim(ax2, [min(v_FCI) max(v_FCI)])
set(ax2,'ytick',[])


set(ax1,'XColor','black')
set(ax1,'YColor','black')
set(ax2,'XColor','black')
set(ax2,'YColor','black')

fontsize(f,7,"points")
set(ax1, 'LineWidth',1)
set(ax2, 'LineWidth',1)
width=3;
height=3;
set(f,'Units','Inches');
set(f,'Position',[0 0 width height]);
set(f,'PaperSize',[width height],'PaperPosition',[0 0 width height]);


upper_bound = -Magnetization_FCI(frames_FCI(3),centery-window:centery+window ,centerx-window:centerx+window);
lower_bound = -Magnetization_FCI(frames_FCI(1),centery-window:centery+window ,centerx-window:centerx+window);
disp('\n\n\n')
disp(append('FCI mean value of lower bound ', num2str(mean(lower_bound,[2 3],'omitnan'))));
disp(append('FCI std of lower bound ', num2str(std(lower_bound(:)))));
disp(append('FCI mean value of upper bound ', num2str(mean(upper_bound,[2 3],'omitnan'))));
disp(append('FCI std of upper bound ', num2str(std(upper_bound(:)))));
deltaM = mean(upper_bound,[2 3],'omitnan') - mean(lower_bound,[2 3],'omitnan');
stdM = sqrt(std(upper_bound(:))^2 + std(lower_bound(:))^2);
disp(append('FCI deltaM ', num2str(deltaM)));
disp(append('FCI stdM ', num2str(stdM)));
disp(append('FCI gap size ', num2str(deltaM*flux_quantum*spin_M./e*1e3*3/2)));
disp(append('FCI stdM energy ', num2str(stdM*flux_quantum*spin_M./e*1e3*3/2)));