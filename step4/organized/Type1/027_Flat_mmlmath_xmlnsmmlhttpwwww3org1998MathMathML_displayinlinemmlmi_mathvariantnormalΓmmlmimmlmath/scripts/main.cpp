/***************************************************************************************
This work is licensed under a Creative Commons BY 4.0 license https://creativecommons.org/licenses/by/4.0/
Copyright (c) 2022-2025, M. Zegrodnik, W Akbar

This code carries out numerical calculations according to Gutzwiller approximation for the t-J-U-V model applied to the description of a flat band of twisted WSe2 bilayer
M. Zegrodnik has developed the main part of the code (t-J-U terms)
W. Akbar has worked on including the V-term in the calculations

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

----------------------------------------------------------------------------------------

data0.dat file provides the initial data for the calculations. 
Run the code with an integer parameter which determines which line of the data0.dat file should be treated as the set of initial parameters.

Compile with the inclusion of GSL library

for example:

g++ -std=c++1y -I/usr/local/include/gsl -L/usr/local/lib main.cpp -lgsl -lgslcblas -lm -Ofast

****************************************************************************************/


#include <cmath>
#include <sstream>
#include <cstring>
#include <string>
#include <iostream>
#include <fstream>

#include <vector>
#include <list>
#include <complex>

#include <gsl/gsl_complex.h>
#include <gsl/gsl_complex_math.h>

#include <gsl/gsl_vector.h>
#include <gsl/gsl_multiroots.h>
#include <gsl/gsl_math.h>
#include <gsl/gsl_errno.h>
#include <gsl/gsl_roots.h>
#include <gsl/gsl_eigen.h>
#include <gsl/gsl_permutation.h>
#include <gsl/gsl_linalg.h>
#include <gsl/gsl_min.h>
#include <gsl/gsl_spline.h>

#define kB 8.617333262e-5    //Boltzmann constant in the units eV/K



using namespace std;



//***************************************************************************************************
//***************************************************************************************************

struct params_sce{

	int Nhop; //number of hoppings in the Hamiltonian
	int NJ;   //number of intersite exchange interactions
	int NP;   //number of unknown normal lines
	int NS;   //number of unknown superconducting lines
	int NEq;  //number of equations
	int Nk;   //number of points in momentum space over which we integrate
	int Nk_dos;   //number of points in momentum space over which we integrate (this is for the calculation of the density of states)
	int nh;   //size of the Hamiltonian matrix

	double h1, h2, h3;              //absolute values of the hopping parameters to fist, second, and third nearest neighbor
	double phi1, phi2, phi3;       //phases of the hopping parameters to the first, second, and third nearest neighbor

	double J;      //intersite exchnage interaction
	double U;      //onsite Coulomb repulsion
	double ntot;   //total number of particles per atomic site
	double V;
	double gv;

	vector <double> *vec_hop;         //table of hopping vectors (size = Nhop)
	vector <double> *vec_P;           //table of vectors representing hopping lines (size = NS)
	vector <double> *vec_S;           //table of vectors representing real space superconducting gaps (size = NP)
	vector <double> *vec_J;           //table of vectors corresponding to the intersite exchange interaction (size = NJ)

	complex<double> *t_up;   // table of hopping values for spin up electrons (size = Nhop)
	complex<double> *t_do;   // table of hopping values for spin down electrons (size = Nhop)

    //stuff needed for the numerical diagonalization (GSL library)
	gsl_matrix_complex *Am;          // = gsl_matrix_complex_alloc(nh, nh);
	gsl_vector *eval;                // = gsl_vector_alloc(nh);
	gsl_matrix_complex *evec;        // = gsl_matrix_complex_alloc(nh, nh);
	gsl_eigen_hermv_workspace * ws;  // = gsl_eigen_hermv_alloc (nh);

	complex <double> EG, E0, EJ, EU, EGmu;

	double T;                        //temperature in K
	double BZ;                       //area of the Brillouin zone (in the units of 1/a)

	//2D tables in which we store the coordinates of the points in k-space (we use this for integration inside the Brillouin zone)
	double **kxtab, **kytab;

	//2D tables in which we store the coordinates of the points in k-space (we use this for integration inside the Brillouin zone)
	//this is for the calculation of the density of states
	double **kxtab_dos, **kytab_dos;

	//double xgg;
};


//***************************************************************************************************
//***************************************************************************************************

//dispersion relation ( tpar - list of hopping parameters, vec_hop - list of vectors to neighbors )
double ek(complex<double>  *tpar, vector<double>  *vec_hop, double kx, double ky, int Nhop){
	complex<double> ekk;

	ekk = 0.0;
	for(int i=0;i<Nhop;i++){
		ekk = ekk + tpar[i]*exp( 1i*(kx*vec_hop[i][0] + ky*vec_hop[i][1]) );
	}

	return ekk.real();
}

//***************************************************************************************************
//***************************************************************************************************

//Superconducting gap, k-dependence (delt - list of hopping parameters, NNLd - list of vectors to neighbors )
//this calculates the gap NOT the complex conjugate of the gap
complex<double> Sk(complex<double> *S, vector<double> *vec_S, double kx, double ky, int NS){
	complex<double> Sk;

	Sk = 0.0;
	for(int i=0;i<NS;i++){
		Sk = Sk + S[i]*exp( 1i*(kx*vec_S[i][0] + ky*vec_S[i][1]) );
	}

	return Sk;
}

//***************************************************************************************************
//***************************************************************************************************

//Superconducting gap, k-dependence (delt - list of hopping parameters, NNLd - list of vectors to neighbors )
//modified version of the Sk function which takes into account all the pairing contributions to the pairing
//originating from the exchange term. This one is for the up-down configuration
//this calculates the gap NOT the complex conjugate of the gap (we do not use this function in this version of the code)
//this calculates the gap NOT the complex conjugate of the gap
complex<double> Skmod(complex<double> *Sud, complex<double> *Sdu, vector<double> *vec_S, double kx, double ky, int NS, double phi){
	complex<double> Sk;

	Sk = 0.0;
	for(int i=0;i<NS;i++){
		Sk = Sk + ( 2*cos(2*phi)*Sud[i] - Sdu[i] )*exp( 1i*(kx*vec_S[i][0] + ky*vec_S[i][1]) );
	}

	return Sk;
}

//***************************************************************************************************
//***************************************************************************************************
//This function calculates the effective hopping parameters within the SGA scheme

void calc_teff(double q, double lmbds, complex<double> *P_up, complex<double> *P_do, complex<double> *teff_up, complex<double> *teff_do, void *params){
	//double q, lmbds;

	complex<double> heff1, heff2, heff3;
	complex<double> cc;
	struct params_sce *p1 = (struct params_sce *) params;


	cc = cos(2*p1->phi1) + 1i*sin(2*p1->phi1);
	//we assume that the exchange interaction term is between the nearest neighbors only
	//so the term which originate from it affects only heff1 effective hopping
	heff1 = q*q*p1->h1*exp(1i*p1->phi1) - p1->J*0.25*pow(lmbds,4)*( 2.*cc*conj(P_do[0]) + conj(P_up[0]) ) + pow(p1->gv, 2)*p1->V*conj(P_up[0]);
	heff2 = q*q*p1->h2*exp(1i*p1->phi2); // - p1->J2*0.25*pow(lmbds,4)*( 2.*cc2*conj(P_do[0]) + conj(P_up[0]) );
	heff3 = q*q*p1->h3*exp(1i*p1->phi3); // - p1->J3*0.25*pow(lmbds,4)*( 2.*cc2*conj(P_do[0]) + conj(P_up[0]) );

	//defining the subsequent effective hopping parameters for spin up
	teff_up[0] =  heff1;
	teff_up[1] =  conj(heff1);
	teff_up[2] =  conj(heff1);
	teff_up[3] =  heff1;
	teff_up[4] =  heff1;
	teff_up[5] =  conj(heff1);

	teff_up[6] =  heff2;
	teff_up[7] =  conj(heff2);
	teff_up[8] =  conj(heff2);
	teff_up[9] =  heff2;
	teff_up[10] =  heff2;
	teff_up[11] =  conj(heff2);

	teff_up[12] =  heff3;
	teff_up[13] =  conj(heff3);
	teff_up[14] =  conj(heff3);
	teff_up[15] =  heff3;
	teff_up[16] =  heff3;
	teff_up[17] =  conj(heff3);

	//defining the subsequent effective hopping parameters for spin down
	teff_do[0] =  conj(heff1);
	teff_do[1] =  heff1;
	teff_do[2] =  heff1;
	teff_do[3] =  conj(heff1);
	teff_do[4] =  conj(heff1);
	teff_do[5] =  heff1;

	teff_do[6] =  conj(heff2);
	teff_do[7] =  heff2;
	teff_do[8] =  heff2;
	teff_do[9] =  conj(heff2);
	teff_do[10] =  conj(heff2);
	teff_do[11] =  heff2;

	teff_do[12] =  conj(heff3);
	teff_do[13] =  heff3;
	teff_do[14] =  heff3;
	teff_do[15] =  conj(heff3);
	teff_do[16] =  conj(heff3);
	teff_do[17] =  heff3;
}

//***************************************************************************************************
//***************************************************************************************************
//This function calculates the effective real-space superconducting gap parameters (NOT their complex conjugates)
void calc_Deff(double lmbds, complex<double> *S_ud, complex<double> *S_du, complex<double> *Deff_ud, complex<double> *Deff_du, double J, void *params){
	complex <double> cc;

	struct params_sce *p1 = (struct params_sce *) params;

	//cc = cos(2*p1->phi1);  // + 1i*sin(2*p1->phi1);

	for(int i=0;i<p1->NS;i++){
		cc = exp( 1i*2.0*arg(p1->t_up[i]) );
		Deff_ud[i] = -pow(lmbds,4)*J*0.5*( 2.*conj(cc)*S_ud[i] - S_du[i] ) - 2.0*pow(p1->gv, 2) * p1->V * S_du[i];
		Deff_du[i] = -pow(lmbds,4)*J*0.5*( 2.*cc*S_du[i] - S_ud[i] ) - 2.0*pow(p1->gv, 2) * p1->V * S_ud[i];
	}

}
//***************************************************************************************************
//***************************************************************************************************

//This function rewrites the hopping lines which are calculated by the self-consistant equations into
//the table with all the hopping lines which correspond to the hopping parameters in the Hamiltonian

void calc_Pt(complex<double> *P_up, complex<double> *P_do, complex<double> *Pt_up, complex<double> *Pt_do){

	//defining the subsequent effective hopping lines for spin up
	Pt_up[0] =  P_up[0];
	Pt_up[1] =  conj(P_up[0]);
	Pt_up[2] =  conj(P_up[0]);
	Pt_up[3] =  P_up[0];
	Pt_up[4] =  P_up[0];
	Pt_up[5] =  conj(P_up[0]);

	Pt_up[6] =  P_up[1];
	Pt_up[7] =  conj(P_up[1]);
	Pt_up[8] =  conj(P_up[1]);
	Pt_up[9] =  P_up[1];
	Pt_up[10] =  P_up[1];
	Pt_up[11] =  conj(P_up[1]);

	Pt_up[12] =  P_up[2];
	Pt_up[13] =  conj(P_up[2]);
	Pt_up[14] =  conj(P_up[2]);
	Pt_up[15] =  P_up[2];
	Pt_up[16] =  P_up[2];
	Pt_up[17] =  conj(P_up[2]);

	//defining the subsequent effective hopping lines for spin down (we assume that time reversal symmetry is conserved)
	Pt_do[0] =  conj(P_up[0]);
	Pt_do[1] =  P_up[0];
	Pt_do[2] =  P_up[0];
	Pt_do[3] =  conj(P_up[0]);
	Pt_do[4] =  conj(P_up[0]);
	Pt_do[5] =  P_up[0];

	Pt_do[6] =  conj(P_up[1]);
	Pt_do[7] =  P_up[1];
	Pt_do[8] =  P_up[1];
	Pt_do[9] =  conj(P_up[1]);
	Pt_do[10] =  conj(P_up[1]);
	Pt_do[11] =  P_up[1];

	Pt_do[12] =  conj(P_up[2]);
	Pt_do[13] =  P_up[2];
	Pt_do[14] =  P_up[2];
	Pt_do[15] =  conj(P_up[2]);
	Pt_do[16] =  conj(P_up[2]);
	Pt_do[17] =  P_up[2];
}

 //***************************************************************************************************
//***************************************************************************************************

//prints dispersion relation to file
void ek_to_file( complex<double>  *tpar, vector<double> *vec_hop, const char * filename, int Nd, int Nhop ){
	double xx, yy;

	ofstream fout;
	fout.open(filename);

	for(int j=0;j<Nd;j++){
		for(int i=0;i<Nd;i++){
			xx = -M_PI*4.0/3.0 + j*(2.0*M_PI*4.0/3.0)/Nd  ;
			yy = -2.0*sqrt(3.0)*M_PI/3.0 + i*(2.0*2.0*sqrt(3.0)*M_PI/3.0)/Nd;
			if( xx>-yy/sqrt(3.0)-4.0*M_PI/3.0 && xx<yy/sqrt(3.0)+4.0*M_PI/3.0 && xx>yy/sqrt(3.0)-4.0*M_PI/3.0 && xx<-yy/sqrt(3.0)+4.0*M_PI/3.0 ){
				fout<<xx<<"\t"<<yy<<"\t"<<ek(tpar, vec_hop, xx, yy, Nhop)<<endl;
			}
		}
		fout<<endl;
	}
	fout.close();
}

//***************************************************************************************************
//***************************************************************************************************

//prints the k-dependence of the SC gap to file
void Sk_to_file(complex<double> *S, vector<double> *vec_S, const char * filename, int Nd, int NS ){
	double xx, yy;

	ofstream fout;
	fout.open(filename);

	for(int j=0;j<Nd;j++){
		for(int i=0;i<Nd;i++){
			xx = -M_PI*4.0/3.0 + j*(2.0*M_PI*4.0/3.0)/Nd  ;
			yy = -2.0*sqrt(3.0)*M_PI/3.0 + i*(2.0*2.0*sqrt(3.0)*M_PI/3.0)/Nd;
			if( xx>-yy/sqrt(3.0)-4.0*M_PI/3.0 && xx<yy/sqrt(3.0)+4.0*M_PI/3.0 && xx>yy/sqrt(3.0)-4.0*M_PI/3.0 && xx<-yy/sqrt(3.0)+4.0*M_PI/3.0 ){
				fout<<xx<<"\t"<<yy<<"\t"<<Sk(S, vec_S, xx, yy, NS).real()<<"\t"<<Sk(S, vec_S, xx, yy, NS).imag()<<endl;
			}
		}
		fout<<endl;
	}
	fout.close();
}

//***************************************************************************************************
//***************************************************************************************************
//This function calculates the singlet and triplet contributions to the pairing and are written in the tables delt_s and delt_t, respectively
//the size of the delt_s and delt_t tables has to be equal to NS/2
void calc_delt_singlet_triplet(gsl_vector *x, int NS, int NP, complex<double> *delt_s, complex<double> *delt_t){
	int j;

	j = 0;
	for(int i=0;i<NS;i=i+2){  //the signs in the singlet and triplet contributions here are correct (checked)
		delt_s[j] = gsl_vector_get(x, 2*NP + i) + 1i*gsl_vector_get(x, 2*NP + NS + i) + gsl_vector_get(x, 2*NP + 1 + i) + 1i*gsl_vector_get(x, 2*NP + NS + 1 + i);
		delt_t[j] = gsl_vector_get(x, 2*NP + i) + 1i*gsl_vector_get(x, 2*NP + NS + i) - gsl_vector_get(x, 2*NP + 1 + i) - 1i*gsl_vector_get(x, 2*NP + NS + 1 + i);
		j++;
	}
}
//***************************************************************************************************
//***************************************************************************************************

void calc_delt_complex(gsl_vector *x, int NS, int NP, complex<double> *delt_ud_c, complex<double> *delt_du_c){

	for(int i=0;i<NS;i++){  //the signs in the singlet and triplet contributions here are correct (checked)
		delt_ud_c[i] = gsl_vector_get(x, 2*NP + i) + 1i*gsl_vector_get(x, 2*NP + NS + i);
	}
	delt_du_c[1] = -delt_ud_c[0];
	delt_du_c[0] = -delt_ud_c[1];

	delt_du_c[3] = -delt_ud_c[2];
	delt_du_c[2] = -delt_ud_c[3];

	delt_du_c[5] = -delt_ud_c[4];
	delt_du_c[4] = -delt_ud_c[5];


}
//***************************************************************************************************
//***************************************************************************************************
//this function calculates the effective gap parameters based on the mean field SC gaps
void calc_delt_eff_complex(gsl_vector *x, int NS, int NP, complex<double> *delt_eff_ud, complex<double> *delt_eff_du, void *params){
	complex<double> delt_ud_c[NS];
	complex<double> delt_du_c[NS];
	double lmbds, ntot, xg;

	struct params_sce *p1 = (struct params_sce *) params;

    ntot = p1->ntot;
    xg = -1.0 / pow((0.5*ntot),2);           //we get rid of the double hole occupancies
    lmbds = sqrt( 1. + xg * (0.5*ntot-1.)*0.5*ntot );

	for(int i=0;i<NS;i++){  //the signs in the singlet and triplet contributions here are correct (checked)
		delt_ud_c[i] = gsl_vector_get(x, 2*NP + i) + 1i*gsl_vector_get(x, 2*NP + NS + i);
	}
	delt_du_c[1] = -delt_ud_c[0];
	delt_du_c[0] = -delt_ud_c[1];

	delt_du_c[3] = -delt_ud_c[2];
	delt_du_c[2] = -delt_ud_c[3];

	delt_du_c[5] = -delt_ud_c[4];
	delt_du_c[4] = -delt_ud_c[5];

	calc_Deff(lmbds, delt_ud_c, delt_du_c, delt_eff_ud, delt_eff_du, p1->J, p1);

}
//***************************************************************************************************
//***************************************************************************************************

void calc_delt_sym(int NS, int NP, int N_sym, double *tet_tab, complex<double> *delt_ud_c, complex<double> *delt_du_c, complex<double> *delt_ud_sym, complex<double> *delt_du_sym){
	double tet;

		for(int k=0;k<N_sym;k++){
			delt_ud_sym[k] = 0.0;
			delt_du_sym[k] = 0.0;
			for(int l=0;l<N_sym;l++){
				tet = k*tet_tab[l];
				delt_ud_sym[k] = delt_ud_sym[k] + exp(-1i*tet)*delt_ud_c[l];
				delt_du_sym[k] = delt_du_sym[k] + exp(-1i*tet)*delt_du_c[l];
			}
		}
}
//***************************************************************************************************
//***************************************************************************************************

void calc_delt_sym_spin(int N_sym, complex<double> *delt_ud_sym, complex<double> *delt_du_sym, complex<double> *delt_s, complex<double> *delt_t){

	for(int k=0;k<N_sym;k++){
		delt_s[k] = delt_ud_sym[k] - delt_du_sym[k];
		delt_t[k] = delt_ud_sym[k] + delt_du_sym[k];
	}
}

//***************************************************************************************************
//***************************************************************************************************

//Fermi-Dirac distribution
double FD(double ene, double T){
	return 1.0/(exp(ene/(kB*T))+1.0);
}

//***************************************************************************************************
//***************************************************************************************************

void cpy_matrix_complex(gsl_matrix_complex *mat_gsl, complex<double> **mat_cpp, int n){

	for(int i=0;i<n;i++){
		for(int j=0;j<n;j++){
			mat_cpp[i][j] = GSL_REAL(gsl_matrix_complex_get( mat_gsl, i, j)) + 1i*GSL_IMAG(gsl_matrix_complex_get( mat_gsl, i, j));
		}
	}
}

//***************************************************************************************************
//***************************************************************************************************

void cpy_vector_double(gsl_vector *vec_gsl, double *vec_cpp, int n){
	for(int i=0;i<n;i++){
		vec_cpp[i] = gsl_vector_get( vec_gsl, i);
	}
}

