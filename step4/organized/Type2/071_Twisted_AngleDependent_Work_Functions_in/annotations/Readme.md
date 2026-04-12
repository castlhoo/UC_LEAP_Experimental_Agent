# Transport effects of twist-angle disorder in mesoscopic twisted bilayer graphene

Magic-angle twisted bilayer graphene is a tunable material with remarkably flat energy bands near the Fermi level, leading to fascinating transport properties and correlated states at low temperatures. However, grown pristine samples of this material tend to break up into landscapes of twist-angle domains, strongly influencing the physical properties of each individual sample. This poses a significant problem to the interpretation and comparison between measurements obtained from different samples. In this work, we study numerically the effects of twist-angle disorder on quantum electron transport in mesoscopic samples of magic-angle twisted bilayer graphene. We find a significant property of twist-angle disorder that distinguishes it from onsite-energy disorder: it leads to an asymmetric broadening of the energy-resolved conductance. The magnitude of the twist-angle variation has a strong effect on conductance, while the number of twist-angle domains is of much lesser significance. We further establish a relationship between the asymmetric broadening and the asymmetric density of states of twisted bilayer graphene at angles smaller than the first magic angle. Our results show that the qualitative differences between the types of disorder in the energy-resolved conductance of twisted bilayer graphene samples can be used to characterize them at temperatures above the critical temperatures of the correlated phases, enabling systematic experimental studies of the effects of the different types of disorders also on the other properties such as the competition of the different types of correlated states appearing at lower temperatures.

## Contents

+ The jupyter script `Code/figure_creator.ipynb` that generates all the figures presented in the manuscript.

+ The jupyter script `Code/generate_disorder_domains.ipynb` that contains the code used to generate randomized disorder domains

+ The folder `Data` that contains all the data for the figures.

## Python requirements

+ The file `twist-disorder.yml` contains the list of packages required for an environment to run the jupyter scripts. This environment can be installed using Conda by running the following command `conda env create -f twist-disorder.yml`. After installing, it is necessary to activate the environment, which can be done with the command `conda activate twist-disorder`.

+ The package `descartes` has an incompatibility bug with the package `shapely`, this causes an error while plotting figure A1. We have included a file `/Code/Descartes fix/patch.py` that fixes this issue. After installation of the environment, it is necessary to replace the installed file (typically located in `/home/user/anaconda3/envs/twist-disorder/lib/python3.8/site-packages/patch.py`) with the fixed one.
