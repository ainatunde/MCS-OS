# Pulzz SDK for Python

The official Python client library for **Pulzz** ([pulzz.stream](https://pulzz.stream)), the African Broadcast & Media Intelligence platform by Multimedia Cloud Solutions (MCS).

## Overview
Pulzz provides second-by-second acoustic watermarking, automated broadcast compliance verification, real-time television audience ratings, and deterministic SCTE-35 dynamic ad insertion (DAI) reconciliation across 1,420+ African linear and digital feeds.

## Installation
```bash
pip install pulzz-sdk
```

## Quick Start
```python
from pulzz import PulzzClient

client = PulzzClient(api_key="your-pulzz-api-key")

# Retrieve real-time broadcast schedules and ratings
ratings = client.get_ratings(channel="channels-tv", market="Lagos")
print(ratings)
```

## Support & Governance
* **Website:** [https://pulzz.stream](https://pulzz.stream)
* **Publisher:** Multimedia Cloud Solutions ([mcsolutions.ng](https://mcsolutions.ng))
* **Contact:** `pulzz@mcsolutions.ng`
* **Identity & Security:** `identities@mcsolutions.ng`