//***************************************************************************************************
//***************************************************************************************************
//with this function we calculate the q parameter using x and ntot
void calc_var(double ntot, double x, double *var_tab){
	double lmbd0, lmbds, lmbdd, q, gv;

	//we calculate the lambda and q parameters using x and ntot
	lmbd0 = sqrt( 1. + x * pow(0.5*ntot, 2) );
	lmbds = sqrt( 1. + x * (0.5*ntot-1.)*0.5*ntot );
	lmbdd = sqrt( 1. + x * pow((1.0 - 0.5*ntot),2) );      //sqrt( 1. + x * (1. - ntot + pow(0.5*ntot, 2)) );
	q = lmbds * lmbdd * 0.5*ntot + lmbds * lmbd0 * (1.0 - 0.5*ntot);
	gv = 1 + x*0.5*ntot*(1.0 - 0.5*ntot);

	var_tab[0] = lmbd0;
	var_tab[1] = lmbds;
	var_tab[2] = lmbdd;
	var_tab[3] = q;
	var_tab[4] = gv;
}
//***************************************************************************************************
//***************************************************************************************************
//This function minimizes the energy of the system with respect to the variational parameter x (we do not use that in this version of the code)
double minimize_energy(double a0, double b0, double x0, void *params, double (*fene)(double x, void *params)){
	double a, b, x;
	int status;
	int iter = 0, max_iter = 100;
	const gsl_min_fminimizer_type *T;
	gsl_min_fminimizer *s;
	gsl_function F;

	F.function = fene;
	F.params = params;


	T = gsl_min_fminimizer_quad_golden;
	s = gsl_min_fminimizer_alloc (T);
	gsl_min_fminimizer_set (s, &F, x0, a0, b0);

	do{
		iter++;
	    status = gsl_min_fminimizer_iterate (s);

	    x = gsl_min_fminimizer_x_minimum (s);
	    a = gsl_min_fminimizer_x_lower (s);
	    b = gsl_min_fminimizer_x_upper (s);

	    status = gsl_min_test_interval (a, b, 0.001, 0.0);


	}while (status == GSL_CONTINUE && iter < max_iter);

	gsl_min_fminimizer_free (s);

	return x;
}
//***************************************************************************************************
//***************************************************************************************************
// This function calculates the energy of the system together with the contribution from the chemical potential term
double fene (double x, double mu, complex<double> *P_up, complex<double> *P_do, \
		complex<double> *Pt_up, complex<double> *Pt_do, complex<double> *S_ud, complex<double> *S_du, void * params){

	complex<double> Ene, cc;

	double lmbds, lmbd0, lmbdd, q, gv;

	struct params_sce *p1 = (struct params_sce *) params;

	lmbd0 = sqrt( 1. + x * pow(0.5*p1->ntot, 2) );
	lmbds = sqrt( 1. + x * ( 0.5*p1->ntot-1.)*0.5*p1->ntot );
	lmbdd = sqrt( 1. + x * pow((1.0 - 0.5*p1->ntot),2) );
	q = lmbds * lmbdd * 0.5*p1->ntot + lmbds * lmbd0 * (1.0 - 0.5*p1->ntot);
	gv = 1 + x*0.5*p1->ntot*(1.0 - 0.5*p1->ntot);


	Ene = 0.0 + 1i*0.0;
	p1->EG = 0.0 + 1i*0.0;
	p1->E0 = 0.0 + 1i*0.0;
	p1->EJ = 0.0 + 1i*0.0;

	//the kinetic energy term
	for(int i=0; i<p1->Nhop; i++){

		Ene = Ene + q*q * p1->t_up[i] * Pt_up[i];
		Ene = Ene + q*q * p1->t_do[i] * Pt_do[i];

		p1->E0 = p1->E0 + q*q * p1->t_up[i] * Pt_up[i];
		p1->E0 = p1->E0 + q*q * p1->t_do[i] * Pt_do[i];
	}

	//the onsite Coulomb repulsion term
	Ene = Ene + p1->U * pow(lmbdd,2) * pow(0.5*p1->ntot,2);
	p1->EU = p1->EU + p1->U * pow(lmbdd,2) * pow(0.5*p1->ntot,2);


	//the intersite Coulomb repulsion term (we assume that we take the same interaction neighbors for the V-term as for the J-term)
	for(int i=0; i<p1->NJ; i++){
		Ene = Ene + p1->V * pow(gv,2) * ( norm(S_ud[i]) + norm(S_du[i]) - norm(Pt_up[i]) - norm(Pt_do[i]) );
	}
	Ene = Ene + p1->V * 4.0 * 6.0 * pow(0.5*p1->ntot,2);

	//the exchange interaction term (here every pairing line and hopping line is transformed to the ij order (not ji))
	for(int i=0; i<p1->NJ; i++){
		cc = exp( 1i*2.0*arg(p1->t_up[i]) );
		Ene = Ene - p1->J * 0.25 * pow(lmbds,4) * ( - 2.*cc * conj(S_ud[i]) * S_du[i] + conj(S_du[i]) * S_du[i] );
		Ene = Ene - p1->J * 0.25 * pow(lmbds,4) * ( - 2.*conj(cc) * conj(S_du[i]) * S_ud[i] + conj(S_ud[i]) * S_ud[i] );

		Ene = Ene - p1->J * 0.25 * pow(lmbds,4) * ( 2.*cc * conj(Pt_do[i]) * Pt_up[i] + conj(Pt_up[i]) * Pt_up[i] );
		Ene = Ene - p1->J * 0.25 * pow(lmbds,4) * ( 2.*conj(cc) * conj(Pt_up[i]) * Pt_do[i] + conj(Pt_do[i]) * Pt_do[i] );

		p1->EJ = p1->EJ - p1->J * 0.25 * pow(lmbds,4) * ( - 2.*cc * conj(S_ud[i]) * S_du[i] + conj(S_du[i]) * S_du[i] );
		p1->EJ = p1->EJ - p1->J * 0.25 * pow(lmbds,4) * ( - 2.*conj(cc) * conj(S_du[i]) * S_ud[i] + conj(S_ud[i]) * S_ud[i] );

		p1->EJ = p1->EJ - p1->J * 0.25 * pow(lmbds,4) * ( 2.*cc * conj(Pt_do[i]) * Pt_up[i] + conj(Pt_up[i]) * Pt_up[i] );
		p1->EJ = p1->EJ - p1->J * 0.25 * pow(lmbds,4) * ( 2.*conj(cc) * conj(Pt_up[i]) * Pt_do[i] + conj(Pt_do[i]) * Pt_do[i] );
	}

	p1->EG = Ene;


	Ene = Ene - mu * p1->ntot;

	p1->EGmu = Ene;

	//return Ene.imag();
	return Ene.real();
}

//***************************************************************************************************
//***************************************************************************************************
//function which calculates the number of particles in the non-correlated state
//This is not used in this version of the code because n0 = nG in the zeroth order expansion (SGA)
double calc_ntot_0(double ns0min, double ns0max, double (*func_n0)(double n0, void *params), void *params){
	int status;
	int iter = 0, max_iter = 100;
	const gsl_root_fsolver_type *T;
	double x_lo, x_hi, r;
	gsl_root_fsolver *s;


	gsl_function F;

	struct params_sce *p1 = (struct params_sce *) params;

	x_lo = ns0min;
	x_hi = ns0max;

	F.function = func_n0;
	F.params = p1;

	T = gsl_root_fsolver_bisection;

	s = gsl_root_fsolver_alloc (T);
	gsl_root_fsolver_set (s, &F, x_lo, x_hi);


	do{
		iter++;
	    status = gsl_root_fsolver_iterate (s);
	    r = gsl_root_fsolver_root (s);
	    x_lo = gsl_root_fsolver_x_lower (s);
	    x_hi = gsl_root_fsolver_x_upper (s);
	    status = gsl_root_test_interval (x_lo, x_hi, 0, 0.001);


	}
	while (status == GSL_CONTINUE && iter < max_iter);

	gsl_root_fsolver_free (s);

	return r;
}
//***************************************************************************************************
//***************************************************************************************************
void pair_density_to_file (const gsl_vector * x, void *params, const char * filename){

	ofstream fout;
	fout.open(filename);


    double kx, ky;
	double mu, mueff;                 // chemical potential and effective chemical potential
	double xg;                        // the x variational parameters
	double lmbds, lmbdd, lmbd0, q;    // variational parameters (they all depend on x)

	double ntot, ntot_new;            //total number of particles per atomic site

	complex<double> *P_up, *P_do;     // table of  lines which correspond to the hopping values for spin up/down electrons (size = NP)
	complex<double> *Pt_up, *Pt_do;   // table of all the lines which correspond to the hopping values for spin up/down electrons (size = Nhop)

	complex<double> *S_ud, *S_du;     // table of real-space superconducting gaps (up, down) and (down, up)  (size = NS)

	complex<double> *teff_up, *teff_do;    // table of effective hopping values for spin up/down electrons (size = Nhop)
	complex<double> *Deff_du, *Deff_ud;    // table of effective superconducting gaps (down, up) and (up, down)

	complex<double> *S_ud_new, *S_du_new;    // table of real-space superconducting gaps (up, down) and (down, up)  (size = NS)
	complex<double> *P_up_new, *P_do_new;    // table of lines which correspond to the hopping values for spin up/down electrons (size = NP)

	double *eval_c;                  // table of eigenvalues in standard c++ variables
	complex<double> **evec_c;        // matrix of eigenvectors in standard c++ variables



	double nupk, ndok, nup, ndo;      // number of particles with spin up and down, respectively
	complex <double> Skud, Skdu;     // pairing expectation values in k-space for up-down and down-up pairing
	complex <double> cc;
	double ekup, ekdo, emkup, emkdo;  // dispersion relations for spin up/down and k/-k momenta
	complex <double> dkud, dkdu;      // k-dependant superconducting gap for (up,down) and (down,up) configurations

	struct params_sce *p1 = (struct params_sce *) params;  //structure which contains all the parameters

	double **kxtab, **kytab;   // tables with kx and ky coordinates inside the Brillouin zone (we will use that for the numerical integration)

	int Nk, nh;     // number of points over which we integrate (Nk) and size of the Hamiltonian matrix (nh)
	double T, BZ;    // temperature and the area of the Brillouin zone



	kxtab = p1->kxtab;
	kytab = p1->kytab;
	ntot = p1->ntot;

	Nk = p1->Nk;
	nh = p1->nh;
	T = p1->T;
	BZ = p1->BZ;


	P_do = new complex<double>[p1->NP];
	P_up = new complex<double>[p1->NP];

	Pt_do = new complex<double>[p1->Nhop];
	Pt_up = new complex<double>[p1->Nhop];

	S_du = new complex<double>[p1->NS];
	S_ud = new complex<double>[p1->NS];

	teff_up = new complex<double>[p1->Nhop];
	teff_do = new complex<double>[p1->Nhop];

	Deff_du = new complex<double>[p1->NS];
	Deff_ud = new complex<double>[p1->NS];

	S_ud_new = new complex<double>[p1->NS];
	S_du_new = new complex<double>[p1->NS];

	P_up_new = new complex<double>[p1->NP];
	P_do_new = new complex<double>[p1->NP];


	//matrix of eigenvectors as standard c++ type
	evec_c = new complex<double>*[nh];
	for(int i=0;i<nh;i++){
		evec_c[i] = new complex<double>[nh];
	}

	//vector of eigenvalues as standard c++ type
	eval_c = new double[nh];


	//copying the chemical potential and the x-variational parameter from the x vector
	mu = gsl_vector_get(x, 2*p1->NP + 2*p1->NS);
	xg = gsl_vector_get(x, 2*p1->NP + 2*p1->NS + 1);


	//copying the values of the gaps from x to the S_ud and S_du tables
	for(int i=0;i<p1->NS;i++){
		S_ud[i] = gsl_vector_get(x, 2*p1->NP + i) + 1i*gsl_vector_get(x, 2*p1->NP + p1->NS + i);
	}

	S_du[1] = -S_ud[0];
	S_du[0] = -S_ud[1];

	S_du[3] = -S_ud[2];
	S_du[2] = -S_ud[3];

	S_du[5] = -S_ud[4];
	S_du[4] = -S_ud[5];


	p1->gv = 1 + xg*0.5*ntot*(1.0 - 0.5*ntot); // corrected (V-term)


	//copying the values of the hopping lines from x to the P_up and P_do tables
	for(int i=0;i<p1->NP;i++){
		P_up[i] = gsl_vector_get(x, i) + 1i*gsl_vector_get(x, p1->NP + i);
		P_do[i] = gsl_vector_get(x, i) - 1i*gsl_vector_get(x, p1->NP + i);
	}

	//we calculate the lambda and q parameters using xg and ntot
	lmbd0 = sqrt( 1. + xg * pow(0.5*ntot, 2) );
	lmbds = sqrt( 1. + xg * (0.5*ntot-1.)*0.5*ntot );
	lmbdd = sqrt( 1. + xg * pow((1.0 - 0.5*ntot),2) );
	q = lmbds * lmbdd * 0.5*ntot + lmbds * lmbd0 * (1.0 - 0.5*ntot);

	//zeroing the variables which are going to be used during the numerical integration (summation)
	nupk = 0.0;
	ndok = 0.0;
	nup = 0.0;
	ndo = 0.0;
	Skud = 0.0;
	Skdu = 0.0;

	for(int i=0;i<p1->NS;i++){
		S_du_new[i] = 0.0;
		S_ud_new[i] = 0.0;
	}

	for(int i=0;i<p1->NP;i++){
		P_up_new[i] = 0.0;
		P_do_new[i] = 0.0;
	}


	//integration over the Brillouin zone
	for(int j=0;j<p1->Nk;j++){
		for(int i=0;i<p1->Nk;i++){

			kx = -1.5*M_PI + j*(3.0*M_PI)/p1->Nk;
			ky = -1.5*M_PI + i*(3.0*M_PI)/p1->Nk;

			//filling the Hamiltonian matrix
			for(int jm=0; jm<nh; jm++){
				for(int im=0; im<nh; im++){
					gsl_matrix_complex_set( p1->Am, jm, im, gsl_complex_rect (0.0, 0.0) );
				}
			}
			//calculating the effective hopping parameters using the variational parameters q and lmbds as well as the hopping lines
			calc_teff(q, lmbds, P_up, P_do, teff_up, teff_do, p1);   //the function changes the teff_up and teff_do tables

			//calculating the effective dispersion relations
			ekup = ek(teff_up, p1->vec_hop, kx, ky, p1->Nhop);
			ekdo = ek(teff_do, p1->vec_hop, kx, ky, p1->Nhop);

			emkup = ek(teff_up, p1->vec_hop, -kx, -ky, p1->Nhop);
			emkdo = ek(teff_do, p1->vec_hop, -kx, -ky, p1->Nhop);

			//calculating the effective chemical potential
			//mueff = mu * ( pow(lmbds,2) - 2.0*( pow(lmbds,2) - pow(lmbdd,2) )*0.5*ntot ) - p1->U*pow(lmbdd,2)*0.5*ntot;
			mueff = mu - p1->U*pow(lmbdd,2)*0.5*ntot - 6.0*p1->V*ntot;

			//diagonal elements of the Hamiltonian matrix (dispersion relations)
			gsl_matrix_complex_set( p1->Am, 0, 0, gsl_complex_rect (0.5*(ekup - mueff), 0.0) );
			gsl_matrix_complex_set( p1->Am, 1, 1, gsl_complex_rect (0.5*(ekdo - mueff), 0.0) );
			gsl_matrix_complex_set( p1->Am, 2, 2, gsl_complex_rect (-0.5*(emkup - mueff), 0.0) );
			gsl_matrix_complex_set( p1->Am, 3, 3, gsl_complex_rect (-0.5*(emkdo - mueff), 0.0) );

			//calculating the effective gap amplitudes in real space using the variational parameter lmbds as well as the superconducting lines
			calc_Deff(lmbds, S_ud, S_du, Deff_ud, Deff_du, p1->J, p1);    //the function changes the Deff_ud and Deff_du tables

			//k-dependent superconducting gaps
			dkud =  Sk(Deff_ud, p1->vec_S, kx, ky, p1->NS);
			dkdu =  Sk(Deff_du, p1->vec_S, kx, ky, p1->NS);

			//off-diagonal elements (SC gaps)
			gsl_matrix_complex_set( p1->Am, 0, 3, gsl_complex_rect ( 0.5*dkdu.real(), 0.5*dkdu.imag() ));
			gsl_matrix_complex_set( p1->Am, 1, 2, gsl_complex_rect ( 0.5*dkud.real(), 0.5*dkud.imag() ));
			gsl_matrix_complex_set( p1->Am, 2, 1, gsl_complex_rect ( 0.5*dkud.real(), -0.5*dkud.imag() ));
			gsl_matrix_complex_set( p1->Am, 3, 0, gsl_complex_rect ( 0.5*dkdu.real(), -0.5*dkdu.imag() ));


			//numerical diagonalization
			gsl_eigen_hermv (p1->Am, p1->eval, p1->evec, p1->ws);

			//we copy the eigenvalues and eigenvectors from the gsl type of variables to the standard c++ type of variables
			cpy_matrix_complex(p1->evec, evec_c, nh);
			cpy_vector_double(p1->eval, eval_c, nh);


			//calculating the k-dependence of the anomalous superconducting expectation values for up,down and down, up configuration
			Skdu = 0.0;
			Skdu = Skdu + conj(evec_c[3][0])*evec_c[0][0] * FD( eval_c[0], T );
			Skdu = Skdu + conj(evec_c[3][1])*evec_c[0][1] * FD( eval_c[1], T );
			Skdu = Skdu - conj(evec_c[3][2])*evec_c[0][2] * FD( -eval_c[2], T );
			Skdu = Skdu - conj(evec_c[3][3])*evec_c[0][3] * FD( -eval_c[3], T );
			Skdu = Skdu + conj(evec_c[3][2])*evec_c[0][2];
			Skdu = Skdu + conj(evec_c[3][3])*evec_c[0][3];

			Skud = 0.0;
			Skud = Skud + conj(evec_c[2][0])*evec_c[1][0] * FD( eval_c[0], T );
			Skud = Skud + conj(evec_c[2][1])*evec_c[1][1] * FD( eval_c[1], T );
			Skud = Skud - conj(evec_c[2][2])*evec_c[1][2] * FD( -eval_c[2], T );
			Skud = Skud - conj(evec_c[2][3])*evec_c[1][3] * FD( -eval_c[3], T );
			Skud = Skud + conj(evec_c[2][2])*evec_c[1][2];
			Skud = Skud + conj(evec_c[2][3])*evec_c[1][3];


			fout<<kx<<"\t"<<ky<<"\t"<<abs(Skdu)<<"\t"<<abs(Skud)<<"\t"<<abs(Skud-Skdu)<<"\t"<<abs(Skud+Skdu)<<endl;

		}
		fout<<endl;
	}
	
	delete[] P_do;
	delete[] P_up;
	delete[] Pt_up;
	delete[] Pt_do;
	delete[] S_ud;
	delete[] S_du;

	delete[] teff_up;
	delete[] teff_do;
	delete[] Deff_ud;
	delete[] Deff_du;

	delete[] P_do_new;
	delete[] P_up_new;
	delete[] S_ud_new;
	delete[] S_du_new;

	for(int i=0;i<nh;i++){
		delete[] evec_c[i];
	}
	delete[] evec_c;

	delete[] eval_c;


}
//***************************************************************************************************
//***************************************************************************************************
//***************************************************************************************************
//***************************************************************************************************

