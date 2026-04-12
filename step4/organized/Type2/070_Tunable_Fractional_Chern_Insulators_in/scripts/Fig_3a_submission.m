filenumbers=[12240];

data = OpenDataVaultFile2(filenumbers(1));
l= max(data(:,2))+1;
squidSlope = 500; 
SR560Gain = 10;
SR560GainDC = 50;
SR860Sensitivity = 0.0005;
filter = 1; 
unit = 1e9; %Desired unit in tesla. 1e6 is uT, 1e9 is nT
ac_excitation = 0.005; %in V
voltage_range = 8; %in V

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
squid_DC_trace = reshape(trace_data(:,12),l,max_x_position_index,[])*unit./(squidSlope*SR560GainDC); 
squid_DC_retrace = reshape(retrace_data(:,12),l,max_x_position_index,[])*unit./(squidSlope*SR560GainDC);
squid_vals = (squid_vals_trace+squid_vals_retrace)/2;
squid_DC = (squid_DC_trace+squid_DC_retrace)/2;
n0 = n0_vals(:,1,1);

y_vals = linspace(0, 2e-6, max_y_position_index);
y_vals = repmat(y_vals, max_x_position_index, 1);
y_vals = repmat(y_vals, 1,1,l);
y_vals = permute(y_vals, [3 1 2]);

x_vals = linspace(0, 2e-6, max_x_position_index).';
x_vals = repmat(x_vals, 1, max_y_position_index, l);
x_vals = permute(x_vals, [3 1 2]);

%%
smooth = 100;
smooth_squid_vals = smoothdata(squid_vals,1,'movmean',smooth); 
smooth_squid_vals_DC = smoothdata(squid_DC,1,'movmean',2*smooth); 
smooth_squid_vals_DC = -(smooth_squid_vals_DC-mean(smooth_squid_vals_DC(1:50,:,:),1));

spatial_filter_squid_vals_DC = zeros(size(squid_vals)); 
spatial_filter_squid_vals = zeros(size(squid_vals)); 
for i = 1:l
    
    this_squid_dataset = reshape(smooth_squid_vals(i,:,:),max_x_position_index,[]); 
    this_squid_dataset_DC = reshape(smooth_squid_vals_DC(i,:,:),max_x_position_index,[]); 

    
    winsize = 5;
    H = [gausswin(winsize) , gausswin(winsize) , gausswin(winsize)];
    H = H./sum(sum(H));
    this_squid_dataset = filter2(H,this_squid_dataset);
    this_squid_dataset_DC = filter2(H,this_squid_dataset_DC);
    
    spatial_filter_squid_vals(i,:,:) = this_squid_dataset; 
    spatial_filter_squid_vals_DC(i,:,:) = this_squid_dataset_DC;
    
end


%%
dx = abs(max(SG_vals,[],'all')-min(SG_vals,[],'all'))/(l);

integrated_B_vals = spatial_filter_squid_vals_DC;

a_M = 0.353 / (2*sin(3.7/180*pi/2)) * 10^-9; % m
%a_M ~ 5nm
Area_of_triangle = sqrt(3)/2*a_M^2;

h = 6.63*10^-34; %  J Hz^(-1)
e = 1.6*10^-19;  % C
m_e = 9.1 * 10^(-31); % kg
flux_quantum = h/e;
spin_M =  e * (h/2/pi) / (2 * m_e) / Area_of_triangle; % mu_B/u.c.

Magnetization = zeros(l, max_x_position_index,max_y_position_index);
for i = 1:l
        this_dataset = integrated_B_vals(i,:, :); 
        Magnetization(i, :, :) = NewMomentCalculatorWithPadding_v3(y_vals, x_vals, this_dataset*1e-9, 140e-9,15);
        Magnetization(i, :, :) = Magnetization(i, :, :)./spin_M;
end


%% ICI gap measurement (16,16) linecuts and value
% frames_FCI = [500 800 1100];
frames = [200 420 640];

