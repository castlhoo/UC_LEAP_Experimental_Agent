close all

%Define various lengths in nm
TFamp = 400e-9;
height = 140e-9; 
diam = 215e-9;

%Start by deciding the distribution of magnetization
[nnDataX,nnDataY] = meshgrid(0:2e-8:500e-8,0:2e-8:500e-8);

%Simulate a rectangular magnetic distribution that's cut off at the top of
%the image, like the real dataset
%Units are 1 ub / u.c
Moment = zeros(251,251);
Moment(85:165, 75:251) = 1;
Moment(115:135, 145:165) = 0;

%Define a circle, if later desired for various testing purposes
%Moment = padarray(fspecial('disk',50),[75 75]);

%Remember where this number comes from, but presumably 1 spin moment
%density per moire? And it's a density probably?
%Moment = Moment.*4.73816e-8./(max(max(Moment)));
%Moment = Moment.*7.13e-8./(max(max(Moment)));

M.X = nnDataX;
M.Y = nnDataY;
M.z = Moment;
M.x = [M.X(1,1) M.X(end,end)];
M.y = [M.Y(end,end) M.Y(1,1)];

%Convert magnetization to a magnetic field for a given height above the
%sample. 1 means using Gaussan padding to make the dataset an even number
%of data points
B = ConvertMomenttoB(M, height, 1);

%Get the TF signal, taking into account the SQUID diameter, the TF
%oscillation amplitude (not peak to peak), and the angle of the oscillation                                                                     
Btf = convolveTFSig(B, diam, TFamp, 20);

%Extacted data
Bext = InterpIntegrate(Btf,70,TFamp);

Bdiff = B;
Bdiff.z = B.z - Bext.z;

Mext = LowPassFilter(ConvertBtoMoment(Bext,height,diam,1), height, 1); 

Mext.z = Mext.z - Mext.z(1,1);
% 
% %Plot everything
% figure, Plot_nSOT_Mag(M);
% figure, Plot_nSOT_Mag(B);
% figure, Plot_nSOT_Mag(Btf);
% figure, Plot_nSOT_Mag(Bext);
% figure, Plot_nSOT_Mag(Bdiff);
% figure, Plot_nSOT_Mag(Mext);
% 
% 
% 
% 
% %Below is orange for magnetization data
% x= [linspace(0,0.35,5),0.5,linspace(0.65,1,5)]; 
% J = customcolormap(x, {'#7f3c0a','#b35807','#e28212','#f9b967','#ffe0b2','#f7f7f5','#d7d9ee','#b3abd2','#8073a9','#562689','#2f004d'});
% colorbar; colormap(J);
% 
% %Below is purple for DC magnetic field data
% x= [linspace(0,0.4,5),0.5,linspace(0.6,1,5)]; 
% J = customcolormap(x, {'#860454','#C51B7C','#DC75AB','#F0B7DA','#FFDEEF','#F8F7F7','#E5F4D9','#B9E084','#7FBC42','#4D921E','#276418'});
% colorbar; colormap(J);
% 
% %Below is red-blue for TF magnetic field data
% x= [linspace(0,0.35,5),0.5,linspace(0.65,1,5)]; 
% J = customcolormap(x, {'#68011d','#b5172f','#d75f4e','#f7a580','#fedbc9','#f5f9f3','#d5e2f0','#93c5dc','#4295c1','#2265ad','#062e61'});
% colorbar; colormap(J);
