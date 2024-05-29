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
This protocol allow you to run an arbitrary command on an input set of particles
(or several), and generates a starfile with one or more new metadata columns.

"""
import glob
import os.path
import re

import pwem
from pwem.objects import Volume
from pyworkflow.protocol import Protocol, params, Integer, MultiPointerParam, BooleanParam, StringParam
from pyworkflow.utils import Message, replaceBaseExt
import pwem.objects as emobj
from pwem.protocols import ProtProcessParticles, ProtParticles, EMProtocol
import relion.convert as convert
from pyworkflow.protocol import constants
from pyworkflow.plugin import Plugin


class GenericCmdProtocol(EMProtocol):
    """
    This protocol allow you to run an arbitrary command on an input set of particles
    (or several), and generates an starfile with one or more new metadata columns.
    """
    _label = 'genericCmdProtocol'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.stepsExecutionMode = constants.STEPS_SERIAL

    # -------------------------- DEFINE param functions ----------------------
    def _defineParams(self, form):

        form.addSection(label=Message.LABEL_INPUT)

        form.addParam('useParticles', BooleanParam,
                      default=True,
                      label="Use particles?")

        form.addParam('inputParticles', MultiPointerParam,
                      pointerClass='SetOfParticles',
                      condition='useParticles',
                      label="Input particles",
                      help='Select the sets of particles that you want to use. They will be accessible as '
                           '$EXTRA_DIR/particles0.star $EXTRA_DIR/particles1.star and so on',
                      allowsNull=True)

        form.addParam('useVolumes', BooleanParam,
                      default=False,
                      label="Use volumes?")

        form.addParam('inputVolumes', MultiPointerParam,
                      pointerClass='Volume',
                      condition='useVolumes',
                      label="Input volumes",
                      help='Select the volumes that you want to use. They will be accessible as '
                           '$EXTRA_DIR/volume0.star $EXTRA_DIR/volume1.star and so on',
                      allowsNull=True)

        # form.addParam('useMicrographs', BooleanParam,
        #               default=False,
        #               label="Use micrographs?")
        #
        # form.addParam('inputMicrographs', MultiPointerParam,
        #               pointerClass='SetOfMicrographs',
        #               condition='useMicrographs',
        #               label="Input micrographs",
        #               help='Select the sets of micrographs that you want to use. They will be accessible as '
        #                    'micrographs0.star micrographs1.star and so on',
        #               allowsNull=True)

        form.addSection(label="Command")
        form.addParam('command', params.StringParam,
                      default=None,
                      label='command', important=True,
                      help='Which command should be executed. Particle sets can '
                           'be accessed as $EXTRA_DIR/particles0.star $EXTRA_DIR/particles2.star, etc. '
                           'The output starfiles generated by the command '
                           'need to follow the patterns defined at the Outputs section and will be written at '
                           'the extra dir as well. $WORKING_DIR points'
                           'to the project root directory ($WORKING_DIR/Runs/...')

        form.addParam('envVars', params.StringParam,
                      default=None,
                      label='ENV vars', allowsNull=True,
                      help='Environmental variables need to run the command.')

        form.addParam('addEnvsToScipion', BooleanParam,
                      default=True,
                      label="Add ENV vars to Scipion",
                      help="Add Environmental variables to Scipion ones (True)or use only ENV vars (False)?")

        form.addParam('condaEnv', params.StringParam,
                      default=None,
                      label='Conda env', allowsNull=True,
                      help='Conda environment to be activated before running the command')

        form.addSection(label=Message.LABEL_OUTPUT)

        form.addParam('outputParticlesFilenames', StringParam,
                      default='outputParticles*.star',
                      label="Output particles filenames pattern",
                      help='Pattern for the output particles filenames. Use * as a placeholder for the output number.'
                           'It will be assumed that the outputFileName is written in $EXTRA_DIR')

        # form.addParam('outputMicrographsFilenames', StringParam,
        #               default='outputMicrographs*.star',
        #               label="Output micrographs filenames pattern",
        #               help='Pattern for the output micrographs filenames. Use * as a placeholder for the output number.'
        #                    'It will be assumed that the outputFileName is written in $EXTRA_DIR')

        form.addParam('outputVolumesFilenames', StringParam,
                      default='outputVolume*.star',
                      label="Output volumes filenames pattern",
                      help='Pattern for the output volumes filenames. Use * as a placeholder for the output number.'
                           'It will be assumed that the outputFileName is written in $EXTRA_DIR')

        form.addParam('extraLabels', StringParam,
                      label="Output extra labels", default='',
                      help="Space separated list of Relion labels "
                           "(without leading underscore) to parse from "
                           "the output STAR files. ")

        __threads, __mpi = self._getDefaultParallel()

        form.addParallelSection(threads=__threads, mpi=__mpi)



    def _getDefaultParallel(self):
        """This protocol doesn't have mpi version"""
        return (0, 0)

    # --------------------------- STEPS functions ------------------------------
    def _insertAllSteps(self):
        # Insert processing steps
        self._insertFunctionStep('convertInputStep')
        self._insertFunctionStep('executeCmd')
        self._insertFunctionStep('createOutputStep')

    def inputPartsStarFname(self, num):
        return self._getExtraPath("particles%d.star"%num)

    def inputVolStarFname(self, num):
        return self._getExtraPath("volume%d.mrc"%num)


    def convertInputStep(self):

        cmd = self.command.get()
        for i, pointer in enumerate(self.inputParticles):
            inputSet = pointer.get()
            convert.writeSetOfParticles(inputSet,
                                        self.inputPartsStarFname(i),
                                        postprocessImageRow=None)
            assert os.path.basename(self.inputPartsStarFname(i)) in cmd, \
                f"Error, {self.inputPartsStarFname(i)}  not found in your command"

        for i, pointer in enumerate(self.inputVolumes):
            inputVol = pointer.get()
            newPix = inputVol.getSamplingRate()
            newDim = inputVol.getXDim()
            if not inputVol.getFileName().endswith('.mrc'):
                inputVol.setLocation(convert.convertBinaryVol(inputVol, self._getTmpPath()))
            convert.convertMask(inputVol, self.inputVolStarFname(i), newPix=newPix, newDim=newDim, threshold=False)
            assert os.path.basename(self.inputVolStarFname(i)) in cmd, \
                f"Error, {self.inputVolStarFname(i)}  not found in your command"

    def replaceDirs(self, s):
        s= s.replace("$EXTRA_DIR", self._getExtraPath() + "/")
        s = s.replace("$WORKING_DIR", self.getProject().getPath() + "/")
        return s

    def executeCmd(self):

        if self.addEnvsToScipion.get():
            envvars = os.environ.copy()
        else:
            envvars = {}

        envvarsStr = self.envVars.get()
        if envvarsStr:

            pattern = r'\b\w+=.*?(?=\s*\w+=|$)'
            matches = re.findall(pattern, envvarsStr)
            # For each match, split the string into the variable name and value, and set the variable in the environment
            for match in matches:
                name, value = match.split('=', 1)
                envvars[name] = str(value).rstrip()

        cmd = self.command.get()
        condaEnv = self.condaEnv.get()
        if condaEnv:
            # cmd = f'eval "$(conda shell.bash hook)" && conda activate {condaEnv} && {cmd}'
            condaActivateCmd = Plugin.getCondaActivationCmd()
            if not condaActivateCmd:
                condaActivateCmd = "conda activate "
            else:
                if not condaActivateCmd.rstrip().endswith("activate"):
                    condaActivateCmd += " conda activate "
            cmd = f'{condaActivateCmd} {condaEnv} && {cmd}'
        import subprocess
        print(f"env vars: {envvars}")
        print(cmd)
        cmd = self.replaceDirs(cmd)
        with open(self._getExtraPath("command.txt"), "w") as f:
            f.write(cmd)

        stdout = subprocess.PIPE
        stderr = subprocess.PIPE
        output = ""
        error = " "
        with subprocess.Popen(cmd, stdout=stdout, stderr=stderr, bufsize=32, env=envvars,
                              universal_newlines=True, shell=True) as p:
            for line in p.stdout:
                print(line, end='', flush=True)  # process line here
                output += line

            for line in p.stderr:
                print(line, end='', flush=True)  # process line here
                error += line

        returncode = p.returncode
        if hasattr(stderr, "close"):
            stderr.close()
        if hasattr(stdout, "close"):
            stdout.close()
        if returncode != 0:
            output += "ERROR:\n" + error
            print(error, flush=True)
            raise RuntimeError(output)

    def createOutputStep(self):
        particleFnames = glob.glob(self._getExtraPath(self.outputParticlesFilenames.get()))
        particlesCounter = 0
        volsCounter = 0

        if particleFnames:
            for particleFname in particleFnames:
                partSet = self._createSetOfParticles()
                # partSet.copyInfo(self.inputSet.get()) Not needed for relion 3.1 starfiles
                convert.readSetOfParticles(particleFname, partSet,
                                           alignType=pwem.constants.ALIGN_PROJ,
                                           extraLabels=self.extraLabels.get().split()
                                           )
                self._defineOutputs(**{"outputParticles"+str(particlesCounter): partSet})
                particlesCounter += 1
                if self.useParticles.get():
                    for pointer in self.inputParticles:
                        self._defineSourceRelation(pointer, partSet)

                # if self.useMicrographs.get():
                #     for pointer in self.inputMicrographs:
                #         self._defineSourceRelation(pointer, partSet)

                if self.useVolumes.get():
                    for pointer in self.inputVolumes:
                        self._defineSourceRelation(pointer, partSet)


        volFnames = glob.glob( self._getExtraPath(self.outputVolumesFilenames.get()))
        if volFnames:
            for volFname in volFnames:
                vol = Volume()
                vol.setFileName(volFname)

                self._defineOutputs(**{"outputVol"+str(volsCounter): vol})
                volsCounter += 1
                if self.useParticles.get():
                    for pointer in self.inputParticles:
                        self._defineSourceRelation(pointer, vol)

                # if self.useMicrographs.get():
                #     for pointer in self.inputMicrographs:
                #         self._defineSourceRelation(pointer, partSet)

                if self.useVolumes.get():
                    for pointer in self.inputVolumes:
                        self._defineSourceRelation(pointer, vol)

        assert particleFnames or volFnames, "Error, no valid output detected"
    # --------------------------- INFO functions -----------------------------------

    def _msg(self):
        return "You have run the command '"+self.command.get()+"'\n Env vars: %s"%self.envVars.get()

    def _summary(self):
        """ Summarize what the protocol has done"""
        summary = []

        if self.isFinished():
            summary.append(self._msg())
        return summary

    def _methods(self):
        methods = []

        if self.isFinished():
            methods.append(self._msg())
        return methods
