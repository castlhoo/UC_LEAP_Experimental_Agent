filenumbers=[11671];

data = OpenDataVaultFile2(filenumbers(1));
l= max(data(:,2))+1;
squidSlope = 280; 
SR560Gain = 10;
SR560GainDC = 50;
SR860Sensitivity = 0.005;
filter = 1; 
unit = 1e9; %Desired unit in tesla. 1e6 is uT, 1e9 is nT
ac_excitation = 0.025; %in V
voltage_range = 8; %in V

max_bottom_gate_index = max(data(:,2)) + 1; %Matlab 1 indexes, Python 0 indexes

max_x_position_index = max(data(:,7)) + 1; %Matlab 1 indexes, Python 0 indexes
max_y_position_index = max(data(:,8)) + 1; %Matlab 1 indexes, Python 0 indexes
squidSlope = zeros(max_bottom_gate_index,max_x_position_index,max_y_position_index);
squidSlope(:,:,1:13) = 280;
squidSlope(:,:,13:30) = 100;

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
SG_vals = reshape(trace_data(:,6),l,max_x_position_index,[]);
BG_vals = reshape(trace_data(:,5),l,max_x_position_index,[]);
squid_vals_trace = reshape(trace_data(:,11),l,max_x_position_index,[])*unit./(squidSlope*SR560Gain)*SR860Sensitivity/10; 
squid_vals_retrace = reshape(retrace_data(:,11),l,max_x_position_index,[])*unit./(squidSlope*SR560Gain)*SR860Sensitivity/10; 
squid_DC_trace = reshape(trace_data(:,12),l,max_x_position_index,[])*unit./(squidSlope*SR560GainDC); 
squid_DC_retrace = reshape(retrace_data(:,12),l,max_x_position_index,[])*unit./(squidSlope*SR560GainDC);
squid_vals = (squid_vals_trace+squid_vals_retrace)/2;
squid_DC = (squid_DC_trace+squid_DC_retrace)/2;
n0 = n0_vals(:,1,1);


filenumbers=[11673];

data = OpenDataVaultFile2(filenumbers(1));
max_bottom_gate_index = max(data(:,2)) + 1; %Matlab 1 indexes, Python 0 indexes

max_x_position_index = max(data(:,7)) + 1; %Matlab 1 indexes, Python 0 indexes

squidSlope = 100;

trace_data = data(data(:,1)==0,:); 
retrace_data = data(data(:,1)==1,:); 

length_data = length(trace_data);
number_of_lines = floor(length_data/max_x_position_index/l);
trace_data = trace_data(1:number_of_lines*max_x_position_index*l,:);
retrace_data = retrace_data(1:number_of_lines*max_x_position_index*l,:);

squid_vals_trace_retake = reshape(trace_data(:,11),l,max_x_position_index,[])*unit/(squidSlope*SR560Gain)*SR860Sensitivity/10; 
squid_vals_retrace_retake = reshape(retrace_data(:,11),l,max_x_position_index,[])*unit/(squidSlope*SR560Gain)*SR860Sensitivity/10; 
squid_DC_trace_retake = reshape(trace_data(:,12),l,max_x_position_index,[])*unit/(squidSlope*SR560GainDC); 
squid_DC_retrace_retake = reshape(retrace_data(:,12),l,max_x_position_index,[])*unit/(squidSlope*SR560GainDC);
squid_vals_retake = (squid_vals_trace_retake+squid_vals_retrace_retake)/2;
squid_DC_retake = (squid_DC_trace_retake+squid_DC_retrace_retake)/2;

squid_vals(:, :, 13:13+number_of_lines-1) = squid_vals_retake;
squid_DC(:, :, 13:13+number_of_lines-1) = squid_DC_retake;


y_vals = linspace(0, 2e-6, max_y_position_index);
y_vals = repmat(y_vals, max_x_position_index, 1);
y_vals = repmat(y_vals, 1,1,l);
y_vals = permute(y_vals, [3 1 2]);

x_vals = linspace(0, 6e-6, max_x_position_index).';
x_vals = repmat(x_vals, 1, max_y_position_index, l);
x_vals = permute(x_vals, [3 1 2]);