v = (n0+n0_offset)/(8.37-n0_offset);

window = 2;
f = figure(4);
clf
t = tiledlayout(1,1);
ax1 = axes(t);

hold on
for i = centerx-window:centerx+window
    for j = centery-window:centery+window
        plot(ax1, n0_density, Magnetization(:,j ,i)-Magnetization(frames(2),j ,i),'Color', [0 0 0 0.4],'LineWidth',0.3)
    end
end
mean_M = mean(Magnetization(:,centery-window:centery+window ,centerx-window:centerx+window),[2 3],'omitnan');
plot(ax1, n0_density, mean_M-mean_M(frames(2)),'Color', [0 0 0 1],'LineWidth',2)
ylim([-1.7 1.7])
xlim(ax1, [min(n0_density), max(n0_density)])

ax2 = axes(t);
ax2.XAxisLocation = 'top';
ax2.YAxisLocation = 'right';
ax2.Color = 'none';
ax1.Box = 'off';
ax2.Box = 'off';
xlim(ax2, [min(v) max(v)])
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

upper_bound = Magnetization(frames(3),centery-window:centery+window ,centerx-window:centerx+window);
lower_bound = Magnetization(frames(1),centery-window:centery+window ,centerx-window:centerx+window);
disp('\n\n\n')
disp(append('ICI mean value of lower bound ', num2str(mean(lower_bound,[2 3],'omitnan'))));
disp(append('ICI std of lower bound ', num2str(std(lower_bound(:)))));
disp(append('ICI mean value of upper bound ', num2str(mean(upper_bound,[2 3],'omitnan'))));
disp(append('ICI std of upper bound ', num2str(std(upper_bound(:)))));
deltaM = mean(upper_bound,[2 3],'omitnan') - mean(lower_bound,[2 3],'omitnan');
stdM = sqrt(std(upper_bound(:))^2 + std(lower_bound(:))^2);
disp(append('ICI deltaM ', num2str(deltaM)));
disp(append('ICI stdM ', num2str(stdM)));
disp(append('ICI gap size ', num2str(deltaM*flux_quantum./e*1e3*spin_M)));
disp(append('ICI stdM energy ', num2str(stdM*flux_quantum./e*1e3*spin_M)));
%% FCI gap measurement (16,16)
frames_FCI = [100 700 920];
centerx = 16;
centery = 16;
% window = 1;
% frames_FCI = [500 800 1100];
% centerx = 14;
% centery = 19;
% frames = [620 720 820];
% centerx = 16;
% centery = 22;
window = 2;
flux_quantum = h/e;

n0_offset = (-2/3*8.37 + 5.89)*3;
Ch_density_off = 8.37-n0_offset;
% n = 1 charge/ u.c.
% epsilon*epsilon_0*V/(e*d) = 1 / [a^2 / (4*sin^2(theta/2))*sqrt(3)/2]
%


f = figure(5);
clf
% spatial_filter_squid_vals = smoothdata(gradient(spatial_filter_squid_vals_DC,1),1,'sgolay',1);
% spatial_filter_squid_vals = spatial_filter_squid_vals_DC;

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
    % clim([-50 50])
    % clim([-300 300])
    colormap((bone))

    hold on
    scatter(centerx,centery, 500, 'ro')
    set(gca, 'XColor','black')
    set(gca, 'YColor','black')
    set(gca, 'LineWidth',1)
