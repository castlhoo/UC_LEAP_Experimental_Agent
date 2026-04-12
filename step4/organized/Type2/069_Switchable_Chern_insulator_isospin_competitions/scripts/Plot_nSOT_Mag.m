function [A] = Plot_nSOT_Mag(data_num, slope, zurich, filter)
%PLOTME2D Summary of this function goes here
%   data_num is either the number of the dataset in data vault or preloaded
%   dataset stored in a structure 
%   slope - if opening from data vault, uses this slope to convert volts to
%   tesla
%   zurich - if opening from data vault, uses this value as the gain on the
%   voltage for the TF reading
%   filter - 0 if you want the data to come out without any spatial
%   filtering

if isa(data_num,'double')
    ZurichGain = zurich; %Gain on the Zurich
    SRGain = 1; %Gain on the SR preamp
    squidSlope = slope; %Sensitivity of SQUID in volts / tesla
    unit = 1; %Desired unit in tesla. 1e6 is uT, 1e9 is nT

    dataset = OpenDataVaultFile(data_num);

    trace = dataset(dataset(:,1) ==0,:);
    retrace = dataset(dataset(:,1) ==1,:);

    l= max(dataset(:,2))+1;

    Axis1 = reshape(trace(:,4),l,[]);
    Axis2 = reshape(trace(:,5),l,[]);
    Axis3 = reshape((trace(:,9)+retrace(:,9))./2,l,[]);

    %1.1 volts to 5.9 microns for x
    %Assuming same for y 

    x = Axis1.*5.333*1e-6;
    y = Axis2.*5.333*1e-6;
    z = Axis3.*unit./(ZurichGain*SRGain*squidSlope);
    
    if filter == 0
        H = [1];
    else
        winsize = 31;
        H = [gausswin(winsize) , gausswin(winsize) , gausswin(winsize)];
        H = H./sum(sum(H));
    end
    z = filter2(H,z);
    
    x = x(50:end-50,3:end-2);
    y = y(50:end-50,3:end-2);
    z = z(50:end-50,3:end-2);
    
    A.X = x;
    A.Y = y;
    
    x = [0 ((A.X(end,1)-A.X(1,1))^2+(A.Y(end,1)-A.Y(1,1))^2)^(1/2)];
    %y is flipped because imagesc by default has weird non cartesan
    %coordinates
    y = [((A.X(1,end)-A.X(1,1))^2+(A.Y(1,end)-A.Y(1,1))^2)^(1/2) 0];
end

if isa(data_num, 'struct')
    x = data_num.x;
    y = data_num.y;
    z = data_num.z;
end

imagesc(x, y, z'); shading flat; hold on
colormap(redblue(500))

bmax = max(max(z));
bmin = abs(min(min(z)));
if bmax>bmin
    caxis([-bmax,bmax])
else
    caxis([-bmin,bmin])
end
axis off; 

h = colorbar;
ylabel(h,'B_{TF} (nT)');
set(gca, 'Layer', 'Top')

aspect = [(x(2)-x(1)) y(1)-y(2) 1];
pbaspect(aspect);

%Length of the scale bar in unit of the specified x axis / y axis. 
%In this case this is in microns
scalebar_length = 1*1e-6;
quiver(x(end)- scalebar_length*1.5, y(1) - scalebar_length*0.25, scalebar_length, 0 ,'ShowArrowHead','off', 'linewidth',3, 'color', [0,0,0])
hold off

A.x = x;
A.y = y;
A.z = z;

end

