filenumbers=[11671];

data = OpenDataVaultFile2(filenumbers(1));
l= max(data(:,2))+1;
squidSlope = 280; 
ZurichGain = 200000; 
SR560Gain = 10;
SR560GainDC = 50;
SR860Sensitivity = 0.005;
filter = 1; 
unit = 1e9; %Desired unit in tesla. 1e6 is uT, 1e9 is nT
ac_excitation = 0.025; %in V

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

y_vals = linspace(0, 6e-6/max_x_position_index*(max_x_position_index-1), max_x_position_index);
y_vals = repmat(y_vals, l, 1, max_y_position_index);

x_vals = linspace(0, 2e-6/max_y_position_index*(max_y_position_index-1), max_y_position_index).';
x_vals = repmat(x_vals, 1, max_x_position_index, l);
x_vals = permute(x_vals, [3 2 1]);

%%
smooth = 100;
smooth_squid_vals = smoothdata(squid_vals,1,'sgolay',smooth); 
smooth_squid_vals_DC = smoothdata(squid_DC,1,'sgolay',4*smooth); 

spatial_filter_squid_vals_DC = zeros(size(squid_vals)); 
spatial_filter_squid_vals = zeros(size(squid_vals)); 
for i = 1:l
    

    this_squid_dataset = reshape(smooth_squid_vals(i,:,:),max_x_position_index,[]); 
    this_squid_dataset_DC = reshape(smooth_squid_vals_DC(i,:,:),max_x_position_index,[]); 

    
    winsize = 1;
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
        Magnetization(i, :, :) = NewMomentCalculatorWithPadding_v3(x_vals, y_vals, this_dataset*1e-9, 190e-9,3);
        Magnetization(i, :, :) = real(Magnetization(i, :, :))./spin_M;
end
max(max(max(Magnetization)))

Magnetization_gradient_prel = zeros(l, max_x_position_index,max_y_position_index);
Magnetization_gradient = zeros(l, max_x_position_index,max_y_position_index);
for i = 1:l
        this_dataset = spatial_filter_squid_vals(i,:, :); 
        
        Magnetization_gradient_prel(i, :, :) = NewMomentCalculatorWithPadding_v3(x_vals, y_vals, this_dataset*1e-9, 190e-9,3);
        Magnetization_gradient_prel(i, :, :) = real(Magnetization_gradient_prel(i, :, :))./spin_M;
        
end
max(max(max(Magnetization_gradient_prel)))

for i = 1:max_x_position_index
    for j = 1:max_y_position_index
        this_dataset = -cumsum(Magnetization_gradient_prel(:, i,j));
        these_bottom_gates = n0_vals; 
        
        p_line = polyfit([min(min(these_bottom_gates(:, 1, 1))) max(max(these_bottom_gates(:, 1, 1)))], [mean(this_dataset(end-10:end)), mean(this_dataset(1:10))], 1);
        average_line_fit = polyval(p_line, these_bottom_gates(:, 1, 1));
        Magnetization_gradient(:,i,j) = -gradient(this_dataset - average_line_fit); 
    end
end

%% Figre 4 c,e
x = reshape(x_vals(1,:,1),max_x_position_index,[]);
y = reshape(y_vals(1,1,:),max_y_position_index,[]);

FCI_window_up = 0.15;
FCI_window_down = 0.2;

FCI2_window_up = 0.15;
FCI2_window_down = 0.15;
n0_offset_guessed = linspace(0.8, 0.8, max_y_position_index);
n0_offset_guessed_2d = repmat(n0_offset_guessed,max_x_position_index,1);
FM_density = zeros(max_x_position_index, max_y_position_index);
FM_strength = zeros(max_x_position_index, max_y_position_index);
Ch_density = zeros(max_x_position_index, max_y_position_index);
Ch_strength = zeros(max_x_position_index, max_y_position_index);
Ch_peak_strength = zeros(max_x_position_index, max_y_position_index);
Ch_width = zeros(max_x_position_index, max_y_position_index);
ind_Ch_min = [];

FCI_density = zeros(max_x_position_index, max_y_position_index);
FCI_strength = zeros(max_x_position_index, max_y_position_index);
FCI_width = zeros(max_x_position_index, max_y_position_index);

FCI2_density = zeros(max_x_position_index, max_y_position_index);
FCI2_strength = zeros(max_x_position_index, max_y_position_index);
FCI2_width = zeros(max_x_position_index, max_y_position_index);
ind_FCI_min = [];

