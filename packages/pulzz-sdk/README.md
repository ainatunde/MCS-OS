# Pulzz SDK for Python

The official Python client library for **Pulzz** ([pulzz.stream](https://pulzz.stream)), the African TV & FM broadcast intelligence, electronic program guide (EPG), and star rankings platform by Multimedia Cloud Solutions (MCS).

## Overview
Pulzz provides real-time broadcast schedules, 24h electronic programming guides, on-air tracking, star popularity rankings, carriage platform drift monitoring, and audience demand insights across 1,420+ African linear and digital feeds in Nigeria, Ghana, Kenya, and South Africa.

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