end
% nexttile
% this_dataset = reshape(Magnetization_FCI(frames_FCI(3),:,:)-Magnetization_FCI(frames_FCI(1),:,:),max_x_position_index,[]);
% imagesc(-this_dataset)
% shading flat; 
% set(gca,'YDir','normal') 
% pbaspect([max_y_position_index max_x_position_index 1])
% 
% a= [linspace(0,0.3,5),0.5,linspace(0.7,1,5)]; 
% J = customcolormap(a, {'#7f3c0a','#b35807','#e28212','#f9b967','#ffe0b2','#f7f7f5','#d7d9ee','#b3abd2','#8073a9','#562689','#2f004d'});
% colormap(customcolormap_preset('red-white-blue'));
% clim([-0.1 0.7])
% % clim([-50 50])
% % clim([-300 300])
% colormap((bone))
% 
% hold on
% scatter(centerx,centery, 500, 'ro')
% set(gca, 'XColor','black')
% set(gca, 'YColor','black')
% set(gca, 'LineWidth',1)
colorbar;

figure(2)
clf

Magnetization_gradient = smoothdata(gradient(Magnetization_FCI,1).*ac_excitation_FCI./dx,1,'sgolay',100);

v_FCI = (n0_FCI+0.93)/(8.35-0.93);
n0_density_FCI = 3*(n0_FCI+0.93)*8.85e-12/1.6e-19/32e-9*10^-4*1e-12;
for i = centerx-window:centerx+window
    for j = centery-window:centery+window %j - vertical linecut, i - horizontal
            nexttile
            
            % plot(n0_density, Magnetization(:,j,i))
            hold on
            plot(n0_density_FCI, -Magnetization_FCI(:,j,i))
            % plot(linspace(1,1200, 1800), Magnetization_FCI(:,j,i))
            % plot(n0, Magnetization_gradient(:,j,i)/5)
            % hold on
            % plot(n0_FCI, Magnetization_gradient_FCI(:,j,i))
            
            ylabel('m (\mu_B/u.c.)')
            box on
            ylim([0 0.7])
    %         ylim([-100 100])
            title(strcat(num2str(i), ', ', num2str(j)))
            % hold off
            if j == centery && i ==centerx
                scatter(n0_density_FCI(frames_FCI), -Magnetization_FCI(round(frames_FCI),j,i),100,'k.');
            end
    end
end
%% FCI gap measurement (16,16)
frames_FCI = [200 680 920];

window = 2;
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
% xline(ax1, n0_density_FCI(frames_FCI), '--')
% xlabel(ax1, 'n_e (10^{12} cm^{-2})')
% ylabel(ax1, '\Delta m (\mu_B/u.c.)')
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

if ismac
    fname = '/Users/macbook/Young Lab Dropbox/Young Group/nSOT Andrea Shared/Papers/tMoTe2/Figures for article/Figure 4';
elseif ispc
    fname = 'C:\Users\Evgeny\Young Lab Dropbox\Young Group\nSOT Andrea Shared\Papers\tMoTe2\Figures for article\Figure 4';
else
    disp('Unknown operating system');
end
print(gcf, fullfile(fname, append('FCI_linecut.pdf')), '-dpdf', '-fillpage')

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

%%
f = figure(2);
clf
t = tiledlayout(1,1);
ax1 = axes(t);
i = 16;
j = 16;
v = (n0+0.8)/(8.72-0.8);
n0_density = 3*(n0+0.8)*8.85e-12/1.6e-19/32e-9*10^-4*1e-12;

linecolors = parula(4);
plot(ax1,n0_density, real(Magnetization(:,j,i)), 'Color', linecolors(1,:))
xlim(ax1, [min(n0_density) max(n0_density)])
ax2 = axes(t);
ylabel(ax1,'\Deltam (\mu_B/u.c.)')
plot(ax2, v, -smoothdata(gradient(real(Magnetization(:,j,i))).*ac_excitation./dx,1,'sgolay',200),'Color', linecolors(2,:))
ax2.XAxisLocation = 'top';
ax2.YAxisLocation = 'right';
ax1.YColor = linecolors(1,:);
ax2.YColor = linecolors(2,:);
% ylim(ax1, [0 1.7])
ylabel(ax2,'\deltam (\mu_B/u.c.)')
xlabel(ax1,'n_e (x10^{12} cm^{-2})')
ax2.Color = 'none';
ax1.Box = 'off';
ax2.Box = 'off';
xlim(ax2, [min(v) max(v)])
fontsize(f,7,"points")
set(gca, 'LineWidth',1)
width =3.5;
height = 3;
set(f,'Units','Inches');
set(f,'Position',[0 0 width height]);
set(f,'PaperSize',[width height],'PaperPosition',[0 0 width height]);
%%
f = figure(2);
clf
t = tiledlayout(1,1);
ax1 = axes(t);
% i = 23;
% j = 29;

