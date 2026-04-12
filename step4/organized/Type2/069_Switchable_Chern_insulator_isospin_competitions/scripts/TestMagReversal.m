clear all
close all

%Start by deciding the distribution of magnetization

[nnDataX,nnDataY] = meshgrid(0:2e-8:400e-8,0:2e-8:400e-8);

Moment = padarray(fspecial('disk',50),[50 50]);
%Moment = fspecial('disk',100);
Moment = Moment.*4.73816e-8./(max(max(Moment)));

%Z = zeros(201,201);

%Z(25:175,25:175) = Moment;

M.X = nnDataX;
M.Y = nnDataY;
M.z = Moment;

M.x = [M.X(1,1) M.X(end,end)];
M.y = [M.Y(end,end) M.Y(1,1)];

%Convert magnetization to a magnetic field for a given height above the
%sample
B = ConvertMomenttoB(M, 140e-9,0);

Mrev = ConvertBtoMoment(B, 140e-9, 100e-9, 0);
Mrev.z = Mrev.z - Mrev.z(1,1);

figure, Plot_nSOT_Mag(M);
figure, Plot_nSOT_Mag(Mrev);
% figure, Plot_nSOT_Mag(B);