#include "udf.h"

double P[7]={0,300,400,500,600,700,10000};
double V[7]={126.5,126.5,131.3,134.0,136.1,136.5,136.5};

double CAZ11(double x[],double y[],int n,double t)
 {
   int n1,n2,i;
   double z;
   if(x[1]>x[0])
   {
    if(t<=x[0])  
    {
         n1=0;n2=1;
    }
    else
    {
         if(t>=x[n-1])
         {
          n1=n-2;
          n2=n-1;
         }
         else
         {
      for(i=1;i<n;i++)
      {
                 if(t<x[i]) {n1=i-1;n2=i;break;}
      }
         }
        }
   }
   else
   {
     if(t>=x[0])  
    {
         n1=0;n2=1;
    }
    else
    {
         if(t<=x[n-1])
         {
          n1=n-2;
          n2=n-1;
         }
         else
         {
      for(i=1;i<n;i++)
      {
                 if(t>x[i]) {n1=i-1;n2=i;break;}
      }
         }
        }
   }
   z=y[n1]+(y[n2]-y[n1])*(t-x[n1])/(x[n2]-x[n1]);
   return (z);
}


DEFINE_PROFILE(mass_in,t,i)
{
  face_t f;
  real x[ND_ND];
  double m,tm;
  
  tm=CURRENT_TIME-30;
  if(tm<0) tm=0;
  
  if(tm<1)
  {
     m=6.052e-07*(1.0+1.3125*tm);
  }
  else if(tm<2)
  {
     m=6.052e-07*(1.0+1.3125*1+0.19*(tm-1.0));
  } 
  else
  {
      m=6.052e-07*(1.0+1.3125*1+0.19*1);
   }

   begin_f_loop(f,t)
  { 
	   F_PROFILE(f,t,i) =m;
  }
  end_f_loop(f,t)
  return;
}

DEFINE_PROFILE(pump_v,t,i)
{
  face_t f;

  cell_t c0; 
  Thread* tc0;
  double p,v;
  int count;

 
   
  begin_f_loop(f,t)
  { 
	   c0=F_C0(f,t);
       tc0=F_C0_THREAD(f,t);
	   p=C_P(c0,tc0)+360;
	   if(p<300) p=300;
	   if(p>900) p=900;
	   F_PROFILE(f,t,i) =-CAZ11(P,V,7,p)/1000.0/60/0.0004908739;
  }
  end_f_loop(f,t)
  return;
}