i = 21;
j = 30;

v = (n0+0.8)/(8.72-0.8);
n0_density = 3*(n0+0.8)*8.85e-12/1.6e-19/32e-9*10^-4*1e-12;

linecolors = parula(4);
plot(ax1,n0_density, real(Magnetization(:,j,i))-1.15, 'Color', linecolors(1,:))
xlim(ax1, [min(n0_density) max(n0_density)])
ax2 = axes(t);
ylabel(ax1,'\Deltam_z (\mu_B/u.c.)')
% plot(ax1,n0_density, real(Magnetization(:,j,i)), 'Color', linecolors(1,:))
ax2.XAxisLocation = 'top';
ax2.YAxisLocation = 'right';
% ax1.YColor = linecolors(1,:);
% ax2.YColor = linecolors(2,:);
% ylim(ax1, [-1 1])
set(ax2,'ytick',[])
% ylabel(ax2,'\deltam (\mu_B/u.c.)')
xlabel(ax1,'n_e (x10^{12} cm^{-2})')
ax2.Color = 'none';
ax1.Box = 'off';
ax2.Box = 'off';
xlim(ax2, [min(v) max(v)])
fontsize(f,7,"points")
set(ax1, 'LineWidth',1)
set(ax2, 'LineWidth',1)
set(ax1, 'XColor','black')
set(ax1, 'YColor','black')
set(ax2, 'XColor','black')
set(ax2, 'YColor','black')
width =2;
height = 2;
set(f,'Units','Inches');
set(f,'Position',[0 0 width height]);
set(f,'PaperSize',[width height],'PaperPosition',[0 0 width height]); 
% print(gcf, 'C:\Users\Evgeny\Young Lab Dropbox\Young Group\nSOT Andrea Shared\Papers\tMoTe2\Figures for article\Figure 4\12240_linecut.pdf', '-dpdf', '-fillpage')
if ismac
    fname = '/Users/macbook/Young Lab Dropbox/Young Group/nSOT Andrea Shared/Papers/tMoTe2/Figures for article/Figure 4';
elseif ispc
    fname = 'C:\Users\Evgeny\Young Lab Dropbox\Young Group\nSOT Andrea Shared\Papers\tMoTe2\Figures for article\Figure 4';
else
    disp('Unknown operating system');
end
% print(gcf, fullfile(fname, append('12240_linecut.pdf')), '-dpdf', '-fillpage')

%%
set(gca, 'LineWidth',1)
xlim([min(n0_density) max(n0_density)])
% set(gca, 'XColor','black')
% set(gca, 'YColor','black')
fontsize(f,7,"points")
factor =0.85;
width =4.5*factor;
height = 2.5*factor;
set(f,'Units','Inches');
set(f,'Position',[0 0 width height]);
set(f,'PaperSize',[width height],'PaperPosition',[0 0 width height]); 

% print(gcf, 'C:\Users\Evgeny\Young Lab Dropbox\Young Group\nSOT Andrea Shared\Papers\tMoTe2\March meeting 2024\11670_dm_m_linecut_65_19.pdf', '-dpdf', '-fillpage')


%%
frames = [1150 500];
f = figure(5);
clf

this_dataset = reshape(real(-Magnetization(frames(1),:,:)),max_x_position_index,[]);
this_dataset_bg = reshape(real(-Magnetization(frames(2),:,:)),max_x_position_index,[]);
imagesc(fliplr(-this_dataset+this_dataset_bg))
shading interp; 
set(gca,'YDir','normal') 
pbaspect([max_y_position_index max_x_position_index 1])
    