k = 0;
for j = 1:max_x_position_index
    for i = 1:max_y_position_index
        upper_extremum_Ch = [];
        lower_extremum_Ch = [];
        upper_extremum_FCI = [];
        lower_extremum_FCI = [];
        this_dataset = smoothdata(real(Magnetization_gradient(:,j,i)),1,'sgolay',1);

        SQUID_masked = this_dataset;
        [max_val, ind_FM] = max(SQUID_masked);
        FM_density(j,i) = n0(ind_FM);
        FM_strength(j,i) = max_val;
        ICI_masked = SQUID_masked;
        ICI_masked(1:1100) = 0;
        ICI_masked(1600:end) = 0;

        [Peak_height, ICI_index, w, P] = findpeaks(-ICI_masked,'SortStr','descend');
        
        if isempty(Peak_height) || w(1) > 150 || P(1) < 0.15
            ind_Ch_min = nan;
            Ch_density(j,i) = nan;
        else
            ind_Ch_min = ICI_index(1);
            Ch_density(j,i) = n0(ind_Ch_min);
        end
        if isnan(Ch_density(j,i))
            Ch_strength(j,i) = nan;
            Ch_width(j,i) = nan;
            Ch_peak_strength(j,i) = nan;
        else
            Ch_peak_strength(j,i) = P(1);
            localmin = find(islocalmin(abs(ICI_masked),'MinProminence',0.05));
            proximity_to_Ch = localmin - ind_Ch_min;
            lower_extremum_Ch = min(proximity_to_Ch(proximity_to_Ch>0))+ind_Ch_min;
            upper_extremum_Ch = max(proximity_to_Ch(proximity_to_Ch<0))+ind_Ch_min;
            left_boundary = max(ind_Ch_min - floor(2*round(w(1))), 1);
            right_boundary = min(ind_Ch_min + floor(1*round(w(1))),l);
            a = (real(Magnetization(right_boundary,j,i)-Magnetization(left_boundary,j,i)))/(n0(right_boundary)-n0(left_boundary));
            b = real(Magnetization(left_boundary,j,i))-a*n0(left_boundary);
            detrend_mag = real(Magnetization(left_boundary:right_boundary,j,i) - n0(left_boundary:right_boundary).*a - b);
            [max_val, max_ind] = max(detrend_mag);
            detrend_mag(max_ind+1:end) = 0;
            [min_val, min_ind] = min(detrend_mag);
            min_ind = left_boundary + min_ind;

            upper_extremum_Ch = min_ind;

            if isempty(upper_extremum_Ch) | isempty(lower_extremum_Ch)
                Ch_strength(j,i) = nan;
            else
                Ch_strength(j,i) = abs(Magnetization(lower_extremum_Ch,j,i) - Magnetization(upper_extremum_Ch,j,i));
            end
        end

        if isnan(Ch_density(j,i))
            FCI_density(j,i) = nan;
            FCI_strength(j,i) = nan;
            FCI_width(j,i) = nan;
            
            FCI2_density(j,i) = nan;
            FCI2_strength(j,i) = nan;
            FCI2_width(j,i) = nan;
        else
            FCI_masked = SQUID_masked;
            upper_range = n0>((Ch_density(j,i)-1/2*n0_offset_guessed_2d(j,i))*2/3+3*FCI_window_up);
            lower_range = n0<((Ch_density(j,i)-1/2*n0_offset_guessed_2d(j,i))*2/3-2*FCI_window_down);
            
            FCI_masked(upper_range) = 0;
            FCI_masked(lower_range) = 0;
            
            [Peak_height, FCI_index, w, P] = findpeaks(-FCI_masked,'SortStr','descend');
            
            if isempty(FCI_index)
                ind_FCI_min = nan;
                FCI_density(j,i) = nan;
            elseif P(1) < 0.1 || w(1) > 200
                ind_FCI_min = nan;
                FCI_density(j,i) = nan;
            else
                ind_FCI_min = FCI_index(1);
                FCI_density(j,i) = n0(ind_FCI_min);
            end
            
            if isnan(ind_FCI_min) 
                FCI_strength(j,i) = nan;
            elseif P(1) < 0.1 || w(1) > 100
                FCI_strength(j,i) = nan;
            elseif n0(ind_FCI_min) == min(n0(~lower_range)) || n0(ind_FCI_min) == max(n0(~upper_range))
                FCI_strength(j,i) = nan;
            else  
                FCI_range = SQUID_masked(ind_FCI_min-round(2*w(1)):ind_FCI_min+round(2*w(1)));
                localmin = find(islocalmin(abs(FCI_range),'MinProminence',0.0005));
                
                proximity_to_FCI = localmin - round(2*w(1));
                lower_extremum_FCI = min(proximity_to_FCI(proximity_to_FCI>0))+ind_FCI_min;
                upper_extremum_FCI = max(proximity_to_FCI(proximity_to_FCI<0))+ind_FCI_min;
                
                left_boundary = max(ind_FCI_min - floor(1*w(1)), 1);
                right_boundary = min(ind_FCI_min + floor(2*w(1)),l);
                a = (real(Magnetization(right_boundary,j,i)-Magnetization(left_boundary,j,i)))/(n0(right_boundary)-n0(left_boundary));
                b = real(Magnetization(left_boundary,j,i))-a*n0(left_boundary);
                detrend_mag = real(Magnetization(left_boundary:right_boundary,j,i) - n0(left_boundary:right_boundary).*a - b);
                [max_val, max_ind] = max(detrend_mag);
                detrend_mag(max_ind+1:end) = 0;
                [min_val, min_ind] = min(detrend_mag);
                min_ind = left_boundary + min_ind;
                max_ind = left_boundary + max_ind;
                upper_extremum_FCI = floor((upper_extremum_FCI+min_ind)/2);
                lower_extremum_FCI = floor((lower_extremum_FCI+max_ind)/2);


                if ~isempty(upper_extremum_FCI) & ~isempty(lower_extremum_FCI) & ~isnan(Ch_strength(j,i))
                    FCI_strength(j,i) = abs(Magnetization(lower_extremum_FCI,j,i) - Magnetization(upper_extremum_FCI,j,i));
                else
                    FCI_strength(j,i) = nan;
                end
            end
        end

        
    end
