# Deprecated monolithic API

The active backend consists of two independent services:

- `services/planetary/` — port 8766.
- `services/earth/` — port 8767.

The static frontend is served on port 8765 by `./run_all.sh`.

This directory is retained only as a reference for the earlier prototype and its `GET /similar` endpoint. Do not use it for the TASI search or worldwide catalog. See the [current architecture](../README.md#architecture-and-api).