int self_consistant_eqs (const gsl_vector * x, void *params, gsl_vector * f){

	double mu, mueff;                 // chemical potential and effective chemical potential
	double xg;                        // the x variational parameters
	double lmbds, lmbdd, lmbd0, q;    // variational parameters (they all depend on x)

	double ntot, ntot_new;            //total number of particles per atomic site

	complex<double> *P_up, *P_do;     // table of  lines which correspond to the hopping values for spin up/down electrons (size = NP)
	complex<double> *Pt_up, *Pt_do;   // table of all the lines which correspond to the hopping values for spin up/down electrons (size = Nhop)

	complex<double> *S_ud, *S_du;     // table of real-space superconducting gaps (up, down) and (down, up)  (size = NS)

	complex<double> *teff_up, *teff_do;    // table of effective hopping values for spin up/down electrons (size = Nhop)
	complex<double> *Deff_du, *Deff_ud;    // table of effective superconducting gaps (down, up) and (up, down)

	complex<double> *S_ud_new, *S_du_new;    // table of real-space superconducting gaps (up, down) and (down, up)  (size = NS)
	complex<double> *P_up_new, *P_do_new;    // table of lines which correspond to the hopping values for spin up/down electrons (size = NP)

	double *eval_c;                  // table of eigenvalues in standard c++ variables
	complex<double> **evec_c;        // matrix of eigenvectors in standard c++ variables



	double nupk, ndok, nup, ndo;      // number of particles with spin up and down, respectively
	complex <double> Skud, Skdu;     // pairing expectation values in k-space for up-down and down-up pairing
	complex <double> cc;
	double ekup, ekdo, emkup, emkdo;  // dispersion relations for spin up/down and k/-k momenta
	complex <double> dkud, dkdu;      // k-dependant superconducting gap for (up,down) and (down,up) configurations

	struct params_sce *p1 = (struct params_sce *) params;  //structure which contains all the parameters

	double **kxtab, **kytab;   // tables with kx and ky coordinates inside the Brillouin zone (we will use that for the numerical integration)

	int Nk, nh;     // number of points over which we integrate (Nk) and size of the Hamiltonian matrix (nh)
	double T, BZ;    // temperature and the area of the Brillouin zone



	kxtab = p1->kxtab;
	kytab = p1->kytab;
	ntot = p1->ntot;

	Nk = p1->Nk;
	nh = p1->nh;
	T = p1->T;
	BZ = p1->BZ;


	P_do = new complex<double>[p1->NP];
	P_up = new complex<double>[p1->NP];

	Pt_do = new complex<double>[p1->Nhop];
	Pt_up = new complex<double>[p1->Nhop];

	S_du = new complex<double>[p1->NS];
	S_ud = new complex<double>[p1->NS];

	teff_up = new complex<double>[p1->Nhop];
	teff_do = new complex<double>[p1->Nhop];

	Deff_du = new complex<double>[p1->NS];
	Deff_ud = new complex<double>[p1->NS];

	S_ud_new = new complex<double>[p1->NS];
	S_du_new = new complex<double>[p1->NS];

	P_up_new = new complex<double>[p1->NP];
	P_do_new = new complex<double>[p1->NP];


	//matrix of eigenvectors as standard c++ type
	evec_c = new complex<double>*[nh];
	for(int i=0;i<nh;i++){
		evec_c[i] = new complex<double>[nh];
	}

	//vector of eigenvalues as standard c++ type
	eval_c = new double[nh];


	//copying the chemical potential and the x-variational parameter from the x vector
	mu = gsl_vector_get(x, 2*p1->NP + 2*p1->NS);
	xg = gsl_vector_get(x, 2*p1->NP + 2*p1->NS + 1);



	//copying the values of the gaps from x to the S_ud and S_du tables
	for(int i=0;i<p1->NS;i++){
		S_ud[i] = gsl_vector_get(x, 2*p1->NP + i) + 1i*gsl_vector_get(x, 2*p1->NP + p1->NS + i);
	}

	S_du[1] = -S_ud[0];
	S_du[0] = -S_ud[1];

	S_du[3] = -S_ud[2];
	S_du[2] = -S_ud[3];

	S_du[5] = -S_ud[4];
	S_du[4] = -S_ud[5];


	p1->gv = 1 + xg*0.5*ntot*(1.0 - 0.5*ntot); // corrected (V-term)


	//copying the values of the hopping lines from x to the P_up and P_do tables
	for(int i=0;i<p1->NP;i++){
		P_up[i] = gsl_vector_get(x, i) + 1i*gsl_vector_get(x, p1->NP + i);
		P_do[i] = gsl_vector_get(x, i) - 1i*gsl_vector_get(x, p1->NP + i);
	}

	//we calculate the lambda and q parameters using xg and ntot
	lmbd0 = sqrt( 1. + xg * pow(0.5*ntot, 2) );
	lmbds = sqrt( 1. + xg * (0.5*ntot-1.)*0.5*ntot );
	lmbdd = sqrt( 1. + xg * pow((1.0 - 0.5*ntot),2) );
	q = lmbds * lmbdd * 0.5*ntot + lmbds * lmbd0 * (1.0 - 0.5*ntot);

	//zeroing the variables which are going to be used during the numerical integration (summation)
	nupk = 0.0;
	ndok = 0.0;
	nup = 0.0;
	ndo = 0.0;
	Skud = 0.0;
	Skdu = 0.0;

	for(int i=0;i<p1->NS;i++){
		S_du_new[i] = 0.0;
		S_ud_new[i] = 0.0;
	}

	for(int i=0;i<p1->NP;i++){
		P_up_new[i] = 0.0;
		P_do_new[i] = 0.0;
	}


	//integration over the Brillouin zone
	for(int j=0;j<p1->Nk;j++){
		for(int i=0;i<p1->Nk;i++){

			//filling the Hamiltonian matrix
			for(int jm=0; jm<nh; jm++){
				for(int im=0; im<nh; im++){
					gsl_matrix_complex_set( p1->Am, jm, im, gsl_complex_rect (0.0, 0.0) );
				}
			}
			//calculating the effective hopping parameters using the variational parameters q and lmbds as well as the hopping lines
			calc_teff(q, lmbds, P_up, P_do, teff_up, teff_do, p1);   //the function changes the teff_up and teff_do tables

			//calculating the effective dispersion relations
			ekup = ek(teff_up, p1->vec_hop, kxtab[i][j], kytab[j][i], p1->Nhop);
			ekdo = ek(teff_do, p1->vec_hop, kxtab[i][j], kytab[j][i], p1->Nhop);

			emkup = ek(teff_up, p1->vec_hop, -kxtab[i][j], -kytab[j][i], p1->Nhop);
			emkdo = ek(teff_do, p1->vec_hop, -kxtab[i][j], -kytab[j][i], p1->Nhop);

			//calculating the effective chemical potential
			//mueff = mu * ( pow(lmbds,2) - 2.0*( pow(lmbds,2) - pow(lmbdd,2) )*0.5*ntot ) - p1->U*pow(lmbdd,2)*0.5*ntot;
			mueff = mu - p1->U*pow(lmbdd,2)*0.5*ntot - 6.0*p1->V*ntot;

			//diagonal elements of the Hamiltonian matrix (dispersion relations)
			gsl_matrix_complex_set( p1->Am, 0, 0, gsl_complex_rect (0.5*(ekup - mueff), 0.0) );
			gsl_matrix_complex_set( p1->Am, 1, 1, gsl_complex_rect (0.5*(ekdo - mueff), 0.0) );
			gsl_matrix_complex_set( p1->Am, 2, 2, gsl_complex_rect (-0.5*(emkup - mueff), 0.0) );
			gsl_matrix_complex_set( p1->Am, 3, 3, gsl_complex_rect (-0.5*(emkdo - mueff), 0.0) );

			//calculating the effective gap amplitudes in real space using the variational parameter lmbds as well as the superconducting lines
			calc_Deff(lmbds, S_ud, S_du, Deff_ud, Deff_du, p1->J, p1);    //the function changes the Deff_ud and Deff_du tables

			//k-dependent superconducting gaps
			dkud =  Sk(Deff_ud, p1->vec_S, kxtab[i][j], kytab[j][i], p1->NS);
			dkdu =  Sk(Deff_du, p1->vec_S, kxtab[i][j], kytab[j][i], p1->NS);

			//off-diagonal elements (SC gaps)
			gsl_matrix_complex_set( p1->Am, 0, 3, gsl_complex_rect ( 0.5*dkdu.real(), 0.5*dkdu.imag() ));
			gsl_matrix_complex_set( p1->Am, 1, 2, gsl_complex_rect ( 0.5*dkud.real(), 0.5*dkud.imag() ));
			gsl_matrix_complex_set( p1->Am, 2, 1, gsl_complex_rect ( 0.5*dkud.real(), -0.5*dkud.imag() ));
			gsl_matrix_complex_set( p1->Am, 3, 0, gsl_complex_rect ( 0.5*dkdu.real(), -0.5*dkdu.imag() ));


			//numerical diagonalization
			gsl_eigen_hermv (p1->Am, p1->eval, p1->evec, p1->ws);

			//we copy the eigenvalues and eigenvectors from the gsl type of variables to the standard c++ type of variables
			cpy_matrix_complex(p1->evec, evec_c, nh);
			cpy_vector_double(p1->eval, eval_c, nh);

			//calculating the number of particles for spin up and down for a given k
			nupk = 0.0;
			nupk = nupk + norm( evec_c[0][0] ) * FD( eval_c[0], T );
			nupk = nupk + norm( evec_c[0][1] ) * FD( eval_c[1], T );
			nupk = nupk - norm( evec_c[0][2] ) * FD( -eval_c[2], T );
			nupk = nupk - norm( evec_c[0][3] ) * FD( -eval_c[3], T );
			nupk = nupk + norm( evec_c[0][2] );
			nupk = nupk + norm( evec_c[0][3] );

			ndok = 0.0;
			ndok = ndok + norm( evec_c[1][0] ) * FD( eval_c[0], T );
			ndok = ndok + norm( evec_c[1][1] ) * FD( eval_c[1], T );
			ndok = ndok - norm( evec_c[1][2] ) * FD( -eval_c[2], T );
			ndok = ndok - norm( evec_c[1][3] ) * FD( -eval_c[3], T );
			ndok = ndok + norm( evec_c[1][2] );
			ndok = ndok + norm( evec_c[1][3] );


			//calculating the number of particles for spin up and spin down - summation over the Brillouin zone
			nup = nup + nupk;
			ndo = ndo + ndok;

			for(int ip=0;ip<p1->NP;ip++){
				P_up_new[ip] = P_up_new[ip] + exp( 1i*(kxtab[i][j]*p1->vec_P[ip][0] + kytab[j][i]*p1->vec_P[ip][1] ) )*nupk;
				P_do_new[ip] = P_do_new[ip] + exp( 1i*(kxtab[i][j]*p1->vec_P[ip][0] + kytab[j][i]*p1->vec_P[ip][1] ) )*ndok;
			}

			//calculating the k-dependence of the anomalous superconducting expectation values for up,down and down, up configuration
			Skdu = 0.0;
			Skdu = Skdu + conj(evec_c[3][0])*evec_c[0][0] * FD( eval_c[0], T );
			Skdu = Skdu + conj(evec_c[3][1])*evec_c[0][1] * FD( eval_c[1], T );
			Skdu = Skdu - conj(evec_c[3][2])*evec_c[0][2] * FD( -eval_c[2], T );
			Skdu = Skdu - conj(evec_c[3][3])*evec_c[0][3] * FD( -eval_c[3], T );
			Skdu = Skdu + conj(evec_c[3][2])*evec_c[0][2];
			Skdu = Skdu + conj(evec_c[3][3])*evec_c[0][3];

			Skud = 0.0;
			Skud = Skud + conj(evec_c[2][0])*evec_c[1][0] * FD( eval_c[0], T );
			Skud = Skud + conj(evec_c[2][1])*evec_c[1][1] * FD( eval_c[1], T );
			Skud = Skud - conj(evec_c[2][2])*evec_c[1][2] * FD( -eval_c[2], T );
			Skud = Skud - conj(evec_c[2][3])*evec_c[1][3] * FD( -eval_c[3], T );
			Skud = Skud + conj(evec_c[2][2])*evec_c[1][2];
			Skud = Skud + conj(evec_c[2][3])*evec_c[1][3];


			for(int is=0;is<p1->NS;is++){
				S_du_new[is] = S_du_new[is] + exp( 1i*(kxtab[i][j]*p1->vec_S[is][0] + kytab[j][i]*p1->vec_S[is][1] ) )*Skdu;
				S_ud_new[is] = S_ud_new[is] + exp( 1i*(kxtab[i][j]*p1->vec_S[is][0] + kytab[j][i]*p1->vec_S[is][1] ) )*Skud;
			}

		}
	}
	nup = nup*BZ/(Nk*Nk);
	nup = nup/BZ;
	//cout<<"nup = "<<nup<<endl;

	ndo = ndo*BZ/(Nk*Nk);
	ndo = ndo/BZ;
	//cout<<"ndo = "<<ndo<<endl;

	ntot_new = nup + ndo;


	for(int i=0;i<p1->NS;i++){
		S_du_new[i] = (1.0/(Nk*Nk)) * S_du_new[i];
		S_ud_new[i] = (1.0/(Nk*Nk)) * S_ud_new[i];
	}

	for(int i=0;i<p1->NP;i++){
		P_do_new[i] = (1.0/(Nk*Nk)) * P_do_new[i];
		P_up_new[i] = (1.0/(Nk*Nk)) * P_up_new[i];
	}


	Skdu = (BZ/(Nk*Nk))*Skdu;
	Skdu = Skdu/BZ;

	Skud = (BZ/(Nk*Nk))*Skud;
	Skud = Skud/BZ;


	//equations for the hopping lines
	for(int i=0;i<p1->NP;i++){
		gsl_vector_set (f, i, (P_up[i] - P_up_new[i]).real() );
		gsl_vector_set (f, p1->NP + i, (P_up[i] - P_up_new[i]).imag() );
	}

	//equations for the superconducting lines
	for(int i=0;i<p1->NS;i++){
		gsl_vector_set (f, 2*p1->NP + i, (S_ud[i] - S_ud_new[i]).real() );
		gsl_vector_set (f, 2*p1->NP + p1->NS + i, (S_ud[i] - S_ud_new[i]).imag() );
	}

	//equations for the chemical potential
	gsl_vector_set (f, 2*p1->NP + 2*p1->NS, ntot - ntot_new );

	//equation for the variational parameter x
	//numerical derivative
	double dF, dx;

	calc_Pt(P_up, P_do, Pt_up, Pt_do);  //we calculate all the lines (Pt) by using the lines from the self-consistent equations (P)
	dx = 0.0001;


	dF = ( fene(xg + dx, mu, P_up, P_do, Pt_up, Pt_do, S_ud, S_du, p1) - fene(xg - dx, mu, P_up, P_do, Pt_up, Pt_do, S_ud, S_du, p1) )/(2.0*dx);

	gsl_vector_set (f, 2*p1->NP + 2*p1->NS + 1, dF );  


	double Ene;

	Ene = fene (xg, mu, P_up, P_do, Pt_up, Pt_do, S_ud, S_du, p1);



	delete[] P_do;
	delete[] P_up;
	delete[] Pt_up;
	delete[] Pt_do;
	delete[] S_ud;
	delete[] S_du;

	delete[] teff_up;
	delete[] teff_do;
	delete[] Deff_ud;
	delete[] Deff_du;

	delete[] P_do_new;
	delete[] P_up_new;
	delete[] S_ud_new;
	delete[] S_du_new;

	for(int i=0;i<nh;i++){
		delete[] evec_c[i];
	}
	delete[] evec_c;

	delete[] eval_c;

	return GSL_SUCCESS;
}
//***************************************************************************************************
//***************************************************************************************************

