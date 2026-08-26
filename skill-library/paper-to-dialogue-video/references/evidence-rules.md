# Evidence rules

## Evidence sheet

For every outward-facing claim, store:

- `claim`: concise Chinese wording;
- `kind`: `paper_fact`, `model_result`, `empirical_result`, `author_interpretation`, `critical_inference`, or `later_evidence`;
- `anchor`: page plus section, equation, figure, or table;
- `scope`: data, population, model parameters, or experimental condition;
- `boundary`: what the evidence does not establish.

## Claim language

- Say “模型在该参数下产生……” for simulation results.
- Say “样本中相关……” when the design does not identify causality.
- Say “作者认为……” for interpretation or policy discussion.
- Reserve causal verbs for randomized, quasi-experimental, or otherwise justified identification.
- Treat calibration and curve similarity as compatibility with a mechanism, not proof that the mechanism caused the observed trend.

## Visual evidence

- Prefer the paper homepage, workflow/model figure, principal result figure, and limitations text.
- Do not crop away axes, legends, uncertainty intervals, sample sizes, or condition labels needed to interpret a result.
- Add author, year, figure/table number, and crop status below every paper excerpt.
- Record the paper license. Use only necessary excerpts for commentary; do not present an edited source figure as an original unmodified figure.

## Final audit

- Check title, authors, venue, year, DOI, and publication status.
- Check all numbers, signs, units, thresholds, sample sizes, and parameter values.
- Search the final dialogue for stronger causal wording than the evidence sheet permits.
- Confirm that every scene source is human-readable and appears in `source-map.md`.
- Mention material post-publication corrections or criticism when they change how the headline result should be interpreted.
