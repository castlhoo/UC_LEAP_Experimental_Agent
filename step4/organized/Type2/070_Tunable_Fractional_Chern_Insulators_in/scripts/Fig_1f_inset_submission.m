% Column 1: Trace (0)/ Retrace (1)
% Column 2: slow axis index
% Column 3: fast axis index
% Column 4: Bottom gate voltage (V)
% Column 5: Top gate voltage (V)
% Column 6: n0 voltage (V)
% Column 7: p0 voltage (V)
% Column 8: SQUID signal 1wx (V)
% Column 9: SQUID signal 1wy (V)
% Column 10: SQUID signal DC (V)

nums = [12140:12142];
SQUID1wx_cum = [];
SQUID1wy_cum = [];
SQUID1wx_cum_trace = [];
SQUID1wx_cum_retrace = [];
SQUID_DC_cum = [];
SG_cum = [];
BG_cum = [];
p0_cum = [];
k = 1;
for i = 1:length(nums)
    num = nums(i);
    dataset = OpenDataVaultFile2(num);
    
    SR560GainDC = 20;
    SR560Gain = 10;
    SR860Sensitivity = 0.0005;
    squidSlope = 200;
    unit = 1e9; %Desired unit in tesla. 1e6 is uT, 1e9 is nT
    
    
    trace = dataset(dataset(:,1)==0, :);
    retrace = dataset(dataset(:,1)==1, :);
    
    n0_ind = max(trace(:,2))+1;
    p0_ind = max(trace(:,3))+1;

    n0 = reshape(trace(:,4),n0_ind,[]);
    p0 = reshape(trace(:,5),n0_ind,[]);
    BG = reshape(trace(:,6),n0_ind,[]);
    SG = reshape(trace(:,7),n0_ind,[]);
    SQUID1wx_trace = reshape(trace(:,8),n0_ind,[])*unit/(SR560Gain*squidSlope)*SR860Sensitivity/10;
    SQUID1wx_retrace = reshape(retrace(:,8),n0_ind,[])*unit/(SR560Gain*squidSlope)*SR860Sensitivity/10;
    SQUID1wx = (SQUID1wx_trace + SQUID1wx_retrace)./2;
    SQUID1wy = reshape((trace(:,9)+retrace(:,9))/2,n0_ind,[])*unit/(SR560Gain*squidSlope)*SR860Sensitivity/10;
    SQUID_DC = reshape((trace(:,10)+retrace(:,10))/2,n0_ind,[])*unit/(SR560GainDC*squidSlope);
    n0_im = n0(:,1);
    p0_im = p0(1,:);
    SQUID1wx_cum_trace = [SQUID1wx_cum_trace SQUID1wx_trace];
    SQUID1wx_cum_retrace = [SQUID1wx_cum_retrace SQUID1wx_retrace];
    SQUID1wx_cum = [SQUID1wx_cum SQUID1wx];
    SQUID1wy_cum = [SQUID1wy_cum SQUID1wy];
    SQUID_DC_cum = [SQUID_DC_cum SQUID_DC];
    SG_cum = [SG_cum SG];
    BG_cum = [BG_cum BG];
    p0_cum = [p0_cum p0_im];
    k = k + length(p0_im);
    
end 


%%
f = figure(2);
clf
x = n0_im;
y = p0_cum;

v = (x+0.95)/(8.29-0.95);
n0_density = 3*(x+0.95)*8.85e-12/1.6e-19/33.1e-9*10^-4*1e-12;
y_D = y ./ 33.1*1000;

z_dSG = movmean(SQUID1wx_cum, 25).';
imagesc(n0_density,y_D, z_dSG)
shading interp; axis xy;
J = colormap(customcolormap_preset('red-white-blue'));
title(num2str(num));
h = colorbar;
caxis([-70 70])
pbaspect([max(max(x))-min(min(x)) max(max(y))-min(min(y)) 1])

set(gca,"YTick",[-60 -30 0])
box on
set(gca, 'LineWidth',1)
set(gca, 'XColor','black')
set(gca, 'YColor','black')

fontsize(f,7,"points")

factor = 1.0;
width =2*factor;
height = 2*factor;
set(f,'Units','Inches');
set(f,'Position',[0 0 width height]);
set(f,'PaperSize',[width height],'PaperPosition',[0 0 width height]);