a= [linspace(0,0.3,5),0.5,linspace(0.7,1,5)]; 
J = customcolormap(a, {'#7f3c0a','#b35807','#e28212','#f9b967','#ffe0b2','#f7f7f5','#d7d9ee','#b3abd2','#8073a9','#562689','#2f004d'});
%     caxis([-limits(i) limits(i)])
% caxis([-0.2 1.5])
% colorbar();
colormap((bone))
set(gca,'xtick',[])
set(gca,'ytick',[])
%     box on
set(gca, 'XColor','black')
set(gca, 'YColor','black')
set(gca, 'LineWidth',1)


% print(gcf, 'C:\Users\Evgeny\Young Lab Dropbox\Young Group\nSOT Andrea Shared\Papers\tMoTe2\Figures for article\Figure 4\12240_frame.pdf', '-dpdf', '-fillpage')


%%
% figure()
i = 1;
j = 16;
f = figure(15);
clf
v = (n0+0.8)/(8.72-0.8);
n0_density = 3*(n0+0.8)*8.85e-12/1.6e-19/32e-9*10^-4*1e-12;

% deltan_conv = dx/((2*1)*3*8.85e-12/1.6e-19/24e-9*10^-4*1e-12); 
% yyaxis left
% plot(n0, real(spatial_filter_squid_vals(:,i,j)))

% hold on
Magnetization_gradient_ave = smoothdata(gradient(real(-Magnetization(:,i,j))).*ac_excitation./dx,1,'sgolay',100);
% Magnetization_gradient_ave = smoothdata(Magnetization_gradient_prel(:,j,i),1,'movmean',100);
Magnetization_gradient_ave_masked = Magnetization_gradient_ave;
Magnetization_gradient_ave_masked(abs(Magnetization_gradient_ave)<0.01) = 0;
plot(n0,Magnetization_gradient_ave,'LineWidth',1)
hold on
plot(n0,Magnetization_gradient_ave_masked,'LineWidth',1)
% ylim([-150 150])

xlabel('\nu')
ylabel('\deltam/\deltan, \mu_B/(u.c.\timescm^{-2})')
% ylim([-1.5e-4 2.5e-4])
title(strcat(num2str(filenumbers(1)), '{ } i ={ }', num2str(i), '{ }j ={ }', num2str(j)))


[pks,locs, widths] = findpeaks(-Magnetization_gradient_ave_masked,'SortStr','descend');
max_peak_ind = locs(1);
width = round(widths(1));
% max_peak_ind = 650;
% max_peak_ind = 2170;
% width = 100;8
scatter(n0(max_peak_ind),Magnetization_gradient_ave(max_peak_ind))
scatter(n0(max_peak_ind-width),Magnetization_gradient_ave(max_peak_ind-width))
scatter(n0(max_peak_ind+width),Magnetization_gradient_ave(max_peak_ind+width))


baseline_lin_fit = polyfit([n0(max_peak_ind-width) n0(max_peak_ind+width)], [Magnetization_gradient_ave(max_peak_ind-width) Magnetization_gradient_ave(max_peak_ind+width)], 1);
baseline = polyval(baseline_lin_fit, n0(max_peak_ind-width:max_peak_ind+width));

inbetween = [baseline, Magnetization_gradient_ave(max_peak_ind-width:max_peak_ind+width)];
fill(n0(max_peak_ind-width:max_peak_ind+width),inbetween, 'yellow','FaceAlpha',0.3,'LineWidth',1)
hold off
% 
ylabel('m, \mu_B/u.c.')

