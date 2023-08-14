import requests
import gzip
import shutil
from pyworkflow.protocol import Protocol, params

class DownloadEMDBMap(Protocol):
    _label = 'download emdb map'

    def _defineParams(self, form):
        form.addSection(label='Input')
        form.addParam('emdbId', params.StringParam, label="EMDB ID", help="Enter the EMDB ID of the map you want to download.")

    def _insertAllSteps(self):
        self._insertFunctionStep('downloadEMDBMapStep')

    def downloadEMDBMapStep(self):
        emdb_id = self.emdbId.get()
        url = f'https://ftp.ebi.ac.uk/pub/databases/emdb/structures/EMD-{emdb_id}/map/emd_{emdb_id}.map.gz'
        response = requests.get(url)

        # Check if the download was successful
        if response.status_code == 200:
            compressed_path = self._getExtraPath(f'emd_{emdb_id}.map.gz')
            with open(compressed_path, 'wb') as file:
                file.write(response.content)

            # Decompress the file
            decompressed_path = self._getExtraPath(f'emd_{emdb_id}.map')
            with gzip.open(compressed_path, 'rb') as f_in:
                with open(decompressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:
            raise Exception(f"Failed to download EMDB map with ID {emdb_id}")