double calc_chern (const gsl_vector * x, void *params){

	double mu, mueff;                 // chemical potential and effective chemical potential
	double xg;                        // the x variational parameters
	double lmbds, lmbdd, lmbd0, q;    // variational parameters (they all depend on x)

	double ntot, ntot_new;            //total number of particles per atomic site

	complex<double> *P_up, *P_do;     // table of  lines which correspond to the hopping values for spin up/down electrons (size = NP)
	complex<double> *Pt_up, *Pt_do;   // table of all the lines which correspond to the hopping values for spin up/down electrons (size = Nhop)

	complex<double> *S_ud, *S_du;     // table of real-space superconducting gaps (up, down) and (down, up)  (size = NS)

	complex<double> *teff_up, *teff_do;    // table of effective hopping values for spin up/down electrons (size = Nhop)
	complex<double> *Deff_du, *Deff_ud;    // table of effective superconducting gaps (down, up) and (up, down)

	complex<double> *S_ud_new, *S_du_new;    // table of real-space superconducting gaps (up, down) and (down, up)  (size = NS)
	complex<double> *P_up_new, *P_do_new;    // table of lines which correspond to the hopping values for spin up/down electrons (size = NP)

	double *eval_c1, *eval_c2, *eval_c3, *eval_c4;                  // table of eigenvalues in standard c++ variables
	complex<double> **evec_c1, **evec_c2, **evec_c3, **evec_c4;        // matrix of eigenvectors in standard c++ variables

    complex <double> M12[2][2], M23[2][2], M34[2][2], M41[2][2];
    complex <double> e_phi, u12, u23, u34, u41;
    double phi;



	double nupk, ndok, nup, ndo;      // number of particles with spin up and down, respectively
	complex <double> Skud, Skdu;     // pairing expectation values in k-space for up-down and down-up pairing
	complex <double> cc;
	double ekup, ekdo, emkup, emkdo;  // dispersion relations for spin up/down and k/-k momenta
	complex <double> dkud, dkdu;      // k-dependant superconducting gap for (up,down) and (down,up) configurations

	struct params_sce *p1 = (struct params_sce *) params;  //structure which contains all the parameters

	double **kxtab, **kytab;   // tables with kx and ky coordinates inside the Brillouin zone (we will use that for the numerical integration)

	int Nk, nh;     // number of points over which we integrate (Nk) and size of the Hamiltonian matrix (nh)
	double T, BZ;    // temperature and the area of the Brillouin zone

	kxtab = p1->kxtab;
	kytab = p1->kytab;
	ntot = p1->ntot;

	Nk = p1->Nk;
	nh = p1->nh;
	T = p1->T;
	BZ = p1->BZ;


	P_do = new complex<double>[p1->NP];
	P_up = new complex<double>[p1->NP];

	Pt_do = new complex<double>[p1->Nhop];
	Pt_up = new complex<double>[p1->Nhop];

	S_du = new complex<double>[p1->NS];
	S_ud = new complex<double>[p1->NS];

	teff_up = new complex<double>[p1->Nhop];
	teff_do = new complex<double>[p1->Nhop];

	Deff_du = new complex<double>[p1->NS];
	Deff_ud = new complex<double>[p1->NS];

	S_ud_new = new complex<double>[p1->NS];
	S_du_new = new complex<double>[p1->NS];

	P_up_new = new complex<double>[p1->NP];
	P_do_new = new complex<double>[p1->NP];


	//matrix of eigenvectors as standard c++ type
	evec_c1 = new complex<double>*[nh];
	for(int i=0;i<nh;i++){
		evec_c1[i] = new complex<double>[nh];
	}

	//vector of eigenvalues as standard c++ type
	eval_c1 = new double[nh];

	//matrix of eigenvectors as standard c++ type
	evec_c2 = new complex<double>*[nh];
	for(int i=0;i<nh;i++){
		evec_c2[i] = new complex<double>[nh];
	}

	//vector of eigenvalues as standard c++ type
	eval_c2 = new double[nh];

	//matrix of eigenvectors as standard c++ type
	evec_c3 = new complex<double>*[nh];
	for(int i=0;i<nh;i++){
		evec_c3[i] = new complex<double>[nh];
	}

	//vector of eigenvalues as standard c++ type
	eval_c3 = new double[nh];

	//matrix of eigenvectors as standard c++ type
	evec_c4 = new complex<double>*[nh];
	for(int i=0;i<nh;i++){
		evec_c4[i] = new complex<double>[nh];
	}

	//vector of eigenvalues as standard c++ type
	eval_c4 = new double[nh];


	//copying the chemical potential and the x-variational parameter from the x vector
	mu = gsl_vector_get(x, 2*p1->NP + 2*p1->NS);
	xg = gsl_vector_get(x, 2*p1->NP + 2*p1->NS + 1);

	//xg = -1.0 / pow((1.0 - 0.5*ntot),2);   //we get rid of the double electron occupancies
	//xg = -1.0 / pow((0.5*ntot),2);           //we get rid of the double hole occupancies


	//copying the values of the gaps from x to the S_ud and S_du tables
	for(int i=0;i<p1->NS;i++){
		S_ud[i] = gsl_vector_get(x, 2*p1->NP + i) + 1i*gsl_vector_get(x, 2*p1->NP + p1->NS + i);
		//cout<<S_ud[i]<<endl;
	}

	S_du[1] = -S_ud[0];
	S_du[0] = -S_ud[1];

	S_du[3] = -S_ud[2];
	S_du[2] = -S_ud[3];

	S_du[5] = -S_ud[4];
	S_du[4] = -S_ud[5];

	p1->gv = 1 + xg*0.5*ntot*(1 - 0.5*ntot); // Assuming ns is calculated elsewhere

	//copying the values of the hopping lines from x to the P_up and P_do tables
	for(int i=0;i<p1->NP;i++){
		P_up[i] = gsl_vector_get(x, i) + 1i*gsl_vector_get(x, p1->NP + i);
		P_do[i] = gsl_vector_get(x, i) - 1i*gsl_vector_get(x, p1->NP + i);
	}



	//we calculate the lambda and q parameters using xg and ntot
	lmbd0 = sqrt( 1. + xg * pow(0.5*ntot, 2) );
	lmbds = sqrt( 1. + xg * (0.5*ntot-1.)*0.5*ntot );
	lmbdd = sqrt( 1. + xg * pow((1.0 - 0.5*ntot),2) );
	q = lmbds * lmbdd * 0.5*ntot + lmbds * lmbd0 * (1.0 - 0.5*ntot);

	//zeroing the variables which are going to be used during the numerical integration (summation)
	nupk = 0.0;
	ndok = 0.0;
	nup = 0.0;
	ndo = 0.0;
	Skud = 0.0;
	Skdu = 0.0;

	for(int i=0;i<p1->NS;i++){
		S_du_new[i] = 0.0;
		S_ud_new[i] = 0.0;
	}

	for(int i=0;i<p1->NP;i++){
		P_up_new[i] = 0.0;
		P_do_new[i] = 0.0;
	}


	ofstream ffout;
	ffout.open("data_tst.dat");



	phi = 0.0;
	//integration over the Brillouin zone
	for(int j=0;j<p1->Nk-1;j++){
		for(int i=0;i<p1->Nk-1;i++){

			//**************************************************************************************************
			//filling the Hamiltonian matrix with zeros initially
			for(int jm=0; jm<nh; jm++){
				for(int im=0; im<nh; im++){
					gsl_matrix_complex_set( p1->Am, jm, im, gsl_complex_rect (0.0, 0.0) );
				}
			}
			//**************************************************************************************************
			//calculating the effective hopping parameters using the variational parameters q and lmbds as well as the hopping lines
			calc_teff(q, lmbds, P_up, P_do, teff_up, teff_do, p1);   //the function changes the teff_up and teff_do tables

			//calculating the effective dispersion relations
			ekup = ek(teff_up, p1->vec_hop, kxtab[i][j], kytab[j][i], p1->Nhop);
			ekdo = ek(teff_do, p1->vec_hop, kxtab[i][j], kytab[j][i], p1->Nhop);

			emkup = ek(teff_up, p1->vec_hop, -kxtab[i][j], -kytab[j][i], p1->Nhop);
			emkdo = ek(teff_do, p1->vec_hop, -kxtab[i][j], -kytab[j][i], p1->Nhop);


			//calculating the effective chemical potential
			mueff = mu - p1->U*pow(lmbdd,2)*0.5*ntot - 6.0*p1->V*ntot;

			//diagonal elements of the Hamiltonian matrix (dispersion relations)
			gsl_matrix_complex_set( p1->Am, 0, 0, gsl_complex_rect (0.5*(ekup - mueff), 0.0) );
			gsl_matrix_complex_set( p1->Am, 1, 1, gsl_complex_rect (0.5*(ekdo - mueff), 0.0) );
			gsl_matrix_complex_set( p1->Am, 2, 2, gsl_complex_rect (-0.5*(emkup - mueff), 0.0) );
			gsl_matrix_complex_set( p1->Am, 3, 3, gsl_complex_rect (-0.5*(emkdo - mueff), 0.0) );

			//calculating the effective gap amplitudes in real space using the variational parameter lmbds as well as the superconducting lines
			calc_Deff(lmbds, S_ud, S_du, Deff_ud, Deff_du, p1->J, p1);    //the function changes the Deff_ud and Deff_du tables


			dkud = Sk(Deff_ud, p1->vec_S, kxtab[i][j], kytab[j][i], p1->NS);
			dkdu = Sk(Deff_du, p1->vec_S, kxtab[i][j], kytab[j][i], p1->NS);

			//off-diagonal elements (SC gaps)
			gsl_matrix_complex_set( p1->Am, 0, 3, gsl_complex_rect ( 0.5*dkdu.real(), 0.5*dkdu.imag() ));
			gsl_matrix_complex_set( p1->Am, 1, 2, gsl_complex_rect ( 0.5*dkud.real(), 0.5*dkud.imag() ));
			gsl_matrix_complex_set( p1->Am, 2, 1, gsl_complex_rect ( 0.5*dkud.real(), -0.5*dkud.imag() ));
			gsl_matrix_complex_set( p1->Am, 3, 0, gsl_complex_rect ( 0.5*dkdu.real(), -0.5*dkdu.imag() ));


			//numerical diagonalization
			gsl_eigen_hermv (p1->Am, p1->eval, p1->evec, p1->ws);
			gsl_eigen_hermv_sort(p1->eval, p1->evec, GSL_EIGEN_SORT_VAL_ASC);

			//we copy the eigenvalues and eigenvectors from the gsl type of variables to the standard c++ type of variables
			cpy_matrix_complex(p1->evec, evec_c1, nh);
			cpy_vector_double(p1->eval, eval_c1, nh);


			//**************************************************************************************************
			//filling the Hamiltonian matrix with zeros initially
			for(int jm=0; jm<nh; jm++){
				for(int im=0; im<nh; im++){
					gsl_matrix_complex_set( p1->Am, jm, im, gsl_complex_rect (0.0, 0.0) );
				}
			}
			//**************************************************************************************************

			//calculating the effective hopping parameters using the variational parameters q and lmbds as well as the hopping lines
			calc_teff(q, lmbds, P_up, P_do, teff_up, teff_do, p1);   //the function changes the teff_up and teff_do tables

			//calculating the effective dispersion relations
			ekup = ek(teff_up, p1->vec_hop, kxtab[i][j+1], kytab[j+1][i], p1->Nhop);
			ekdo = ek(teff_do, p1->vec_hop, kxtab[i][j+1], kytab[j+1][i], p1->Nhop);

			emkup = ek(teff_up, p1->vec_hop, -kxtab[i][j+1], -kytab[j+1][i], p1->Nhop);
			emkdo = ek(teff_do, p1->vec_hop, -kxtab[i][j+1], -kytab[j+1][i], p1->Nhop);

			//calculating the effective chemical potential
			//mueff = mu * ( pow(lmbds,2) - 2.0*( pow(lmbds,2) - pow(lmbdd,2) )*0.5*ntot ) - p1->U*pow(lmbdd,2)*0.5*ntot;
			mueff = mu - p1->U*pow(lmbdd,2)*0.5*ntot - 6.0*p1->V*ntot;

			//diagonal elements of the Hamiltonian matrix (dispersion relations)
			gsl_matrix_complex_set( p1->Am, 0, 0, gsl_complex_rect (0.5*(ekup - mueff), 0.0) );
			gsl_matrix_complex_set( p1->Am, 1, 1, gsl_complex_rect (0.5*(ekdo - mueff), 0.0) );
			gsl_matrix_complex_set( p1->Am, 2, 2, gsl_complex_rect (-0.5*(emkup - mueff), 0.0) );
			gsl_matrix_complex_set( p1->Am, 3, 3, gsl_complex_rect (-0.5*(emkdo - mueff), 0.0) );

			//calculating the effective gap amplitudes in real space using the variational parameter lmbds as well as the superconducting lines
			calc_Deff(lmbds, S_ud, S_du, Deff_ud, Deff_du, p1->J, p1);    //the function changes the Deff_ud and Deff_du tables


			dkud = Sk(Deff_ud, p1->vec_S, kxtab[i][j+1], kytab[j+1][i], p1->NS);
			dkdu = Sk(Deff_du, p1->vec_S, kxtab[i][j+1], kytab[j+1][i], p1->NS);

			//off-diagonal elements (SC gaps)
			gsl_matrix_complex_set( p1->Am, 0, 3, gsl_complex_rect ( 0.5*dkdu.real(), 0.5*dkdu.imag() ));
			gsl_matrix_complex_set( p1->Am, 1, 2, gsl_complex_rect ( 0.5*dkud.real(), 0.5*dkud.imag() ));
			gsl_matrix_complex_set( p1->Am, 2, 1, gsl_complex_rect ( 0.5*dkud.real(), -0.5*dkud.imag() ));
			gsl_matrix_complex_set( p1->Am, 3, 0, gsl_complex_rect ( 0.5*dkdu.real(), -0.5*dkdu.imag() ));

			//numerical diagonalization
			gsl_eigen_hermv (p1->Am, p1->eval, p1->evec, p1->ws);
			gsl_eigen_hermv_sort(p1->eval, p1->evec, GSL_EIGEN_SORT_VAL_ASC);


			//we copy the eigenvalues and eigenvectors from the gsl type of variables to the standard c++ type of variables
			cpy_matrix_complex(p1->evec, evec_c2, nh);
			cpy_vector_double(p1->eval, eval_c2, nh);


			//**************************************************************************************************
			//filling the Hamiltonian matrix with zeros initially
			for(int jm=0; jm<nh; jm++){
				for(int im=0; im<nh; im++){
					gsl_matrix_complex_set( p1->Am, jm, im, gsl_complex_rect (0.0, 0.0) );
				}
			}
			//**************************************************************************************************
			//calculating the effective hopping parameters using the variational parameters q and lmbds as well as the hopping lines
			calc_teff(q, lmbds, P_up, P_do, teff_up, teff_do, p1);   //the function changes the teff_up and teff_do tables

			//calculating the effective dispersion relations
			ekup = ek(teff_up, p1->vec_hop, kxtab[i+1][j+1], kytab[j+1][i+1], p1->Nhop);
			ekdo = ek(teff_do, p1->vec_hop, kxtab[i+1][j+1], kytab[j+1][i+1], p1->Nhop);

			emkup = ek(teff_up, p1->vec_hop, -kxtab[i+1][j+1], -kytab[j+1][i+1], p1->Nhop);
			emkdo = ek(teff_do, p1->vec_hop, -kxtab[i+1][j+1], -kytab[j+1][i+1], p1->Nhop);

			//calculating the effective chemical potential
			mueff = mu - p1->U*pow(lmbdd,2)*0.5*ntot - 6.0*p1->V*ntot;

			//diagonal elements of the Hamiltonian matrix (dispersion relations)
			gsl_matrix_complex_set( p1->Am, 0, 0, gsl_complex_rect (0.5*(ekup - mueff), 0.0) );
			gsl_matrix_complex_set( p1->Am, 1, 1, gsl_complex_rect (0.5*(ekdo - mueff), 0.0) );
			gsl_matrix_complex_set( p1->Am, 2, 2, gsl_complex_rect (-0.5*(emkup - mueff), 0.0) );
			gsl_matrix_complex_set( p1->Am, 3, 3, gsl_complex_rect (-0.5*(emkdo - mueff), 0.0) );

			//calculating the effective gap amplitudes in real space using the variational parameter lmbds as well as the superconducting lines
			calc_Deff(lmbds, S_ud, S_du, Deff_ud, Deff_du, p1->J, p1);    //the function changes the Deff_ud and Deff_du tables

			//k-dependent superconducting gaps
			//dkud = -p1->J * Sk(Deff_ud, p1->vec_S, kxtab[i][j], kytab[j][i], p1->NS);
			//dkdu = -p1->J * Sk(Deff_du, p1->vec_S, kxtab[i][j], kytab[j][i], p1->NS);

			dkud = Sk(Deff_ud, p1->vec_S, kxtab[i+1][j+1], kytab[j+1][i+1], p1->NS);
			dkdu = Sk(Deff_du, p1->vec_S, kxtab[i+1][j+1], kytab[j+1][i+1], p1->NS);

			//off-diagonal elements (SC gaps)
			gsl_matrix_complex_set( p1->Am, 0, 3, gsl_complex_rect ( 0.5*dkdu.real(), 0.5*dkdu.imag() ));
			gsl_matrix_complex_set( p1->Am, 1, 2, gsl_complex_rect ( 0.5*dkud.real(), 0.5*dkud.imag() ));
			gsl_matrix_complex_set( p1->Am, 2, 1, gsl_complex_rect ( 0.5*dkud.real(), -0.5*dkud.imag() ));
			gsl_matrix_complex_set( p1->Am, 3, 0, gsl_complex_rect ( 0.5*dkdu.real(), -0.5*dkdu.imag() ));

			//numerical diagonalization
			gsl_eigen_hermv (p1->Am, p1->eval, p1->evec, p1->ws);
			gsl_eigen_hermv_sort(p1->eval, p1->evec, GSL_EIGEN_SORT_VAL_ASC);


			//we copy the eigenvalues and eigenvectors from the gsl type of variables to the standard c++ type of variables
			cpy_matrix_complex(p1->evec, evec_c3, nh);
			cpy_vector_double(p1->eval, eval_c3, nh);


			//**************************************************************************************************
			//filling the Hamiltonian matrix with zeros initially
			for(int jm=0; jm<nh; jm++){
				for(int im=0; im<nh; im++){
					gsl_matrix_complex_set( p1->Am, jm, im, gsl_complex_rect (0.0, 0.0) );
				}
			}
			//**************************************************************************************************
			//calculating the effective hopping parameters using the variational parameters q and lmbds as well as the hopping lines
			calc_teff(q, lmbds, P_up, P_do, teff_up, teff_do, p1);   //the function changes the teff_up and teff_do tables

			//calculating the effective dispersion relations
			ekup = ek(teff_up, p1->vec_hop, kxtab[i+1][j], kytab[j][i+1], p1->Nhop);
			ekdo = ek(teff_do, p1->vec_hop, kxtab[i+1][j], kytab[j][i+1], p1->Nhop);

			emkup = ek(teff_up, p1->vec_hop, -kxtab[i+1][j], -kytab[j][i+1], p1->Nhop);
			emkdo = ek(teff_do, p1->vec_hop, -kxtab[i+1][j], -kytab[j][i+1], p1->Nhop);

			//calculating the effective chemical potential
			mueff = mu - p1->U*pow(lmbdd,2)*0.5*ntot - 6.0*p1->V*ntot;

			//diagonal elements of the Hamiltonian matrix (dispersion relations)
			gsl_matrix_complex_set( p1->Am, 0, 0, gsl_complex_rect (0.5*(ekup - mueff), 0.0) );
			gsl_matrix_complex_set( p1->Am, 1, 1, gsl_complex_rect (0.5*(ekdo - mueff), 0.0) );
			gsl_matrix_complex_set( p1->Am, 2, 2, gsl_complex_rect (-0.5*(emkup - mueff), 0.0) );
			gsl_matrix_complex_set( p1->Am, 3, 3, gsl_complex_rect (-0.5*(emkdo - mueff), 0.0) );

			//calculating the effective gap amplitudes in real space using the variational parameter lmbds as well as the superconducting lines
			calc_Deff(lmbds, S_ud, S_du, Deff_ud, Deff_du, p1->J, p1);    //the function changes the Deff_ud and Deff_du tables

			dkud = Sk(Deff_ud, p1->vec_S, kxtab[i+1][j], kytab[j][i+1], p1->NS);
			dkdu = Sk(Deff_du, p1->vec_S, kxtab[i+1][j], kytab[j][i+1], p1->NS);

			//off-diagonal elements (SC gaps)
			gsl_matrix_complex_set( p1->Am, 0, 3, gsl_complex_rect ( 0.5*dkdu.real(), 0.5*dkdu.imag() ));
			gsl_matrix_complex_set( p1->Am, 1, 2, gsl_complex_rect ( 0.5*dkud.real(), 0.5*dkud.imag() ));
			gsl_matrix_complex_set( p1->Am, 2, 1, gsl_complex_rect ( 0.5*dkud.real(), -0.5*dkud.imag() ));
			gsl_matrix_complex_set( p1->Am, 3, 0, gsl_complex_rect ( 0.5*dkdu.real(), -0.5*dkdu.imag() ));

			//numerical diagonalization
			gsl_eigen_hermv (p1->Am, p1->eval, p1->evec, p1->ws);
			gsl_eigen_hermv_sort(p1->eval, p1->evec, GSL_EIGEN_SORT_VAL_ASC); //ascending order with respect to the value

			//we copy the eigenvalues and eigenvectors from the gsl type of variables to the standard c++ type of variables
			cpy_matrix_complex(p1->evec, evec_c4, nh);
			cpy_vector_double(p1->eval, eval_c4, nh);

			//**************************************************************************************************


			M12[0][0] = conj(evec_c1[0][0]) * evec_c2[0][0] + conj(evec_c1[1][0]) * evec_c2[1][0] + conj(evec_c1[2][0]) * evec_c2[2][0] + conj(evec_c1[3][0]) * evec_c2[3][0];
			M12[0][1] = conj(evec_c1[0][0]) * evec_c2[0][1] + conj(evec_c1[1][0]) * evec_c2[1][1] + conj(evec_c1[2][0]) * evec_c2[2][1] + conj(evec_c1[3][0]) * evec_c2[3][1];
			M12[1][0] = conj(evec_c1[0][1]) * evec_c2[0][0] + conj(evec_c1[1][1]) * evec_c2[1][0] + conj(evec_c1[2][1]) * evec_c2[2][0] + conj(evec_c1[3][1]) * evec_c2[3][0];
			M12[1][1] = conj(evec_c1[0][1]) * evec_c2[0][1] + conj(evec_c1[1][1]) * evec_c2[1][1] + conj(evec_c1[2][1]) * evec_c2[2][1] + conj(evec_c1[3][1]) * evec_c2[3][1];

			u12 = (M12[0][0] * M12[1][1] - M12[0][1] * M12[1][0]);
			u12 = u12/abs(u12);

			M23[0][0] = conj(evec_c2[0][0]) * evec_c3[0][0] + conj(evec_c2[1][0]) * evec_c3[1][0] + conj(evec_c2[2][0]) * evec_c3[2][0] + conj(evec_c2[3][0]) * evec_c3[3][0];
			M23[0][1] = conj(evec_c2[0][0]) * evec_c3[0][1] + conj(evec_c2[1][0]) * evec_c3[1][1] + conj(evec_c2[2][0]) * evec_c3[2][1] + conj(evec_c2[3][0]) * evec_c3[3][1];
			M23[1][0] = conj(evec_c2[0][1]) * evec_c3[0][0] + conj(evec_c2[1][1]) * evec_c3[1][0] + conj(evec_c2[2][1]) * evec_c3[2][0] + conj(evec_c2[3][1]) * evec_c3[3][0];
			M23[1][1] = conj(evec_c2[0][1]) * evec_c3[0][1] + conj(evec_c2[1][1]) * evec_c3[1][1] + conj(evec_c2[2][1]) * evec_c3[2][1] + conj(evec_c2[3][1]) * evec_c3[3][1];

			u23 = M23[0][0] * M23[1][1] - M23[0][1] * M23[1][0];
			u23 = u23/abs(u23);


			M34[0][0] = conj(evec_c3[0][0]) * evec_c4[0][0] + conj(evec_c3[1][0]) * evec_c4[1][0] + conj(evec_c3[2][0]) * evec_c4[2][0] + conj(evec_c3[3][0]) * evec_c4[3][0];
			M34[0][1] = conj(evec_c3[0][0]) * evec_c4[0][1] + conj(evec_c3[1][0]) * evec_c4[1][1] + conj(evec_c3[2][0]) * evec_c4[2][1] + conj(evec_c3[3][0]) * evec_c4[3][1];
			M34[1][0] = conj(evec_c3[0][1]) * evec_c4[0][0] + conj(evec_c3[1][1]) * evec_c4[1][0] + conj(evec_c3[2][1]) * evec_c4[2][0] + conj(evec_c3[3][1]) * evec_c4[3][0];
			M34[1][1] = conj(evec_c3[0][1]) * evec_c4[0][1] + conj(evec_c3[1][1]) * evec_c4[1][1] + conj(evec_c3[2][1]) * evec_c4[2][1] + conj(evec_c3[3][1]) * evec_c4[3][1];

			u34 = M34[0][0] * M34[1][1] - M34[0][1] * M34[1][0];
			u34 = u34/abs(u34);

			M41[0][0] = conj(evec_c4[0][0]) * evec_c1[0][0] + conj(evec_c4[1][0]) * evec_c1[1][0] + conj(evec_c4[2][0]) * evec_c1[2][0] + conj(evec_c4[3][0]) * evec_c1[3][0];
			M41[0][1] = conj(evec_c4[0][0]) * evec_c1[0][1] + conj(evec_c4[1][0]) * evec_c1[1][1] + conj(evec_c4[2][0]) * evec_c1[2][1] + conj(evec_c4[3][0]) * evec_c1[3][1];
			M41[1][0] = conj(evec_c4[0][1]) * evec_c1[0][0] + conj(evec_c4[1][1]) * evec_c1[1][0] + conj(evec_c4[2][1]) * evec_c1[2][0] + conj(evec_c4[3][1]) * evec_c1[3][0];
			M41[1][1] = conj(evec_c4[0][1]) * evec_c1[0][1] + conj(evec_c4[1][1]) * evec_c1[1][1] + conj(evec_c4[2][1]) * evec_c1[2][1] + conj(evec_c4[3][1]) * evec_c1[3][1];

			u41 = M41[0][0] * M41[1][1] - M41[0][1] * M41[1][0];
			u41 = u41/abs(u41);

			e_phi = u12 * u23 * u34 * u41;
			phi = phi + arg(e_phi)/(2.0*M_PI);


			//ffout<<p1->kxtab[i][j]<<"\t"<<p1->kytab[j][i]<<"\t"<<arg(e_phi)<<"\t"<<abs(e_phi)<<"\t"<<eval_c1[0]<<"\t"<<eval_c1[1]<<"\t"<<eval_c1[2]<<"\t"<<eval_c1[3]<<endl;;

		}
        //ffout<<endl;
	}

    ffout.close();


	delete[] P_do;
	delete[] P_up;
	delete[] Pt_up;
	delete[] Pt_do;
	delete[] S_ud;
	delete[] S_du;

	delete[] teff_up;
	delete[] teff_do;
	delete[] Deff_ud;
	delete[] Deff_du;

	delete[] P_do_new;
	delete[] P_up_new;
	delete[] S_ud_new;
	delete[] S_du_new;

	return phi;
}

