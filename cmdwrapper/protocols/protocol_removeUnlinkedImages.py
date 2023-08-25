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


"""
This protocol removes any metadata row for which the image file is not available.

"""
import glob
import os.path
import re
import sys

from pyworkflow.protocol import Protocol, params, Integer, MultiPointerParam, BooleanParam, StringParam
from pwem.protocols import ProtProcessParticles, ProtParticles, EMProtocol, ProtSets
from pyworkflow.utils import ProgressBar, getListFromRangeString

class RemoveUnlinkedImages(ProtSets):
    """ Protocol to remove items with missing binary files from a set. """
    _label = 'remove unlinked images'

    def _defineParams(self, form):
        form.addSection(label='Input')
        form.addParam('inputSet', params.PointerParam, pointerClass='EMSet',
                      label="Input Set", help="Select the set you want to clean.")

    def _insertAllSteps(self):
        self._insertFunctionStep('removeUnlinkedImagesStep')

    def removeUnlinkedImagesStep(self):
        inputFullSet = self.inputSet.get()
        inputClassName = self.inputSet.getClassName()

        nElements = len(inputFullSet.getIdSet())

        progress = ProgressBar(total=nElements, fmt=ProgressBar.NOBAR)
        progress.start()
        sys.stdout.flush()
        step = max(10000, nElements // 10000)

        try:
            outputSetFunction = getattr(self, "_create%s" % inputClassName)
            outputSet = outputSetFunction()
        except Exception:
            outputSet = inputFullSet.createCopy(self._getPath())

        outputSet.copyInfo(inputFullSet)


        for i, elem in enumerate(inputFullSet.iterItems()):
                if progress and i % step == 0:
                    progress.update(i+1)
                binary_file_path = elem.getFileName()  # Assuming the binary file path is accessible this way
                if os.path.exists(binary_file_path):
                    self._append(outputSet, elem)

        if outputSet.getSize():
            key = 'output' + inputClassName.replace('SetOf', '')
            self._defineOutputs(**{key: outputSet})
            self._defineTransformRelation(inputFullSet, outputSet)
        else:
            self.summaryVar.set('Output was not generated. Resulting set '
                                'was EMPTY!!!')

# class RemoveUnlinkedImages(EMProtocol):
#     """
#     This protocol allow you to run an arbitrary command on an input set of particles
#     (or several), and generates an starfile with one or more new metadata columns.
#     """
#     _label = 'Removed unlinked images'
#
#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         self.stepsExecutionMode = constants.STEPS_SERIAL
#
#     # -------------------------- DEFINE param functions ----------------------
#     def _defineParams(self, form):
#         form.addSection(label='Input')
#         form.addParam('inputSet', params.PointerParam, pointerClass='Set',
#                       label="Input Set")
#
#     def _getDefaultParallel(self):
#         """This protocol doesn't have mpi version"""
#         return (0, 0)
#
#     # --------------------------- STEPS functions ------------------------------
#     def _insertAllSteps(self):
#         # Insert processing steps
#
#         self._insertFunctionStep('createOutputStep')
#
#     def inputPartsStarFname(self, num):
#         return self._getExtraPath("particles%d.star"%num)
#
#
#     def createOutputStep(self):
#
#         input_set = self.inputSet.get()
#         output_set = Set.create(self._getPath("outputSet.sqlite"))
#
#         # Iterate through the items and check if the binary files exist
#         for item in input_set:
#             binary_file_path = item.getFileName()  # Assuming the binary file path is accessible this way
#             if os.path.exists(binary_file_path):
#                 output_set.append(item)
#
#         # Set the output
#         self._defineOutputs(outputSet=output_set)
#         self._defineTransformRelation(self.inputSet, output_set)
#
#     # --------------------------- INFO functions -----------------------------------
#
#     # def _msg(self):
#     #     return "You have run the command '"+self.command.get()+"'\n Env vars: %s"%self.envVars.get()
#     #
#     # def _summary(self):
#     #     """ Summarize what the protocol has done"""
#     #     summary = []
#     #
#     #     if self.isFinished():
#     #         summary.append(self._msg())
#     #     return summary
#     #
#     # def _methods(self):
#     #     methods = []
#     #
#     #     if self.isFinished():
#     #         methods.append(self._msg())
#     #     return methods
