import {Link, Typography} from '@mui/material';

export const PAPER_URL='https://pubmed.ncbi.nlm.nih.gov/41558480/';
export const DOI_URL='https://doi.org/10.1016/j.cub.2025.12.022';
export const SOURCE_URL='https://github.com/amathislab/BrownBear_ReID';

const externalProps={target:'_blank',rel:'noreferrer'} as const;

export function ResearchCredits(){
 return <div className="research-credits">
  <Typography component="p" variant="body2">Only Bears builds on pose-aware brown-bear re-identification research by Beth Rosenberg, Mu Zhou, Nathan Wolf, Mackenzie Weygandt Mathis, Bradley P. Harris, and Alexander Mathis.</Typography>
  <Typography component="p" variant="body2"><Link href={PAPER_URL} {...externalProps}><cite>Individual identification of brown bears using pose-aware metric learning</cite></Link><br/><span className="research-citation">Current Biology 36(3), 645–659.e14 (2026) · <Link href={DOI_URL} {...externalProps}>doi:10.1016/j.cub.2025.12.022</Link></span></Typography>
  <Typography component="p" variant="body2">The recognition worker includes adapted PoseSwin code from the Mathis Lab’s <Link href={SOURCE_URL} {...externalProps}>BrownBear_ReID repository</Link>. We gratefully acknowledge the authors and contributors who made this research and code available.</Typography>
  <Typography component="p" variant="caption" color="text.secondary">Only Bears is an independent application and is not presented as an official Mathis Lab, EPFL, or Alaska Pacific University project.</Typography>
 </div>;
}

export function ResearchCreditLinks(){
 return <span>Research foundation: <a href={PAPER_URL} {...externalProps}>Rosenberg et al. (2026)</a> · <a href={SOURCE_URL} {...externalProps}>BrownBear_ReID</a></span>;
}
