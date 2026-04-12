clear all
close all
clc
para=parameter;
it=0;
for b1=para.t1
    for b2=para.t2
        it=it+1;
      for ix=0:100 %G-M
        kx=pi*ix/100;
        ky=kx/sqrt(3);
        [H]=HamiltonianR(kx,ky,b1,b2,para.t3);
        [V,D]=eig(H);
        for n=1:3
        K(ix+1,1,it)=kx;
        K(ix+1,2,it)=ky;
        E(ix+1,n,it)=D(n,n);
        end
      end
      for ix=101:200  %M-K
        kx=pi-pi*(ix-100)/300;
        ky=-kx*sqrt(3)+4*pi/sqrt(3);
        [H]=HamiltonianR(kx,ky,b1,b2,para.t3);
        [V,D]=eig(H);
        for n=1:3
        K(ix+1,1,it)=(ix-100)*pi/(100*sqrt(3))+pi;
        K(ix+1,2,it)=ky;
        E(ix+1,n,it)=D(n,n);
        end
      end
      for ix=201:300 %K-G
        kx=2*pi/3-pi*(ix-200)/150;
        ky=kx*sqrt(3);
        [H]=HamiltonianR(kx,ky,b1,b2,para.t3);
        [V,D]=eig(H);
        for n=1:3
        K(ix+1,1,it)=(ix-200)*2*pi/(100*sqrt(3))+pi+pi/sqrt(3);
        K(ix+1,2,it)=ky;
        E(ix+1,n,it)=D(n,n);
        end
      end
      T(it,1)=b1;
      T(it,2)=b2;
     end
end
%%%%%%%%%%%%%%%%%%%%%%%
[~,~,Nt]=size(K);

[~,s1]=size(para.t1);[~,s2]=size(para.t2);
 figure(1);
 for in=1:Nt
     b1=T(in,1);b2=T(in,2);
     subplot(s1,s2,in)
     for ib=1:3
      %axis([-pi/3 pi/3 -10 10]);
      plot(K(:,1,in),E(:,ib,in),'r')
      xlim([0 8.583])
      ylim([-0.5 0.6])
      %axis square
      hold on;
      plot([0 8.583],[0 0],'k--')
     end
    %name=['t=','0.1',', t2=','0.005'];
    %title(name)
 end
 
 