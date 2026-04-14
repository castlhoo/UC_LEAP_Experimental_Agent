clc
close all
clear
%%
% Local workspace bootstrap
script_dir = fileparts(mfilename('fullpath'));
addpath(genpath(script_dir));

par = {}; %basic parameters
par.base_path = script_dir;
par.field_of_view = 36; %scan field of view in angstroms
par.scan_step_size = 4; %scan step size in angstroms
par.N_dp = 256; %size of experimental diffraction pattern in pixels
par.N_dp_orig = 1024; %size of true diffraction pattern in pixels
par.max_position_error = 0; %max scan position errors in angstroms
par.voltage = 200;

par.Niter = 500;
par.Niter_save_results_every = par.Niter;
par.grouping = inf;
par.method = 'MLc';
par.Nprobe = 1;

% for evaluation
par.ground_truth_recon = fullfile(par.base_path, 'MoSe2_2048_true_object.mat');

par.crop_y = 120;
par.crop_x = 120;

par.overwrite_data = true;

%% load true object
disp('Load test object...')
load(fullfile(par.base_path, 'MoSe2_2048.mat'))
proj_potentials = sigma_vz;
proj_potentials = padarray(proj_potentials, [1024, 1024], 'circular', 'post');

%create a complex object
par.object_true = ones(size(proj_potentials)).*exp(1i*proj_potentials);
par.dx = 0.1232; %real-space pixel size in angstrom

% Save reusable processed inputs
summary_dir = fullfile(par.base_path, 'summary');
if ~exist(summary_dir, 'dir'); mkdir(summary_dir); end
save(fullfile(summary_dir, 'MoSe2_2048_processed_inputs.mat'), 'proj_potentials', 'par', 'script_dir', '-v7.3');

disp('Load test object...done')
%% Test
%{
clc
par.dose = 1e7;
par.alpha_max = 20;
par.GPU_list = [1];
if par.dose < inf
    par.base_data_path = strcat('dose', num2str(par.dose));
else
    par.base_data_path = strcat('dose_inf');
end

par.base_data_path = sprintf([par.base_data_path,'_Ndp%d_ss%0.2fA_a%0.1fmrad_dx0.24A/probe'], par.N_dp, par.scan_step_size, par.alpha_max);

[recon_score] = sim_electron_ptycho_recon(par, 'df', 0, 'cs', 1.0);
%}
%% Use BO to find optimal aberrations
clc
par.dose = 1e7;
par.alpha_max = 20;
par.GPU_list = [1];

N_bo = 1;
verbose = 2;
%plot_funcs = {};
plot_funcs = {@plotObjectiveModel, @plotMinObjective};

df = optimizableVariable('df',[0, 400]); %nm
cs = optimizableVariable('cs',[0, 1],'Transform','none'); %mm
c5 = optimizableVariable('c5',[-1, 1]); %m
c7 = optimizableVariable('c7',[-2e3, 2e3], 'Transform','none'); %m
f_a2 = optimizableVariable('f_a2',[0, 150]); %nm
f_a3 = optimizableVariable('f_a3',[0, 10]); %um
theta_a2 = optimizableVariable('theta_a2',[0, pi]); %rad
theta_a3 = optimizableVariable('theta_a3',[0, 2*pi/3]); %rad

aberrations = 'df';


