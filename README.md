# Bath Photonics 2 Lab pieces

App pieces for Photonics 2 lab, Department of Physics, University of Bath. 

## Brief Introduction

This module contains the pieces for buliding the experiments notebook with GUI. Pieces includes hardware communications and measurement modules for basic measurement routine. These pieces are designed for the use in the environment of Bath Photonics 2 Lab.

## How to use the code

Git pull this ......

### Note to datasets
git clone https://github.com/jdranczewski/dataset-suite.git in document, and rename the folder to "datasets", and add .pth file in venv\Lib\site-packages

Usage: import datasets as ds

### Issues to be fixed
* Randomly happens a +- 1 count offset per pixels (Dark count?), independent to integration time, vs_speed and amp_mode settings
* Fire laser only when CCD integrating & threading