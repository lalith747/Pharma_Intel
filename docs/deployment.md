# Hosting PharmaIntel

## Recommended: Streamlit Community Cloud

PharmaIntel's interface is already a Streamlit application. Community Cloud
can deploy it directly from GitHub, including a private repository. Keep the
repository private: the app will inherit its visibility, and you can invite a
professor as a viewer by email. Private-app viewer access requires sign-in.
Community Cloud currently allows one private app per account/workspace, so
check that limit before creating another private app.

Deployment settings:

- Repository: `lalith747/Pharma_Intel`
- Branch: `main`
- Main file: `dashboard/app.py`
- Python: 3.12
- Dependencies: root `requirements.txt`
- Secrets: none for the packaged results explorer

The repository includes compressed, precomputed evidence, graph, and ranking
assets under `dashboard/data/`. The hosted app does **not** download model
weights or run transformer inference. It also displays a live PubMed literature
carousel; NCBI E-utilities responses are shared-cached server-side for six hours.
A feed outage does not prevent the saved dashboard results from loading. To
refresh the hosted research results after a new analysis, run:

```bash
python scripts/run_transformer_corpus_ner.py
python scripts/prepare_dashboard_assets.py
```

Then commit the updated `dashboard/data/` assets and push to `main`; Community
Cloud redeploys from the repository. Corpus and model inference remain a local
or Colab workflow.

## Why not Vercel for this app?

Vercel's Python runtime is designed for serverless functions. Streamlit runs a
long-lived Python web server with its own WebSocket/session model, so putting
the current app behind a serverless function is not a direct deployment. Vercel
could host a separately designed frontend and API, but that would mean
rewriting this Streamlit application. Community Cloud is a smaller, better-fit
deployment for the current project.

## API usage and credentials

| Component | Uses an API? | Credentials |
|---|---|---|
| PubMed retrieval | Yes: NCBI E-utilities via Biopython, during data acquisition | Set `NCBI_EMAIL`; `NCBI_API_KEY` is optional |
| Biomedical model | Public Hugging Face Hub download of the pinned checkpoint when not cached; inference is local PyTorch | No token for this public model |
| Hosted dashboard | Reads precomputed assets, NCBI PubMed updates, and the public FDA Drug Safety Communications page | None |
| OpenAI/LLM service | Not used | None |
| GitHub | Repository hosting and source control | GitHub login for maintainers/deployment |

The PubMed carousel sends only general clozapine/blood-cell search terms to NCBI. SocialPulse reads the public FDA Drug Safety Communications archive and filters its titles for clozapine/Clozaril. Neither feed transmits user input. Results are shared-cached for six hours. The FDA page contains its current archive listing and links to older archived communications. This source is official safety communication, not general news or individual adverse-event reports. PharmaIntel does not call the paid X API or scrape X.
Never
put NCBI keys, GitHub tokens, or other secrets in source control.
