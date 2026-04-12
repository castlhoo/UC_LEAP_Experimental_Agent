clear all

[nnDataX,nnDataY] = meshgrid(0:2e-8:400e-8,0:2e-8:400e-8);

X = zeros(201,201);
x = linspace(0,1,201);
for n=1:201
    X(n,:) = x;
end

M.X = nnDataX;
M.Y = nnDataY;
M.z = X;

M.x = [0 398e-8];
M.y = [398e-8 0];

M_TF_0 = convolveTFSig(M, 215e-9, 50e-9, 0);
M_TF_90 = convolveTFSig(M, 215e-9, 50e-9, 90);

%Stupidly InterpIntegrate and convolveTFSig have different angle
%conventions -_-
M_Int_0 = InterpIntegrate(M_TF_0,90,50e-9);
M_Int_90 = InterpIntegrate(M_TF_90,0,50e-9);

%Plot everything
figure, Plot_nSOT_Mag(M);
figure, Plot_nSOT_Mag(M_TF_0);
figure, Plot_nSOT_Mag(M_Int_0);
figure, Plot_nSOT_Mag(M_TF_90);
figure, Plot_nSOT_Mag(M_Int_90);