dx = abs(max(SG_vals,[],'all')-min(SG_vals,[],'all'))/(l);
sum(Magnetization_gradient_ave(max_peak_ind-width:max_peak_ind+width)-baseline).* dx ./ (ac_excitation)
%%
dx = abs(max(SG_vals,[],'all')-min(SG_vals,[],'all'))/(l);
gap_size = zeros(max_x_position_index,max_y_position_index);
gap_position = zeros(max_x_position_index,max_y_position_index);
gap_width = zeros(max_x_position_index,max_y_position_index);
for i = 1:max_x_position_index
    for j = 1:max_y_position_index
        Magnetization_gradient_ave = smoothdata(gradient(-Magnetization(:,i,j)).*ac_excitation./dx,1,'sgolay', 100);
        Magnetization_gradient_ave_masked = Magnetization_gradient_ave;
%         Magnetization_gradient_ave_masked(abs(Magnetization_gradient_ave)<0.01) = 0;
        
        [pks,locs, widths, prom] = findpeaks(-Magnetization_gradient_ave_masked,'SortStr','descend');
        if length(locs) > 0
            max_peak_ind = locs(1);
            width = round(widths(1));
            gap_position(i,j) = max_peak_ind;
            gap_width(i,j) = width;
            left_boundary = max_peak_ind-width;
            right_boundary = max_peak_ind+width;
            if width == max_peak_ind | width > 800 | width <50 |prom(1)<0.06
                gap_size(i,j) = nan;
            elseif left_boundary<1
                left_boundary = 1;
                baseline_lin_fit = polyfit([n0(left_boundary) n0(right_boundary)], [Magnetization_gradient_ave(left_boundary) Magnetization_gradient_ave(right_boundary)], 1);
                baseline = polyval(baseline_lin_fit, n0(left_boundary:right_boundary));
%                 gap_size(i,j) = -sum(Magnetization_gradient_ave(left_boundary:right_boundary)-baseline).* dx ./ (ac_excitation);
                gap_size(i,j) = abs(Magnetization(left_boundary,j,i) - Magnetization(right_boundary,j,i));
            elseif right_boundary>l
                right_boundary = l;
                baseline_lin_fit = polyfit([n0(left_boundary) n0(right_boundary)], [Magnetization_gradient_ave(left_boundary) Magnetization_gradient_ave(right_boundary)], 1);
                baseline = polyval(baseline_lin_fit, n0(left_boundary:right_boundary));
                gap_size(i,j) = abs(Magnetization(left_boundary,j,i) - Magnetization(right_boundary,j,i));
            else
                baseline_lin_fit = polyfit([n0(left_boundary) n0(right_boundary)], [Magnetization_gradient_ave(left_boundary) Magnetization_gradient_ave(right_boundary)], 1);
                baseline = polyval(baseline_lin_fit, n0(left_boundary:right_boundary));
                gap_size(i,j) = abs(Magnetization(left_boundary,j,i) - Magnetization(right_boundary,j,i));
            end
        else
            gap_size(i,j) = nan;
        end
        
        
    end
end

figure(13)
clf
ax(1) = subplot(1,3,1);
gap_figure = imagesc(fliplr(gap_size));
shading interp;
set(gca,'YDir','normal') 
pbaspect([max_y_position_index max_x_position_index 1])
colorbar;
set(gap_figure, 'AlphaData', ~isnan(fliplr(gap_size)))
caxis([0 2.5])
colormap(hot)
set(gca,'xtick',[])
set(gca,'ytick',[])

ax(2) = subplot(1,3,2);
gap__position_figure = imagesc(gap_position);
shading interp;
set(gca,'YDir','normal') 
pbaspect([max_y_position_index max_x_position_index 1])
colorbar;
set(gap__position_figure, 'AlphaData', ~isnan(gap_width))
colormap(ax(2), spring)
% caxis([0 1200])
set(gca,'xtick',[])
set(gca,'ytick',[])

