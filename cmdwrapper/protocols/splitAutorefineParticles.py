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
import os

from pwem.protocols import ProtProcessParticles
from pyworkflow.protocol import PointerParam, IntParam
from pyworkflow.utils import makePath
from relion.convert import writeSetOfParticles, readSetOfParticles


class ProtRelionAutorefSplitData(ProtProcessParticles):
    """ Protocol to split a Relion autorefine run into subsets """
    _label = 'split relion autorefine run particles'

    def _defineParams(self, form):
        form.addSection(label='Input')
        # Directly add a pointer parameter to select the previous autorefine run
        form.addParam('inputAutoRefineRun', PointerParam,
                      pointerClass='ProtRelionAutoRefine',
                      label='Select autorefine run',
                      help='Select a previous autorefine run to split the particle stacks.')

        form.addParam('numberOfSubsets', IntParam, default=2,
                      label="Number of subsets",
                      help="Number of subsets to split the particles into.")

    def _insertAllSteps(self):

        self._insertFunctionStep('splitRunStep')

    def splitRunStep(self):
        # Get the particles directly from the autorefine run input
        inputParticles = self.inputAutoRefineRun.get().outputParticles

        nSubsets = self.numberOfSubsets.get()
        nParticles = inputParticles.getSize()
        particlesPerSubset = nParticles // nSubsets

        subsetLists = [[] for _ in range(nSubsets)]

        for idx, particle in enumerate(inputParticles):
            subsetIndex = idx // particlesPerSubset
            if subsetIndex >= nSubsets:
                subsetIndex = nSubsets - 1  # push remaining particles into the last subset
            subsetLists[subsetIndex].append(particle)

        for subsetIndex, subset in enumerate(subsetLists):
            outputSet = self._createSetOfParticles()
            outputSet.copyInfo(inputParticles)
            outputSetPath = self._getExtraPath(f"subset_{subsetIndex}")
            makePath(outputSetPath)
            subsetStar = os.path.join(outputSetPath, "particles.star")

            # Write the particles to a new star file
            writeSetOfParticles(subset, subsetStar, outputDir=outputSetPath)

            # This assumes there's a function in relion.convert like readSetOfParticles
            # to populate the Scipion object from a star file
            readSetOfParticles(subsetStar, outputSet)

            self._defineOutputs(**{f"outputSubset_{subsetIndex}": outputSet})
            self._defineTransformRelation(inputParticles, outputSet)

    def _methods(self):
        return ["Particles were split into %d subsets." % self.numberOfSubsets.get()]