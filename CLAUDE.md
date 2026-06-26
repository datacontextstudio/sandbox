# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Context

This is a sandbox/planning repository for **DataContext Studio** — a self-hosted RAG (Retrieval-Augmented Generation) platform. The repository currently contains an architecture diagram (`architecture.txt`) and is the starting point for building out this system.

## Intended Architecture

The system is designed as a set of horizontally-scalable layers, all containerized with Docker:

- **API Layer** — stateless FastAPI VMs behind a load balancer, exposed via a public load balancer
- **LLM Layer** — GPU VMs running vLLM, behind an internal load balancer
- **Embedding Layer** — CPU/GPU VMs running TEI (Text Embeddings Inference), behind an internal load balancer
- **Vector DB Layer** — Qdrant cluster (multi-node with persistent disk)
- **Ingestion Layer** — message queue (Redis or RabbitMQ) feeding Docker-based workers that parse docs (Docling), chunk them, embed them, and write to Qdrant
- **Storage Layer** — local disk object storage for raw documents before ingestion

## Launching Claude

```bash
./claude.sh   # runs: claude --dangerously-skip-permissions
```
