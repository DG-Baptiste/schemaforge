# Evaluation datasets

The selected task is vacancy extraction. For larger experiments, download a
public labelled corpus outside the repository and keep it under `data/`:

- `conll2003` for entity extraction;
- `ai4privacy/pii-masking-200k` for personal-data extraction;
- `Babelscape/wikineural` for multilingual named entities.

The repository includes a small vacancy sample in `examples/vacancies.jsonl`
and `examples/vacancies_gold.jsonl`, so the CLI and evaluation workflow work
without registration or a large download.