//***************************************************************************************************
//***************************************************************************************************
void qp_energy (const gsl_vector * x, void *params){

	double mu, mueff;                 // chemical potential and effective chemical potential
	double xg;                        // the x variational parameters
	double lmbds, lmbdd, lmbd0, q;    // variational parameters (they all depend on x)

	double ntot, ntot_new;            //total number of particles per atomic site

	complex<double> *P_up, *P_do;     // table of  lines which correspond to the hopping values for spin up/down electrons (size = NP)
	complex<double> *Pt_up, *Pt_do;   // table of all the lines which correspond to the hopping values for spin up/down electrons (size = Nhop)

	complex<double> *S_ud, *S_du;     // table of real-space superconducting gaps (up, down) and (down, up)  (size = NS)

	complex<double> *teff_up, *teff_do;    // table of effective hopping values for spin up/down electrons (size = Nhop)
	complex<double> *Deff_du, *Deff_ud;    // table of effective superconducting gaps (down, up) and (up, down)

	complex<double> *S_ud_new, *S_du_new;    // table of real-space superconducting gaps (up, down) and (down, up)  (size = NS)
	complex<double> *P_up_new, *P_do_new;    // table of lines which correspond to the hopping values for spin up/down electrons (size = NP)

	double *eval_c1, *eval_c2, *eval_c3, *eval_c4;                  // table of eigenvalues in standard c++ variables
	complex<double> **evec_c1, **evec_c2, **evec_c3, **evec_c4;        // matrix of eigenvectors in standard c++ variables

    complex <double> M12[2][2], M23[2][2], M34[2][2], M41[2][2];
    complex <double> e_phi, u12, u23, u34, u41;
    double phi;



	double nupk, ndok, nup, ndo;      // number of particles with spin up and down, respectively
	complex <double> Skud, Skdu;     // pairing expectation values in k-space for up-down and down-up pairing
	complex <double> cc;
	double ekup, ekdo, emkup, emkdo;  // dispersion relations for spin up/down and k/-k momenta
	complex <double> dkud, dkdu;      // k-dependant superconducting gap for (up,down) and (down,up) configurations

	struct params_sce *p1 = (struct params_sce *) params;  //structure which contains all the parameters

	double **kxtab, **kytab;   // tables with kx and ky coordinates inside the Brillouin zone (we will use that for the numerical integration)

	int Nk, nh;     // number of points over which we integrate (Nk) and size of the Hamiltonian matrix (nh)
	double T, BZ;    // temperature and the area of the Brillouin zone

	kxtab = p1->kxtab;
	kytab = p1->kytab;
	ntot = p1->ntot;

	Nk = p1->Nk;
	nh = p1->nh;
	T = p1->T;
	BZ = p1->BZ;


	P_do = new complex<double>[p1->NP];
	P_up = new complex<double>[p1->NP];

	Pt_do = new complex<double>[p1->Nhop];
	Pt_up = new complex<double>[p1->Nhop];

	S_du = new complex<double>[p1->NS];
	S_ud = new complex<double>[p1->NS];

	teff_up = new complex<double>[p1->Nhop];
	teff_do = new complex<double>[p1->Nhop];

	Deff_du = new complex<double>[p1->NS];
	Deff_ud = new complex<double>[p1->NS];

	S_ud_new = new complex<double>[p1->NS];
	S_du_new = new complex<double>[p1->NS];

	P_up_new = new complex<double>[p1->NP];
	P_do_new = new complex<double>[p1->NP];


	//matrix of eigenvectors as standard c++ type
	evec_c1 = new complex<double>*[nh];
	for(int i=0;i<nh;i++){
		evec_c1[i] = new complex<double>[nh];
	}

	//vector of eigenvalues as standard c++ type
	eval_c1 = new double[nh];

	//matrix of eigenvectors as standard c++ type
	evec_c2 = new complex<double>*[nh];
	for(int i=0;i<nh;i++){
		evec_c2[i] = new complex<double>[nh];
	}

	//vector of eigenvalues as standard c++ type
	eval_c2 = new double[nh];

	//matrix of eigenvectors as standard c++ type
	evec_c3 = new complex<double>*[nh];
	for(int i=0;i<nh;i++){
		evec_c3[i] = new complex<double>[nh];
	}

	//vector of eigenvalues as standard c++ type
	eval_c3 = new double[nh];

	//matrix of eigenvectors as standard c++ type
	evec_c4 = new complex<double>*[nh];
	for(int i=0;i<nh;i++){
		evec_c4[i] = new complex<double>[nh];
	}

	//vector of eigenvalues as standard c++ type
	eval_c4 = new double[nh];


	//copying the chemical potential and the x-variational parameter from the x vector
	mu = gsl_vector_get(x, 2*p1->NP + 2*p1->NS);
	//xg = -1.0 / pow((1.0 - 0.5*ntot),2);   //we get rid of the double electron occupancies
	//xg = -1.0 / pow((0.5*ntot),2);           //we get rid of the double hole occupancies

	xg = gsl_vector_get(x, 2*p1->NP + 2*p1->NS + 1);


	//copying the values of the gaps from x to the S_ud and S_du tables
	for(int i=0;i<p1->NS;i++){
		S_ud[i] = gsl_vector_get(x, 2*p1->NP + i) + 1i*gsl_vector_get(x, 2*p1->NP + p1->NS + i);
		//cout<<S_ud[i]<<endl;
	}

	S_du[1] = -S_ud[0];
	S_du[0] = -S_ud[1];

	S_du[3] = -S_ud[2];
	S_du[2] = -S_ud[3];

	S_du[5] = -S_ud[4];
	S_du[4] = -S_ud[5];

	p1->gv = 1 + xg*0.5*ntot*(1 - 0.5*ntot); // Assuming ns is calculated elsewhere

	//copying the values of the hopping lines from x to the P_up and P_do tables
	for(int i=0;i<p1->NP;i++){
		P_up[i] = gsl_vector_get(x, i) + 1i*gsl_vector_get(x, p1->NP + i);
		P_do[i] = gsl_vector_get(x, i) - 1i*gsl_vector_get(x, p1->NP + i);
	}



	//we calculate the lambda and q parameters using xg and ntot
	lmbd0 = sqrt( 1. + xg * pow(0.5*ntot, 2) );
	lmbds = sqrt( 1. + xg * (0.5*ntot-1.)*0.5*ntot );
	lmbdd = sqrt( 1. + xg * pow((1.0 - 0.5*ntot),2) );
	q = lmbds * lmbdd * 0.5*ntot + lmbds * lmbd0 * (1.0 - 0.5*ntot);

	//zeroing the variables which are going to be used during the numerical integration (summation)
	nupk = 0.0;
	ndok = 0.0;
	nup = 0.0;
	ndo = 0.0;
	Skud = 0.0;
	Skdu = 0.0;

	for(int i=0;i<p1->NS;i++){
		S_du_new[i] = 0.0;
		S_ud_new[i] = 0.0;
	}

	for(int i=0;i<p1->NP;i++){
		P_up_new[i] = 0.0;
		P_do_new[i] = 0.0;
	}


	ofstream ffout;
	ffout.open("data_qp.dat");

    double S, dS, kk, kx, ky;
    int Nd;

    S = 4.0*M_PI/3.0;
    Nd = 500;
    dS = S/Nd;
    kk = 0.0;



	phi = 0.0;

    for(int i=0;i<Nd;i++){
        kx = 0.0 + i*(-2.0*M_PI/3.0)/Nd;
        ky = 0.0 + i*(sqrt(3.0)*2.0*M_PI/3.0)/Nd;

		//**************************************************************************************************
		//filling the Hamiltonian matrix with zeros initially
		for(int jm=0; jm<nh; jm++){
			for(int im=0; im<nh; im++){
				gsl_matrix_complex_set( p1->Am, jm, im, gsl_complex_rect (0.0, 0.0) );
			}
		}
		//**************************************************************************************************
			//calculating the effective hopping parameters using the variational parameters q and lmbds as well as the hopping lines
		calc_teff(q, lmbds, P_up, P_do, teff_up, teff_do, p1);   //the function changes the teff_up and teff_do tables

			//calculating the effective dispersion relations
		ekup = ek(teff_up, p1->vec_hop, kx, ky, p1->Nhop);
		ekdo = ek(teff_do, p1->vec_hop, kx, ky, p1->Nhop);

		emkup = ek(teff_up, p1->vec_hop, -kx, -ky, p1->Nhop);
		emkdo = ek(teff_do, p1->vec_hop, -kx, -ky, p1->Nhop);


		mueff = mu - p1->U*pow(lmbdd,2)*0.5*ntot - 6.0*p1->V*ntot;

		//diagonal elements of the Hamiltonian matrix (dispersion relations)
		gsl_matrix_complex_set( p1->Am, 0, 0, gsl_complex_rect (0.5*(ekup - mueff), 0.0) );
		gsl_matrix_complex_set( p1->Am, 1, 1, gsl_complex_rect (0.5*(ekdo - mueff), 0.0) );
		gsl_matrix_complex_set( p1->Am, 2, 2, gsl_complex_rect (-0.5*(emkup - mueff), 0.0) );
		gsl_matrix_complex_set( p1->Am, 3, 3, gsl_complex_rect (-0.5*(emkdo - mueff), 0.0) );

		//calculating the effective gap amplitudes in real space using the variational parameter lmbds as well as the superconducting lines
		calc_Deff(lmbds, S_ud, S_du, Deff_ud, Deff_du, p1->J, p1);    //the function changes the Deff_ud and Deff_du tables


		dkud = Sk(Deff_ud, p1->vec_S, kx, ky, p1->NS);
		dkdu = Sk(Deff_du, p1->vec_S, kx, ky, p1->NS);

		//off-diagonal elements (SC gaps)
		gsl_matrix_complex_set( p1->Am, 0, 3, gsl_complex_rect ( 0.5*dkdu.real(), 0.5*dkdu.imag() ));
		gsl_matrix_complex_set( p1->Am, 1, 2, gsl_complex_rect ( 0.5*dkud.real(), 0.5*dkud.imag() ));
		gsl_matrix_complex_set( p1->Am, 2, 1, gsl_complex_rect ( 0.5*dkud.real(), -0.5*dkud.imag() ));
		gsl_matrix_complex_set( p1->Am, 3, 0, gsl_complex_rect ( 0.5*dkdu.real(), -0.5*dkdu.imag() ));


		//numerical diagonalization
		gsl_eigen_hermv (p1->Am, p1->eval, p1->evec, p1->ws);
		gsl_eigen_hermv_sort(p1->eval, p1->evec, GSL_EIGEN_SORT_VAL_ASC);

		//we copy the eigenvalues and eigenvectors from the gsl type of variables to the standard c++ type of variables
		cpy_matrix_complex(p1->evec, evec_c1, nh);
		cpy_vector_double(p1->eval, eval_c1, nh);

        ffout<<kx<<"\t"<<ky<<"\t"<<kk<<"\t"<<eval_c1[0]<<"\t"<<eval_c1[1]<<"\t"<<eval_c1[2]<<"\t"<<eval_c1[3]<<endl;

        kk = kk + dS;
	}


    for(int i=0;i<Nd;i++){
        kx = -2.0*M_PI/3.0 + i*(4.0*M_PI/3.0)/Nd;
        ky = sqrt(3.0)*2.0*M_PI/3.0;

		//**************************************************************************************************
		//filling the Hamiltonian matrix with zeros initially
		for(int jm=0; jm<nh; jm++){
			for(int im=0; im<nh; im++){
				gsl_matrix_complex_set( p1->Am, jm, im, gsl_complex_rect (0.0, 0.0) );
			}
		}
		//**************************************************************************************************
			//calculating the effective hopping parameters using the variational parameters q and lmbds as well as the hopping lines
		calc_teff(q, lmbds, P_up, P_do, teff_up, teff_do, p1);   //the function changes the teff_up and teff_do tables

			//calculating the effective dispersion relations
		ekup = ek(teff_up, p1->vec_hop, kx, ky, p1->Nhop);
		ekdo = ek(teff_do, p1->vec_hop, kx, ky, p1->Nhop);

		emkup = ek(teff_up, p1->vec_hop, -kx, -ky, p1->Nhop);
		emkdo = ek(teff_do, p1->vec_hop, -kx, -ky, p1->Nhop);


		mueff = mu - p1->U*pow(lmbdd,2)*0.5*ntot - 6.0*p1->V*ntot;

		//diagonal elements of the Hamiltonian matrix (dispersion relations)
		gsl_matrix_complex_set( p1->Am, 0, 0, gsl_complex_rect (0.5*(ekup - mueff), 0.0) );
		gsl_matrix_complex_set( p1->Am, 1, 1, gsl_complex_rect (0.5*(ekdo - mueff), 0.0) );
		gsl_matrix_complex_set( p1->Am, 2, 2, gsl_complex_rect (-0.5*(emkup - mueff), 0.0) );
		gsl_matrix_complex_set( p1->Am, 3, 3, gsl_complex_rect (-0.5*(emkdo - mueff), 0.0) );

		//calculating the effective gap amplitudes in real space using the variational parameter lmbds as well as the superconducting lines
		calc_Deff(lmbds, S_ud, S_du, Deff_ud, Deff_du, p1->J, p1);    //the function changes the Deff_ud and Deff_du tables


		dkud = Sk(Deff_ud, p1->vec_S, kx, ky, p1->NS);
		dkdu = Sk(Deff_du, p1->vec_S, kx, ky, p1->NS);

		//off-diagonal elements (SC gaps)
		gsl_matrix_complex_set( p1->Am, 0, 3, gsl_complex_rect ( 0.5*dkdu.real(), 0.5*dkdu.imag() ));
		gsl_matrix_complex_set( p1->Am, 1, 2, gsl_complex_rect ( 0.5*dkud.real(), 0.5*dkud.imag() ));
		gsl_matrix_complex_set( p1->Am, 2, 1, gsl_complex_rect ( 0.5*dkud.real(), -0.5*dkud.imag() ));
		gsl_matrix_complex_set( p1->Am, 3, 0, gsl_complex_rect ( 0.5*dkdu.real(), -0.5*dkdu.imag() ));


		//numerical diagonalization
		gsl_eigen_hermv (p1->Am, p1->eval, p1->evec, p1->ws);
		gsl_eigen_hermv_sort(p1->eval, p1->evec, GSL_EIGEN_SORT_VAL_ASC);

		//we copy the eigenvalues and eigenvectors from the gsl type of variables to the standard c++ type of variables
		cpy_matrix_complex(p1->evec, evec_c1, nh);
		cpy_vector_double(p1->eval, eval_c1, nh);

        ffout<<kx<<"\t"<<ky<<"\t"<<kk<<"\t"<<eval_c1[0]<<"\t"<<eval_c1[1]<<"\t"<<eval_c1[2]<<"\t"<<eval_c1[3]<<endl;

        kk = kk + dS;
	}


    for(int i=0;i<Nd;i++){
        kx = 2.0*M_PI/3.0 - i*(2.0*M_PI/3.0)/Nd;
        ky = sqrt(3.0)*2.0*M_PI/3.0 - i*(sqrt(3.0)*2.0*M_PI/3.0)/Nd;

		//**************************************************************************************************
		//filling the Hamiltonian matrix with zeros initially
		for(int jm=0; jm<nh; jm++){
			for(int im=0; im<nh; im++){
				gsl_matrix_complex_set( p1->Am, jm, im, gsl_complex_rect (0.0, 0.0) );
			}
		}
		//**************************************************************************************************
			//calculating the effective hopping parameters using the variational parameters q and lmbds as well as the hopping lines
		calc_teff(q, lmbds, P_up, P_do, teff_up, teff_do, p1);   //the function changes the teff_up and teff_do tables

			//calculating the effective dispersion relations
		ekup = ek(teff_up, p1->vec_hop, kx, ky, p1->Nhop);
		ekdo = ek(teff_do, p1->vec_hop, kx, ky, p1->Nhop);

		emkup = ek(teff_up, p1->vec_hop, -kx, -ky, p1->Nhop);
		emkdo = ek(teff_do, p1->vec_hop, -kx, -ky, p1->Nhop);


		mueff = mu - p1->U*pow(lmbdd,2)*0.5*ntot - 6.0*p1->V*ntot;

		//diagonal elements of the Hamiltonian matrix (dispersion relations)
		gsl_matrix_complex_set( p1->Am, 0, 0, gsl_complex_rect (0.5*(ekup - mueff), 0.0) );
		gsl_matrix_complex_set( p1->Am, 1, 1, gsl_complex_rect (0.5*(ekdo - mueff), 0.0) );
		gsl_matrix_complex_set( p1->Am, 2, 2, gsl_complex_rect (-0.5*(emkup - mueff), 0.0) );
		gsl_matrix_complex_set( p1->Am, 3, 3, gsl_complex_rect (-0.5*(emkdo - mueff), 0.0) );

		//calculating the effective gap amplitudes in real space using the variational parameter lmbds as well as the superconducting lines
		calc_Deff(lmbds, S_ud, S_du, Deff_ud, Deff_du, p1->J, p1);    //the function changes the Deff_ud and Deff_du tables


		dkud = Sk(Deff_ud, p1->vec_S, kx, ky, p1->NS);
		dkdu = Sk(Deff_du, p1->vec_S, kx, ky, p1->NS);

		//off-diagonal elements (SC gaps)
		gsl_matrix_complex_set( p1->Am, 0, 3, gsl_complex_rect ( 0.5*dkdu.real(), 0.5*dkdu.imag() ));
		gsl_matrix_complex_set( p1->Am, 1, 2, gsl_complex_rect ( 0.5*dkud.real(), 0.5*dkud.imag() ));
		gsl_matrix_complex_set( p1->Am, 2, 1, gsl_complex_rect ( 0.5*dkud.real(), -0.5*dkud.imag() ));
		gsl_matrix_complex_set( p1->Am, 3, 0, gsl_complex_rect ( 0.5*dkdu.real(), -0.5*dkdu.imag() ));


		//numerical diagonalization
		gsl_eigen_hermv (p1->Am, p1->eval, p1->evec, p1->ws);
		gsl_eigen_hermv_sort(p1->eval, p1->evec, GSL_EIGEN_SORT_VAL_ASC);

		//we copy the eigenvalues and eigenvectors from the gsl type of variables to the standard c++ type of variables
		cpy_matrix_complex(p1->evec, evec_c1, nh);
		cpy_vector_double(p1->eval, eval_c1, nh);

        ffout<<kx<<"\t"<<ky<<"\t"<<kk<<"\t"<<eval_c1[0]<<"\t"<<eval_c1[1]<<"\t"<<eval_c1[2]<<"\t"<<eval_c1[3]<<endl;

        kk = kk + dS;
	}



    ffout.close();




	delete[] P_do;
	delete[] P_up;
	delete[] Pt_up;
	delete[] Pt_do;
	delete[] S_ud;
	delete[] S_du;

	delete[] teff_up;
	delete[] teff_do;
	delete[] Deff_ud;
	delete[] Deff_du;

	delete[] P_do_new;
	delete[] P_up_new;
	delete[] S_ud_new;
	delete[] S_du_new;

}
//***************************************************************************************************
//***************************************************************************************************

