% Column 1: Trace (0)/ Retrace (1)
% Column 2: slow axis index
% Column 3: fast axis index
% Column 4: Bottom gate voltage (V)
% Column 5: Top gate voltage (V)
% Column 6: SQUID signal 1wx (V)

nums = [11756:11759];

SQUID_TG_cum_prelim = [];
SQUID_BG_cum_prelim = [];
SQUID_DC_cum_prelim = [];
TG_cum = [];
BG_cum = [];
p0_cum = [];
k = 0;

for i = 1:length(nums)
    num = nums(i);
    dataset = OpenDataVaultFile2(num);
    
    squidSlope = 200; 
    ZurichGain = 500; 
    SR560Gain = 10;
    SR860Sensitivity = 0.005; 
    unit = 1e9; %Desired unit in tesla. 1e6 is uT, 1e9 is nT
    
    
    trace = dataset(dataset(:,1)==0, :);
    retrace = dataset(dataset(:,1)==1, :);
    
    l = max(trace(:,2))+1;
    TG_ind = max(trace(:,3))+1;
    BG = reshape(trace(:,4),l,[]);
    TG = reshape(trace(:,5),l,[]);
    squid_TG_signal = reshape((retrace(:,6)+trace(:,6))/2,l,[])*unit/(squidSlope*SR560Gain)*SR860Sensitivity/10;
    BG_im = BG(1,:);
    TG_im = TG(:,1);
    SQUID_TG_cum_prelim = [SQUID_TG_cum_prelim squid_TG_signal];
    TG_cum = [TG_cum TG];
    BG_cum = [BG_cum BG];
    k = k + length(BG_im);
    
end 

%% Plotting AC BG phase diagram
SQUID_TG_cum = SQUID_TG_cum_prelim;
SQUID_BG_cum = SQUID_BG_cum_prelim;
smooth = 20;
y_im = BG_cum(:,1);
x_im = TG_cum(1,:);

delta = -0.053;

x = BG_cum*(1-delta)+(1+delta)*TG_cum;
y = -BG_cum*(1-delta)+(1+delta)*TG_cum;
n0_density = 3*(x-0.8)*8.85e-12/1.6e-19/33.1e-9*10^-4*1e-12;
y_D = y ./ 33.1*1000;

x_sym_labels = [-12 -9 -6 -3 0];

averaged_squid_signal = movmean(SQUID_TG_cum,smooth,1);
averaged_squid_signal= averaged_squid_signal - mean(averaged_squid_signal(end-200:end,:));
B_field = cumsum(averaged_squid_signal,1);
f = figure(1);
clf
pcolor(x,y_D, movmean(averaged_squid_signal,1))
axis xy;
shading interp;
J = customcolormap_preset('red-white-blue');
x_axis = x_sym_labels./(min(x_im+y_im,[],'all') - max(x_im+y_im,[],'all'))*(min(x,[],'all') - max(x,[],'all'));
xticks(x_axis);
xticklabels(x_sym_labels);
colormap(J)
caxis([-150,150])
xlim([min(min(x)) 0])

xlabel('TG')
ylabel('BG')
xlabel('n_e (x10^{12} cm^{-2})')
xlabel('V_{TG}+V_{BG} (V)')
ylabel('D (mV/nm)')
pbaspect([0-min(min(x)) max(max(y))-min(min(y)) 1])

box on
set(gca, 'LineWidth',1)
set(gca, 'XColor','black')
set(gca, 'YColor','black')


fontsize(f,7,"points")

factor = 1.0;
width =4*factor;
height = 4*factor;
set(f,'Units','Inches');
set(f,'Position',[0 0 width height]);
set(f,'PaperSize',[width height],'PaperPosition',[0 0 width height]);

set(f,'Units','Inches');
set(f,'Position',[0 0 width height]);
set(f,'PaperSize',[width height],'PaperPosition',[0 0 width height]); 
