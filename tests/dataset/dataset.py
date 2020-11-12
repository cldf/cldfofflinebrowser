from pathlib import Path

import cldfbench


class Dataset(cldfbench.Dataset):
    dir = Path(__file__).parent
    id = "dataset"

    def cldf_specs(self):
        return {
            None: cldfbench.CLDFSpec(
                dir=self.cldf_dir,
                module='Wordlist',
                writer_cls=cldfbench.CLDFWriter,
            ),
        }