void disp_and_delta (const gsl_vector * x, void *params,  string filename_disp, string filename_SC, string filename_params, double D){

	double mu, mueff;                 // chemical potential and effective chemical potential
	double xg;                        // the x variational parameters
	double lmbds, lmbdd, lmbd0, q;    // variational parameters (they all depend on x)

	double ntot, ntot_new;            //total number of particles per atomic site

	complex<double> *P_up, *P_do;     // table of  lines which correspond to the hopping values for spin up/down electrons (size = NP)
	complex<double> *Pt_up, *Pt_do;   // table of all the lines which correspond to the hopping values for spin up/down electrons (size = Nhop)

	complex<double> *S_ud, *S_du;     // table of real-space superconducting gaps (up, down) and (down, up)  (size = NS)

	complex<double> *teff_up, *teff_do;    // table of effective hopping values for spin up/down electrons (size = Nhop)
	complex<double> *Deff_du, *Deff_ud;    // table of effective superconducting gaps (down, up) and (up, down)

	complex<double> *S_ud_new, *S_du_new;    // table of real-space superconducting gaps (up, down) and (down, up)  (size = NS)
	complex<double> *P_up_new, *P_do_new;    // table of lines which correspond to the hopping values for spin up/down electrons (size = NP)


	double nupk, ndok, nup, ndo;      // number of particles with spin up and down, respectively
	complex <double> Skud, Skdu;     // pairing expectation values in k-space for up-down and down-up pairing
	complex <double> cc;
	double ekup, ekdo, emkup, emkdo;  // dispersion relations for spin up/down and k/-k momenta
	complex <double> dkud, dkdu;      // k-dependant superconducting gap for (up,down) and (down,up) configurations

	struct params_sce *p1 = (struct params_sce *) params;  //structure which contains all the parameters

	double **kxtab, **kytab;   // tables with kx and ky coordinates inside the Brillouin zone (we will use that for the numerical integration)

	int Nk, nh;     // number of points over which we integrate (Nk) and size of the Hamiltonian matrix (nh)
	double T, BZ;    // temperature and the area of the Brillouin zone


	ofstream fout_disp, fout_SC, fout_params;

	char *filename_disp_c;
	char *filename_SC_c;
	char *filename_params_c;

	int length_disp, length_SC, length_params;

	length_disp = filename_disp.length();
	length_SC = filename_SC.length();
	length_params = filename_params.length();

	filename_disp_c = new char(length_disp+1);
	filename_SC_c = new char(length_SC+1);
	filename_params_c = new char(length_params+1);

	strcpy(filename_disp_c, filename_disp.c_str());
	strcpy(filename_SC_c, filename_SC.c_str());
	strcpy(filename_params_c, filename_params.c_str());

	fout_disp.open(filename_disp_c);
	fout_SC.open(filename_SC_c);
	fout_params.open(filename_params_c);



	kxtab = p1->kxtab;
	kytab = p1->kytab;
	ntot = p1->ntot;

	Nk = p1->Nk;
	nh = p1->nh;
	T = p1->T;
	BZ = p1->BZ;


	P_do = new complex<double>[p1->NP];
	P_up = new complex<double>[p1->NP];

	Pt_do = new complex<double>[p1->Nhop];
	Pt_up = new complex<double>[p1->Nhop];

	S_du = new complex<double>[p1->NS];
	S_ud = new complex<double>[p1->NS];

	teff_up = new complex<double>[p1->Nhop];
	teff_do = new complex<double>[p1->Nhop];

	Deff_du = new complex<double>[p1->NS];
	Deff_ud = new complex<double>[p1->NS];

	S_ud_new = new complex<double>[p1->NS];
	S_du_new = new complex<double>[p1->NS];

	P_up_new = new complex<double>[p1->NP];
	P_do_new = new complex<double>[p1->NP];



	//copying the chemical potential and the x-variational parameter from the x vector
	mu = gsl_vector_get(x, 2*p1->NP + 2*p1->NS);
	xg = gsl_vector_get(x, 2*p1->NP + 2*p1->NS + 1);

	//copying the values of the gaps from x to the S_ud and S_du tables
	for(int i=0;i<p1->NS;i++){
		S_ud[i] = gsl_vector_get(x, 2*p1->NP + i) + 1i*gsl_vector_get(x, 2*p1->NP + p1->NS + i);
		//cout<<S_ud[i]<<endl;
	}

	S_du[1] = -S_ud[0];
	S_du[0] = -S_ud[1];

	S_du[3] = -S_ud[2];
	S_du[2] = -S_ud[3];

	S_du[5] = -S_ud[4];
	S_du[4] = -S_ud[5];

	p1->gv = 1 + xg*0.5*ntot*(1 - 0.5*ntot); // Assuming ns is calculated elsewhere

	//copying the values of the hopping lines from x to the P_up and P_do tables
	for(int i=0;i<p1->NP;i++){
		P_up[i] = gsl_vector_get(x, i) + 1i*gsl_vector_get(x, p1->NP + i);
		P_do[i] = gsl_vector_get(x, i) - 1i*gsl_vector_get(x, p1->NP + i);
	}

	//we calculate the lambda and q parameters using xg and ntot
	lmbd0 = sqrt( 1. + xg * pow(0.5*ntot, 2) );
	lmbds = sqrt( 1. + xg * (0.5*ntot-1.)*0.5*ntot );

	lmbdd = sqrt( 1. + xg * pow((1.0 - 0.5*ntot),2) );
	q = lmbds * lmbdd * 0.5*ntot + lmbds * lmbd0 * (1.0 - 0.5*ntot);

	//zeroing the variables which are going to be used during the numerical integration (summation)
	nupk = 0.0;
	ndok = 0.0;
	nup = 0.0;
	ndo = 0.0;
	Skud = 0.0;
	Skdu = 0.0;

	for(int i=0;i<p1->NS;i++){
		S_du_new[i] = 0.0;
		S_ud_new[i] = 0.0;
	}

	for(int i=0;i<p1->NP;i++){
		P_up_new[i] = 0.0;
		P_do_new[i] = 0.0;
	}



	//first we print the effective hopping and pairing parameters to the file

	fout_params<<endl;
	fout_params<<"n = "<<p1->ntot<<endl;
	fout_params<<"J = "<<p1->J<<endl;
	fout_params<<"T = "<<p1->T<<endl;
	fout_params<<"U = "<<p1->U<<endl;
	fout_params<<"D = "<<D<<endl;
	fout_params<<endl;
	fout_params<<endl;

	calc_teff(q, lmbds, P_up, P_do, teff_up, teff_do, p1);   //the function changes the teff_up and teff_do tables
	fout_params<<"hopping up"<<endl;
	for(int iu=0;iu<6;iu++){
		//fout_params<<iu<<"\t"<<teff_up[iu]<<endl;
		fout_params<<"teff"<<iu<<"_up = "<<real(teff_up[iu])<<" + 1j*("<<imag(teff_up[iu])<<")"<<endl;
	}
	fout_params<<endl;

	fout_params<<"hopping down"<<endl;
	for(int iu=0;iu<6;iu++){
		//fout_params<<iu<<"\t"<<teff_do[iu]<<endl;
		fout_params<<"teff"<<iu<<"_do = "<<real(teff_do[iu])<<" + 1j*("<<imag(teff_do[iu])<<")"<<endl;
	}
	fout_params<<endl;


	calc_Deff(lmbds, S_ud, S_du, Deff_ud, Deff_du, p1->J, p1);    //the function changes the Deff_ud and Deff_du tables
	fout_params<<"pairing ud"<<endl;
	for(int iu=0;iu<6;iu++){
		fout_params<<"delt"<<iu<<"_ud = "<<real(Deff_ud[iu])<<" + 1j*("<<imag(Deff_ud[iu])<<")"<<endl;
	}
	fout_params<<endl;
	fout_params<<"pairing du"<<endl;
	for(int iu=0;iu<6;iu++){
		fout_params<<"delt"<<iu<<"_du = "<<real(Deff_du[iu])<<" + 1j*("<<imag(Deff_du[iu])<<")"<<endl;
	}
	fout_params<<endl;
	fout_params<<"chemical potential"<<endl;
	fout_params<<mu - p1->U*pow(lmbdd,2)*0.5*ntot<<endl;


	fout_params.close();


    double S, dS, kk, kx, ky;
    int Nd;

    S = 4.0*M_PI/3.0;
    Nd = 200;  //this is only for printing the dispersion relation
    dS = S/Nd;
    kk = 0.0;


    for(int i=0;i<Nd;i++){
        for(int j=0;j<Nd;j++){
        	kx = -8.0 + i*16.0/Nd;
        	ky = -8.0 + j*16.0/Nd;

			//calculating the effective hopping parameters using the variational parameters q and lmbds as well as the hopping lines
        	calc_teff(q, lmbds, P_up, P_do, teff_up, teff_do, p1);   //the function changes the teff_up and teff_do tables

			//calculating the effective dispersion relations
        	ekup = ek(teff_up, p1->vec_hop, kx, ky, p1->Nhop);
        	ekdo = ek(teff_do, p1->vec_hop, kx, ky, p1->Nhop);

        	emkup = ek(teff_up, p1->vec_hop, -kx, -ky, p1->Nhop);
        	emkdo = ek(teff_do, p1->vec_hop, -kx, -ky, p1->Nhop);

        	mueff = mu - p1->U*pow(lmbdd,2)*0.5*ntot - 6.0*p1->V*ntot;

        	//calculating the effective gap amplitudes in real space using the variational parameter lmbds as well as the superconducting lines
        	calc_Deff(lmbds, S_ud, S_du, Deff_ud, Deff_du, p1->J, p1);    //the function changes the Deff_ud and Deff_du table

        	dkud = Sk(Deff_ud, p1->vec_S, kx, ky, p1->NS);
        	dkdu = Sk(Deff_du, p1->vec_S, kx, ky, p1->NS);


        	fout_disp<<kx<<"\t"<<ky<<"\t"<<ekup-mueff<<"\t"<<ekdo-mueff<<endl;
        	fout_SC<<kx<<"\t"<<ky<<"\t"<<abs(dkud)<<"\t"<<arg(dkud)<<"\t"<<abs(dkdu)<<"\t"<<arg(dkdu)<<endl;

        }
    	fout_disp<<endl;
    	fout_SC<<endl;
	}


    fout_disp.close();
    fout_SC.close();



	delete[] P_do;
	delete[] P_up;
	delete[] Pt_up;
	delete[] Pt_do;
	delete[] S_ud;
	delete[] S_du;

	delete[] teff_up;
	delete[] teff_do;
	delete[] Deff_ud;
	delete[] Deff_du;

	delete[] P_do_new;
	delete[] P_up_new;
	delete[] S_ud_new;
	delete[] S_du_new;

	delete[] filename_disp_c;
	delete[] filename_SC_c;
	delete[] filename_params_c;

}
//***************************************************************************************************
//***************************************************************************************************
double dos_at_mu (const gsl_vector * x, void *params){

	double mu, mueff;                 // chemical potential and effective chemical potential
	double xg;                        // the x variational parameters
	double lmbds, lmbdd, lmbd0, q;    // variational parameters (they all depend on x)

	double ntot, ntot_new;            //total number of particles per atomic site

	complex<double> *P_up, *P_do;     // table of  lines which correspond to the hopping values for spin up/down electrons (size = NP)
	complex<double> *Pt_up, *Pt_do;   // table of all the lines which correspond to the hopping values for spin up/down electrons (size = Nhop)

	complex<double> *S_ud, *S_du;     // table of real-space superconducting gaps (up, down) and (down, up)  (size = NS)

	complex<double> *teff_up, *teff_do;    // table of effective hopping values for spin up/down electrons (size = Nhop)
	complex<double> *Deff_du, *Deff_ud;    // table of effective superconducting gaps (down, up) and (up, down)

	complex<double> *S_ud_new, *S_du_new;    // table of real-space superconducting gaps (up, down) and (down, up)  (size = NS)
	complex<double> *P_up_new, *P_do_new;    // table of lines which correspond to the hopping values for spin up/down electrons (size = NP)


	double nupk, ndok, nup, ndo;      // number of particles with spin up and down, respectively
	complex <double> Skud, Skdu;     // pairing expectation values in k-space for up-down and down-up pairing
	complex <double> cc;
	double ekup, ekdo, emkup, emkdo;  // dispersion relations for spin up/down and k/-k momenta
	complex <double> dkud, dkdu;      // k-dependant superconducting gap for (up,down) and (down,up) configurations

	struct params_sce *p1 = (struct params_sce *) params;  //structure which contains all the parameters

	double **kxtab, **kytab;   // tables with kx and ky coordinates inside the Brillouin zone (we will use that for the numerical integration)

	int Nk, nh;     // number of points over which we integrate (Nk) and size of the Hamiltonian matrix (nh)
	double T, BZ;    // temperature and the area of the Brillouin zone

	double dos;


	kxtab = p1->kxtab_dos;
	kytab = p1->kytab_dos;
	ntot = p1->ntot;

	Nk = p1->Nk_dos;
	nh = p1->nh;
	T = p1->T;
	BZ = p1->BZ;


	P_do = new complex<double>[p1->NP];
	P_up = new complex<double>[p1->NP];

	Pt_do = new complex<double>[p1->Nhop];
	Pt_up = new complex<double>[p1->Nhop];

	S_du = new complex<double>[p1->NS];
	S_ud = new complex<double>[p1->NS];

	teff_up = new complex<double>[p1->Nhop];
	teff_do = new complex<double>[p1->Nhop];

	Deff_du = new complex<double>[p1->NS];
	Deff_ud = new complex<double>[p1->NS];

	S_ud_new = new complex<double>[p1->NS];
	S_du_new = new complex<double>[p1->NS];

	P_up_new = new complex<double>[p1->NP];
	P_do_new = new complex<double>[p1->NP];



	//copying the chemical potential and the x-variational parameter from the x vector
	mu = gsl_vector_get(x, 2*p1->NP + 2*p1->NS);
	//xg = -1.0 / pow((1.0 - 0.5*ntot),2);   //we get rid of the double electron occupancies
	//xg = -1.0 / pow((0.5*ntot),2);           //we get rid of the double hole occupancies
	xg = gsl_vector_get(x, 2*p1->NP + 2*p1->NS + 1);


	//copying the values of the gaps from x to the S_ud and S_du tables
	for(int i=0;i<p1->NS;i++){
		S_ud[i] = gsl_vector_get(x, 2*p1->NP + i) + 1i*gsl_vector_get(x, 2*p1->NP + p1->NS + i);
		//cout<<S_ud[i]<<endl;
	}

	S_du[1] = -S_ud[0];
	S_du[0] = -S_ud[1];

	S_du[3] = -S_ud[2];
	S_du[2] = -S_ud[3];

	S_du[5] = -S_ud[4];
	S_du[4] = -S_ud[5];

	p1->gv = 1 + xg*0.5*ntot*(1 - 0.5*ntot); // Assuming ns is calculated elsewhere

	//copying the values of the hopping lines from x to the P_up and P_do tables
	for(int i=0;i<p1->NP;i++){
		P_up[i] = gsl_vector_get(x, i) + 1i*gsl_vector_get(x, p1->NP + i);
		P_do[i] = gsl_vector_get(x, i) - 1i*gsl_vector_get(x, p1->NP + i);
	}

	//we calculate the lambda and q parameters using xg and ntot
	lmbd0 = sqrt( 1. + xg * pow(0.5*ntot, 2) );
	lmbds = sqrt( 1. + xg * (0.5*ntot-1.)*0.5*ntot );

	lmbdd = sqrt( 1. + xg * pow((1.0 - 0.5*ntot),2) );
	q = lmbds * lmbdd * 0.5*ntot + lmbds * lmbd0 * (1.0 - 0.5*ntot);

	//zeroing the variables which are going to be used during the numerical integration (summation)
	nupk = 0.0;
	ndok = 0.0;
	nup = 0.0;
	ndo = 0.0;
	Skud = 0.0;
	Skdu = 0.0;

	for(int i=0;i<p1->NS;i++){
		S_du_new[i] = 0.0;
		S_ud_new[i] = 0.0;
	}

	for(int i=0;i<p1->NP;i++){
		P_up_new[i] = 0.0;
		P_do_new[i] = 0.0;
	}


    double N1up, N2up, N1do, N2do, kx, ky, ene1, ene2, dene;

    mueff = mu - p1->U*pow(lmbdd,2)*0.5*ntot - 6.0*p1->V*ntot;

    dene = 0.0001;

    ene1 = mueff - dene;
    ene2 = mueff + dene;

    N1up = 0;
    N2up = 0;

    N1do = 0;
    N2do = 0;

    for(int i=0;i<Nk;i++){
        for(int j=0;j<Nk;j++){
        	kx = kxtab[i][j];
        	ky = kytab[j][i];

			//calculating the effective hopping parameters using the variational parameters q and lmbds as well as the hopping lines
        	calc_teff(q, lmbds, P_up, P_do, teff_up, teff_do, p1);   //the function changes the teff_up and teff_do tables

			//calculating the effective dispersion relations
        	ekup = ek(teff_up, p1->vec_hop, kx, ky, p1->Nhop);
        	ekdo = ek(teff_do, p1->vec_hop, kx, ky, p1->Nhop);

        	if(ekup <= ene1) N1up++;
            if(ekup <= ene2) N2up++;

        	if(ekdo <= ene1) N1do++;
            if(ekdo <= ene2) N2do++;

        }
	}

    dos = (N2up - N1up)/(2*dene) + (N2do - N1do)/(2*dene);
    dos = dos/(Nk*Nk);


	delete[] P_do;
	delete[] P_up;
	delete[] Pt_up;
	delete[] Pt_do;
	delete[] S_ud;
	delete[] S_du;

	delete[] teff_up;
	delete[] teff_do;
	delete[] Deff_ud;
	delete[] Deff_du;

	delete[] P_do_new;
	delete[] P_up_new;
	delete[] S_ud_new;
	delete[] S_du_new;


	return dos;
}
//***************************************************************************************************
//***************************************************************************************************