for i=1:N_bo
    close all
    N_workers = length(par.GPU_list);
    if N_workers>1
        delete(gcp('nocreate'))
        c = parcluster('local');
        c.NumWorkers = N_workers;
        p = parpool(c);
    end

    if par.dose < inf
        par.base_data_path = strcat('dose', num2str(par.dose));
    else
        par.base_data_path = strcat('dose_inf');
    end
    par.base_data_path = sprintf([par.base_data_path,'_Ndp%d_ss%0.2fA_a%0.1fmrad/probe'], par.N_dp, par.scan_step_size, par.alpha_max);

    switch aberrations
        case 'df'
            par.base_data_path = [par.base_data_path, '_', aberrations, '/probe'];
            fun = @(x)sim_electron_ptycho_recon(par, 'df', x.df);
            results = bayesopt(fun, [df],...
                'Verbose',verbose,...
                'AcquisitionFunctionName','expected-improvement-plus',...
                'ExplorationRatio', 0.3,...
                'IsObjectiveDeterministic',false,...
                'MaxObjectiveEvaluations', 50,...
                'NumSeedPoints', 5,...
                'PlotFcn',plot_funcs,'UseParallel', N_workers>1);
        case 'cs'
            par.base_data_path = [par.base_data_path, '_', aberrations, '/probe'];
            fun = @(x)sim_electron_ptycho_recon(par, 'cs', x.cs);
            results = bayesopt(fun, [cs],...
                'Verbose',verbose,...
                'AcquisitionFunctionName','expected-improvement-plus',...
                'ExplorationRatio', 0.3,...
                'IsObjectiveDeterministic',false,...
                'MaxObjectiveEvaluations', 50,...
                'NumSeedPoints', 5,...
                'PlotFcn',plot_funcs,'UseParallel', N_workers>1);
        case 'c7'
            par.base_data_path = [par.base_data_path, '_', aberrations, '/probe'];
            fun = @(x)sim_electron_ptycho_recon(par, 'c7', x.c7);
            results = bayesopt(fun, [c7],...
                'Verbose',verbose,...
                'AcquisitionFunctionName','expected-improvement-plus',...
                'IsObjectiveDeterministic',false,...
                'MaxObjectiveEvaluations', 50,...
                'NumSeedPoints', 5,...
                'PlotFcn',plot_funcs,'UseParallel', N_workers>1);
        case 'c5'
            par.base_data_path = [par.base_data_path, '_', aberrations, '/probe'];
            fun = @(x)sim_electron_ptycho_recon(par, 'c5', x.c5);
            results = bayesopt(fun, [c5],...
                'Verbose',verbose,...
                'AcquisitionFunctionName','expected-improvement-plus',...
                'ExplorationRatio', 0.3,...
                'IsObjectiveDeterministic',false,...
                'MaxObjectiveEvaluations', 50,...
                'NumSeedPoints', 5,...
                'PlotFcn',plot_funcs,'UseParallel', N_workers>1);
        case 'df_cs1.1mm'
            par.base_data_path = [par.base_data_path, '_', aberrations, '/probe'];
            fun = @(x)sim_electron_ptycho_recon(par, 'df', x.df, 'cs', 1.1);
            results = bayesopt(fun, [df],...
                'Verbose',verbose,...
                'AcquisitionFunctionName','expected-improvement-plus',...
                'ExplorationRatio', 0.3,...
                'IsObjectiveDeterministic',false,...
                'MaxObjectiveEvaluations', 50,...
                'NumSeedPoints', 5,...
                'PlotFcn',plot_funcs,'UseParallel', N_workers>1);
        case 'df_cs'
            par.base_data_path = [par.base_data_path, '_', aberrations, '/probe'];
            fun = @(x)sim_electron_ptycho_recon(par, 'df', x.df, 'cs', x.cs);
            results = bayesopt(fun, [df, cs],...
                'Verbose', verbose,...
                'AcquisitionFunctionName', 'expected-improvement-plus',...
                'ExplorationRatio', 0.3,...
                'IsObjectiveDeterministic', false,...
                'MaxObjectiveEvaluations', 100,...
                'NumSeedPoints', 20,...
                'PlotFcn',plot_funcs,'UseParallel', N_workers>1);
        case 'f_a2_theta_a2'
            par.base_data_path = [par.base_data_path, '_', aberrations, '/probe'];
            fun = @(x)sim_electron_ptycho_recon(par, 'f_a2', x.f_a2, 'theta_a2', x.theta_a2);
            results = bayesopt(fun, [f_a2, theta_a2],...
                'Verbose', verbose,...
                'AcquisitionFunctionName', 'expected-improvement-plus',...
                'ExplorationRatio', 0.3,...
                'IsObjectiveDeterministic', false,...
                'MaxObjectiveEvaluations', 100,...
                'NumSeedPoints', 20,...
                'PlotFcn',plot_funcs,'UseParallel', N_workers>1);
       case 'f_a3_theta_a3'
            par.base_data_path = [par.base_data_path, '_', aberrations, '/probe'];
            fun = @(x)sim_electron_ptycho_recon(par, 'f_a3', x.f_a3, 'theta_a3', x.theta_a3);
            results = bayesopt(fun, [f_a3, theta_a3],...
                'Verbose', verbose,...
                'AcquisitionFunctionName', 'expected-improvement-plus',...
                'ExplorationRatio', 0.3,...
                'IsObjectiveDeterministic', false,...
                'ExplorationRatio', 0.1,...
                'MaxObjectiveEvaluations', 100,...
                'NumSeedPoints', 20,...
                'PlotFcn',plot_funcs,'UseParallel', N_workers>1);
        case 'df_cs_c5'
            par.base_data_path = [par.base_data_path, '_', aberrations, '/probe'];
            fun = @(x)sim_electron_ptycho_recon(par, 'df', x.df, 'cs', x.cs, 'c5', x.c5);
            results = bayesopt(fun, [df, cs, c5],...
                'Verbose', verbose,...
                'AcquisitionFunctionName', 'expected-improvement-plus',...
                'ExplorationRatio', 0.3,...
                'IsObjectiveDeterministic', false,...
                'MaxObjectiveEvaluations', 200,...
                'NumSeedPoints', 30,...
                'PlotFcn',plot_funcs,'UseParallel', N_workers>1);
    end

    %save BO result
    save_path = sprintf([par.base_path,'/summary/bo_dose%d_Ndp%d_ss%0.2fA_a%0.1fmrad/'], par.dose, par.N_dp, par.scan_step_size, par.alpha_max);
    save_name = sprintf([aberrations, '_%d.mat'], i+4);

    if ~exist(save_path, 'dir'); mkdir(save_path); end
    save(fullfile(save_path,save_name),'results')
    save(fullfile(save_path, sprintf('%s_%d_metadata.mat', aberrations, i+4)), 'par', 'aberrations', 'N_bo', 'verbose', 'script_dir', '-v7.3');

    delete(gcp('nocreate'))

end

disp('Optimization completed')
