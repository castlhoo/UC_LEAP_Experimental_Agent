function H=HamiltonianR(kx,ky,t1,t2,t3) 
m=3;
H_0=zeros(m,m);
a0=1;
l1=a0*kx;
l2=a0*(-kx/2+sqrt(3)*ky/2);

a1=-l1/3-2*l2/3;
a2=2*l1/3+l2/3;
a3=-l1/3+l2/3;
%%%%nearest-neighboring hopping
A12=t1*exp(1i*a1)+t2*exp(1i*a2)+t3*exp(1i*a3);
A13=t1*exp(-1i*a3)+t2*exp(-1i*a1)+t3*exp(-1i*a2);
A23=t1*exp(1i*a2)+t2*exp(1i*a3)+t3*exp(1i*a1);

H_0=[0,A12,A13;0,0,A23;0,0,0]; 
H=H_0+H_0';
end