int print_state_terminal (size_t iter, gsl_multiroot_fsolver * s, int n){
	double sum;

	sum = 0.0;
	for(int i=0;i<n;i++){
		//cout<<i<<"\t"<<gsl_vector_get (s->x, i)<<"\t"<<gsl_vector_get (s->f, i)<<endl;
		sum = sum + pow(gsl_vector_get (s->f, i),2);
	}
	sum = sqrt(sum);
	cout<<endl;
	cout<<"sum = "<<sum<<endl;

	return 0;
}
//***************************************************************************************************
//***************************************************************************************************
void print_params_file(void *params, gsl_vector *x, const char *filename){
	ofstream ffout4;

	ffout4.open(filename, ios::app); //opening an existing file and append new text at the end of that file


	struct params_sce *p1 = (struct params_sce *) params;

	ffout4<<endl;
	ffout4<<endl;
	ffout4<<"***********************************************************************"<<endl;
	ffout4<<"vec_hop:"<<endl;
	for(int i=0;i<p1->Nhop;i++){
		ffout4<<i<<"\t"<<p1->vec_hop[i][0]<<"\t"<<p1->vec_hop[i][1]<<endl;
	}
	ffout4<<endl;
	ffout4<<endl;
	ffout4<<"vec_P:"<<endl;
	for(int i=0;i<p1->NP;i++){
		ffout4<<i<<"\t"<<p1->vec_P[i][0]<<"\t"<<p1->vec_P[i][1]<<endl;
	}
	ffout4<<endl;
	ffout4<<endl;
	ffout4<<"vec_S"<<endl;
	for(int i=0;i<p1->NS;i++){
		ffout4<<i<<"\t"<<p1->vec_S[i][0]<<"\t"<<p1->vec_S[i][1]<<endl;
	}
	ffout4<<endl;
	ffout4<<endl;
	ffout4<<"t:"<<endl;
	for(int i=0;i<p1->Nhop;i++){
		ffout4<<i<<"\t"<<p1->t_up[i]<<"\t"<<p1->t_do[i]<<endl;
	}
	ffout4<<endl;
	ffout4<<endl;
	ffout4<<"Nk = "<<p1->Nk<<endl;
	ffout4<<"BZ = "<<p1->BZ<<endl;
	ffout4<<"Nhop = "<<p1->Nhop<<endl;
	ffout4<<"NP = "<<p1->NP<<endl;
	ffout4<<"NS = "<<p1->NS<<endl;
	ffout4<<"NEq = "<<p1->NEq<<endl;
	ffout4<<endl;
	ffout4<<endl;
	ffout4<<"h1, h2, h3 = "<<p1->h1<<"\t"<<p1->h2<<"\t"<<p1->h3<<endl;
	ffout4<<"phi1, phi2, phi3 = "<<p1->phi1<<"\t"<<p1->phi2<<"\t"<<p1->phi3<<endl;
	ffout4<<"T = "<<p1->T<<endl;
	ffout4<<"J = "<<p1->J<<endl;
	ffout4<<"U = "<<p1->U<<endl;
	ffout4<<"V = "<<p1->V<<endl;
	ffout4<<"ntot = "<<p1->ntot<<endl;

	ffout4<<endl;
	ffout4<<endl;
	ffout4<<"printing the initial values of our solution"<<endl;
	for(int i=0;i<p1->NEq;i++){
		ffout4<<i<<"\t"<<gsl_vector_get( x, i )<<endl;
	}
	cout<<endl;

	ffout4.close();

}
//***************************************************************************************************
//***************************************************************************************************
void print_state_file(size_t iter, gsl_multiroot_fsolver * s, int n, const char *filename, int inter){
	double sum;
	ofstream ffout4;

	ffout4.open(filename, ios::app);  //opening an existing file and append new text at the end of that file

	sum = 0.0;
	ffout4<<endl;
	ffout4<<endl;
	ffout4<<"iter = "<<iter<<endl;
	ffout4<<endl;
	for(int i=0;i<n;i++){
		//ffout4<<i<<"\t"<<gsl_vector_get (s->x, i)<<"\t"<<gsl_vector_get (s->f, i)<<endl;
		sum = sum + pow(gsl_vector_get (s->f, i),2);
	}
	sum = sqrt(sum);
	ffout4<<endl;
	ffout4<<"sum = "<<sum<<endl;

	ffout4.close();
}
//***************************************************************************************************
//***************************************************************************************************
int print_gsl_vector_terminal (gsl_vector * y, int n){
	double sum;

	sum = 0.0;
	for(int i=0;i<n;i++){
		//cout<<i<<"\t"<<gsl_vector_get (s->x, i)<<"\t"<<gsl_vector_get (s->f, i)<<endl;
		sum = sum + pow(gsl_vector_get (y, i),2);
	}
	sum = sqrt(sum);
	cout<<endl;
	cout<<"sum = "<<sum<<endl;

	return 0;
}
//***************************************************************************************************
//***************************************************************************************************


