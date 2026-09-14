# Acknowledgements and research provenance

Only Bears is an independent application built on research and software created by the BrownBear_ReID team. We are grateful to the researchers, field teams, and contributors whose work made pose-aware brown-bear re-identification possible.

## Research foundation

Please cite the associated paper when using or building on this work:

> Beth Rosenberg, Mu Zhou, Nathan Wolf, Mackenzie Weygandt Mathis, Bradley P. Harris, and Alexander Mathis. “[Individual identification of brown bears using pose-aware metric learning](https://doi.org/10.1016/j.cub.2025.12.022).” *Current Biology* 36, no. 3 (2026): 645–659.e14. DOI: [10.1016/j.cub.2025.12.022](https://doi.org/10.1016/j.cub.2025.12.022). [PubMed record](https://pubmed.ncbi.nlm.nih.gov/41558480/).

## Upstream software

The recognition worker includes a locally adapted subset of the PoseSwin implementation from the Mathis Lab’s [BrownBear_ReID repository](https://github.com/amathislab/BrownBear_ReID), pinned to commit [`4a9f5be8a57c7493096cab1b114dcd71489a3dbe`](https://github.com/amathislab/BrownBear_ReID/tree/4a9f5be8a57c7493096cab1b114dcd71489a3dbe). The upstream repository credits Beth Rosenberg, Mu Zhou, Nathan Wolf, Mackenzie W. Mathis, Bradley P. Harris, and Alexander Mathis.

Only Bears adds the photo-library, review, identity-management, deployment, and human-confirmation workflow around that research foundation. It is an independent project and is not presented as an official Mathis Lab, EPFL, or Alaska Pacific University application.

Technical source hashes and local modifications are recorded in [`workers/vendor/NOTICE`](workers/vendor/NOTICE) and [`workers/vendor/SOURCE_HASHES.json`](workers/vendor/SOURCE_HASHES.json). At the pinned upstream commit, no code license file was present; the upstream dataset README declares its dataset under CC BY-NC 4.0, while checkpoint terms are unspecified. Those questions must be resolved before any broader or commercial rollout.
