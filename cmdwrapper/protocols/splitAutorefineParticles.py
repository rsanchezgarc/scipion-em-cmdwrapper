# -*- coding: utf-8 -*-
# **************************************************************************
# *
# * Authors:     Ruben Sanchez Garcia (ruben.sanchez-garcia@stats.ox.ac.uk
# *
# * University of Oxford, Dept. of Statistics
# *
# * This program is free software; you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation; either version 2 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program; if not, write to the Free Software
# * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# * 02111-1307  USA
# *
# *  All comments concerning this program package may be sent to the
# *  e-mail address 'you@yourinstitution.email'
# *
# **************************************************************************
import glob
import os
import random
import starfile
from pwem import ALIGN_PROJ

from pwem.protocols import ProtProcessParticles
from pyworkflow.protocol import PointerParam, IntParam, BooleanParam
from pyworkflow.utils import makePath
from relion.convert import readSetOfParticles
from starstack.particlesStar import ParticlesStarSet


class ProtRelionAutorefSplitData(ProtProcessParticles):
    """ Protocol to split a Relion autorefine run into subsets """
    _label = 'split relion autorefine run particles'

    def _defineParams(self, form):
        form.addSection(label='Input')
        form.addParam('inputAutoRefineRun', PointerParam,
                      pointerClass='ProtRelionRefine3D',
                      label='Select autorefine run',
                      help='Select a previous autorefine run to split the particle stacks.')
        form.addParam('numberOfSubsets', IntParam, default=2,
                      label="Number of subsets",
                      help="Number of subsets to split the particles into.")
        form.addParam('randomize', BooleanParam, default=False,
                      label="Randomize particle indices?",
                      help="If set to True, particles will be randomly assigned to subsets.")

    def _insertAllSteps(self):
        self._insertFunctionStep('splitRunStep')


    def _methods(self):
        return [f"Particles were split into {self.numberOfSubsets.get()} subsets."]

    def splitRunStep(self):
        inputParticles = self.inputAutoRefineRun.get().outputParticles
        extra_path = self.inputAutoRefineRun.get()._getExtraPath()
        list_of_files = glob.glob(os.path.join(extra_path, '*_data.star'))
        latest_file = max(list_of_files, key=os.path.getctime)

        starData = starfile.read(latest_file)

        psset = ParticlesStarSet(latest_file)

        particles_data = starData['particles']
        n_parts = len(particles_data)
        if self.randomize.get():
            print("Shuffling idxs")
            particles_data = particles_data.sample(frac=1).reset_index(drop=True)

        nSubsets = self.numberOfSubsets.get()
        nParticles = len(particles_data)
        particlesPerSubset = nParticles // nSubsets

        for subsetIndex in range(nSubsets):
            start_idx = subsetIndex * particlesPerSubset
            end_idx = start_idx + particlesPerSubset if subsetIndex < nSubsets - 1 else nParticles
            subsetStar = self._getExtraPath(f"subset_{subsetIndex}", f"particles_{subsetIndex}.star")
            subsetMrcs = self._getExtraPath(f"subset_{subsetIndex}", f"particles_{subsetIndex}.mrcs")
            print("Writing here : ", os.path.split(subsetStar)[0])
            os.makedirs(os.path.split(subsetStar)[0], exist_ok=True)
            print(start_idx, end_idx)
            psset_subset = psset.createSubset(start_idx, end_idx)
            scipion_starfile = self._getTmpPath(f"subset_{subsetIndex}_particles.star")
            psset_subset.save(scipion_starfile,
                               stackFname=None, overwrite=True, basenameOnlyForNewStar=False)
            psset_subset.save(subsetStar, stackFname=subsetMrcs, overwrite=True, basenameOnlyForNewStar=True)

            #TODO: This part is not working, the N outputs of the protocol are the same.
            # outputSet = self._createSetOfParticles()
            # outputSet.copyInfo(inputParticles)
            # readSetOfParticles(scipion_starfile, outputSet, alignType=ALIGN_PROJ)
            # outputs = {}
            # outputs[f"outputSubset_{subsetIndex}"] = outputSet
            # self._defineOutputs(**outputs)
            # print(outputSet)
        # for n,o in outputs.items():
        #     print(n,o)
        #     self._defineOutputs(n=o)
        #     self._store(o)
            # self._defineTransformRelation(inputParticles, o)
