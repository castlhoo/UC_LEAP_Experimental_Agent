filenumbers=[12273];

data = OpenDataVaultFile2(filenumbers(1));
l= max(data(:,2))+1;
squidSlope = 500; 
ZurichGain = 200000; 
SR560Gain = 10;
SR560GainDC = 50;
SR860Sensitivity = 0.001;
filter = 1; 
unit = 1e9; %Desired unit in tesla. 1e6 is uT, 1e9 is nT
ac_excitation = 0.02; %in V

max_bottom_gate_index = max(data(:,2)) + 1; %Matlab 1 indexes, Python 0 indexes

max_x_position_index = max(data(:,7)) + 1; %Matlab 1 indexes, Python 0 indexes
max_y_position_index = max(data(:,8)) + 1; %Matlab 1 indexes, Python 0 indexes

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
squid_vals = (squid_vals_trace+squid_vals_retrace)/2;

squid_DC = reshape((trace_data(:,12)+trace_data(:,12))./2,l,max_x_position_index,[])*unit./(squidSlope*SR560GainDC); 

p0 = p0_vals(:,1,1);

%%
smooth = 100;
smooth_squid_vals = smoothdata(squid_vals,1,'movmean',smooth); 
smooth_squid_vals_trace = smoothdata(squid_vals_trace,1,'movmean',smooth); 
smooth_squid_vals_retrace = smoothdata(squid_vals_retrace,1,'movmean',smooth); 
smooth_squid_DC = smoothdata(squid_DC,1,'movmean',1*smooth); 
smooth_squid_DC = smooth_squid_DC - mean(smooth_squid_DC);

spatial_filter_squid_vals = zeros(size(squid_vals)); 
spatial_filter_squid_vals_DC = zeros(size(squid_vals)); 
for i = 1:l
    
    this_squid_dataset = reshape(smooth_squid_vals(i,:,:),max_x_position_index,[]); 
    this_squid_dataset_DC = reshape(smooth_squid_DC(i,:,:),max_x_position_index,[]); 
    
    winsize = 3;
    H = [gausswin(winsize) , gausswin(winsize) , gausswin(winsize)];
    H = H./sum(sum(H));
    this_squid_dataset = filter2(H,this_squid_dataset);
    this_squid_dataset_DC = filter2(H,this_squid_dataset_DC);
    
    spatial_filter_squid_vals(i,:,:) = this_squid_dataset; 
    spatial_filter_squid_vals_DC(i,:,:) = this_squid_dataset_DC; 
end

%%

x = reshape(x_vals(1,:,1),max_x_position_index,[]);
x = x - min(min(x));
y = reshape(y_vals(1,1,:),max_y_position_index,[]);
y = y - min(min(y));

D_offset = zeros(max_x_position_index, max_y_position_index);

SQUID_mask_ind = [];
for j = 1:max_x_position_index
    for i = 1:max_y_position_index
        this_dataset = smooth_squid_vals(:,j,i);
        SQUID_mask_ind = abs(this_dataset)<3;
        SQUID_masked = this_dataset;
        SQUID_masked(SQUID_mask_ind) = 0;
        
        [max_val, ind_top] = min(SQUID_masked);
        if ind_top > 200 && ind_top < 800
            SQUID_masked(ind_top-200:ind_top+200) = 0;
        elseif ind_top > 800
            SQUID_masked(ind_top-200:end) = 0;
        else
            SQUID_masked(1:ind_top+200) = 0;
        end
        [min_val, ind_bottom] = min(SQUID_masked);
        if min_val == 0 | max_val == 0
            D_offset(j,i) = nan;
        else
            D_offset(j,i) = (p0(ind_top) + p0(ind_bottom))/2;
        end
    end
end

D_offset_real = D_offset ./ 33.1*1000;

f = figure(4);
clf
D_offset_fig = imagesc(fliplr(D_offset_real));
set(gca,'xtick',[])
set(gca,'ytick',[])
axis xy;
shading flat; 
set(gca,'YDir','normal') 
pbaspect([max_y_position_index max_x_position_index 1])
J = colormap(customcolormap_preset('red-white-blue'));
colormap('jet')
h = colorbar();
caxis([-30 0])
title(h, 'D (mV/nm)')
set(D_offset_fig, 'AlphaData', ~isnan(fliplr(D_offset_real)))


colormap(parula)