%%
smooth = 100;
smooth_squid_vals = smoothdata(squid_vals,1,'sgolay',smooth); 
smooth_squid_vals_DC = smoothdata(squid_DC,1,'sgolay',4*smooth); 
smooth_squid_vals_DC = smooth_squid_vals_DC-mean(smooth_squid_vals_DC);

spatial_filter_squid_vals_DC = zeros(size(squid_vals)); 
spatial_filter_squid_vals = zeros(size(squid_vals)); 
for i = 1:l
    

    this_squid_dataset = reshape(smooth_squid_vals(i,:,:),max_x_position_index,[]); 
    this_squid_dataset_DC = reshape(smooth_squid_vals_DC(i,:,:),max_x_position_index,[]); 

    
    winsize = 3;
    H = [gausswin(winsize) , gausswin(winsize) , gausswin(winsize)];
    H = H./sum(sum(H));
    this_squid_dataset = filter2(H,this_squid_dataset);
    this_squid_dataset_DC = filter2(H,this_squid_dataset_DC);
    
    spatial_filter_squid_vals(i,:,:) = this_squid_dataset; 
    spatial_filter_squid_vals_DC(i,:,:) = this_squid_dataset_DC;
    
end

%% Assuming 3.7 degree twist angle calculate magnetization 
dx = (max(BG_vals(:, 1,1)) - min(BG_vals(:, 1,1)))/l;
integrated_B_vals = cumsum(smooth_squid_vals,'reverse').* dx ./ (ac_excitation);  

for i = 1:max_x_position_index
    for j = 1:max_y_position_index
        this_dataset = integrated_B_vals(:,i,j); 
        these_bottom_gates = BG_vals(:,i,j); 
        
        p_line = polyfit([min(min(these_bottom_gates(:, 1, 1))) max(max(these_bottom_gates(:, 1, 1)))], [mean(integrated_B_vals(end-100:end, i, j)), mean(integrated_B_vals(1:100, i, j))], 1);
        average_line_fit = polyval(p_line, these_bottom_gates(:, 1, 1));
        integrated_B_vals(:,i,j) = integrated_B_vals(:,i,j) - average_line_fit; 
    end
end


a_M = 0.353 / (2*sin(3.7/180*pi/2)) * 10^-9; % m
%a_M ~ 5nm
Area_of_triangle = sqrt(3)/2*a_M^2;

h = 6.63*10^-34; %  J Hz^(-1)
e = 1.6*10^-19;  % C
m_e = 9.1 * 10^(-31); % kg
spin_M =  e * (h/2/pi) / (2 * m_e) / Area_of_triangle; % mu_B/u.c.

Magnetization = zeros(l, max_x_position_index,max_y_position_index);
for i = 1:l
        this_dataset = integrated_B_vals(i,:, :); 
        Magnetization(i, :, :) = NewMomentCalculatorWithPadding_v3(y_vals, x_vals, this_dataset*1e-9, 190e-9,3);
        Magnetization(i, :, :) = Magnetization(i, :, :)./spin_M;
end

Magnetization_gradient_prel = zeros(l, max_x_position_index,max_y_position_index);
Magnetization_gradient = zeros(l, max_x_position_index,max_y_position_index);
for i = 1:l
        this_dataset = spatial_filter_squid_vals(i,:, :); 
        
        Magnetization_gradient_prel(i, :, :) = NewMomentCalculatorWithPadding_v3(y_vals, x_vals, this_dataset*1e-9, 190e-9,3);
        Magnetization_gradient_prel(i, :, :) = Magnetization_gradient_prel(i, :, :)./spin_M;
        
end

for i = 1:max_x_position_index
    for j = 1:max_y_position_index
        this_dataset = -cumsum(Magnetization_gradient_prel(:, i,j));
        these_bottom_gates = n0_vals; 
        
        p_line = polyfit([min(min(these_bottom_gates(:, 1, 1))) max(max(these_bottom_gates(:, 1, 1)))], [mean(this_dataset(end-10:end)), mean(this_dataset(1:10))], 1);
        average_line_fit = polyval(p_line, these_bottom_gates(:, 1, 1));
        Magnetization_gradient(:,i,j) = -gradient(this_dataset - average_line_fit); 
    end