ax(3) = subplot(1,3,3);
frames = [1049 500];
this_dataset = reshape(real(-Magnetization(frames(1),:,:)),max_x_position_index,[]);
this_dataset_bg = reshape(real(-Magnetization(frames(2),:,:)),max_x_position_index,[]);
imagesc(-fliplr(this_dataset-this_dataset_bg))
shading interp; 
set(gca,'YDir','normal') 
pbaspect([max_y_position_index max_x_position_index 1])
    
a= [linspace(0,0.3,5),0.5,linspace(0.7,1,5)]; 
J = customcolormap(a, {'#7f3c0a','#b35807','#e28212','#f9b967','#ffe0b2','#f7f7f5','#d7d9ee','#b3abd2','#8073a9','#562689','#2f004d'});
%     caxis([-limits(i) limits(i)])
caxis([-0.2 1.5])
% colorbar();
colormap(ax(3),(bone))
set(gca,'xtick',[])
set(gca,'ytick',[])
%     box on
set(gca, 'XColor','black')
set(gca, 'YColor','black')
set(gca, 'LineWidth',1)

colormap(ax(1),hot)
%%
f = figure(24);
clf
twist_angle_FCI_corr = zeros(max_x_position_index*max_y_position_index);
twist_angle_list = gap_position';
twist_angle_list = twist_angle_list(:)';
twist_angle_FCI_corr(1,:) = twist_angle_list;

FCI_strength_list = (gap_size)';
FCI_strength_list = FCI_strength_list(:)';
twist_angle_FCI_corr(2,:) = FCI_strength_list;

twist_angle_FCI_corr(1,:) = round(twist_angle_FCI_corr(1,:)./10,0);

unique_twist_angles = unique(twist_angle_FCI_corr(1,:));
unique_twist_angles = sortrows(unique_twist_angles,1);
unique_twist_angles = unique_twist_angles(~isnan(unique_twist_angles));
averaged_FCI_gap = [];
std_FCI_gap = [];
for i = 1:length(unique_twist_angles)
    indices = find(twist_angle_FCI_corr(1,:)==unique_twist_angles(i));
    if length(indices) > 10
        averaged_FCI_gap(i) = mean(twist_angle_FCI_corr(2,indices));
        std_FCI_gap(i) = std(twist_angle_FCI_corr(2,indices));
    else
        averaged_FCI_gap(i) = nan;
        std_FCI_gap(i) = nan;
    end
end
twist_angle_FCI_corr = [unique_twist_angles; averaged_FCI_gap];

errorbar(unique_twist_angles, averaged_FCI_gap, std_FCI_gap,"o")
% scatter(twist_angle_FCI_corr(:,1),twist_angle_FCI_corr(:,2),10)
% xlim([4 4.5])
box on
ax = gca;
ax.LineWidth = 1;
set(gca, 'XColor','black')
set(gca, 'YColor','black')
% twist_angle_FCI_corr_ave = smoothdata(twist_angle_FCI_corr,1,'sgolay', 10);
% hold on
% scatter(twist_angle_FCI_corr_ave(:,1), twist_angle_FCI_corr_ave(:,2),10)

% fit = polyfit(twist_angle_FCI_corr(~isnan(twist_angle_FCI_corr(:,2)),1), twist_angle_FCI_corr(~isnan(twist_angle_FCI_corr(:,2)),2),1)
% y1 = polyval(fit, twist_angle_FCI_corr(:,1));
% hold on
% plot(twist_angle_FCI_corr(:,1),y1)
% xlim([0 max(twist_angle_FCI_corr(:,1))])
% ylim([0 max(twist_angle_FCI_corr(:,2))])
title('Dependence of the ICI position on the twist angle')
xlabel('\theta (deg)')
ylabel('ICI strength (a.u.)')
% xlabel('\deltam_{ICI} (\mu_B/u.c.)')

% factor = 1.0;
% width = 4*factor;
% height = 4*factor;
% set(f,'Units','Inches');
% set(f,'Position',[0 0 width height]);
% set(f,'PaperSize',[width height],'PaperPosition',[0 0 width height]);
