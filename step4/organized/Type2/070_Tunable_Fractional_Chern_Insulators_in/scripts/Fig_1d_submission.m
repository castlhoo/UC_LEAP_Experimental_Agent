% Column 1: Trace (0)/ Retrace (1)
% Column 2: fast axis index
% Column 3: slow axis index
% Column 4: Bottom gate voltage (V)
% Column 5: Top gate voltage (V)
% Column 6: SQUID signal 1wx (V)
% Column 7: SQUID signal DC (V)

nums = [12068];
SQUID_dn_cum_prelim = [];
SQUID_DC_cum_prelim = [];
SG_cum = [];
BG_cum = [];
p0_cum = [];
k = 1;

for i = 1:length(nums)
    num = nums(i);
    dataset = OpenDataVaultFile2(num);
    
    squidSlope = -500; 
    SR560Gain = 10;
    SR560GainDC = 20;
    SR860Sensitivity = 0.05; 
    unit = 1e9; %Desired unit in tesla. 1e6 is uT, 1e9 is nT
    
    
    trace = dataset(dataset(:,1)==0, :);
    retrace = dataset(dataset(:,1)==1, :);
    
    l = max(trace(:,2))+1;
    TG_ind = max(trace(:,3))+1;
    BG = reshape(trace(:,4),l,[]);
    TG = reshape(trace(:,5),l,[]);
    squid_dn_signal = reshape((retrace(:,6)+trace(:,6))/2,l,[])*unit/(squidSlope*SR560Gain)*SR860Sensitivity/10;
    DC_signal = ((trace(:,7))+(retrace(:,7)))/2;
    squid_DC_signal = reshape(DC_signal,l,[])*unit/(squidSlope*SR560GainDC);
    BG_im = BG(1,:);
    TG_im = TG(:,1);
    SQUID_dn_cum_prelim = [SQUID_dn_cum_prelim squid_dn_signal];
    SQUID_DC_cum_prelim = [SQUID_DC_cum_prelim squid_DC_signal];
    SG_cum = [SG_cum TG];
    BG_cum = [BG_cum BG];
    k = k + length(BG_im);
    
end 

%%
f = figure(1);
clf

SQUID_dn_cum = SQUID_dn_cum_prelim;
SQUID_DC_cum = SQUID_DC_cum_prelim;
smooth = 10;
y = BG_cum(:,1);
x = SG_cum(1,:);

delta = -0.053;

xn0 = BG_cum*(1-delta)+(1+delta)*SG_cum;
yp0 = -BG_cum*(1-delta)+(1+delta)*SG_cum;
v = (x+0.95)/(8.29-0.95);
n0_density = 3*(xn0+0.95)*8.85e-12/1.6e-19/33.1e-9*10^-4*1e-12;
y_D = yp0 ./ 33.1*1000;

averaged_squid_signal = movmean(SQUID_dn_cum,smooth,1);
averaged_squid_signal = movmean(averaged_squid_signal,1,2);
averaged_squid_signal= averaged_squid_signal - mean(averaged_squid_signal(1:100,:));

pcolor(n0_density, y_D, (averaged_squid_signal))
axis xy; 
shading interp;
caxis([-50 50]) 
colormap(customcolormap_preset('red-white-blue'));
box on
set(gca, 'LineWidth',1)
set(gca, 'XColor','black')
set(gca, 'YColor','black')

box on
set(gca, 'LineWidth',1)
set(gca, 'XColor','black')
set(gca, 'YColor','black')

fontsize(f,7,"points")

factor = 1.0;
width =2*factor;
height = 3.5/2*factor;
set(f,'Units','Inches');
set(f,'Position',[0 0 width height]);
set(f,'PaperSize',[width height],'PaperPosition',[0 0 width height]);

