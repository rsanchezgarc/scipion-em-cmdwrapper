
from glob import glob

from pyworkflow.tests import setupTestProject, DataSet
from pyworkflow.plugin import Domain
from pyworkflow.utils import magentaStr
from pwem.objects import SetOfMovies
from pwem.protocols import (ProtImportAverages, ProtImportCTF,
                            ProtImportParticles, ProtImportCoordinates)

# from relion.protocols import *
from relion.convert import *
from relion.constants import *
from relion.convert.convert31 import OpticsGroups
from relion.tests.test_protocols_base import TestRelionBase, USE_GPU, RUN_CPU, CPUS, MTF_FILE

from cmdwrapper.protocols import GenericCmdProtocol


class TestGenericCmd(TestRelionBase):

    @classmethod
    def setUpClass(cls):
        setupTestProject(cls)
        cls.dataset = DataSet.getDataSet('relion_tutorial')
        cls.partRef3dFn = cls.dataset.getFile('import/refine3d/extra/relion_data.star')
        cls.protImport = cls.runImportParticlesStar(cls.partRef3dFn, 7.08)

    def test_single(self):

        genericCmd = self.newProtocol(GenericCmdProtocol,
                                      useParticles=True,
                                      useVolumes=False,
                                      condaEnv=None,
                                      command='pwd && ls $EXTRA_DIR/particles0.star && scipion python -c "import starfile; data = starfile.read(\'$EXTRA_DIR/particles0.star\');data[\'particles\'][\'newMetadata\']=1.; print(data);starfile.write(data, \'$EXTRA_DIR/outputParticles0.star\')" ',
                                      extraLabels='newMetadata',
                                      areThereOutputVols=False,
                                      )

        genericCmd.inputParticles.set([self.protImport.outputParticles])
        genericCmd = self.launchProtocol(genericCmd)
        output = genericCmd.outputParticles0
        # print(dir(output))
        # print(output.getObjDict())
        # print(list(output.getAttributes()))
        first = output.getFirstItem()
        attributes = first.getObjDict()
        self.assertTrue('_newMetadata' in attributes,
                        msg="Error, new metadata label not found")
        self.assertAlmostEqual(first._newMetadata.get(), 1.0)

        output.close()