int main(int argc, char* argv[]){

	clock_t t;
	cout<<"start..."<<endl;
    time_t now = time(0);
    t = clock();

    double q;


    //reading the input argument of the main function
    int aarg1;
    aarg1 = atoi(argv[1]);
    cout<<"aarg1 "<<argv[1]<<"\t"<<aarg1<<endl;


    //hopping parameters
	complex<double> h1, h2, h3;    //absolute values of the hopping parameters to fist, second, and third nearest neighbor
	int N_sym = 6;                 //rotational symmetry factor (hexagonal lattice)

	struct params_sce p1;  //structure with all the parameters used while solving the self-consistant equations
	int nh = 4;                 //size of the matrix Hamiltonian

	p1.nh = nh;


	//stuff required for the multidimentional root finding (gsl library)
	p1.Am = gsl_matrix_complex_alloc(nh, nh);
	p1.eval = gsl_vector_alloc(nh);
	p1.evec = gsl_matrix_complex_alloc(nh,nh);
	p1.ws = gsl_eigen_hermv_alloc (nh);

	//Nk x Nk is the number of points in the Brillouin zone over which we integrate
	p1.Nk = 2048;  //4096;  //2048;  //3096;  //256;  // 512;  //512;

	//Nk x Nk is the number of points in the Brillouin zone over which we integrate when calculating the density of states
	p1.Nk_dos = 512;  //1024

	vector<double> abar, bbar, k0;   //reciprocal lattice vectors

	double t1_tab[15];
	double l1_tab[15];
	double D_tab[15];


	//reciprocal lattice vectors for the triangular lattice
	abar = {2.0*M_PI, -sqrt(3.0)*2.0*M_PI/3.0};
	bbar = {0.0, sqrt(3.0)*4.0*M_PI/3.0};
	k0 = {0.0, 0.0};

	//***********************************************************************************************************************
	//**************************************For the self consistant equations************************************************
	//tables with kx and ky coordinates inside the Brillouin zone (we will use that for the numerical integration)
	p1.kxtab = new double*[p1.Nk];
	p1.kytab = new double*[p1.Nk];
	for(int i=0;i<p1.Nk;i++){
		p1.kxtab[i] = new double[p1.Nk];
		p1.kytab[i] = new double[p1.Nk];
	}

	//filling out the kxtab and kytab tables with coordinates
	for(int i=0;i<p1.Nk;i++){
		for(int j=0;j<p1.Nk;j++){
			p1.kxtab[i][j] = k0[0] + i*abar[0]/p1.Nk + j*bbar[0]/p1.Nk;
			p1.kytab[i][j] = k0[1] + i*bbar[1]/p1.Nk + j*abar[1]/p1.Nk;
		}
	}

	//***********************************************************************************************************************
	//***************************************For the density of states calculations******************************************
	//tables with kx and ky coordinates inside the Brillouin zone (we will use that for the numerical integration)
	p1.kxtab_dos = new double*[p1.Nk_dos];
	p1.kytab_dos = new double*[p1.Nk_dos];

	for(int i=0;i<p1.Nk_dos;i++){
		p1.kxtab_dos[i] = new double[p1.Nk_dos];
		p1.kytab_dos[i] = new double[p1.Nk_dos];
	}

	//filling out the kxtab and kytab tables with coordinates
	for(int i=0;i<p1.Nk_dos;i++){
		for(int j=0;j<p1.Nk_dos;j++){
			p1.kxtab_dos[i][j] = k0[0] + i*abar[0]/p1.Nk_dos + j*bbar[0]/p1.Nk_dos;
			p1.kytab_dos[i][j] = k0[1] + i*bbar[1]/p1.Nk_dos + j*abar[1]/p1.Nk_dos;
		}
	}
	//***********************************************************************************************************************

	p1.BZ = (abar[0]*bbar[1] - abar[1]*bbar[0]);  //the area of the Brillouin zone


	p1.Nhop = 18; //number of hoppings in the Hamiltonian
	p1.NP = 3;    //number of unknown normal lines
	p1.NS = 6;    //number of unknown superconducting lines
	p1.NJ = 6;    //number of number of intersite echxange interaction


	//hopping(paramagnetic) lines (real and imag), superconducting lines (real and imag), chemical potential, variational parameter x
	p1.NEq = 2*p1.NP + 2*p1.NS + 1 + 1;   //number of self-consistant equations (for the t-J model we don't have the unknown variational parameter x)


	complex<double> *delt_s, *delt_t;    //tables in which the singlet and triplet components are going to be stored (used after the self-consistent equations are solved)
	complex<double> *delt_ud_c, *delt_du_c;
	complex<double> *delt_ud_sym, *delt_du_sym;

	complex<double> *delt_eff_ud_c, *delt_eff_du_c;
	complex<double> *delt_eff_ud_sym, *delt_eff_du_sym;
	complex<double> *delt_eff_s, *delt_eff_t;

	double var_tab[5];

	clock_t t1;
	cout<<"start..."<<endl;
    time_t now1 = time(0);
    t1 = clock();


	delt_ud_c = new complex<double>[p1.NS];
	delt_du_c = new complex<double>[p1.NS];

	delt_eff_ud_c = new complex<double>[p1.NS];
	delt_eff_du_c = new complex<double>[p1.NS];


	delt_ud_sym = new complex<double>[3*N_sym];  //we consider 6 different symmetry factors
	delt_du_sym = new complex<double>[N_sym];   //we consider 6 different symmetry factors

	delt_eff_ud_sym = new complex<double>[3*N_sym];  //we consider 6 different symmetry factors
	delt_eff_du_sym = new complex<double>[N_sym];   //we consider 6 different symmetry factors

	delt_s = new complex<double>[N_sym];      //spin resolved symmetry factors
	delt_t = new complex<double>[N_sym];

	delt_eff_s = new complex<double>[N_sym];      //spin resolved symmetry factors
	delt_eff_t = new complex<double>[N_sym];


	p1.vec_hop = new vector <double>[p1.Nhop];
	p1.t_up = new complex<double>[p1.Nhop];
	p1.t_do = new complex<double>[p1.Nhop];

	p1.vec_J = new vector<double>[p1.NJ];

	p1.vec_P = new vector <double>[p1.NP];
	p1.vec_S = new vector <double>[p1.NS];


	cout<<endl;
	cout<<endl;
	time_t after1 = time(0);
	t1 = clock() - t1;

	cout <<"time1: "<< after1 - now1 << endl;
	cout <<"number of clicks1: "<<t1 << endl;


	p1.vec_hop[0] = {1.0, 0.0};
	p1.vec_hop[1] = {-1.0, 0.0};
	p1.vec_hop[2] = {0.5, sqrt(3.0)/2.0};
	p1.vec_hop[3] = {-0.5, -sqrt(3.0)/2.0};
	p1.vec_hop[4] = {-0.5, sqrt(3.0)/2.0};
	p1.vec_hop[5] = {0.5, -sqrt(3.0)/2.0};

	p1.vec_hop[6] = {3.0/2.0, sqrt(3.0)/2.0};
	p1.vec_hop[7] = {-3.0/2.0, -sqrt(3.0)/2.0};
	p1.vec_hop[8] = {0.0, sqrt(3.0)};
	p1.vec_hop[9] = {0.0, -sqrt(3.0)};
	p1.vec_hop[10] = {-3.0/2.0, sqrt(3.0)/2.0};
	p1.vec_hop[11] = {3.0/2.0, -sqrt(3.0)/2.0};

	p1.vec_hop[12] = {2.0, 0.0};
	p1.vec_hop[13] = {-2.0, 0.0};
	p1.vec_hop[14] = {1.0, sqrt(3.0)};
	p1.vec_hop[15] = {-1.0, -sqrt(3.0)};
	p1.vec_hop[16] = {-1.0, sqrt(3.0)};
	p1.vec_hop[17] = {1.0, -sqrt(3.0)};


	cout<<endl;
	cout<<endl;
	cout<<"vec_hop:"<<endl;
	for(int i=0;i<p1.Nhop;i++){
		cout<<i<<"\t"<<p1.vec_hop[i][0]<<"\t"<<p1.vec_hop[i][1]<<endl;
	}


	p1.vec_J[0] = {1.0, 0.0};
	p1.vec_J[1] = {-1.0, 0.0};
	p1.vec_J[2] = {0.5, sqrt(3.0)/2.0};
	p1.vec_J[3] = {-0.5, -sqrt(3.0)/2.0};
	p1.vec_J[4] = {-0.5, sqrt(3.0)/2.0};
	p1.vec_J[5] = {0.5, -sqrt(3.0)/2.0};

	cout<<endl;
	cout<<endl;
	cout<<"vec_J:"<<endl;
	for(int i=0;i<p1.NJ;i++){
		cout<<i<<"\t"<<p1.vec_J[i][0]<<"\t"<<p1.vec_J[i][1]<<endl;
	}


	p1.vec_P[0] = {1.0, 0.0};
	p1.vec_P[1] = {3.0/2.0, sqrt(3.0)/2.0};
	p1.vec_P[2] = {2.0, 0.0};


	cout<<endl;
	cout<<endl;
	cout<<"vec_P:"<<endl;
	for(int i=0;i<p1.NP;i++){
		cout<<i<<"\t"<<p1.vec_P[i][0]<<"\t"<<p1.vec_P[i][1]<<endl;
	}


	//pairing (delta) vectors
	p1.vec_S[0] = {1.0, 0.0};
	p1.vec_S[1] = {-1.0, 0.0};
	p1.vec_S[2] = {0.5, sqrt(3.0)/2.0};
	p1.vec_S[3] = {-0.5, -sqrt(3.0)/2.0};
	p1.vec_S[4] = {-0.5, sqrt(3.0)/2.0};
	p1.vec_S[5] = {0.5, -sqrt(3.0)/2.0};


	cout<<endl;
	cout<<endl;
	cout<<"vec_S"<<endl;
	for(int i=0;i<p1.NS;i++){
		cout<<i<<"\t"<<p1.vec_S[i][0]<<"\t"<<p1.vec_S[i][1]<<endl;
	}



	//*****************************************************************************************
	//****************table with hoppings for different displacement fields********************

	t1_tab[0] = -0.0155;
	t1_tab[1] = -0.0156;
	t1_tab[2] = -0.0155;
	t1_tab[3] = -0.0153;
	t1_tab[4] = -0.0153;
	t1_tab[5] = -0.0150;
	t1_tab[6] = -0.0148;
	t1_tab[7] = -0.0145;
	t1_tab[8] = -0.0142;
	t1_tab[9] = -0.0139;
	t1_tab[10] = -0.0136;
	t1_tab[11] = -0.0129;
	t1_tab[12] = -0.0123;
	t1_tab[13] = -0.0118;
	t1_tab[14] = -0.0114;

	l1_tab[0] = 0.0006;
	l1_tab[1] = 0.0006;
	l1_tab[2] = 0.0025;
	l1_tab[3] = 0.0038;
	l1_tab[4] = 0.0051;
	l1_tab[5] = 0.0063;
	l1_tab[6] = 0.0074;
	l1_tab[7] = 0.0085;
	l1_tab[8] = 0.0095;
	l1_tab[9] = 0.0106;
	l1_tab[10] = 0.0116;
	l1_tab[11] = 0.0133;
	l1_tab[12] = 0.0148;
	l1_tab[13] = 0.0161;
	l1_tab[14] = 0.0172;

	for(int i=0;i<11;i++){
		D_tab[i] = i*0.05;
	}
	D_tab[11] = 0.6;
	D_tab[12] = 0.7;
	D_tab[13] = 0.8;
	D_tab[14] = 0.9;


	//***************************************************************************************
	//******************Interpolation of the hopping values**********************************
    int NDp;
    double D_range;
    double D0; 
    NDp = 50;  //100;  //36;  //144;  //36;  //1152;   //288;  // 36;  // 144;  //72;  //36;

	double Dp_tab[NDp+1];
    double t1p_tab[NDp+1];
    double l1p_tab[NDp+1];
    D_range = 0.35;  //0.6 was for the DnV diagram calculations
    D0 = 0.35;      //0.0 was for the DnV diagram calculations

    ofstream ffout4i, ffout5i;


   	for(int i=0;i<=NDp;i++){     //values of the displacement field used for the interpolation
   		Dp_tab[i] = D0 + i*D_range/NDp;
   	}

    ffout4i.open("data_t.dat");
    ffout5i.open("data_l.dat");


    //*****carrying out the interpolation in order to have evenly spaced points in D*********

    gsl_interp_accel *acc = gsl_interp_accel_alloc ();
    gsl_spline *spline = gsl_spline_alloc (gsl_interp_cspline, 15);

    gsl_spline_init (spline, D_tab, t1_tab, 15);


   /*for (int in = 0; in <= 14; in++){
	   ffout4i<<D_tab[in]<<"\t"<<t1_tab[in]<<endl;
    }

   ffout4i<<endl;
   ffout4i<<endl;*/

   for (int in = 0; in <= NDp; in++){
	   t1p_tab[in] = gsl_spline_eval (spline, Dp_tab[in], acc);
       //cout<<in<<"\t"<<Dp_tab[in]<<endl;
       //ffout4i<<in<<"\t"<<Dp_tab[in]<<endl;
   }

   gsl_spline_free (spline);
   gsl_interp_accel_free (acc);

   ffout4i.close();

   //****************************************************************************************
   gsl_interp_accel *acc_l = gsl_interp_accel_alloc ();
   gsl_spline *spline_l = gsl_spline_alloc (gsl_interp_cspline, 15);
   gsl_spline_init (spline_l, D_tab, l1_tab, 15);


   for (int in = 0; in <= NDp; in++){
	   l1p_tab[in] = gsl_spline_eval (spline_l, Dp_tab[in], acc_l);
       //cout<<Dp_tab[in]<<"\t"<<l1p_tab[in]<<endl;
       //ffout5i<<Dp_tab[in]<<"\t"<<l1p_tab[in]<<endl;
   }

   gsl_spline_free (spline);
   gsl_interp_accel_free (acc);

   ffout5i.close();

   cout<<endl;
   cout<<"Printing our the table with the values of the displacement fields and the corresponding hoppings (real and imaginary part)"<<endl;
   for(int i=0;i<=NDp;i++){
	   cout<<i<<"\t"<<Dp_tab[i]<<"\t"<<t1p_tab[i]<<"\t"<<l1p_tab[i]<<"\t"<<0.5*sqrt(t1p_tab[i]*t1p_tab[i] + l1p_tab[i]*l1p_tab[i])<<endl;
   }
   cout<<endl;
   //*****************************************************************************************
   //*****************************************************************************************

	//parameters from Nat. Mat. 19, 861 (2020)
    double tt1, tt2, tt3, ll1, ll2, ll3;

    int Dn;
    //Dn = 8;

    tt1 = t1_tab[Dn]/2.0;
    tt2 =  0.0;      
    tt3 =  0.0;      

    ll1 =  l1_tab[Dn]/2.0;
    ll2 =  0.0;     
    ll3 =  0.0;     


    h1 = tt1 + 1i*ll1;
    h2 = tt2 + 1i*ll2;
    h3 = tt3 + 1i*ll3;


    p1.h1 = abs(h1);
    p1.h2 = abs(h2);
    p1.h3 = abs(h3);


    p1.phi1 = arg(h1);
    p1.phi2 = arg(h2);
    p1.phi3 = arg(h3);


	//defining the subsequent hopping parameters for spin up (this is only to print the dispersion relations to the file)
	p1.t_up[0] =  h1;
	p1.t_up[1] =  conj(h1);
	p1.t_up[2] =  conj(h1);
	p1.t_up[3] =  h1;
	p1.t_up[4] =  h1;
	p1.t_up[5] =  conj(h1);

	p1.t_up[6] =  h2;
	p1.t_up[7] =  conj(h2);
	p1.t_up[8] =  conj(h2);
	p1.t_up[9] =  h2;
	p1.t_up[10] =  h2;
	p1.t_up[11] =  conj(h2);

	p1.t_up[12] =  h3;
	p1.t_up[13] =  conj(h3);
	p1.t_up[14] =  conj(h3);
	p1.t_up[15] =  h3;
	p1.t_up[16] =  h3;
	p1.t_up[17] =  conj(h3);

	//defining the subsequent hopping parameters for spin down
	p1.t_do[0] =  conj(h1);
	p1.t_do[1] =  h1;
	p1.t_do[2] =  h1;
	p1.t_do[3] =  conj(h1);
	p1.t_do[4] =  conj(h1);
	p1.t_do[5] =  h1;

	p1.t_do[6] =  conj(h2);
	p1.t_do[7] =  h2;
	p1.t_do[8] =  h2;
	p1.t_do[9] =  conj(h2);
	p1.t_do[10] =  conj(h2);
	p1.t_do[11] =  h2;

	p1.t_do[12] =  conj(h3);
	p1.t_do[13] =  h3;
	p1.t_do[14] =  h3;
	p1.t_do[15] =  conj(h3);
	p1.t_do[16] =  conj(h3);
	p1.t_do[17] =  h3;


	cout<<endl;
	cout<<endl;
	cout<<"t:"<<endl;
	for(int i=0;i<p1.Nhop;i++){
		cout<<i<<"\t"<<p1.t_up[i]<<"\t"<<p1.t_do[i]<<endl;
	}

	//***********************printing the dispersion relation into a file*********************
	ek_to_file(p1.t_up, p1.vec_hop, "ekup.dat", 200, p1.Nhop);
	ek_to_file(p1.t_do, p1.vec_hop, "ekdo.dat", 200, p1.Nhop);
	//****************************************************************************************


	gsl_vector *x = gsl_vector_alloc(p1.NEq);   //vector of unknowns
	gsl_vector *x0 = gsl_vector_alloc(p1.NEq);  //vector of unknowns
	gsl_vector *dx = gsl_vector_alloc(p1.NEq);  //vector of unknowns
	gsl_vector *y = gsl_vector_alloc(p1.NEq);   //vector of left-hand side of the equation set



	//**************************reading the initial values from file**************************
	ifstream fin0;
	fin0.open("data0.dat");

	double xinit, x_dummy;
	int status_dummy, iter_dummy;
	double D_dummy;
	int Dn0;
	double U0;
	double ntot0;

	for(int j=0;j<aarg1;j++){
		fin0>>ntot0;
		fin0>>D_dummy;
		//fin0>>p1.T;
		fin0>>Dn0;  //D_dummy;
		fin0>>U0;
		for(int i=0;i<p1.NEq;i++){
			fin0>>xinit;
			cout<<xinit<<endl;
			gsl_vector_set( x0, i, xinit);
		}
		fin0>>x_dummy;
		fin0>>status_dummy;
		fin0>>iter_dummy;
	}
	fin0.close();

	//****************************************************************************************
	//*******************************printing out the initial values**************************
	cout<<endl;
	cout<<endl;
	cout<<"printing the initial values of our solution"<<endl;
	for(int i=0;i<p1.NEq;i++){
		cout<<i<<"\t"<<gsl_vector_get( x0, i )<<endl;
	}
	cout<<endl;
	//****************************************************************************************
	//****************************************************************************************

	//in case we want to test the function which determines the form of the self-consistent equations before running the multiroot solver
	int tst;
	double chern;
	double dos;

	/*p1.ntot = 0.9;
	p1.J = 0.007;
	p1.T = 0.001;
	p1.U = 0.0;


	tst = self_consistant_eqs(x0, &p1, y);

	for(int i = 0;i<p1.NEq;i++){
		cout<<gsl_vector_get(y, i)<<endl;
	}

	cout<<endl;
	cout<<"n = "<<p1.ntot<<endl;
	cout<<"J = "<<p1.J<<endl;
	cout<<"T = "<<p1.T<<endl;
	cout<<"U = "<<p1.U<<endl;


	chern = calc_chern(x0, &p1);

	cout<<"chern number = "<<chern<<endl;*/


	//*****************************************************************************************
	//******************here we prepare the table with subsequent angles***********************

	double *tet_tab;
	double dtet;

	tet_tab = new double[N_sym];

	dtet = 2*M_PI/N_sym;

	tet_tab[0] = 0.0;
	tet_tab[1] = 3*dtet;
	tet_tab[2] = dtet;
	tet_tab[3] = 4*dtet;
	tet_tab[4] = 2*dtet;
	tet_tab[5] = 5*dtet;

	//*********************preparing the multiroot solver from GSL*****************************
	//*****************************************************************************************
	const gsl_multiroot_fsolver_type *T;
	gsl_multiroot_fsolver *s;
	int status, status1, status2;
	size_t i, iter = 0;
	const size_t n = p1.NEq;
	gsl_multiroot_function f = {&self_consistant_eqs, n, &p1};


	//T = gsl_multiroot_fsolver_dnewton;
	//T = gsl_multiroot_fsolver_broyden;
	//T = gsl_multiroot_fsolver_hybrids;
	T = gsl_multiroot_fsolver_hybrid;
	s = gsl_multiroot_fsolver_alloc(T, n);


	ofstream ffout1, ffout2, ffout3, ffout4, ffout5, ffout6, ffout7;
	string dname1, dname2, dname3, dname4, dname5, dname6, dname7;
	string dname_disp, dname_delt, dname_params;
	string send, smid;
	string saarg1;
	stringstream ssaarg1;

	string saarg2;
	stringstream ssaarg2;


	dname1 = "data1_";
	send = ".dat";
	smid = "_";

	ssaarg1<<aarg1;
	saarg1 = ssaarg1.str();

	dname1.append(saarg1);
	dname1.append(send);

	dname2 = "data2_";
	dname2.append(saarg1);
	dname2.append(send);

	dname3 = "data3_";
	dname3.append(saarg1);
	dname3.append(send);

	dname4 = "data4_";
	dname4.append(saarg1);
	dname4.append(send);

	dname5 = "data5_";
	dname5.append(saarg1);
	dname5.append(send);

	dname6 = "data6_";
	dname6.append(saarg1);
	dname6.append(send);

	dname7 = "data7_";
	dname7.append(saarg1);
	dname7.append(send);


	ffout1.open(dname1.c_str());
	ffout2.open(dname2.c_str());
	ffout3.open(dname3.c_str());
	ffout4.open(dname4.c_str());
	ffout5.open(dname5.c_str());
	ffout6.open(dname6.c_str());
	ffout7.open(dname7.c_str());

	//****************************THE*MAIN*LOOP************************************************
	//*****************************************************************************************

	complex <double> ctemp;



	int Nn = 50;  //70
	for(int in=0; in<=Nn; in++){

		saarg2.clear();
		ssaarg2.str("");

	    dname_disp.clear();
	    dname_delt.clear();
	    dname_params.clear();

		ssaarg2<<in;

		saarg2 = ssaarg2.str();


		dname_disp = "data_disp_";   //name of the file where we will store the dispersion relation after solving the self-consistent equations
		dname_disp.append(saarg1);
		dname_disp.append(smid);
		dname_disp.append(saarg2);
		dname_disp.append(send);

		dname_delt = "data_delt_";   //name of the file where we will store the k-dependence of delta after solving the self-consistent equations
		dname_delt.append(saarg1);
		dname_delt.append(smid);
		dname_delt.append(saarg2);
		dname_delt.append(send);

		dname_params = "data_params_";  //name of the file where we will store the effective parameters
		dname_params.append(saarg1);
		dname_params.append(smid);
		dname_params.append(saarg2);
		dname_params.append(send);


		Dn = Dn0;    
		cout<<"D= "<<Dp_tab[Dn]<<endl;




		tt1 = t1p_tab[Dn]/2.0;
		tt2 = 0.0;      
		tt3 = 0.0;       

		ll1 = l1p_tab[Dn]/2.0;
		ll2 = 0.0;     
		ll3 = 0.0;      

	    h1 = tt1 + 1i*ll1;
	    h2 = tt2 + 1i*ll2;
	    h3 = tt3 + 1i*ll3;


		//changing the parameter values inside the for loop
		p1.ntot = ntot0 - in*0.04/Nn; 
 		p1.T = 0.001;
		p1.U = U0; 

		p1.J = 0.5 * 4.0*norm(h1)/p1.U;      //the 0.5 factor comes from the fact that we want to take interactions once per every bond

		p1.V = 0.5 * p1.U/3.635;            //the 0.5 factor comes from the fact that we want to take interactions once per every bond


		p1.h1 = abs(h1);
		p1.h2 = abs(h2);
		p1.h3 = abs(h3);

		p1.phi1 = arg(h1);
		p1.phi2 = arg(h2);
		p1.phi3 = arg(h3);

		//defining the subsequent hopping parameters for spin up (this is only to print the dispersion relations to the file)
		p1.t_up[0] =  h1 ;
		p1.t_up[1] =  conj(h1);
		p1.t_up[2] =  conj(h1);
		p1.t_up[3] =  h1;
		p1.t_up[4] =  h1;
		p1.t_up[5] =  conj(h1);

		p1.t_up[6] =  h2;
		p1.t_up[7] =  conj(h2);
		p1.t_up[8] =  conj(h2);
		p1.t_up[9] =  h2;
		p1.t_up[10] =  h2;
		p1.t_up[11] =  conj(h2);

		p1.t_up[12] =  h3;
		p1.t_up[13] =  conj(h3);
		p1.t_up[14] =  conj(h3);
		p1.t_up[15] =  h3;
		p1.t_up[16] =  h3;
		p1.t_up[17] =  conj(h3);

		//defining the subsequent hopping parameters for spin down
		p1.t_do[0] =  conj(h1);
		p1.t_do[1] =  h1;
		p1.t_do[2] =  h1;
		p1.t_do[3] =  conj(h1);
		p1.t_do[4] =  conj(h1);
		p1.t_do[5] =  h1;

		p1.t_do[6] =  conj(h2);
		p1.t_do[7] =  h2;
		p1.t_do[8] =  h2;
		p1.t_do[9] =  conj(h2);
		p1.t_do[10] =  conj(h2);
		p1.t_do[11] =  h2;

		p1.t_do[12] =  conj(h3);
		p1.t_do[13] =  h3;
		p1.t_do[14] =  h3;
		p1.t_do[15] =  conj(h3);
		p1.t_do[16] =  conj(h3);
		p1.t_do[17] =  h3;
		
		cout<<"ntot = "<<p1.ntot<<endl;
		cout<<"J = "<<p1.J<<endl;
		cout<<"U = "<<p1.U<<endl;
		cout<<"V = "<<p1.V<<endl;
		cout<<"h1 = "<<p1.h1<<endl;
		cout<<"phi1 = "<<p1.phi1<<endl;
		cout<<"Nk = "<<p1.Nk<<endl;
		cout<<"NDp = "<<NDp<<endl;
		cout<<"D_range = "<<D_range<<endl;
		cout<<"D0 = "<<D0<<endl;

		print_params_file(&p1, x, dname4.c_str());   //printing chosen parameters into the file

		

        //pair_density_to_file (x0, &p1, "pair_density.dat");


        cout<<"setting the solver"<<endl;

		gsl_multiroot_fsolver_set(s, &f, x0);  //preparing for iteration

		//*********************************start iterating***********************************
		iter = 0;
		do{
			iter++;
			status = gsl_multiroot_fsolver_iterate (s);

			cout<<"iteration = "<<iter<<endl;

			print_state_terminal (iter, s, p1.NEq);                      //printing the current solution on the screen
			print_state_file (iter, s, p1.NEq, dname4.c_str(), iter);    //printing the current solution to the file


			for(int i=0;i<p1.NEq;i++){
				gsl_vector_set(x0, i, gsl_vector_get (s->x, i));
			}

			if (status)   /* check if solver is stuck */
				break;

	    	status1 = gsl_multiroot_test_residual (s->f, 1e-6);         //1e-7
	    	status2 = gsl_multiroot_test_delta (dx, s->x, 1e-7, 0.0);  //1e-10
	    	cout<<"status1 = "<<status1<<endl;
	    	cout<<"status2 = "<<status2<<endl;
	    	cout<<endl;

			if (status1 == GSL_CONTINUE || status2 == GSL_CONTINUE){
				status = GSL_CONTINUE;
			}

	    }while (status == GSL_CONTINUE && iter < 50);
		//**********************************stop iterating***********************************

		printf ("status = %s\n", gsl_strerror (status)); //printing out the status
		cout<<"status = "<<status<<endl;



		//****************************calculating the chern number***************************

		chern = calc_chern(s->x, &p1);

		//disp_and_delta(s->x, &p1, dname_disp, dname_delt, dname_params, Dp_tab[Dn]);

		dos = dos_at_mu (s->x, &p1);

		//******************printing the final solution vector to the file*******************
		//ffout1<<p1.ntot<<"\t"<<p1.J<<"\t"<<Dn<<"\t"<<chern<<"\t";
		ffout1<<p1.ntot<<"\t"<<Dp_tab[Dn]<<"\t"<<Dn<<"\t"<<p1.U<<"\t";
		for(int i=0;i<p1.NEq;i++){
			ffout1<<gsl_vector_get (s->x, i)<<"\t";
		}
		ffout1<<p1.U<<"\t"<<status<<"\t"<<iter<<endl;

		//******printing the final solution vector multiplied by q*q to the file*******************
		calc_var(p1.ntot, gsl_vector_get(s->x, p1.NEq-1), var_tab);  //calculating the q factor with the use of ntot and x variational parameter
		q = var_tab[3];
		ffout3<<p1.ntot<<"\t"<<Dp_tab[Dn]<<"\t"<<p1.V<<"\t"<<chern<<"\t";
		for(int i=0;i<p1.NEq;i++){
			ffout3<<q*q*gsl_vector_get (s->x, i)<<"\t";
		}
		ffout3<<var_tab[0]<<"\t"<<var_tab[1]<<"\t"<<var_tab[2]<<"\t"<<var_tab[3]<<"\t"<<var_tab[4]<<endl;  //lmbd_0, lmbd_s, lmbd_d, q, gv


		//***********************************************************************************
		//***************Calculating the symmetry resolved gap amplitudes********************
		calc_delt_complex(s->x, p1.NS, p1.NP, delt_ud_c, delt_du_c);
		calc_delt_sym(p1.NS, p1.NP, N_sym, tet_tab, delt_ud_c, delt_du_c, delt_ud_sym, delt_du_sym);
		calc_delt_sym_spin(N_sym, delt_ud_sym, delt_du_sym, delt_s, delt_t);


		calc_delt_eff_complex(s->x, p1.NS, p1.NP, delt_eff_ud_c, delt_eff_du_c, &p1);

		calc_delt_sym(p1.NS, p1.NP, N_sym, tet_tab, delt_eff_ud_c, delt_eff_du_c, delt_eff_ud_sym, delt_eff_du_sym);

		calc_delt_sym_spin(N_sym, delt_eff_ud_sym, delt_eff_du_sym, delt_eff_s, delt_eff_t);

		//****************printing the pair-density in k-space to a file**********************
		//pair_density_to_file (s->x, &p1, "pair_density.dat");

		//*****************printing the symmetry resolved gap amplitudes**********************
		ffout5<<p1.ntot<<"\t"<<Dp_tab[Dn]<<"\t"<<p1.V<<"\t"<<chern<<"\t";
		for(int i=0;i<N_sym;i++){
			ffout5<<abs(delt_s[i])<<"\t";
		}
		for(int i=0;i<N_sym;i++){
			ffout5<<abs(delt_t[i])<<"\t";
		}

		for(int i=0;i<N_sym;i++){
			ffout5<<arg(delt_s[i])<<"\t";
		}
		for(int i=0;i<N_sym;i++){
			ffout5<<arg(delt_t[i])<<"\t";
		}


		for(int i=0;i<N_sym;i++){
			ffout5<<abs(delt_ud_sym[i])<<"\t";
		}
		for(int i=0;i<N_sym;i++){
			ffout5<<abs(delt_du_sym[i])<<"\t";
		}
		for(int i=0;i<N_sym;i++){
			ffout5<<arg(delt_ud_sym[i])<<"\t";
		}
		for(int i=0;i<N_sym;i++){
			ffout5<<arg(delt_du_sym[i])<<"\t";
		}


		for(int i=0;i<p1.NS;i++){
			ffout5<<abs(delt_ud_c[i])<<"\t";
		}
		for(int i=0;i<p1.NS;i++){
			ffout5<<abs(delt_du_c[i])<<"\t";
		}
		for(int i=0;i<p1.NS;i++){
			ffout5<<arg(delt_ud_c[i])<<"\t";
		}
		for(int i=0;i<p1.NS;i++){
			ffout5<<arg(delt_du_c[i])<<"\t";
		}
		ffout5<<endl;

		//***********printing the correlated symmetry resolved gap amplitudes*****************
		//ffout6<<p1.ntot<<"\t"<<p1.J<<"\t"<<p1.T<<"\t"<<p1.U<<"\t";
		//ffout6<<p1.ntot<<"\t"<<real(p1.E0)<<"\t"<<real(p1.EJ)<<"\t"<<real(p1.EG)<<"\t";
		//ffout6<<p1.ntot<<"\t"<<Dp_tab[Dn]<<"\t"<<Dn<<"\t"<<chern<<"\t";
		ffout6<<p1.ntot<<"\t"<<Dp_tab[Dn]<<"\t"<<p1.V<<"\t"<<p1.U<<"\t";
		for(int i=0;i<N_sym;i++){
			ffout6<<q*q*abs(delt_s[i])<<"\t";
		}
		for(int i=0;i<N_sym;i++){
			ffout6<<q*q*abs(delt_t[i])<<"\t";
		}

		for(int i=0;i<N_sym;i++){
			ffout6<<q*q*abs(delt_s[6+i])<<"\t";
		}
		for(int i=0;i<N_sym;i++){
			ffout6<<q*q*abs(delt_t[6+i])<<"\t";
		}


		for(int i=0;i<N_sym;i++){
			ffout6<<q*q*abs(delt_ud_sym[i])<<"\t";
		}
		for(int i=0;i<N_sym;i++){
			ffout6<<q*q*abs(delt_du_sym[i])<<"\t";
		}
		for(int i=0;i<N_sym;i++){
			ffout6<<arg(delt_ud_sym[i])<<"\t";
		}
		for(int i=0;i<N_sym;i++){
			ffout6<<arg(delt_du_sym[i])<<"\t";
		}


		for(int i=0;i<p1.NS;i++){
			ffout6<<q*q*abs(delt_ud_c[i])<<"\t";
		}
		for(int i=0;i<p1.NS;i++){
			ffout6<<q*q*abs(delt_du_c[i])<<"\t";
		}
		for(int i=0;i<p1.NS;i++){
			ffout6<<arg(delt_ud_c[i])<<"\t";
		}
		for(int i=0;i<p1.NS;i++){
			ffout6<<arg(delt_du_c[i])<<"\t";
		}
		ffout6<<dos<<"\t";
		ffout6<<endl;

		//***********************************************************************************
		//*****************printing the symmetry resolved effective gap amplitudes**********************

		ffout7<<p1.ntot<<"\t"<<p1.J<<"\t"<<Dn<<"\t"<<chern<<"\t";
		for(int i=0;i<N_sym;i++){
			ffout7<<abs(delt_eff_s[i])<<"\t";
		}
		for(int i=0;i<N_sym;i++){
			ffout7<<abs(delt_eff_t[i])<<"\t";
		}
		for(int i=0;i<N_sym;i++){
			ffout7<<abs(delt_eff_s[6+i])<<"\t";
		}
		for(int i=0;i<N_sym;i++){
			ffout7<<abs(delt_eff_t[6+i])<<"\t";
		}

		ffout7<<dos<<"\t";
		ffout7<<endl;


	}
	//***************************************************************************************

	gsl_multiroot_fsolver_free (s);
	gsl_vector_free (x);

	ffout1.close();
	ffout2.close();
	ffout3.close();
	//ffout4.close();
	ffout5.close();
	ffout6.close();
	ffout7.close();

	cout<<endl;
	cout<<endl;
	time_t after = time(0);
	t = clock() - t;

	cout <<"time: "<< after - now << endl;
	cout <<"number of clicks: "<<t << endl;

	cout<<"stop."<<endl;
}