end


n0_offset = (-2/3*Ch_density + FCI_density)*3;
n0_offset_density = n0_offset*3*8.85e-12/1.6e-19/33.1e-9*10^-4*1e-12;

Ch_density_off = Ch_density-n0_offset;
% n = 1 charge/ u.c.
% epsilon*epsilon_0*V/(e*d) = 1 / [a^2 / (4*sin^2(theta/2))*sqrt(3)/2]

twist_angle = sqrt(-Ch_density_off*sqrt(3)/8*(3*8.85e-12/1.6e-19/33.1e-9)*(0.353e-9)^2);
twist_angle = 2*asin(twist_angle)/pi*180;
 
figure(1)
clf
ax(1) = nexttile;
twist_figure = imagesc(twist_angle);

shading flat; 
axis xy
set(gca,'YDir','normal') 
h = colorbar; 
colormap(ax(1), 'jet');
caxis([3.4 3.9])
pbaspect([30 90 1])
set(gca,'xtick',[])
set(gca,'ytick',[])
set(twist_figure, 'AlphaData', ~isnan(twist_angle))
set(gca, 'LineWidth',1)
set(gca, 'XColor','black')
set(gca, 'YColor','black')

ax(2) = nexttile;
twist_figure = imagesc(n0_offset);

shading flat; 
axis xy
set(gca,'YDir','normal') 
h = colorbar; 
colormap(ax(2), 'spring');
caxis([-1.2 -0.4])
pbaspect([30 90 1])
set(gca,'xtick',[])
set(gca,'ytick',[])
set(twist_figure, 'AlphaData', ~isnan(n0_offset))
set(gca, 'LineWidth',1)
set(gca, 'XColor','black')
set(gca, 'YColor','black')


%% Figre 4 a,b
f = figure(4); 
clf
ax1 = subplot(1,5,1:4);
i = 20;
BG = BG_vals(:,1,1);
TG = SG_vals(:,1,1);
n0_density = 3*n0*8.85e-12/1.6e-19/33.1e-9*10^-4*1e-12;
x = linspace(0,5,75);
imagesc(ax1, TG+BG,x, real(Magnetization_gradient(:,1:75,i)).')
axis xy;
shading interp;
a= [linspace(0,0.3,5),0.5,linspace(0.7,1,5)]; 
J = customcolormap(a, {'#7f3c0a','#b35807','#e28212','#f9b967','#ffe0b2','#f7f7f5','#d7d9ee','#b3abd2','#8073a9','#562689','#2f004d'});

ylabel(ax1, 'Coordinate (\mum)')
colormap(J)
clim(ax1, [-0.5,0.5]) 
box on
ax1.LineWidth = 1;

ax2 = subplot(1,5,5);
plot(ax2, smoothdata(twist_angle(1:75,i),1,'sgolay',1),x)

box on
ax2.LineWidth = 1;

yticks(ax2, [])
xlim([3.5 3.9])
ylim([0 5])
xticks([3.6 3.8])
fontsize(f,7,"points")

factor = 1.0;
width = 4*factor;
height = 1.5*factor;
set(f,'Units','Inches');
set(f,'Position',[0 0 width height]);
set(f,'PaperSize',[width height],'PaperPosition',[0 0 width height]); 





