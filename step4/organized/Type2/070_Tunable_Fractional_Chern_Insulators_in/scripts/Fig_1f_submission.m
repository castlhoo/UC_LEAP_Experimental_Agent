% Dataset 12060 
% Column 1: Trace (0)/ Retrace (1)
% Column 2: slow axis index
% Column 3: fast axis index
% Column 4: Bottom gate voltage (V)
% Column 5: Top gate voltage (V)
% Column 6: n0 voltage (V)
% Column 7: p0 voltage (V)
% Column 8: SQUID signal 1wx (V)
% Column 9: SQUID signal DC (V)
%
% Dataset 12061
% Column 1: Trace (0)/ Retrace (1)
% Column 2: slow axis index
% Column 3: fast axis index
% Column 4: Bottom gate voltage (V)
% Column 5: Top gate voltage (V)
% Column 6: SQUID signal 1wx (V)
% Column 7: SQUID signal DC (V)
% 
datanum = 12060;
datanum_BG = 12061;

SR_sensitivity = 0.002;
SR560Gain = 10;
SR560GainDC = 20;
squidSlope = -200; %V/T
unit = 1e9;

dataset = OpenDataVaultFile2(datanum);

trace = dataset(dataset(:,1)==0, :);
retrace = dataset(dataset(:,1)==1, :);

line_ind = max(dataset(:,2))+1;
gate_ind = max(trace(:,3))+1;
BG = reshape(trace(:,4),gate_ind,[]);
TG = reshape(trace(:,5),gate_ind,[]);
n0 = reshape(trace(:,6),gate_ind,[]);
p0 = reshape(trace(:,7),gate_ind,[]);
BG = BG(:,1);
TG = TG(:,1);
n0 = n0(:,1);
SQUID1wx = reshape((trace(:,8)+retrace(:,8))./2,gate_ind,[]).*unit./(squidSlope*SR560Gain)*SR_sensitivity/10;  
SQUID_DC = reshape((trace(:,9)+retrace(:,9))./2,gate_ind,[]).*unit./(SR560GainDC*squidSlope);

dataset = OpenDataVaultFile2(datanum_BG);

line_ind = max(dataset(:,2))+1;

trace = dataset(dataset(:,1)==0, :);
retrace = dataset(dataset(:,1)==1, :);

gate_ind = max(trace(:,3))+1;

SQUID1wx_BG = reshape((trace(:,6)+retrace(:,6))./2,gate_ind,[]).*unit./(squidSlope*SR560Gain)*SR_sensitivity/10;  
SQUID_DC_BG = reshape((trace(:,7)+retrace(:,7))./2,gate_ind,[]).*unit./(SR560GainDC*squidSlope);

%%
i = line_ind;
SQUID1wx_adj = SQUID1wx(:,1:i);
SQUID1wx_BG_adj = SQUID1wx_BG(:,1:i);

SQUID_DC_adj = SQUID_DC(:,1:i);
SQUID_DC_BG_adj = SQUID_DC_BG(:,1:i);


v = (n0+0.982)/(8.29-0.982);
n0_density = 3*(n0+0.982)*8.85e-12/1.6e-19/33.1e-9*10^-4*1e-12;

mean_SQUID1wx = mean(SQUID1wx_adj,2);
mean_SQUID1wx_BG = mean(SQUID1wx_BG_adj,2);

mean_SQUID_DC = mean(SQUID_DC_adj,2);
mean_SQUID_DC_BG = mean(SQUID_DC_BG_adj,2);
mean_SQUID_DC_subtr = mean_SQUID_DC-mean_SQUID_DC_BG;

dx = abs(max(n0)-min(n0))/gate_ind;
ac_excitation = 0.055;

f = figure(8);
clf
t = tiledlayout(1,1);
ax1 = axes(t);

plot(ax1,n0_density, smoothdata(mean_SQUID1wx-mean_SQUID1wx_BG,1,'sgolay',50),'LineWidth',1,'Color', "#8C8246")
ylabel(ax1,'\deltaB_n (nT)')
xlabel(ax1,texlabel('n_e (10^{12} cm^{-2})'));
ax1.YColor = "#8C8246";
xlim(ax1, [min(n0_density) max(n0_density)])
ylim(ax1,[-300 350])
ax2 = axes(t);
plot(ax2,v, (smoothdata(mean_SQUID_DC_subtr,1,'movmean',100)),'LineWidth',1,'Color',"#4E4D6A")

ax2.XAxisLocation = 'top';
ax2.YAxisLocation = 'right';
ax2.YColor = "#4E4D6A";
ax2.Color = 'none';
ax1.Box = 'off';
ax2.Box = 'off';
xlim(ax2, [min(v) max(v)])
ylim(ax2, [-500 1800])
ylabel('B_{DC} (\muT)')
xlabel('\nu')

fontsize(f,7,"points")

factor = 1.0;
width =5.5*factor;
height = 3*factor;
set(f,'Units','Inches');
set(f,'Position',[0 0 width height]);
set(f,'PaperSize',[width height],'PaperPosition',[0 0 width height]);