end

%% Figure 2d
i = [17 31 44 56 68];
j = 19;
f = figure(10);
clf
linecolors = parula(length(i)+1);
for k = 1:length(i)

    n0_density = 3*n0*8.85e-12/1.6e-19/33.1e-9*10^-4*1e-12;
    plot(n0_density, real(Magnetization(:,i(k),j)),'Color', linecolors(k,:),'DisplayName',num2str(k))
    hold on
end

xlabel('n_e (x10^{12} cm^{-2})')
ylabel('m_z (\mu_B/u.c.)')
set(gca, 'LineWidth',1)
xlim([min(n0_density) max(n0_density)])

set(gca, 'XColor','black')
set(gca, 'YColor','black')
fontsize(f,7,"points")
factor =0.85;
width =4*factor;
height = 4*factor;
set(f,'Units','Inches');
set(f,'Position',[0 0 width height]);
set(f,'PaperSize',[width height],'PaperPosition',[0 0 width height]); 

%% Figure 2a,b,c
frames = flip([750 1440 1740]);
limits = flip([0.3 0.6 0.8]);
f = figure(5);
clf
for i = 1:length(frames)
    subplot(1,3,i)
    this_dataset = reshape(real(Magnetization_gradient(frames(i),:,:)),max_x_position_index,[]);
    [Fx,Fy] = gradient(this_dataset);
    Current = sqrt(Fx.^2+Fy.^2);
    mag_grad_figure = imagesc(this_dataset);
    shading interp; 
    set(gca,'YDir','normal') 
    pbaspect([max_y_position_index max_x_position_index 1])
        
    a= [linspace(0,0.3,5),0.5,linspace(0.7,1,5)]; 
    J = customcolormap(a, {'#7f3c0a','#b35807','#e28212','#f9b967','#ffe0b2','#f7f7f5','#d7d9ee','#b3abd2','#8073a9','#562689','#2f004d'});
    caxis([-limits(i) limits(i)])
    % caxis([-0.3 0.3])
    
    set(mag_grad_figure, 'AlphaData', ~isnan(this_dataset))
    colormap(J)
    % colormap(flipud(bone))
    set(gca,'xtick',[])
    set(gca,'ytick',[])
%     box on
    set(gca, 'XColor','black')
    set(gca, 'YColor','black')
    set(gca, 'LineWidth',1)
end
%% Figure 2e
frames = flip([1430]);
limits = flip([0.3 0.3 0.3 0.6 0.6 0.6]);
f = figure(6);
x = reshape(x_vals(1,:,1),max_x_position_index,[]);
y = reshape(y_vals(1,1,:),max_y_position_index,[]);

A.X = x_vals(1,:,1);
A.Y = y_vals(1,1,:);
    
y = [0 ((A.X(end,1)-A.X(1,1))^2+(A.Y(end,1)-A.Y(1,1))^2)^(1/2)];
x = [0 ((A.X(1,end)-A.X(1,1))^2+(A.Y(1,end)-A.Y(1,1))^2)^(1/2)];

clf
for i = 1:length(frames)
    this_dataset = reshape(real(Magnetization(frames(i),:,:)),max_x_position_index,[]);
    [Fx,Fy] = gradient(this_dataset);
    Current = sqrt(Fx.^2+Fy.^2);
    imagesc(fliplr(this_dataset))
    shading flat; 
    set(gca,'YDir','normal') 
    pbaspect([max_y_position_index max_x_position_index 1])
        
    a= [linspace(0,0.3,5),0.5,linspace(0.7,1,5)]; 
    caxis([0 11])
    colormap((bone))
    set(gca,'xtick',[])
    set(gca,'ytick',[])
    set(gca, 'XColor','black')
    set(gca, 'YColor','black')
    set(gca, 'LineWidth',1)
    colorbar();
end

fontsize(f,7,"points")
factor =1;
width =4*factor;
height = 3*factor;
set(f,'Units','Inches');
set(f,'Position',[0 0 width height]);
set(f,'PaperSize',[width height],'PaperPosition',[0 0 width height]); 