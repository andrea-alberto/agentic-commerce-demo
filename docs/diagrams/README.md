# Diagrams as Code — UCP Architecture on Google Cloud

This directory contains the **Diagrams as Code** implementation for the GCP UCP Merchant Middleware architecture described in [`docs/gcp-ucp-architecture.md`](../gcp-ucp-architecture.md).

It uses the [`diagrams`](https://diagrams.mingrammer.com/) Python library with official Google Cloud Platform vector icons.

---

## Files

- **`gcp_architecture.py`**: The Python script defining the cloud topology, services, clusters, and communication edges.
- **`requirements.txt`**: Python dependencies (`diagrams>=0.23.4`).
- **`../images/ucp_gcp_architecture.png`**: High-resolution rendered raster image.
- **`../images/ucp_gcp_architecture.svg`**: Scalable vector graphics export.
- **`../../.github/workflows/generate-diagrams.yml`**: GitHub Actions workflow for automatic regeneration on push.

---

## Local Execution

### Prerequisites

You must have **Graphviz** installed on your system.

#### Windows
```powershell
winget install Graphviz.Graphviz
# or with Chocolatey:
choco install graphviz
```

#### macOS
```bash
brew install graphviz
```

#### Ubuntu / Debian
```bash
sudo apt-get update && sudo apt-get install -y graphviz
```

### Running the Generator

Using `pip`:
```bash
pip install -r docs/diagrams/requirements.txt
python docs/diagrams/gcp_architecture.py
```

Or using `uv` (zero-install virtual environment):
```bash
uv run --with diagrams python docs/diagrams/gcp_architecture.py
```

The output will be placed in `docs/images/ucp_gcp_architecture.png` and `docs/images/ucp_gcp_architecture.svg`.

---

## Automated CI/CD (GitHub Actions)

Any commit that modifies `docs/diagrams/gcp_architecture.py` triggers `.github/workflows/generate-diagrams.yml`:
1. Boots an `ubuntu-latest` runner with Graphviz.
2. Installs Python dependencies.
3. Generates the latest `.png` and `.svg` files.
4. Automatically commits and pushes them back to `docs/images/` with `[skip ci]`.
